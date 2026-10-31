// Normal five-minute pending-code expiry. No server clock/fault hook or CDP.
import { performance } from "node:perf_hooks";
import { readPairingCode } from "./browser_pairing_check.mjs";

const ORIGIN = /^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com$/;
const WAIT = 305000;
const CLEANUP = 60000;
const RECOVERY = 120000;

export async function* pairingExpirySteps({ origin, newTab, deadlineUtc } = {}) {
  const report = { status: "failed", stage: "invalid-options", required_fixture: "baseline-candidate-off", checks: [], wait_seconds: 0, session_cleanup: "not-required", tabs_closed: false, device_verified: false };
  const tabs = [];
  let ended = false;
  let sessionPossible = false;
  let msx;
  let companion;
  let deadline;
  let closing = false;
  let pendingCreations = 0;
  let previous = -Infinity;
  const now = () => {
    const value = performance.now();
    if (!Number.isFinite(value) || value < previous) throw null;
    previous = value;
    return value;
  };
  const budget = (needed = CLEANUP) => { if (deadline - now() < needed) throw null; };
  const timeout = () => Math.max(1, Math.min(15000, deadline - now() - CLEANUP));
  const progress = () => ({ status: "running", stage: report.stage, wait_seconds: report.wait_seconds });
  async function* act(stage, operation) {
    report.stage = stage;
    budget();
    yield progress(); // One bounded browser operation per next(); no private result yielded.
    budget();
    const allowance = Math.min(15000, deadline - now() - CLEANUP);
    if (allowance <= 0) throw null; // Never schedule an operation on cleanup's boundary.
    let timer;
    let value;
    try {
      value = await Promise.race([Promise.resolve().then(operation), new Promise((_, reject) => { timer = setTimeout(() => reject(null), allowance); })]);
    } finally { clearTimeout(timer); }
    budget();
    return value;
  }
  const close = async tab => {
    let timer;
    try { await Promise.race([tab.close(), new Promise((_, reject) => { timer = setTimeout(() => reject(null), 2000); })]); return true; }
    catch { return false; }
    finally { clearTimeout(timer); }
  };
  const open = async () => {
    pendingCreations++;
    try {
      const tab = await newTab();
      tabs.push(tab);
      if (closing) await close(tab); // A timed-out creation can still resolve later.
      return tab;
    } finally { pendingCreations--; }
  };
  const visible = (tab, text) => tab.playwright.getByText(text).waitFor({ state: "visible", timeoutMs: timeout() });
  const click = (tab, name) => tab.playwright.getByRole("button", { name, exact: true }).click({ timeoutMs: timeout() });
  const fill = (name, value) => companion.playwright.getByLabel(name, { exact: true }).fill(value, { timeoutMs: timeout() });
  const pass = name => report.checks.push(name);
  const formState = () => companion.playwright.evaluate(() => {
    const text = document.body.innerText;
    return { expired: text.includes("TV code is invalid, expired or already used"), csrf: text.includes("Form expired."), verified: text.includes("TV code verified"), success: text.includes("Sign-in succeeded"), status_empty: document.querySelector('[role="status"]')?.textContent.trim() === "" };
  });
  try {
    if (typeof origin !== "string" || !ORIGIN.test(origin) || typeof newTab !== "function" || typeof deadlineUtc !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(deadlineUtc)) throw null;
    const remaining = Date.parse(deadlineUtc) - Date.now();
    if (!Number.isFinite(remaining) || remaining <= 0 || remaining > 900000) throw null;
    deadline = now() + remaining; // Original supervisor deadline, never a fresh 900 seconds.
    report.stage = "original-budget";
    budget(WAIT + RECOVERY + CLEANUP);
    const health = yield* act("synthetic-service-tab", open);
    yield* act("synthetic-service-navigation", () => health.goto(origin + "/__synthetic/ready"));
    const synthetic = yield* act("synthetic-service-identity", () => health.playwright.evaluate(() => {
      try { const value = JSON.parse(document.querySelector("pre")?.innerText ?? document.body.innerText); return value.mode === "public-synthetic" && value.configured === true && Object.keys(value).length === 2; } catch { return false; }
    }));
    if (synthetic !== true) throw null;
    pass("synthetic-service-identity");
    msx = yield* act("official-runtime-tab", open);
    const start = new URL("https://msx.benzac.de/");
    start.searchParams.set("start", "content:" + origin + "/msx/pair.json");
    for (const [key, value] of Object.entries({ input: "2", init: "1", suspend: "0", animate: "0" })) start.searchParams.set(key, value);
    yield* act("official-runtime-navigation", () => msx.goto(start.href));
    yield* act("pending-code-visible", () => visible(msx, /^[0-9]{4}[ \u00a0]+[0-9]{4}$/));
    const oldCode = yield* act("pending-code-read", () => msx.playwright.evaluate(readPairingCode));
    if (typeof oldCode !== "string" || !/^[0-9]{8}$/.test(oldCode)) throw null;
    const readAt = now(); // Server creation precedes this read; do not claim its birth time.
    report.stage = "post-code-original-budget";
    budget(WAIT + RECOVERY + CLEANUP);
    let waited = 0;
    for (let count = 0; waited < WAIT; count++) {
      report.stage = "pending-code-expiry-wait";
      if (count >= 70) throw null;
      budget(WAIT - waited + RECOVERY + CLEANUP);
      yield* act("pending-code-expiry-wait", () => msx.playwright.waitForTimeout(Math.min(5000, WAIT - waited)));
      waited = now() - readAt;
      report.wait_seconds = Math.min(900, Math.floor(waited / 1000));
    }
    pass("normal-pending-lifetime-elapsed");
    report.stage = "post-expiry-recovery-budget";
    budget(RECOVERY + CLEANUP); // Includes any last timer overshoot.
    companion = yield* act("fresh-companion-tab", open);
    yield* act("fresh-companion-navigation", () => companion.goto(origin + "/pair"));
    yield* act("fresh-step-one", () => visible(companion, /Enter the code shown/));
    const clean = yield* act("fresh-step-one-state", formState);
    const beforeCredentials = yield* act("fresh-step-one-fields", () => companion.playwright.getByLabel("Jellyfin username", { exact: true }).count());
    const beforePassword = yield* act("fresh-step-one-password", () => companion.playwright.getByLabel("Jellyfin password", { exact: true }).count());
    const codeFields = yield* act("fresh-step-one-code", () => companion.playwright.getByLabel("TV code", { exact: true }).count());
    if (clean.expired !== false || clean.csrf !== false || clean.verified !== false || clean.success !== false || clean.status_empty !== true || beforeCredentials !== 0 || beforePassword !== 0 || codeFields !== 1) throw null;
    yield* act("expired-code-fill", () => fill("TV code", oldCode));
    yield* act("expired-code-single-submit", () => click(companion, "Check TV code"));
    yield* act("expired-code-visible-denial", () => visible(companion, /TV code is invalid, expired or already used/));
    const denial = yield* act("expired-code-denial-state", formState);
    const credentials = yield* act("expired-code-denial-fields", () => companion.playwright.getByLabel("Jellyfin username", { exact: true }).count());
    const password = yield* act("expired-code-denial-password", () => companion.playwright.getByLabel("Jellyfin password", { exact: true }).count());
    if (denial.expired !== true || denial.csrf !== false || denial.verified !== false || denial.success !== false || credentials !== 0 || password !== 0) throw null;
    pass("expired-unused-code-denied");
    yield* act("expired-tv-continue", () => msx.playwright.getByText(/Continue after pairing/i).click({ timeoutMs: timeout() }));
    yield* act("expired-tv-notice", () => visible(msx, /Pairing or session expired/i));
    yield* act("normal-create-new-code", () => msx.playwright.getByText(/^Create new code$/i).click({ timeoutMs: timeout() }));
    yield* act("new-code-visible", () => visible(msx, /^[0-9]{4}[ \u00a0]+[0-9]{4}$/));
    const code = yield* act("new-code-read", () => msx.playwright.evaluate(readPairingCode));
    if (typeof code !== "string" || !/^[0-9]{8}$/.test(code)) throw null; // Equality after pruning is allowed.
    yield* act("recovery-form-reload", () => companion.reload());
    yield* act("recovery-step-one", () => visible(companion, /Enter the code shown/));
    yield* act("recovery-code-fill", () => fill("TV code", code));
    yield* act("recovery-code-submit", () => click(companion, "Check TV code"));
    yield* act("recovery-code-verified", () => visible(companion, /TV code verified/));
    yield* act("recovery-username", () => fill("Jellyfin username", "synthetic-viewer"));
    yield* act("recovery-password", () => fill("Jellyfin password", "synthetic-password"));
    yield* act("recovery-login-submit", () => {
      sessionPossible = true; // A lost post-submit observation may still leave backend auth.
      return click(companion, "Pair this TV");
    });
    yield* act("recovery-login-confirmed", () => visible(companion, /Sign-in succeeded/));
    yield* act("recovery-msx-continue", () => msx.playwright.getByText(/Continue after pairing/i).click({ timeoutMs: timeout() }));
    yield* act("recovery-libraries", () => visible(msx, /Synthetic movies/i));
    pass("normal-new-code-pairing-recovery");
    yield* act("normal-disconnect", () => msx.playwright.getByText(/Disconnect TV/i).click({ timeoutMs: timeout() }));
    yield* act("normal-disconnect-confirmation", () => visible(msx, /Confirm disconnect/i));
    yield* act("normal-disconnect-confirm", () => msx.playwright.getByText(/Confirm disconnect/i).click({ timeoutMs: timeout() }));
    yield* act("normal-disconnected-settle", () => msx.playwright.waitForTimeout(1000));
    yield* act("normal-disconnected", () => visible(msx, /Disconnected/i));
    yield* act("normal-pair-again", () => visible(msx, /Pair again/i));
    sessionPossible = false;
    report.session_cleanup = "normal-disconnect";
    pass("normal-confirmed-disconnect");
    report.status = "passed";
    report.stage = "complete";
    ended = true;
  } catch { ended = true; } // Never emit browser exceptions, form data or page text.
  finally {
    closing = true;
    if (!ended) { report.status = "cancelled"; report.stage = "cancelled"; }
    if (sessionPossible) report.session_cleanup = "deferred-to-bounded-service";
    // No yields in finally: return()/next() completes bounded owned-tab cleanup.
    report.pending_tab_creations = pendingCreations;
    report.tabs_closed = pendingCreations === 0;
    if (pendingCreations) { report.status = "failed"; report.stage = "owned-tab-creation-unconfirmed"; }
    for (const tab of tabs.reverse()) {
      if (!await close(tab)) { report.tabs_closed = false; report.status = "failed"; report.stage = "owned-tab-cleanup"; }
    }
    return report;
  }
}
