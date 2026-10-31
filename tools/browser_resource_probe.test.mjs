import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import test from "node:test";
import { captureFailure, createResourceProbe } from "./browser_resource_probe.mjs";
import { checkSessions, collectRenderedImages, disconnectSession, inspectOwnPosters, selectOwnPoster } from "./browser_session_check.mjs";

// Non-live authorities made entirely in this mocked test; no browser or HTTP.
const origin = "https://synthetic-only.trycloudflare.com";
const item = "3".repeat(32);
const source = "5".repeat(32);
function fixture() {
  let current;
  let sequence = 0;
  let events = [];
  let responseBody;
  let revoked = false;
  let transform = value => value;
  let bodyOverride;
  let bodyCalls = 0;
  let commands = [];
  const prefix = letter => origin + "/msx/device/" + letter.repeat(43);
  const poster = letter => prefix(letter) + "/image/" + item;
  // Full production playback.py query shape, including its session/device pins.
  const media = letter => `${origin}/jellyfin/Videos/${item}/stream.mp4?Static=true&MediaSourceId=${source}&DeviceId=${"6".repeat(32)}&PlaySessionId=${"7".repeat(32)}&ApiKey=${letter.repeat(32)}`;
  const resolver = letter => `${prefix(letter)}/play.json?item_id=${item}&media_source_id=${source}&force=false&subtitle=-1&platform={PLATFORM}&player={PLAYER}`;
  const route = url => {
    const letter = url.includes("/msx/device/") ? new URL(url).pathname.split("/")[3][0] : new URL(url).searchParams.get("ApiKey")[0];
    const denied = revoked && letter === "A";
    const binary = /\/image\/|stream.mp4/.test(url);
    if (denied) return binary ? { status: 401, mimeType: "text/plain", body: "" } : { status: 200, mimeType: "application/json", body: JSON.stringify({ response: { status: 401, text: "Error", message: "Session expired", data: null } }) };
    if (url.includes("home.json")) return json({ headline: "Jellyfin libraries", items: [{ title: "Synthetic movies", action: "content:" + prefix(letter) + "/browse.json?parent_id=" + "2".repeat(32) }] });
    if (url.includes("browse.json")) return json({ headline: "Library", items: [{ title: "Synthetic clip", image: poster(letter), action: "content:" + prefix(letter) + "/detail.json?item_id=" + item }] });
    if (url.includes("detail.json")) return json({ headline: "Synthetic clip", items: [{ title: "Try original (TV unverified)", action: "video:resolve:" + resolver(letter) }] });
    if (url.includes("play.json")) return json({ response: { status: 200, text: "OK", data: { url: media(letter) } } });
    return { status: 200, mimeType: url.includes("/image/") ? "image/png" : "video/mp4", body: "not-read" };
  };
  const json = value => ({ status: 200, mimeType: "application/json", body: JSON.stringify(value) });
  const cdp = {
    async send(method) {
      commands.push(method);
      if (method === "Network.getResponseBody") { bodyCalls++; return (typeof bodyOverride === "function" ? bodyOverride(responseBody, current) : bodyOverride) ?? { body: responseBody, base64Encoded: false }; }
      return {};
    },
    async readEvents(options) {
      if (options.afterSequence === undefined) return { cursor: sequence, events: [], hasMore: false, truncated: false };
      const found = events.filter(event => event.sequence > options.afterSequence);
      return { cursor: sequence, events: found, hasMore: false, truncated: false };
    },
  };
  const tab = {
    async url() { return current; },
    async goto(url) {
      current = url;
      if (url.endsWith("/__synthetic/ready")) return;
      const response = route(url);
      responseBody = response.body;
      const requestId = "request-" + sequence;
      const value = [
        { method: "Network.requestWillBeSent", params: { requestId, type: "Document", request: { method: "GET", url } } },
        { method: "Network.responseReceived", params: { requestId, response: { url, status: response.status, mimeType: response.mimeType, fromDiskCache: false, fromServiceWorker: false, fromPrefetchCache: false } } },
        { method: "Network.loadingFinished", params: { requestId } },
      ];
      events = transform(value).map(event => ({ ...event, sequence: ++sequence }));
    },
    playwright: { evaluate: async () => true },
    capabilities: { get: async () => cdp },
  };
  return { tab, cdp, poster, prefix, media, commands, revoke: () => { revoked = true; }, transform: fn => { transform = fn; }, body: value => { bodyOverride = value; }, bodyCalls: () => bodyCalls, foreign: () => { current = "https://foreign.invalid/"; } };
}

