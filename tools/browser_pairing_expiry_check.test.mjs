import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import test from "node:test";
import vm from "node:vm";
import { pairingExpirySteps } from "./browser_pairing_expiry_check.mjs";

const origin = "https://synthetic-only.trycloudflare.com";
const deadlineUtc = () => new Date(Date.now() + 899000).toISOString();
function model(t, fault = "none") {
  let clock = 0;
  t.mock.method(performance, "now", () => clock); // Offline only; live entry has no clock option.
  let expires = 300000;
  let generation = 0;
  let tv = "pairing";
  let form = "entry";
  let paired = false;
  let closed = 0;
  let made = 0;
  const fields = {};
  const submissions = [];
  const waits = [];
  const created = [];
  const code = "12345678"; // Non-live model deliberately reuses the pruned numeric code.
  const match = (pattern, text) => typeof pattern === "string" ? text.includes(pattern) : text.split("\n").some(line => pattern.test(line));
  const tvText = () => tv === "pairing" ? "1234 5678\nContinue after pairing\nCreate new code" : tv === "expired" ? "Pairing or session expired\nCreate new code" : tv === "home" ? "Synthetic movies\nDisconnect TV" : tv === "confirm" ? "Confirm disconnect" : "Disconnected\nPair again";
  const formText = () => form === "entry" ? "Enter the code shown" : form === "denied" ? "TV code is invalid, expired or already used" : form === "csrf" ? "Form expired. Reload this page and retry." : form === "credentials" ? "TV code verified" : "Sign-in succeeded";
  const getState = () => ({ expired: form === "denied" || (fault === "stale" && form === "credentials"), csrf: form === "csrf", verified: form === "credentials", success: form === "paired", status_empty: form === "entry" });
  const labelExists = name => name === "TV code" ? ["entry", "denied", "csrf"].includes(form) : form === "credentials";
  const locator = (pattern, text, action) => ({ waitFor: async () => { if (!match(pattern, text())) throw new Error("private-code/private-url"); }, click: action });
  const msx = {
    goto: async () => {}, close: async () => { closed++; },
    playwright: {
      evaluate: async () => { if (fault === "late-setup" && generation === 0) clock += 500000; return code; },
      waitForTimeout: async ms => { waits.push(ms); if (fault !== "frozen") clock += ms; if (fault === "overshoot" && clock >= 305000) clock += 450000; },
      getByText: pattern => locator(pattern, tvText, async () => {
        if (!match(pattern, tvText())) throw new Error("private-code");
        if (String(pattern).includes("Continue")) tv = paired ? "home" : clock >= expires ? "expired" : "pairing";
        else if (String(pattern).includes("Create new code")) { generation++; expires = clock + 300000; tv = "pairing"; }
        else if (String(pattern).includes("Confirm disconnect")) { paired = false; tv = "disconnected"; }
        else if (String(pattern).includes("Disconnect TV")) tv = "confirm";
      }),
    },
  };
  const companion = {
    goto: async () => { form = fault === "dirty-entry" ? "denied" : "entry"; },
    reload: async () => { form = "entry"; for (const key of Object.keys(fields)) delete fields[key]; },
    close: async () => { closed++; if (fault === "close") throw new Error("private-code"); },
    playwright: {
      evaluate: async () => getState(),
      getByText: pattern => locator(pattern, formText),
      getByLabel: name => ({ count: async () => labelExists(name) ? 1 : 0, fill: async value => { if (!labelExists(name)) throw new Error("field absent"); fields[name] = value; } }),
      getByRole: (_, { name }) => ({ click: async () => {
        if (name === "Check TV code") {
          submissions.push({ generation, at: clock });
          if (fault === "csrf" && generation === 0) form = "csrf";
          else form = fault === "recovery" && generation > 0 ? "denied" : fields["TV code"] === code && (clock < expires || ["retained", "stale"].includes(fault)) ? "credentials" : "denied";
        } else {
          assert.equal(form, "credentials");
          assert.equal(fields["Jellyfin username"], "synthetic-viewer");
          assert.equal(fields["Jellyfin password"], "synthetic-password");
          form = "paired"; paired = true;
        }
      } }),
    },
  };
  const health = { goto: async () => {}, close: async () => { closed++; }, playwright: { evaluate: async fn => vm.runInNewContext(`(${fn.toString()})()`, { document: { querySelector: () => ({ innerText: JSON.stringify({ mode: "public-synthetic", configured: true, ...(fault === "candidate" ? { original_delivery: "authenticated-file" } : {}) }) }) } }) } };
  const queue = [health, msx, companion];
  return { newTab: async () => { made++; created.push(clock); return queue.shift(); }, submissions, waits, created, closed: () => closed, made: () => made, setClock: value => { clock = value; } };
}
async function finish(iterator) {
  const progress = [];
  for (;;) { const step = await iterator.next(); if (step.done) return { report: step.value, progress }; progress.push(step.value); }
}

test("normal modeled expiry requires elapsed lifetime and recovers even when digits recur", async t => {
  const m = model(t);
  const result = await finish(pairingExpirySteps({ origin, newTab: m.newTab, deadlineUtc: deadlineUtc() }));
  assert.equal(result.report.status, "passed");
  assert.ok(result.report.wait_seconds >= 305);
  assert.deepEqual(result.report.checks, ["synthetic-service-identity", "normal-pending-lifetime-elapsed", "expired-unused-code-denied", "normal-new-code-pairing-recovery", "normal-confirmed-disconnect"]);
  assert.equal(result.report.session_cleanup, "normal-disconnect");
  assert.equal(m.submissions.filter(s => s.generation === 0).length, 1);
  assert.ok(m.created[2] >= 305000);
  assert.ok(m.waits.every(ms => ms <= 5000));
  assert.equal(m.closed(), 3);
  assert.doesNotMatch(JSON.stringify(result), /12345678|private-code|private-url|trycloudflare|synthetic-password/);
});

