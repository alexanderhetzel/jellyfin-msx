// First-party UI driver. It neither imports nor inspects the proprietary MSX runtime.
// Run through the connected browser's documented Tab APIs, never against an operator lab.
import { exerciseFailures } from "./browser_failure_check.mjs";
const ORIGIN = /^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com$/;
const FAULTS = new Set(["none", "csrf", "login", "json", "playback"]);

export async function checkPairing({ origin, newTab, fault = "none", scenario = "pairing", saveEvidence } = {}) {
  if (typeof origin !== "string" || !ORIGIN.test(origin) || !FAULTS.has(fault) || !["pairing", "failures"].includes(scenario) || (scenario === "failures" && ["csrf", "login"].includes(fault)) || (scenario === "pairing" && ["json", "playback"].includes(fault))) {
    return { status: "failed", stage: "invalid-synthetic-options", checks: [] };
  }
  if (typeof newTab !== "function") {
    return { status: "failed", stage: "browser-connector-required", checks: [] };
  }
  const tabs = [];
  const checks = [];
  let stage = "synthetic-service-identity";
  let authenticated = false;
  let msx;
  let companion;
  let result;
  let media;
  let stop;
  let failureDenial;
  const open = async (url) => {
    const tab = await newTab(); // Create blank tabs so automatic snapshots contain no code.
    tabs.push(tab);
    await tab.goto(url);
    return tab;
  };
  const visible = async (tab, expression) => {
    await tab.playwright.getByText(expression).waitFor({ state: "visible", timeoutMs: 15000 });
  };
  const click = async (tab, name) => tab.playwright.getByRole("button", { name, exact: true }).click();
  const fill = async (tab, name, value) => tab.playwright.getByLabel(name, { exact: true }).fill(value);
  const pass = () => checks.push(stage);
  try {
    const health = await open(origin + "/__synthetic/ready");
    await visible(health, /public-synthetic/);
    const synthetic = await health.playwright.evaluate(() => {
      try {
        const value = JSON.parse(document.querySelector("pre")?.innerText ?? document.body.innerText);
        return value.mode === "public-synthetic" && value.configured === true;
      } catch { return false; }
    });
    if (!synthetic) throw new Error("not-synthetic");
    pass();
    stage = "official-runtime-start";
    const start = new URL("https://msx.benzac.de/");
    start.searchParams.set("start", "content:" + origin + "/msx/pair.json");
    for (const [name, value] of Object.entries({ input: "2", init: "1", suspend: "0", animate: "0" })) {
      start.searchParams.set(name, value);
    }
    msx = await open(start.href);
    await visible(msx, /TV code:/i);
    // The code stays in this closure. Never return body text, private URLs or raw errors.
    const code = await msx.playwright.evaluate(() => {
      const match = document.body.innerText.match(/TV code:\s*([A-Z0-9]{4})\s+([A-Z0-9]{4})/i);
      return match ? match[1] + match[2] : null;
    });
    if (!code) throw new Error("missing-code");
    pass();

    stage = "stale-csrf-denied";
    companion = await open(origin + "/pair");
    await visible(companion, /Enter the code shown/);
    const newerForm = await open(origin + "/pair");
    await visible(newerForm, /Enter the code shown/);
    await fill(companion, "TV code", code);
    await click(companion, "Check TV code");
    await visible(companion, /Form expired\. Reload this page and retry\./);
    pass();

    stage = "wrong-code-denied";
    await companion.reload();
    await fill(companion, "TV code", code === "00000000" ? "11111111" : "00000000");
    await click(companion, "Check TV code");
    await visible(companion, /TV code is invalid, expired or already used/);
    pass();

    stage = "valid-code-recovery";
    await fill(companion, "TV code", code);
    await click(companion, "Check TV code");
    await visible(companion, /TV code verified/);
    pass();

    stage = "wrong-credentials-denied";
    await fill(companion, "Jellyfin username", "synthetic-viewer");
    await fill(companion, "Jellyfin password", "deliberately-wrong");
    await click(companion, "Pair this TV");
    await visible(companion, /Jellyfin sign-in failed\. Check your credentials and server availability\./);
    pass();

    stage = "clean-sign-in-recovery";
    await companion.reload();
    await visible(companion, /Enter the code shown/);
    await fill(companion, "TV code", code);
    await click(companion, "Check TV code");
    await visible(companion, /TV code verified/);
    const cleanForm = await companion.playwright.evaluate(() =>
      !document.body.innerText.includes("Jellyfin sign-in failed. Check your credentials and server availability.") &&
      !document.body.innerText.includes("Form expired. Reload this page and retry.")
    );
    if (!cleanForm) throw new Error("unclean-sign-in-form");
    pass();

    stage = "normal-pairing";
    if (fault === "csrf") {
      await newerForm.reload(); // A real second form rotates the HttpOnly CSRF cookie.
      await visible(newerForm, /Enter the code shown/);
    }
    await fill(companion, "Jellyfin username", "synthetic-viewer");
    await fill(companion, "Jellyfin password", fault === "login" ? "deliberately-wrong" : "synthetic-password");
    await click(companion, "Pair this TV");
    await visible(companion, /Sign-in succeeded/);
    authenticated = true;
    pass();

    stage = "official-msx-continue";
    await msx.playwright.getByText(/Continue after pairing/i).click();
    await visible(msx, /Synthetic movies/i);
    pass();

    if (scenario === "failures") {
      stage = "hosted-failure-recovery";
      const report = await exerciseFailures(msx, fault);
      checks.push(...report.checks);
      stage = report.stage;
      if (report.status !== "passed") {
        failureDenial = report.observed_denial;
        throw new Error("failure-scenario-incomplete");
      }
      media = report.media;
      stop = report.stop;
    }

    stage = "own-session-disconnect";
    await msx.playwright.getByText(/Disconnect TV/i).click();
    await visible(msx, /Confirm disconnect/i);
    await msx.playwright.getByText(/Confirm disconnect/i).click();
    await visible(msx, /Pair again/i);
    // The outgoing scene can still be painting after its replacement enters the DOM.
    await msx.playwright.waitForTimeout(1000);
    await visible(msx, /Disconnected/i);
    authenticated = false;
    pass();
    if (saveEvidence) {
      stage = "disconnected-frame-evidence";
      await saveEvidence(await msx.screenshot({ fullPage: false }));
    }
    result = { status: "passed", stage: "complete", checks, fault, category: "hosted-browser-pairing", device_verified: false };
    if (media) result.media = media;
    if (stop) result.stop = stop;
  } catch {
    // Browser exceptions may contain page URLs or form values. Never forward them.
    result = { status: "failed", stage, checks, fault, category: "hosted-browser-pairing", device_verified: false };
    if (failureDenial !== undefined) result.observed_denial = failureDenial;
    if (stage === "normal-pairing" && companion) {
      try {
        result.observed_denial = await companion.playwright.evaluate(() => {
          const value = document.body.innerText;
          if (value.includes("Form expired. Reload this page and retry.")) return "csrf";
          if (value.includes("Jellyfin sign-in failed. Check your credentials and server availability.")) return "credentials";
          return null;
        });
      } catch { result.observed_denial = null; }
    }
    if (["own-session-disconnect", "disconnected-frame-evidence"].includes(stage) && msx) {
      try {
        result.last_ui = await msx.playwright.evaluate(() => {
          const value = document.body.innerText.toLowerCase();
          return { disconnected: value.includes("disconnected"), confirm: value.includes("confirm disconnect"), pair_again: value.includes("pair again") };
        });
        if (saveEvidence) await saveEvidence(await msx.screenshot({ fullPage: false }));
      } catch { /* Keep evidence failures fixed and redacted too. */ }
    }
  } finally {
    // Only tabs made by this invocation are touched. No cookie clearing or user-tab lookup.
    // A failed post-login UI can leave RAM auth until the bounded service ends; report that.
    if (authenticated) checks.push("session-cleanup-deferred-to-bounded-service");
    for (const tab of tabs.reverse()) {
      try { await tab.close(); } catch {
        checks.push("owned-tab-close-failed");
        result.status = "failed";
        result.stage = "owned-tab-cleanup";
      }
    }
  }
  result.scenario = scenario;
  return result;
}
