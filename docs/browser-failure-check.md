# Hosted synthetic failure/recovery check — issue #9

**Implemented / automated-tested / device-unverified:** the connected-Chrome pairing command has a
`scenario: 'failures'` extension. It uses the same normal authentication and
supported Tab APIs, not a second browser driver. Production code and dependencies
are unchanged. Actual execution results are recorded separately from mocked
transport and guard tests; this is not the complete issue #9 matrix.

## Trusted startup selection

After the separately required explicit authorization for temporary synthetic
Cloudflare exposure, start a dedicated instance:

```sh
uv run python -m tools.synthetic_https --activate-public-synthetic --seconds 900 --scenario failures
```

The default remains `baseline`. Only these two startup values are allowed; the
supervisor passes the choice to its owned backend helper. No query, request Host,
header or public fault-control endpoint selects or mutates a scenario. Both use
explicit settings, strict same-origin MockTransport, normal code/CSRF/login/token
checks, the checksum-reviewed clip in RAM and no operator configuration, secret
store, real transport or fallback. The baseline/operator labs are unchanged.
Readiness prints the fixed startup scenario. Startup still consumes the original
900-second budget; cleanup, origin, TLS and no-conversion rules are unchanged.

The failure fixture adds authenticated named choices:

| Choice | Controlled upstream response |
| --- | --- |
| Broken JSON library | Malformed JSON instead of the items object. |
| Denied access library | HTTP 403, mapped through normal application access handling. |
| Unreachable upstream library | MockTransport ConnectError, mapped through normal timeout handling. This is simulated upstream unavailability, not real relay/browser packet loss. |
| Rejected playback | Eligible metadata followed by PlaybackInfo denying Direct Play. The baseline selected-source and no-conversion request assertions still apply. |
| Synthetic movies / Synthetic clip | Unchanged authenticated healthy original clip for recovery. |

## Browser command

Use the setup and dedicated-origin/shared-cookie precautions in
[the pairing command](browser-pairing-check.md). Load the local first-party module
through the connected Chrome tool session, not a shell browser launcher:

```js
let driver = await import('file:///C:/absolute/checkout/tools/browser_pairing_check.mjs');
let result = await driver.checkPairing({
  origin: 'https://owned-ready-name.trycloudflare.com',
  scenario: 'failures',
  newTab: () => cua.createBrowserTab('CURRENT_CHROME_EXTENSION_ID', 'about:blank', {
    sessionName: '🧪 Failure recovery'
  })
});
nodeRepl.write(result);
```

Require `status: passed`, the full failure/recovery check list, healthy media
dimensions 1280x720, readyState 4, no error and advancing playback time. The command
operates the real hosted MSX choices, checks specific visible denial messages,
uses visible Back controls for recovery, then plays/stops the healthy clip and
disconnects its own session. No playback state is assigned. Only fixed stage names,
denial categories and URL-free media properties are returned. Generic runtime
error dialogs must be described as observed, not as polished application UX.

After at least 61 seconds between invocations, repeat with `fault: 'json'`, then
with `fault: 'playback'`, keeping `scenario: 'failures'`. These trusted driver
options operate already-visible faulty fixture choices at the final healthy
recovery step; they do not change server configuration or request fault switches.
Each must return `status: failed`, `stage: healthy-original-recovery`, and the
matching fresh `observed_denial` (`json` or `playback`). Neither may claim healthy
media recovery or final disconnect. A failed invocation can leave RAM auth until
the bounded service ends; its fixed report says so and owned tabs still close.
Stop the dedicated instance after the trials and verify exact owned helpers,
listener and control-directory cleanup. Never repurpose a user test relay.

## Local verification and remaining scope

```sh
uv run pytest tests/test_synthetic_failures.py tests/test_synthetic_https.py -W error
node --test tools/browser_pairing_check.test.mjs
node --check tools/browser_failure_check.mjs
```

Mocked checks establish auth/origin/no-fallback boundaries, specific error mapping,
healthy recovery, pinned original-source delivery, no conversion, public scenario
switch refusal and startup/helper propagation. They are not hosted-browser passes.
The connector command still requires the browser tool and external Cloudflare/MSX
availability; it is not an unattended standalone shell or public-CI browser job.
Expired codes/login, actual relay/network interruption, series/episodes/pagination,
full source-version and resource/cross-session isolation remain open. Audible
audio and physical Philips behavior remain unverified.

## Actual execution — 2026-10-31

One approved dedicated failure-scenario relay started at 00:57:41 Vienna, with
the original 01:12:41 deadline. Local and verified public HTTPS readiness passed
before browser actions. The first connector call used a stale browser ID and
failed before opening a tab; inventory showed the same Chrome extension had
reconnected under a new ID. The actual trials used that current extension,
not another browser or native automation. Runtime version was not independently
reread in this command; earlier observations recorded official MSX 0.1.167.

| Invocation | Actual result |
| --- | --- |
| Positive, completed 01:00:30 | Passed 21 stages: normal pairing/Continue; specific malformed-JSON, access-denied and simulated-upstream messages followed by Back/home recovery; Direct Play denial with no decoded media followed by details/library recovery; healthy original media; Stop/home and own disconnect. |
| JSON variant, completed 01:02:03 | Failed healthy-original-recovery with fresh observed_denial=json. Selecting the broken library made the same ordinary healthy-item assertion fail; no special fault-branch throw remained. |
| Playback variant, completed 01:03:29 | Failed healthy-original-recovery with fresh observed_denial=playback. Selecting the rejected item reached the same ordinary healthy-media assertion, which rejected the visible denial/no decoded recovery. |

The positive native media observations were 1280x720, readyState 4, paused=false,
error=null and time advancing to 1.691273 seconds. The driver only read decoded
dimensions, time and pause/ready/error state; it never read the private media
source URL or assigned player state. Stop was separately observed as paused=true,
time=0, readyState=0 before returning home. The saved screenshot supports the
settled Disconnected / Pair again screen; decoded frame/time observations came
from native media properties, not that final screenshot. Audible audio was not
verified. Error checks matched the specific application messages in the official
runtime's generic error presentation; no polished error/retry UX is claimed.

Each invocation made and closed four owned blank-initialized tabs, with at least
61 seconds between invocations. Failed variants reported remaining RAM session
cleanup as deferred to the bounded service, rather than claiming logout. The
service was stopped after the trials: exit 0 / stopped, absent listener/control
directory and every captured helper/vendor/console PID were verified at 01:03:41,
within the original 900-second total. No real server, account, media, operator
configuration, secret store, conversion or security/DNS change was used.

Sanitized reports and the inspected final screen remain local in ignored
`.lab/failure-check-results.json` and `.lab/failure-check-disconnected.png`.
They contain no code, credential, capability, private URL or raw body/error.
Independent source review identified and resolved the earlier special fault-branch
throws and missing Stop-media assertion before activation. The independent
reviewer repeated mocked/guard/source checks, not the browser actions or cleanup.

Local checks: full `uv run pytest -W error` **398 passed / 1 POSIX skip**;
focused failure/supervision tests **38 passed**; Node guards **5 passed**;
syntax and diff checks passed. Ruff initially found an unused test import; it was
removed and Ruff passed. Formatting passed **88 files**. These automated local
checks remain separate from the actual browser trials above. This milestone does
not close #9 or establish actual relay-outage, expiry, source-version, series,
cross-session, real-server, audible-audio or physical-device acceptance.