test("actual HTTP and wrapped portal denial remain separate; plans serialize only roles", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const a = await probe.capture("A", f.poster("A"));
  assert.equal(JSON.stringify(a), '{"role":"A"}');
  assert.equal((await probe.check(a, "home", "served")).ok, true);
  f.revoke();
  const home = await probe.check(a, "home", "denied");
  assert.deepEqual([home.ok, home.http_status, home.portal_status], [true, 200, 401]);
  const native = await probe.check(a, "media", "denied");
  assert.deepEqual([native.ok, native.http_status, native.portal_status], [true, 401, null]);
  assert.doesNotMatch(JSON.stringify([home, native, a]), /trycloudflare|ApiKey|Session expired|\/msx\//);
});

test("authorized B media makes the unchanged A denial predicate fail at actual 200 without reading video", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const a = await probe.capture("A", f.poster("A"));
  const b = await probe.capture("B", f.poster("B"));
  f.revoke();
  const before = f.bodyCalls();
  f.body({ body: "x".repeat(100000), base64Encoded: false });
  const result = await probe.check(a, "media", "denied", b);
  assert.deepEqual([result.ok, result.http_status, result.problem], [false, 200, "not-denied"]);
  assert.equal(f.bodyCalls(), before);
});

for (const label of ["disk", "worker", "prefetch", "missing", "cache-event", "redirect", "wrong-url", "duplicate", "failed-body", "missing-request"]) test("rejects " + label + " evidence", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const a = await probe.capture("A", f.poster("A"));
  f.revoke();
  f.transform(events => {
    const response = events[1].params.response;
    if (label === "disk") response.fromDiskCache = true;
    if (label === "worker") response.fromServiceWorker = true;
    if (label === "prefetch") response.fromPrefetchCache = true;
    if (label === "missing") delete response.fromDiskCache;
    if (label === "cache-event") events.push({ method: "Network.requestServedFromCache", params: { requestId: events[0].params.requestId } });
    if (label === "redirect") events[0].params.redirectResponse = {};
    if (label === "wrong-url") response.url += "wrong";
    if (label === "duplicate") events.push(events[0]);
    if (label === "failed-body") events[2].method = "Network.loadingFailed";
    if (label === "missing-request") return events.slice(1);
    return events;
  });
  assert.equal((await probe.check(a, "media", "denied")).ok, false);
});

for (const label of ["truncated", "stale", "nonprogress", "oversized-events", "body-refused", "body-large", "base64-invalid", "base64-noncanonical"]) test("unknown observation fails closed: " + label, async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const a = await probe.capture("A", f.poster("A"));
  f.revoke();
  const read = f.cdp.readEvents;
  f.cdp.readEvents = async options => {
    const page = await read(options);
    if (label === "truncated") page.truncated = true;
    if (options.afterSequence !== undefined) {
      if (label === "stale" && page.events.length) page.events[0].sequence = options.afterSequence;
      if (label === "nonprogress") { page.hasMore = true; page.cursor = options.afterSequence; }
      if (label === "oversized-events") page.events = Array(129).fill(page.events[0]);
    }
    return page;
  };
  if (label === "body-refused") {
    const send = f.cdp.send;
    f.cdp.send = async method => { if (method === "Network.getResponseBody") throw new Error("ApiKey=DO-NOT-EMIT"); return send(method); };
  }
  if (label === "body-large") f.body({ body: "x".repeat(16385), base64Encoded: false });
  if (label === "base64-invalid") f.body({ body: "!!!!", base64Encoded: true });
  if (label === "base64-noncanonical") f.body({ body: "YR==", base64Encoded: true });
  const result = await probe.check(a, "media", "denied");
  assert.equal(result.ok, false);
  assert.doesNotMatch(JSON.stringify(result), /DO-NOT-EMIT|ApiKey/);
});

