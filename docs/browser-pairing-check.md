# Connected Chrome pairing check — issue #9

**Implemented / automated-tested / device-unverified:** `tools/browser_pairing_check.mjs` is a
first-party driver for the connected browser's supported Tab APIs. It operates
the real official MSX runtime and normal production pairing forms. It does not
import vendor code, inspect runtime internals, inject authentication or assign
player state. This pairing milestone is not the complete hosted-browser matrix.

## Prerequisites and commands

Use a fresh checkout, locked Python environment and the separately reviewed
[synthetic HTTPS supervisor](temporary-synthetic-https.md). Public activation
requires the explicit authorization described there; preparing or reading this
document does not grant it. Start one approved synthetic-only instance:

```sh
uv sync --locked --extra dev
uv run python -m tools.synthetic_https --activate-public-synthetic --seconds 900
```

Wait for **ready**, not merely origin-assigned. Startup consumes the original
900-second lifetime. Use its validated bare origin only; never supply an operator
server or a capability URL. The driver checks the fixed synthetic health identity
before entering the public fixture credentials. HTTPS/browser warnings must never
be bypassed. No resolver, certificate or security setting is changed.

The browser command runs inside the connected Chrome tool session. Discover the
current Chrome **extension** browser ID through the supported inventory and load
its documentation. Replace the example absolute checkout path and bare origin
with this checkout and the current owned ready instance:

```js
let driver = await import('file:///C:/absolute/checkout/tools/browser_pairing_check.mjs');
let result = await driver.checkPairing({
  origin: 'https://owned-ready-name.trycloudflare.com',
  newTab: () => cua.createBrowserTab('CURRENT_CHROME_EXTENSION_ID', 'about:blank', {
    sessionName: '🧪 Pairing checks'
  })
});
nodeRepl.write(result);
```

This is a **connector command**, not a standalone shell command, ordinary Node
browser launcher or unattended public-CI E2E job. The connected Chrome tool must
be available and authorized. No substitute native browser, shell Playwright,
runtime copy or arbitrary network driver is included. The driver creates blank
tabs before navigation so automatic tab-open observations do not print codes.
Read-only DOM code extraction remains inside its closure. Reports contain only
fixed stage names, check names and scope flags; raw body text, exceptions, codes,
capabilities and private URLs are never forwarded.

Run this only on a **dedicated synthetic origin with no simultaneous manual
companion forms**. Separate tabs share Chrome cookies. Opening a second normal
form deliberately rotates the HttpOnly CSRF cookie and can expire another pending
form at the same origin. This is the fault being tested, not cookie isolation.
The driver never clears cookies, lists user tabs or operates tabs it did not create.

The expected positive result has `status: passed`, `stage: complete` and checks
for synthetic service identity, official runtime startup, stale-CSRF denial,
wrong-code denial, valid-code recovery, wrong-credential denial, clean sign-in
recovery before the final credential submission, normal pairing,
actual MSX Continue and own-session disconnect. A failed check returns
`status: failed` and its fixed stage. It closes its owned tabs in either case;
post-login UI failure can leave RAM authorization until the bounded service ends,
reported explicitly. Owned-tab cleanup failure is also a failed result.

## Demonstrate failure sensitivity

After the positive run, wait **at least 61 seconds between invocations** so the
unchanged normal per-minute code/login rate limits do not mask the intended fault.
Within the same still-ready bounded instance, invoke the same command with
`fault: 'csrf'`, then with `fault: 'login'`, again separated by at least 61 seconds.
Both deliberately broken positive paths must return `status: failed` at
`stage: normal-pairing`, with `observed_denial: csrf` or `credentials`
respectively; they must not reach MSX Continue or disconnect checks. A missing
denial category is inconclusive about the intended injected fault, even if the
command failed.
The CSRF variant opens a second normal form before credential submission; the
login variant submits a deliberately wrong fixture password. Neither changes the
server's authentication policy. Before either final submission, the driver
reopens the normal form and checks the code again to obtain a clean Step 2 with
no prior error. A stale error cannot establish denial of the new request.
These expected failures demonstrate sensitivity;
they are not successful positive pairing runs.

