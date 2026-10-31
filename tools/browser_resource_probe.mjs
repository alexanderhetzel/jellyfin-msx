// Own-tab, normal-navigation observer. All URLs, request IDs and bodies stay here.
import { Buffer } from "node:buffer";

const ORIGIN = /^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com$/;
const METHODS = ["Network.requestWillBeSent", "Network.responseReceived", "Network.loadingFinished", "Network.loadingFailed", "Network.requestServedFromCache"];
const BODY_LIMIT = 16384;
// Public, committed synthetic.mp4 prefix; never an operator media sample.
const ORIGINAL_PREFIX = Buffer.from("000000206674797069736f6d0000020069736f6d69736f32617663316d703431", "hex");
const PNG_PREFIX = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const CATEGORIES = new Set(["home", "browse", "detail", "poster", "resolver", "media"]);
const ROLES = new Set(["A", "B", "repaired-A"]);

function fail(code) { throw { probeCode: code }; }
function mime(value) {
  const normalized = typeof value === "string" ? value.split(";", 1)[0].trim().toLowerCase() : "";
  return ["application/json", "image/png", "video/mp4"].includes(normalized) ? normalized : "other";
}
function bodyBytes(value) {
  if (!value || typeof value.body !== "string" || typeof value.base64Encoded !== "boolean" || value.body.length > BODY_LIMIT * 2) fail("body-unavailable-or-large");
  if (value.base64Encoded && (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value.body))) fail("body-unavailable-or-large");
  const bytes = Buffer.from(value.body, value.base64Encoded ? "base64" : "utf8");
  if (value.base64Encoded && bytes.toString("base64") !== value.body) fail("body-unavailable-or-large");
  if (bytes.length > BODY_LIMIT) fail("body-unavailable-or-large");
  return bytes;
}
function rows(page) {
  if (!page || typeof page !== "object") fail("catalog-shape");
  return [...(Array.isArray(page.items) ? page.items : []), ...(Array.isArray(page.pages) ? page.pages.flatMap(p => Array.isArray(p.items) ? p.items : []) : [])];
}
function select(page, label) {
  const found = rows(page).filter(row => typeof row.title === "string" && row.title.startsWith(label));
  if (found.length !== 1) fail("catalog-selection");
  return found[0];
}