test("denial bodies containing original media or PNG bytes anywhere fail", async () => {
  const prefix = readFileSync(new URL("../tests/fixtures/msx-public/synthetic.mp4", import.meta.url)).subarray(0, 32);
  for (const bytes of [prefix, Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])]) {
    const f = fixture();
    const probe = await createResourceProbe(f.tab, origin);
    const a = await probe.capture("A", f.poster("A"));
    f.revoke();
    f.body({ body: Buffer.concat([Buffer.from("denied-but-leaked:"), bytes]).toString("base64"), base64Encoded: true });
    assert.equal((await probe.check(a, "media", "denied")).problem, "not-denied");
  }
});

test("data-bearing wrapped denial and malformed successful portal JSON cannot pass", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const a = await probe.capture("A", f.poster("A"));
  for (const value of [{ response: { status: 401, data: null, private: "payload" } }, { response: { status: 401, data: "payload" } }, {}]) {
    f.body({ body: JSON.stringify(value), base64Encoded: false });
    assert.equal((await probe.check(a, "home", "denied")).ok, false);
    assert.equal((await probe.check(a, "home", "served")).ok, false);
  }
});

test("only own distinct capabilities can be captured; raw capture exceptions are withheld", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  await probe.capture("A", f.poster("A"));
  for (const [role, url] of [["B", f.poster("A")], ["B", origin + "/msx/pair/image/" + "C".repeat(43) + ".png"], ["B", "https://foreign.invalid/secret"]]) {
    await assert.rejects(probe.capture(role, url), value => value.probeCode === "capture-unavailable" && value.captureStage === "poster-target" && !JSON.stringify(value).includes("https://"));
  }
  f.foreign();
  const before = f.commands.length;
  assert.equal(await probe.close(), false);
  assert.equal(f.commands.length, before);
});

test("per-origin observer permission refusal is fixed, never bypassed", async () => {
  const f = fixture();
  f.cdp.send = async () => { throw new Error("permission required: private URL"); };
  await assert.rejects(createResourceProbe(f.tab, origin), value => JSON.stringify(value) === '{"probeCode":"observer-unavailable"}');
});

for (const label of ["missing-device", "missing-session", "wrong-item", "wrong-source", "duplicate-token", "foreign"]) test("capture rejects altered native contract: " + label, async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  f.body((body, current) => {
    if (!current.includes("play.json")) return;
    const value = JSON.parse(body);
    const url = new URL(value.response.data.url);
    if (label === "missing-device") url.searchParams.delete("DeviceId");
    if (label === "missing-session") url.searchParams.delete("PlaySessionId");
    if (label === "wrong-item") url.pathname = url.pathname.replace(item, "4".repeat(32));
    if (label === "wrong-source") url.searchParams.set("MediaSourceId", "8".repeat(32));
    if (label === "duplicate-token") url.searchParams.append("ApiKey", "Z".repeat(32));
    if (label === "foreign") url.hostname = "foreign.invalid";
    value.response.data.url = url.href;
    return { body: JSON.stringify(value), base64Encoded: false };
  });
  await assert.rejects(probe.capture("A", f.poster("A")), value => value.probeCode === "capture-unavailable");
});

test("matching events may span advancing pages; same cursor filters are retained", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  const read = f.cdp.readEvents;
  let methods;
  f.cdp.readEvents = async options => {
    methods ??= options.methods;
    assert.deepEqual(options.methods, methods);
    const page = await read(options);
    if (options.afterSequence !== undefined && page.events.length > 1) return { ...page, cursor: page.events[0].sequence, events: page.events.slice(0, 1), hasMore: true };
    return page;
  };
  const a = await probe.capture("A", f.poster("A"));
  f.revoke();
  assert.equal((await probe.check(a, "media", "denied")).ok, true);
});