The five local guard tests require Node (observed locally with Node 24) and use
only its built-in test runner:

```sh
node --test tools/browser_pairing_check.test.mjs
node --check tools/browser_pairing_check.mjs
```

They cover destination/fault validation, missing connector, raw-error redaction,
synthetic identity refusal before credentials and owned-tab cleanup failure.
They do **not** simulate or certify hosted MSX behavior. The Python suite and
public CI do not run the connector command. Production artifacts exclude these
helpers under the existing packaging allowlists.

## Remaining scope

Expired codes/login, deliberate JSON/playback faults, controlled network recovery,
series/seasons/episode pagination/focus, full source-version consistency and
cross-session/post-disconnect resource isolation remain outside this pairing
driver. Existing [partial HTTPS observations](msx-synthetic-https-results.md) and
HTTP tests do not close those gaps. Audio, real-server compatibility and physical
Philips behavior remain unverified. Issue #9 remains open until its complete
actual matrix and reproducibility requirements are satisfied.

## Actual connector execution — 2026-10-31

The final driver ran in the connected Chrome extension against one fresh,
explicitly approved, synthetic-only HTTPS instance. The official MSX web runtime
was used; no vendor code was copied. The Python factory, supervisor, production
code and dependencies were unchanged. External Cloudflare allocation, public DNS,
TLS and the hosted MSX service remain availability dependencies outside this
driver; local guard tests do not establish them.

| Final invocation | Observed result |
| --- | --- |
| Positive, completed 00:36:17 Vienna | Passed all ten stages through clean sign-in recovery, authenticated MSX Continue and settled own-session Disconnected / Pair again. |
| CSRF fault, completed 00:37:43 Vienna | Failed at normal-pairing with observed_denial=csrf; only the seven prerequisite stages passed, with no MSX Continue or disconnect pass. |
| Login fault, completed 00:39:02 Vienna | Failed at normal-pairing with observed_denial=credentials; only the seven prerequisite stages passed, with no MSX Continue or disconnect pass. |

The invocations were separated by at least 61 seconds. Each made and closed four
owned blank-initialized tabs. The settled Disconnected / Pair again screenshot
was inspected and retained only at ignored `.lab/pairing-check-disconnected.png`;
the fixed-field reports are local at `.lab/pairing-check-results.json`. Neither
artifact contains a code, capability, private URL, body text or credential.
The dedicated relay was stopped after the trials, within its original 900-second
budget. Supervisor exit 0 / stopped, absent loopback listener, control directory
and all captured helper/vendor/console processes were verified at 00:39:08 Vienna.
No simultaneous user companion form or session was operated.

Earlier development trials are not silently counted as final passes: an immediate
screenshot captured the outgoing confirmation scene, and a subsequent settled
screen assertion failed. The driver now requires the settled disconnected state
even when no screenshot is requested. Independent review also found that a prior
credential error could misattribute a later submission failure; the clean recovery
stage now eliminates that stale message before entering normal-pairing. The final
positive and two fault trials above exercised the corrected driver. The screenshot
supports the final disconnected screen, not every intermediate browser action.

Local verification: `node --test tools/browser_pairing_check.test.mjs` **5 passed**;
Node syntax and diff checks passed; `uv run pytest -W error` **394 passed / 1 POSIX
skip**; Ruff passed; formatting passed **85 files**. No Python behavior changed.
The independent reviewer repeated the five guard tests, syntax and diff checks,
reviewed source/privacy and resolved the attribution finding; that reviewer did
not operate the browser. This result establishes a reusable pairing connector
check and limited fault sensitivity, not the complete shell/CI/browser contract
or remaining issue #9 matrix.