export async function createResourceProbe(tab, origin) {
  if (typeof origin !== "string" || !ORIGIN.test(origin)) fail("invalid-origin");
  const plans = new WeakMap();
  const authorities = new Set();
  const mediaAuthorities = new Set();
  const roles = new Set();
  let cdp;
  let attempted = false;
  let closed = false;
  const own = value => {
    let url;
    try { url = new URL(value); } catch { fail("invalid-resource-target"); }
    if (url.origin !== origin || url.username || url.password || url.hash) fail("invalid-resource-target");
    return url;
  };
  const currentOrigin = async () => {
    try { return new URL(await tab.url()).origin; } catch { return null; }
  };
  try {
    // The documented wrapper requires navigation BEFORE the first CDP command.
    await tab.goto(origin + "/__synthetic/ready");
    if (await currentOrigin() !== origin) fail("origin-binding-changed");
    const identity = await tab.playwright.evaluate(() => {
      try {
        const value = JSON.parse(document.querySelector("pre")?.innerText ?? document.body.innerText);
        return value.mode === "public-synthetic" && value.configured === true;
      } catch { return false; }
    });
    if (!identity) fail("synthetic-identity-unavailable");
    cdp = await tab.capabilities.get("cdp");
    attempted = true;
    // These are observation buffers, not cache/security/network-behavior overrides.
    // Platform permission checks still apply to THIS origin. No force/fallback.
    await cdp.send("Network.enable", { maxTotalBufferSize: 65536, maxResourceBufferSize: BODY_LIMIT, maxPostDataSize: 0 }, { timeoutMs: 2000 });
  } catch {
    if (attempted && cdp && await currentOrigin() === origin) {
      try { await cdp.send("Network.disable", {}, { timeoutMs: 1000 }); } catch { /* Owner closes tab. */ }
    }
    fail("observer-unavailable");
  }

  const observe = async (target, bodyMode) => {
    if (closed || await currentOrigin() !== origin) fail("origin-binding-changed");
    own(target);
    let page = await cdp.readEvents({ methods: METHODS, limit: 128, timeoutMs: 0 });
    if (!page || page.truncated || !Number.isInteger(page.cursor)) fail("events-unavailable");
    for (let drain = 0; page.hasMore && drain < 24; drain++) {
      const previous = page.cursor;
      page = await cdp.readEvents({ afterSequence: previous, methods: METHODS, limit: 128, timeoutMs: 0 });
      if (!page || page.truncated || !Number.isInteger(page.cursor) || page.cursor <= previous) fail("events-unavailable");
    }
    if (page.hasMore) fail("events-unavailable");
    let cursor = page.cursor;
    const requests = new Map();
    const cached = new Set();
    try { await tab.goto(target); } catch { /* HTTP errors still need fresh matching evidence. */ }
    if (await currentOrigin() !== origin) fail("origin-binding-changed");
    let quiet = 0;
    for (let batch = 0; batch < 24; batch++) {
      page = await cdp.readEvents({ afterSequence: cursor, methods: METHODS, limit: 128, timeoutMs: 250 });
      if (!page || page.truncated || !Array.isArray(page.events) || !Number.isInteger(page.cursor) || (page.hasMore && page.cursor <= cursor)) fail("events-unavailable");
      const previousCursor = cursor;
      if (page.cursor < cursor || page.events.length > 128) fail("events-unavailable");
      cursor = page.cursor;
      for (const event of page.events) {
        if (!Number.isInteger(event.sequence) || event.sequence <= previousCursor || event.sequence > cursor) fail("events-unavailable");
        const p = event.params ?? {};
        if (event.method === "Network.requestWillBeSent" && p.request?.url === target && p.type === "Document") {
          if (p.redirectResponse || p.request.method !== "GET" || typeof p.requestId !== "string" || p.requestId.length > 256) fail("redirect-or-method");
          if (requests.has(p.requestId) || requests.size >= 4) fail("ambiguous-request");
          requests.set(p.requestId, { response: null, finished: false, failed: false });
        }
        if (event.method === "Network.requestServedFromCache" && typeof p.requestId === "string") {
          if (cached.size >= 128) fail("events-unavailable");
          cached.add(p.requestId);
        }
        const request = requests.get(p.requestId);
        if (!request) continue;
        if (event.method === "Network.responseReceived") {
          if (p.response?.url !== target || !Number.isInteger(p.response.status) || p.response.status < 100 || p.response.status > 599) fail("response-mismatch");
          if (request.response) fail("ambiguous-request");
          request.response = { status: p.response.status, mimeType: p.response.mimeType, fromDiskCache: p.response.fromDiskCache, fromServiceWorker: p.response.fromServiceWorker, fromPrefetchCache: p.response.fromPrefetchCache };
        }
        if (event.method === "Network.loadingFinished") request.finished = true;
        if (event.method === "Network.loadingFailed") request.failed = true;
      }
      if (page.hasMore) continue; // Same filters/cursor; never treat evicted events as absence.
      if (requests.size > 1) fail("ambiguous-request");
      const entry = [...requests.entries()][0];
      if (!entry?.[1].response) continue;
      const [requestId, request] = entry;
      const response = request.response;
      const needBody = bodyMode === "always" || (bodyMode === "denial" && [401, 403].includes(response.status));
      // Missing freshness flags are unknown, not proof of a fresh response.
      if (cached.has(requestId) || response.fromDiskCache !== false || response.fromServiceWorker !== false || response.fromPrefetchCache !== false) fail("cached-or-unknown");
      if (needBody && (request.failed || !request.finished)) {
        if (request.failed) fail("body-unavailable-or-large");
        continue;
      }
      quiet = page.events.length ? 0 : quiet + 1;
      if (quiet < 2) continue;
      let bytes = null;
      if (needBody) bytes = bodyBytes(await cdp.send("Network.getResponseBody", { requestId }, { timeoutMs: 2000 }));
      return { http: response.status, mime: mime(response.mimeType), bytes };
    }
    fail("fresh-response-unavailable");
  };
  const portal = async target => {
    const response = await observe(target, "always");
    if (response.http !== 200 || response.mime !== "application/json") fail("catalog-response");
    let value;
    try { value = JSON.parse(response.bytes.toString("utf8")); } catch { fail("catalog-shape"); }
    return value;
  };
  const fixed = (role, category, response, portalStatus = null) => ({ role, category, http_status: response.http, portal_status: portalStatus, mime: response.mime, fresh: true });

  return {
    async capture(role, poster) {
      try {
        if (!ROLES.has(role) || roles.has(role)) fail("invalid-role");
        const image = own(poster);
        const match = image.pathname.match(/^(\/msx\/device\/[A-Za-z0-9_-]{43})\/image\/([a-f0-9]{32})$/);
        if (!match || image.search) fail("private-poster-unavailable");
        const prefix = match[1];
        if (authorities.has(prefix)) fail("authority-mismatch");
        const scoped = (value, endpoint, allowed) => {
          const url = own(value);
          if (url.pathname !== prefix + "/" + endpoint || [...url.searchParams.keys()].some(key => !allowed.includes(key) || url.searchParams.getAll(key).length !== 1)) fail("authority-mismatch");
          return url.href;
        };
        const home = origin + prefix + "/home.json";
        const homePage = await portal(home);
        if (homePage.headline !== "Jellyfin libraries") fail("catalog-shape");
        const browse = scoped(select(homePage, "Synthetic movies").action?.replace(/^content:/, ""), "browse.json", ["parent_id"]);
        if (new URL(browse).searchParams.get("parent_id") !== "2".repeat(32)) fail("authority-mismatch");
        const movie = select(await portal(browse), "Synthetic clip");
        if (own(movie.image).href !== image.href) fail("authority-mismatch");
        const detail = scoped(movie.action?.replace(/^content:/, ""), "detail.json", ["item_id"]);
        if (new URL(detail).searchParams.get("item_id") !== match[2]) fail("authority-mismatch");
        const play = select(await portal(detail), "Try original").action;
        if (typeof play !== "string" || !play.startsWith("video:resolve:")) fail("catalog-selection");
        const resolver = scoped(play.slice("video:resolve:".length), "play.json", ["item_id", "media_source_id", "force", "subtitle", "platform", "player"]);
        const resolverQuery = new URL(resolver).searchParams;
        const source = resolverQuery.get("media_source_id");
        if (resolverQuery.get("item_id") !== match[2] || !/^[a-f0-9]{32}$/.test(source ?? "") || resolverQuery.get("force") !== "false" || resolverQuery.get("subtitle") !== "-1") fail("authority-mismatch");
        const resolved = await portal(resolver);
        if (resolved.response?.status !== 200) fail("catalog-response");
        const media = own(resolved.response?.data?.url);
        const token = media.searchParams.get("ApiKey");
        const validMedia = media.pathname === `/jellyfin/Videos/${match[2]}/stream.mp4`
          && [...media.searchParams.keys()].every(key => ["ApiKey", "MediaSourceId", "Static", "DeviceId", "PlaySessionId"].includes(key) && media.searchParams.getAll(key).length === 1)
          && media.searchParams.get("MediaSourceId") === source
          && media.searchParams.get("Static") === "true"
          && /^[a-f0-9]{32}$/.test(media.searchParams.get("DeviceId") ?? "")
          && /^[a-f0-9]{32}$/.test(media.searchParams.get("PlaySessionId") ?? "")
          && /^[A-Za-z0-9_-]{16,512}$/.test(token ?? "")
          && !mediaAuthorities.has(token);
        if (!validMedia) fail("invalid-resource-target");
        const handle = Object.freeze({ role }); // Serializes only the role, never authority.
        plans.set(handle, Object.freeze({ home, browse, detail, poster: image.href, resolver, media: media.href }));
        roles.add(role);
        authorities.add(prefix);
        mediaAuthorities.add(token);
        return handle;
      } catch { fail("capture-unavailable"); }
    },
    async check(handle, category, expectation, substitute = null) {
      if (!CATEGORIES.has(category) || !["served", "denied"].includes(expectation)) return { ok: false, problem: "invalid-probe" };
      const plan = plans.get(substitute ?? handle);
      if (!plan || !plans.has(handle)) return { ok: false, problem: "invalid-handle" };
      try {
        const isPortal = ["home", "browse", "detail", "resolver"].includes(category);
        const response = await observe(plan[category], isPortal ? "always" : expectation === "denied" ? "denial" : "none");
        let portalStatus = null;
        let noData = false;
        let healthy = false;
        if (isPortal) {
          if (response.mime !== "application/json") fail("protocol-shape");
          let value;
          try { value = JSON.parse(response.bytes.toString("utf8")); } catch { fail("protocol-shape"); }
          portalStatus = Number.isInteger(value?.response?.status) ? value.response.status : null;
          noData = Object.keys(value).length === 1 && value.response?.data === null && Object.keys(value.response).every(key => ["status", "text", "message", "data"].includes(key));
          healthy = category === "resolver" ? portalStatus === 200 && typeof value.response?.data?.url === "string" : portalStatus === null && typeof value.headline === "string" && (Array.isArray(value.items) || Array.isArray(value.pages));
        }
        const observation = fixed(handle.role, category, response, portalStatus);
        if (expectation === "served") {
          const ok = isPortal ? response.http === 200 && healthy : [200, 206].includes(response.http) && response.mime === (category === "poster" ? "image/png" : "video/mp4");
          return { ...observation, ok, problem: ok ? null : "not-served" };
        }
        const rawDenial = [401, 403].includes(response.http) && (!isPortal || (noData && [401, 403].includes(portalStatus)));
        const wrappedDenial = isPortal && response.http === 200 && [401, 403].includes(portalStatus) && noData;
        // Native binary at a denial status is not accepted as revoked data.
        const looksBinary = response.bytes?.includes(ORIGINAL_PREFIX) || response.bytes?.includes(PNG_PREFIX);
        const ok = (rawDenial || wrappedDenial) && !looksBinary;
        return { ...observation, ok, problem: ok ? null : "not-denied" };
      } catch {
        return { role: handle.role, category, ok: false, problem: "probe-unavailable" };
      }
    },
    async close() {
      closed = true;
      if (await currentOrigin() !== origin) return false; // Owner closes tab, never send on a new origin.
      try { await cdp.send("Network.disable", {}, { timeoutMs: 1000 }); return true; } catch { return false; }
    },
  };
}