test("entry rejects arbitrary destinations and closes owned tabs on observer failure", async () => {
  assert.equal((await checkSessions({ origin: "https://operator.invalid", newTab: () => assert.fail() })).stage, "invalid-options");
  let closed = 0;
  const result = await checkSessions({ origin, newTab: async () => ({ goto: async () => { throw new Error("private URL"); }, close: async () => { closed++; } }) });
  assert.equal(result.stage, "scoped-observer-availability");
  assert.equal(closed, 1);
  assert.doesNotMatch(JSON.stringify(result), /private URL/);
});

for (const stage of ["home-response", "home-shape", "browse-target", "browse-response", "movie-selection", "detail-target", "detail-response", "resolver-target", "resolver-response", "native-target"]) test("fixed capture substage identifies " + stage + " without raw values", async () => {
  const f = fixture();
  const probe = await createResourceProbe(f.tab, origin);
  f.body((body, current) => {
    const value = JSON.parse(body);
    const at = endpoint => current.includes(endpoint + ".json");
    if ((stage === "home-response" && at("home")) || (stage === "browse-response" && at("browse")) || (stage === "detail-response" && at("detail"))) return { body: "not JSON: private-secret", base64Encoded: false };
    if (stage === "home-shape" && at("home")) value.headline = "unexpected private-secret";
    if (stage === "browse-target" && at("home")) value.items[0].action = "content:https://foreign.invalid/private-secret";
    if (stage === "movie-selection" && at("browse")) value.items = [];
    if (stage === "detail-target" && at("browse")) value.items[0].action = "content:https://foreign.invalid/private-secret";
    if (stage === "resolver-target" && at("detail")) value.items = [];
    if (stage === "resolver-response" && at("play")) value.response.status = 401;
    if (stage === "native-target" && at("play")) value.response.data.url = "https://foreign.invalid/private-secret";
    return { body: JSON.stringify(value), base64Encoded: false };
  });
  await assert.rejects(probe.capture("A", f.poster("A")), error => {
    const result = captureFailure(error);
    assert.equal(result.stage, stage);
    assert.doesNotMatch(JSON.stringify(result), /private-secret|foreign|https:/);
    return true;
  });
});

test("external or forged capture diagnostics cannot serialize arbitrary text", () => {
  assert.deepEqual(captureFailure(new Error("private-secret")), { stage: "unknown", problem: "unknown" });
  assert.deepEqual(captureFailure({ captureStage: "https://private-secret", problem: "private-secret" }), { stage: "unknown", problem: "unknown" });
});

function attributeTab({ images = [], styles = [] } = {}) {
  const reads = [];
  return {
    reads,
    playwright: { locator: selector => {
      assert.ok(["img", '[style*="url(" i]'].includes(selector));
      const items = selector === "img" ? images : styles;
      return {
        count: async () => items.length,
        all: async () => items.map(value => ({ getAttribute: async (name, options) => {
          assert.equal(name, selector === "img" ? "src" : "style");
          assert.equal(options.timeoutMs, 2000);
          reads.push(name);
          return value;
        } })),
      };
    } },
  };
}

test("documented attributes work without DOM constructor/tagName/src proxy globals", async () => {
  const f = fixture();
  const image = { getAttribute: name => name === "src" ? f.poster("A") : null };
  const context = { document: { querySelectorAll: () => [image] } };
  assert.throws(() => vm.runInNewContext("document.querySelectorAll('*')[0] instanceof HTMLImageElement", context), /HTMLImageElement/);
  assert.equal(vm.runInNewContext("document.querySelectorAll('*')[0].tagName === 'IMG'", context), false);
  const tab = attributeTab({ images: [image.getAttribute("src")], styles: [`background-image: url("${f.poster("A")}")`] });
  const result = await collectRenderedImages(tab);
  assert.equal(selectOwnPoster(origin, result.images), f.poster("A"));
  assert.deepEqual(result.counts, { img_elements: 1, background_elements: 1, background_unavailable: 0 });
  assert.deepEqual(tab.reads, ["src", "style"]);
  // Public adapter counterexample only: original live cause remains unknown.
});