for (const fault of ["retained", "stale", "csrf", "dirty-entry", "frozen", "late-setup", "close", "recovery", "overshoot", "candidate"]) test("false-pass/cleanup counterexample: " + fault, async t => {
  const m = model(t, fault);
  const { report } = await finish(pairingExpirySteps({ origin, newTab: m.newTab, deadlineUtc: deadlineUtc() }));
  assert.notEqual(report.status, "passed");
  if (fault === "retained") assert.equal(report.stage, "expired-code-visible-denial"); // Same ordinary assertion, no driver fault branch.
  if (["retained", "stale", "csrf"].includes(fault)) assert.equal(m.submissions.length, 1);
  if (["dirty-entry", "frozen", "late-setup"].includes(fault)) assert.equal(m.submissions.length, 0);
  if (!["close", "recovery"].includes(fault)) assert.ok(!report.checks.includes("expired-unused-code-denied"));
  if (fault === "recovery") assert.ok(!report.checks.includes("normal-new-code-pairing-recovery"));
  if (fault === "overshoot") assert.equal(report.stage, "post-expiry-recovery-budget");
  assert.equal(m.closed(), m.made());
  assert.doesNotMatch(JSON.stringify(report), /12345678|private-code|private-url|trycloudflare/);
});

test("post-submit cancellation never claims normal logout", async t => {
  const m = model(t);
  const iterator = pairingExpirySteps({ origin, newTab: m.newTab, deadlineUtc: deadlineUtc() });
  let step;
  do { step = await iterator.next(); assert.equal(step.done, false); } while (step.value.stage !== "recovery-login-confirmed");
  const cancelled = await iterator.return();
  assert.equal(cancelled.done, true);
  assert.equal(cancelled.value.session_cleanup, "deferred-to-bounded-service");
  assert.equal(m.closed(), 3);
});

test("stalled navigation is bounded and closes its known owned tab", async t => {
  model(t);
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let closed = 0;
  const tab = { goto: () => new Promise(() => {}), close: async () => { closed++; } };
  const iterator = pairingExpirySteps({ origin, newTab: async () => tab, deadlineUtc: deadlineUtc() });
  await iterator.next(); // Before creation.
  await iterator.next(); // Creation completes; before navigation.
  const pending = iterator.next();
  await Promise.resolve(); await Promise.resolve();
  t.mock.timers.tick(15000);
  const result = await pending;
  assert.equal(result.done, true);
  assert.equal(result.value.status, "failed");
  assert.equal(result.value.tabs_closed, true);
  assert.equal(closed, 1);
});

test("unresolved creation cannot claim closed tabs; a late owned tab is closed", async t => {
  model(t);
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let resolveTab;
  let closed = 0;
  const iterator = pairingExpirySteps({ origin, newTab: () => new Promise(resolve => { resolveTab = resolve; }), deadlineUtc: deadlineUtc() });
  await iterator.next();
  const pending = iterator.next();
  await Promise.resolve(); await Promise.resolve();
  t.mock.timers.tick(15000);
  const result = await pending;
  assert.equal(result.done, true);
  assert.equal(result.value.pending_tab_creations, 1);
  assert.equal(result.value.tabs_closed, false);
  assert.equal(result.value.status, "failed");
  resolveTab({ close: async () => { closed++; } });
  for (let i = 0; i < 10; i++) await Promise.resolve();
  assert.equal(closed, 1);
});

test("cancellation while waiting closes owned tabs without another app action", async t => {
  const m = model(t);
  const iterator = pairingExpirySteps({ origin, newTab: m.newTab, deadlineUtc: deadlineUtc() });
  let step;
  do { step = await iterator.next(); assert.equal(step.done, false); } while (step.value.stage !== "pending-code-expiry-wait");
  const cancelled = await iterator.return();
  assert.equal(cancelled.done, true); // Finally has no suspended cleanup yields.
  assert.equal(cancelled.value.status, "cancelled");
  assert.equal(cancelled.value.tabs_closed, true);
  assert.equal(m.closed(), 2);
  assert.equal(m.waits.length, 0);
  assert.equal(m.submissions.length, 0);
});

test("invalid destinations/deadlines or insufficient original budget create no tab", async () => {
  for (const options of [{ origin: "https://operator.invalid", deadlineUtc: deadlineUtc() }, { origin, deadlineUtc: "later" }, { origin, deadlineUtc: new Date(Date.now() + 400000).toISOString() }]) {
    const { report } = await finish(pairingExpirySteps({ ...options, newTab: async () => assert.fail("opened tab") }));
    assert.equal(report.status, "failed");
  }
});

test("exact cleanup-reserve boundary schedules no foreground operation", async t => {
  const m = model(t);
  t.mock.method(Date, "now", () => 0);
  const iterator = pairingExpirySteps({ origin, newTab: m.newTab, deadlineUtc: new Date(900000).toISOString() });
  await iterator.next();
  m.setClock(840000);
  const result = await iterator.next();
  assert.equal(result.done, true);
  assert.equal(result.value.status, "failed");
  assert.equal(m.made(), 0);
});
