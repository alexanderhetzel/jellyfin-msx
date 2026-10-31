// Source-only entry until an exclusive browser/relay slot is explicitly granted.
import { readPairingCode } from "./browser_pairing_check.mjs";
import { createResourceProbe } from "./browser_resource_probe.mjs";

const ORIGIN = /^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com$/;
const CATEGORIES = ["home", "browse", "detail", "poster", "resolver", "media"];

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
    report.stage = role + "-own-rendered-poster";
    // Read standard DOM rendering only, never vendor caches, QR grants or AX.
    const images = await msx.playwright.evaluate(() => {
      const elements = Array.from(document.querySelectorAll("*"));
      if (elements.length > 4000) return null;
      const values = [];
      for (const element of elements) {
        if (element instanceof HTMLImageElement && element.src) values.push(element.src);
        const background = getComputedStyle(element).backgroundImage;
        const match = background.match(/^url\(["']?([^"')]+)["']?\)$/);
        if (match) values.push(match[1]);
        if (values.length > 128 || values.some(value => value.length > 4096)) return null;
      }
      return values;
    });
    if (!Array.isArray(images)) throw null;
    const candidates = [...new Set(images.filter(value => {
      try {
        const url = new URL(value);
        // The baseline fixture's public MOVIE ID, not a guessed bearer/QR grant.
        return url.origin === origin && !url.search && !url.hash && /^\/msx\/device\/[A-Za-z0-9_-]{43}\/image\/33333333333333333333333333333333$/.test(url.pathname);
      } catch { return false; }
    }))];
    if (candidates.length !== 1) throw null;
    const handle = await probe.capture(role, candidates[0]);
    await msx.playwright.getByText("Libraries", { exact: true }).click();
    await visible(msx, /Disconnect TV/i);
    report.checks.push(role + "-normal-pairing-and-capture");
    return { session, handle };
  };
  const disconnect = async session => {
    await session.msx.playwright.getByText(/Disconnect TV/i).click();
    await visible(session.msx, /Confirm disconnect/i);
    await session.msx.playwright.getByText(/Confirm disconnect/i).click();
    await visible(session.msx, /Pair again/i);
    await visible(session.msx, /Disconnected/i);
    session.authenticated = false;
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
    await disconnect(a.session);
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
      try { await disconnect(session); } catch {
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
