// Source-only entry until an exclusive browser/relay slot is explicitly granted.
import { readPairingCode } from "./browser_pairing_check.mjs";
import { captureFailure, createResourceProbe } from "./browser_resource_probe.mjs";

const ORIGIN = /^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com$/;
const CATEGORIES = ["home", "browse", "detail", "poster", "resolver", "media"];

// Only documented locator/attribute reads; no DOM proxy properties or globals.
export async function collectRenderedImages(msx) {
  const deadline = Date.now() + 15000;
  const read = async operation => {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw null;
    let timer;
    try {
      return await Promise.race([operation(), new Promise((_, reject) => { timer = setTimeout(() => reject(null), Math.min(2000, remaining)); })]);
    } finally { clearTimeout(timer); }
  };
  try {
  const values = [];
  const counts = { img_elements: 0, background_elements: 0, background_unavailable: 0 };
  for (const [selector, attribute, key] of [["img", "src", "img_elements"], ['[style*="url(" i]', "style", "background_elements"]]) {
    const group = msx.playwright.locator(selector);
    const count = await read(() => group.count());
    if (!Number.isInteger(count) || count < 0 || count > 128) return null;
    const elements = await read(() => group.all());
    if (elements.length !== count) return null; // A changing DOM is unknown.
    counts[key] = count;
    for (const element of elements) {
      const value = await read(() => element.getAttribute(attribute, { timeoutMs: 2000 }));
      if (value === null || value === "") continue;
      if (typeof value !== "string" || value.length > 4096) return null;
      if (attribute === "src") values.push(value);
      else {
        // Parse only ordinary inline background declarations. No vendor data/cache.
        if (value.includes("\\") || value.includes("/*") || value.includes("*/") || /(?:^|;)\s*all\s*:/i.test(value)) { counts.background_unavailable++; continue; }
        const declarations = value.split(";").filter(part => /^\s*background(?:-image)?\s*:/i.test(part));
        if (declarations.length === 0) continue;
        // Do not guess CSS cascade or select a URL an overriding value hides.
        if (declarations.length !== 1) { counts.background_unavailable++; continue; }
        const match = declarations[0].match(/^\s*background(?:-image)?\s*:\s*url\(\s*(?:"([^"\\]*)"|'([^'\\]*)'|([^()'"\\\s]+))\s*\)\s*(?:!important)?\s*$/i);
        if (match) values.push(match[1] ?? match[2] ?? match[3]);
        else counts.background_unavailable++;
      }
      if (values.length > 128) return null;
    }
  }
  return { images: values, counts }; // Private values never enter the report.
  } catch { return null; } // No new read follows a timeout/refusal; owner closes tab.
}

export function inspectOwnPosters(origin, images) {
  const counts = { supplied: 0, transformed: 0, foreign: 0, pending_grant: 0, decorated: 0, noncanonical: 0, wrong_shape_or_item: 0, exact: 0, distinct: 0 };
  if (!ORIGIN.test(origin ?? "") || !Array.isArray(images) || images.length > 128 || images.some(value => typeof value !== "string" || value.length > 4096)) return { poster: null, summary: { status: "invalid", ...counts } };
  const candidates = new Set();
  counts.supplied = images.length;
  for (const value of images) {
    try {
      if (/^(?:blob|data):/i.test(value)) { counts.transformed++; continue; }
      const url = new URL(value);
      if (url.origin !== origin) { counts.foreign++; continue; }
      if (url.pathname.startsWith("/msx/pair/image/")) { counts.pending_grant++; continue; }
      if (url.username || url.password || value.includes("?") || value.includes("#")) { counts.decorated++; continue; }
      if (value !== url.href || /[\\\x00-\x20]/.test(value)) { counts.noncanonical++; continue; }
      // Exact public baseline MOVIE ID; no rewritten URLs or guessed authority.
      if (!/^\/msx\/device\/[A-Za-z0-9_-]{43}\/image\/33333333333333333333333333333333$/.test(url.pathname)) { counts.wrong_shape_or_item++; continue; }
      counts.exact++;
      candidates.add(value);
    } catch { counts.wrong_shape_or_item++; }
  }
  counts.distinct = candidates.size;
  return { poster: candidates.size === 1 ? [...candidates][0] : null, summary: { status: candidates.size === 1 ? "selected" : candidates.size ? "ambiguous" : "unavailable", ...counts } };
}

export function selectOwnPoster(origin, images) { return inspectOwnPosters(origin, images).poster; }

export async function disconnectSession(session) {
  const visible = async pattern => session.msx.playwright.getByText(pattern).waitFor({ state: "visible", timeoutMs: 15000 });
  const available = async locator => {
    try { await locator.waitFor({ state: "visible", timeoutMs: 500 }); return true; }
    catch { return false; }
  };
  const disconnect = session.msx.playwright.getByText(/Disconnect TV/i);
  if (!await available(disconnect)) {
    const libraries = session.msx.playwright.getByText("Libraries", { exact: true });
    if (!await available(libraries)) throw null;
    await libraries.click();
    await visible(/Disconnect TV/i);
  }
  await disconnect.click();
  await visible(/Confirm disconnect/i);
  await session.msx.playwright.getByText(/Confirm disconnect/i).click();
  await visible(/Pair again/i);
  await visible(/Disconnected/i);
  session.authenticated = false;
}