test("DOM bounds and absent/ambiguous/QR/foreign poster selections fail closed", async () => {
  const f = fixture();
  for (const values of [Array(129).fill(f.poster("A")), ["x".repeat(4097)]]) assert.equal(await collectRenderedImages(attributeTab({ images: values })), null);
  for (const values of [null, [], [f.poster("A"), f.poster("B")], [origin + "/msx/pair/image/fake.png"], [f.poster("A").replace(origin, "https://foreign.invalid")], [f.poster("A").replace("https://", "https://user:pass@")]]) assert.equal(selectOwnPoster(origin, values), null);
});

test("standard single CSS URL parsing preserves strict targets and ignores unsupported values", async () => {
  const f = fixture();
  for (const style of [`background-image: url( '${f.poster("A")}' ) !important`, `color:red; BACKGROUND:URL(${f.poster("A")});opacity:1`]) {
    const result = await collectRenderedImages(attributeTab({ styles: [style] }));
    assert.equal(selectOwnPoster(origin, result.images), f.poster("A"));
  }
  for (const style of [`content: url("${f.poster("A")}")`, `background-image: "text url(${f.poster("A")})"`, `background-image:url("${f.poster("A")}"),url("${f.poster("B")}")`, `background:url("${f.poster("A")}") center / cover`, `background-image: image-set(url("${f.poster("A")}") 1x)`]) {
    const result = await collectRenderedImages(attributeTab({ styles: [style] }));
    assert.deepEqual(result.images, []);
  }
});

test("overridden or competing background declarations cannot expose a selected authority", async () => {
  const f = fixture();
  for (const style of [`background-image:url("${f.poster("A")}");background-image:none`, `background:url("${f.poster("A")}") !important;background-image:url("${f.poster("B")}")`, `background-image:url("${f.poster("A")}");background: red`, `background:none;background-image:url("${f.poster("A")}")`, `background-image:url("${f.poster("A")}");background-image:image-set(url("${f.poster("B")}") 1x)`, `background-image:url("${f.poster("A")}");/**/background-image:none`, `background-image:url("${f.poster("A")}");back\\67round-image:none`, `background-image:url("${f.poster("A")}");all:unset`]) {
    const result = await collectRenderedImages(attributeTab({ styles: [style] }));
    assert.deepEqual(result.images, []);
    assert.equal(result.counts.background_unavailable, 1);
    assert.equal(inspectOwnPosters(origin, result.images).summary.status, "unavailable");
  }
});

test("only finite rejection counts escape selection, never malformed attribute values", () => {
  const f = fixture();
  const images = ["blob:https://private-secret.invalid/id", "data:image/png,private-secret", "https://foreign.invalid/private-secret", origin + "/msx/pair/image/private-secret.png", f.poster("A") + "?private-secret", f.poster("A") + "#private-secret", f.poster("A").replace("/msx/", "/before/../msx/"), f.poster("A").replace(item, "4".repeat(32)), "private-secret", f.poster("A"), f.poster("A")];
  const selected = inspectOwnPosters(origin, images);
  assert.equal(selected.poster, f.poster("A"));
  assert.deepEqual(selected.summary, { status: "selected", supplied: 11, transformed: 2, foreign: 1, pending_grant: 1, decorated: 2, noncanonical: 1, wrong_shape_or_item: 2, exact: 2, distinct: 1 });
  assert.doesNotMatch(JSON.stringify(selected.summary), /private-secret|https|ApiKey|333333/);
  assert.equal(inspectOwnPosters(origin, []).summary.status, "unavailable");
  assert.equal(inspectOwnPosters(origin, [f.poster("A"), f.poster("B")]).summary.status, "ambiguous");
  assert.equal(inspectOwnPosters(origin, ["x".repeat(4097)]).summary.status, "invalid");
  for (const value of ["blob:https://private-secret.invalid/id", f.poster("A") + "?any", f.poster("A") + "#any", f.poster("A") + "?", f.poster("A") + "#"]) assert.equal(inspectOwnPosters(origin, [value]).poster, null);
});

test("changing or malformed locator groups cannot produce an authority", async () => {
  for (const count of [-1, 129, 0.5, "1", 1]) {
    const tab = { playwright: { locator: () => ({ count: async () => count, all: async () => [] }) } };
    assert.equal(await collectRenderedImages(tab), null);
  }
  const tab = attributeTab({ images: [null, ""] });
  assert.deepEqual((await collectRenderedImages(tab)).images, []);
});

