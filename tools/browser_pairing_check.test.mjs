import assert from "node:assert/strict";
import test from "node:test";
import { checkPairing } from "./browser_pairing_check.mjs";

const origin = "https://synthetic-only.trycloudflare.com";

test("invalid destinations or fault choices cannot open any tab", async () => {
  for (const value of ["http://localhost", "https://operator.example", origin + "/pair", origin + "?token=private", "https://nested.host.trycloudflare.com"]) {
    const result = await checkPairing({ origin: value, newTab: () => assert.fail("opened tab") });
    assert.equal(result.stage, "invalid-synthetic-options");
  }
  assert.equal((await checkPairing({ origin, fault: "arbitrary", newTab: () => assert.fail("opened tab") })).status, "failed");
});

test("missing connector fails without a substitute browser or network driver", async () => {
  assert.equal((await checkPairing({ origin })).stage, "browser-connector-required");
});

test("raw connector errors containing secrets are reduced to a fixed stage", async () => {
  const result = await checkPairing({ origin, newTab: async () => { throw new Error("private-capability password TV-code"); } });
  assert.equal(result.status, "failed");
  assert.equal(result.stage, "synthetic-service-identity");
  assert.doesNotMatch(JSON.stringify(result), /private-capability|password|TV-code/);
});

test("failed service identity closes only the owned tab and never reaches credentials", async () => {
  let closed = 0;
  let opened = 0;
  const result = await checkPairing({
    origin,
    newTab: async () => {
      opened++;
      return {
        goto: async url => assert.equal(url, origin + "/__synthetic/ready"),
        close: async () => { closed++; },
        playwright: {
          getByText: () => ({ waitFor: async () => {} }),
          evaluate: async () => false,
        },
      };
    },
  });
  assert.equal(result.status, "failed");
  assert.equal(result.stage, "synthetic-service-identity");
  assert.equal(opened, 1);
  assert.equal(closed, 1);
});

test("owned-tab cleanup failure is visible without forwarding raw exception text", async () => {
  const result = await checkPairing({ origin, newTab: async () => ({ goto: async () => { throw new Error("secret"); }, close: async () => { throw new Error("secret"); } }) });
  assert.equal(result.status, "failed");
  assert.equal(result.stage, "owned-tab-cleanup");
  assert.doesNotMatch(JSON.stringify(result), /secret/);
});