export async function checkSessions({ origin, newTab, fault = "none" } = {}) {
  const report = { status: "failed", stage: "invalid-options", fault: ["none", "authorized-target"].includes(fault) ? fault : "invalid", category: "hosted-session-authority", checks: [], observations: [], browser_verified: false, device_verified: false };
  report.positive_control_target = fault === "authorized-target" ? "authorized-B-native-media" : null;
  if (typeof origin !== "string" || !ORIGIN.test(origin) || !["none", "authorized-target"].includes(fault)) return report;
  if (typeof newTab !== "function") return { ...report, stage: "browser-connector-required" };
  const tabs = [];
  const sessions = [];
  let probe;
  const open = async url => {
    const tab = await newTab(); // Blank creation avoids automatic QR/private snapshots.
    tabs.push(tab);
    await tab.goto(url);
    return tab;
  };
  const visible = async (tab, pattern) => tab.playwright.getByText(pattern).waitFor({ state: "visible", timeoutMs: 15000 });
  const pair = async (role, existing = null) => {
    report.stage = role + "-normal-pairing";
    const start = new URL("https://msx.benzac.de/");
    start.searchParams.set("start", "content:" + origin + "/msx/pair.json");
    for (const [key, value] of Object.entries({ input: "2", init: "1", suspend: "0", animate: "0" })) start.searchParams.set(key, value);
    const msx = existing?.msx ?? await open(start.href);
    if (existing) await msx.playwright.getByText(/Pair again/i).click();
    await visible(msx, /^[0-9]{4}[ \u00a0]+[0-9]{4}$/);
    const code = await msx.playwright.evaluate(readPairingCode);
    if (!code) throw null;
    const companion = await open(origin + "/pair");
    const fill = async (name, value) => companion.playwright.getByLabel(name, { exact: true }).fill(value);
    const click = async name => companion.playwright.getByRole("button", { name, exact: true }).click();
    await visible(companion, /Enter the code shown/);
    await fill("TV code", code);
    await click("Check TV code");
    await visible(companion, /TV code verified/);
    await fill("Jellyfin username", "synthetic-viewer");
    await fill("Jellyfin password", "synthetic-password");
    await click("Pair this TV");
    const session = { msx, authenticated: true };
    sessions.push(session); // Cleanup still records auth if a later UI step fails.
    await visible(companion, /Sign-in succeeded/);
    await msx.playwright.getByText(/Continue after pairing/i).click();
    await visible(msx, /Synthetic movies/i);
    await msx.playwright.getByText(/Synthetic movies/i).click();
    await visible(msx, /Synthetic clip/i);
    report.stage = role + "-poster-DOM-collection";
    // Read standard DOM rendering only, never vendor caches, QR grants or AX.
    const collection = await collectRenderedImages(msx);
    if (!collection || !Array.isArray(collection.images)) throw null;
    report.stage = role + "-poster-target-selection";
    const { poster, summary } = inspectOwnPosters(origin, collection.images);
    report.poster_selections ??= [];
    report.poster_selections.push({ role, attributes: collection.counts, ...summary });
    if (!poster) throw null;
    report.stage = role + "-opaque-capture";
    let handle;
    try { handle = await probe.capture(role, poster); }
    catch (error) {
      const failure = captureFailure(error);
      report.stage = role + "-capture-" + failure.stage;
      report.capture_problem = failure.problem;
      throw null;
    }
    report.stage = role + "-Libraries-return";
    await msx.playwright.getByText("Libraries", { exact: true }).click();
    await visible(msx, /Disconnect TV/i);
    report.checks.push(role + "-normal-pairing-and-capture");
    return { session, handle };
  };
  const check = async (handle, category, expectation, substitute = null) => {
    report.stage = handle.role + "-" + category + "-" + expectation;
    const result = await probe.check(handle, category, expectation, substitute);
    report.observations.push(result);
    if (!result.ok) throw null; // Same predicate in the deliberately wrong-target run.
    report.checks.push(report.stage);
  };
  try {
    report.stage = "scoped-observer-availability";
    const observerTab = await open(origin + "/__synthetic/ready");
    probe = await createResourceProbe(observerTab, origin);
    const a = await pair("A");
    const b = await pair("B");
    for (const handle of [a.handle, b.handle]) for (const category of CATEGORIES) await check(handle, category, "served");
    report.stage = "A-confirmed-disconnect";
    await disconnectSession(a.session);
    report.checks.push(report.stage);
    for (const category of CATEGORIES) await check(a.handle, category, "denied", fault === "authorized-target" && category === "media" ? b.handle : null);
    for (const category of CATEGORIES) await check(b.handle, category, "served");
    const repaired = await pair("repaired-A", a.session);
    for (const category of CATEGORIES) await check(repaired.handle, category, "served");
    for (const category of CATEGORIES) await check(a.handle, category, "denied");
    report.status = "passed";
    report.stage = "complete";
    report.browser_verified = true;
  } catch { /* Raw browser/permission/network errors may contain credentials. */ }
  finally {
    for (const session of sessions) if (session.authenticated) {
      try { await disconnectSession(session); } catch {
        report.checks.push("session-cleanup-deferred-to-bounded-service");
        report.status = "failed";
        report.browser_verified = false;
      }
    }
    if (probe && !await probe.close()) {
      report.status = "failed";
      report.browser_verified = false;
      report.checks.push("observer-disable-unconfirmed");
    }
    for (const tab of tabs.reverse()) try { await tab.close(); } catch {
      report.status = "failed";
      report.stage = "owned-tab-cleanup";
      report.browser_verified = false;
    }
  }
  return report;
}