test("one stalled attribute lookup times out without issuing another read", async () => {
  let countCalls = 0;
  let allCalls = 0;
  const tab = { playwright: { locator: () => ({ count: () => { countCalls++; return new Promise(() => {}); }, all: async () => { allCalls++; return []; } }) } };
  assert.equal(await collectRenderedImages(tab), null);
  assert.equal(countCalls, 1);
  assert.equal(allCalls, 0);
});

function catalogSession() {
  let page = "catalog";
  const actions = [];
  const locator = pattern => {
    const text = String(pattern);
    const name = text.includes("Confirm disconnect") ? "confirm" : text.includes("Disconnect TV") ? "disconnect" : text === "Libraries" ? "libraries" : text.includes("Pair again") ? "pair-again" : text.includes("Disconnected") ? "disconnected" : "other";
    const visible = () => name === "libraries" ? page === "catalog" : name === "disconnect" ? page === "home" : name === "confirm" ? page === "confirm" : ["pair-again", "disconnected"].includes(name) ? page === "disconnected" : true;
    return {
      waitFor: async () => { if (!visible()) throw new Error("private-secret"); },
      click: async () => {
        if (!visible()) throw new Error("private-secret");
        actions.push(name);
        if (name === "libraries") page = "home";
        if (name === "disconnect") page = "confirm";
        if (name === "confirm") page = "disconnected";
      },
    };
  };
  return { session: { authenticated: true, msx: { playwright: { getByText: locator } } }, actions, unavailable: () => { page = "unavailable"; } };
}

test("capture-failure cleanup must navigate visible Libraries before confirmed Disconnect", async () => {
  const f = catalogSession();
  await assert.rejects(f.session.msx.playwright.getByText(/Disconnect TV/i).click()); // Old home-only cleanup fails in this state.
  assert.equal(f.session.authenticated, true);
  await disconnectSession(f.session);
  assert.deepEqual(f.actions, ["libraries", "disconnect", "confirm"]);
  assert.equal(f.session.authenticated, false);
});

test("missing Libraries and Disconnect cannot manufacture cleanup success", async () => {
  const f = catalogSession();
  f.unavailable();
  await assert.rejects(disconnectSession(f.session));
  assert.deepEqual(f.actions, []);
  assert.equal(f.session.authenticated, true);
});

for (const mode of ["DOM", "selection", "capture"]) test("entry preserves fixed " + mode + " failure and still cleans catalog session", async () => {
  const f = fixture();
  const ui = catalogSession();
  let closed = 0;
  const msx = { ...ui.session.msx, goto: async () => {}, close: async () => { closed++; } };
  msx.playwright.evaluate = async fn => {
    if (fn.name === "readPairingCode") return "12345678"; // Non-live mocked form value.
    assert.fail("undocumented DOM evaluation");
  };
  msx.playwright.locator = mode === "DOM" ? () => { throw new Error("https://private-secret.invalid/"); } : attributeTab({ images: mode === "selection" ? [] : [f.poster("A")] }).playwright.locator;
  const companion = { goto: async () => {}, close: async () => { closed++; }, playwright: { getByText: () => ({ waitFor: async () => {} }), getByLabel: () => ({ fill: async () => {} }), getByRole: () => ({ click: async () => {} }) } };
  f.tab.close = async () => { closed++; };
  if (mode === "capture") f.body({ body: "https://private-secret.invalid/", base64Encoded: false });
  const queue = [f.tab, msx, companion];
  const result = await checkSessions({ origin, newTab: async () => queue.shift() });
  const expected = { DOM: "A-poster-DOM-collection", selection: "A-poster-target-selection", capture: "A-capture-home-response" };
  assert.equal(result.stage, expected[mode]);
  assert.equal(result.status, "failed");
  assert.equal(result.browser_verified, false);
  assert.equal(closed, 3);
  assert.deepEqual(ui.actions.slice(-3), ["libraries", "disconnect", "confirm"]);
  assert.doesNotMatch(JSON.stringify(result), /private-secret|trycloudflare|12345678|ApiKey/);
});
