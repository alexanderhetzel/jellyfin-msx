# Two-stage companion pairing — issue #13

**Implemented / automated-tested / device-unverified — 2026-10-30.**
`/pair` first asks only for the TV code. Check TV code validates a pending,
unexpired, unused device before showing Jellyfin username/password. Invalid,
expired, used and currently claimed codes return the same fixed recovery message.
No upstream authentication occurs at this stage. Spaces and hyphens in manual
codes are accepted; other non-digit inputs are rejected. Legacy combined form
posts perform only the code check and cannot authenticate.

The credential form contains an independent random 256-bit grant, held by its
SHA-256 verifier in bounded RAM state. It binds one pending device to the exact
form's CSRF cookie, inherits the original pending expiry, and is consumed before
the upstream await. An atomic event-loop claim prevents concurrent authentication.
After authentication, expiry and continued device membership are checked again;
an expired/removed device cannot become paired, and its newly obtained upstream
token is logged out best-effort. The existing single-process/worker assumption
remains. Success consumes the TV code and deletes the browser CSRF cookie.

Wrong credentials return blank fields and a fresh bound grant for the same TV.
An explicit Use a different TV code link restarts manual entry. Opening another
form tab rotates the cookie, so older forms fail closed and return code entry;
the app never silently retargets an old form to another device. A lost/cancelled
credential request consumes its grant; retry starts with the current TV code.
No sliding pending expiry or password persistence is introduced.

## Software acceptance evidence — 2026-10-31

**Implemented / automated-tested / device-unverified:** the remaining #13 normal
hosted-MS​​X pairing-to-authenticated-libraries criterion is now supported by the
reviewed synthetic HTTPS observations below. The earlier loopback Data Load Error
is historical; it does not describe the later authorized HTTPS runs. This
acceptance reconciliation changes documentation only and starts no new relay.

| Criterion | Evidence and boundary |
| --- | --- |
| Code before credentials, invalid-code recovery | PR #45 implemented the protocol; the actual #9 connector run in [PR #58](https://github.com/alexanderhetzel/jellyfin-msx/pull/58) passed wrong-code denial, valid-code recovery and clean Step 2 using normal visible forms. |
| Activation link skips manual entry | The independently reviewed #13 receiving route and its native Chrome activation/recovery checks below satisfy this route contract. QR rendering and exposing the link in MSX remain #14. |
| Device/cookie-bound stages, expiry and single-use | Current `tests/test_pairing_stages.py` and normal pairing regressions retain expiry-before/after-authentication, replay, tampering and concurrency coverage. Expiry is automated evidence, not a new browser expiry pass. |
| CSRF/origins, bounded attempts, redaction and password non-persistence | Existing source/regressions and #13 security review; PR #58's actual stale-CSRF and wrong-credential recovery checks, plus deliberately broken final CSRF/login paths with fresh matching denials. |
| Normal official runtime pairing → private libraries | [Manual HTTPS observations](msx-synthetic-https-results.md) record the actual displayed MSX code, normal two-stage sign-in, TV paired, Continue and Synthetic movies/libraries. The corrected [connector execution](browser-pairing-check.md#actual-connector-execution--2026-10-31) independently repeats that path through `official-msx-continue` and own-session disconnect. |

Evidence provenance: the manual record merged as PR #57 / `c22a3a9`; the corrected
ten-stage connector record merged as PR #58 / `6d08521`, from reviewed head
`5e4b29c7ab66a1799a290a596c36d4a26a49e9e2`. PR #59 / `31aeeb4` extends that same
normal pairing path into authenticated failure/recovery; it changes only lab/
driver/tests/docs. This reconciliation uses baseline
`31aeeb4c0cf300daa2172cd7b6be81692dba7902`. Pairing state/security logic has not
changed since PR #45; the later PR #51 presentation changes were already present
in these hosted runs. The fixed-field local positive report contains all ten
stages, and the negative reports stop at normal-pairing with `csrf` or
`credentials` denial. The settled Disconnected / Pair again screenshot was
inspected again for this audit; it supports that final screen, not every earlier
step. Actual earlier actions are attributed to the #9 worker, not replayed by
this documentation audit. No new browser action, screenshot or media pass is
claimed here.

This closes #13's software acceptance gap, not the complete #9 browser matrix.
The dedicated factory used strict mocked Jellyfin, normal CSRF and random RAM
capabilities, without operator data, real Jellyfin or an authentication bypass.
The source-code/HTTP-only limitation from the initial run is therefore resolved
by actual hosted UI evidence, not by equating an HTTP test with MSX integration.
Mobile layout remains unverified; QR/UI follow-ups remain #14/#16, real-server
compatibility remains separate, and physical Philips acceptance is deferred to
#4. No new device, audible-audio, retention or deployment claim follows.

## Activation link contract and privacy

`/pair?activation=…` accepts the device's independent random pending-only secret,
never its private session capability. Valid links skip manual entry. Issue #14
adds local PNG encoding and native MSX image delivery of that pending link;
the readable companion address and grouped code remain beside it. The image
route revalidates pending state on every request and rejects expired, removed,
paired or currently claimed devices. Its independent peer/global request budget
does not consume the activation-form budget. No external QR service is used.
Activation validates pending state twice, before a 303 redirect and when
rendering credentials at clean `/pair`. A transient HttpOnly `pair_activation`
cookie carries only that activation secret for approximately the remaining
pending lifetime (integer cookie expiry can round up by less than a second);
server pending expiry remains authoritative. It is deleted after the handoff.
Its `SameSite=Lax` permits a cross-site top-level
GET redirect; it does not authorize a POST. The credential CSRF cookie remains
HttpOnly, `SameSite=Strict`, Secure outside explicit HTTP development, and scoped
to `/pair`. Every POST requires the exact configured Origin and double-submit
CSRF validation. Grant-to-CSRF binding is additionally checked server-side.
Invalid/expired/used activation queries also redirect clean, using a non-secret
invalid sentinel cookie, before showing manual recovery. A form left on the
no-referrer activation URL would submit Origin:null in Chromium and fail its
next code check; clean recovery prevents that conflict.

The activation response uses `no-referrer`; the clean form keeps `same-origin`
for normal Chromium form POSTs. Every response remains no-store/private, with
the existing CSP and body limit. Code guesses and credential attempts each allow
five per immediate peer/minute and twenty globally; an early overall POST limit
allows ten/forty for the two-stage flow. Activation GETs have their own five/twenty
budget; both redirect requests count. Generic form GETs retain thirty/120.
Stage storage is bounded by configured `max_states` and pruned on expiry/removal/
pairing. Fixed errors never echo submitted credentials, codes or grants.

An activation URL is a short-lived bearer link, not permission to read a library
or pair without credentials. Keep it private. The clean redirect/no-referrer/
no-store controls do **not** erase browser history, initial request targets,
browser/password-manager retention, screenshots, copied links or operator/proxy
logs. Disable URI/body/header logging at every hop as already required; do not
send links to shared preview origins. Browser history and password-manager erasure
are not implemented or claimed. Device codes and activation/token values are
excluded from the Device representation. No real credentials are required for CI.
An attacker-supplied valid link can identify the attacker's pending TV; it cannot
submit credentials or silently retarget an existing credential form. The user
still explicitly signs in to pair the identified TV. QR rollout must tell users
to initiate pairing from their own TV; no link-level proof of physical ownership
is claimed by this receiving-route milestone.

## Initial implementation evidence — 2026-10-30

This section preserves the original implementation checks and delivery failure.
The later software acceptance evidence above supersedes its hosted-flow blocker.

`tests/test_pairing_stages.py` and updated normal pairing/durable/synthetic
regressions cover code-only/legacy posts, invalid/expired/used/claimed devices,
pending-only activation and clean redirect, stage expiry, post-await expiry and
upstream logout, cross-device tampering, replay, cookie/tab changes, strict origins,
non-ASCII CSRF, password retry, bounded grants/guesses/login attempts and concurrent
submissions with one upstream authentication. All upstream traffic is mocked.
The lab labels successful POST responses `http-accepted`; status 200 at code check
does not mean authentication succeeded. Its separate paired-session count remains
the session observation.

Actual connected Chrome (`Mein Chrome`, default 2560-pixel width) operated the
normal companion form using native visible controls. Invalid code showed recovery
with no credentials; a valid code revealed blank credentials; wrong password
returned cleared retry fields; a correct retry displayed TV paired. The pending
code came from the normal visibly rendered `/msx/pair.json` response, not an MSX
screen. A second form tab caused the older credential submission to show Form
expired and manual entry. Use a different TV code returned manual entry. The
recovery link's initially low-contrast visited color was corrected; the final
light link and keyboard focus outline were visually inspected with the full
heading present. Empty stage and success screenshots remain local under ignored
`.lab/reports/`, with no pairing values or credentials in those images.

A clearly labeled **local activation-route fixture**, absent from shipped source,
created an ordinary pending device and linked from loopback `127.0.0.1` to
`localhost`. Initial Strict handoff cookies returned manual entry after the
cross-site redirect; Lax fixed that actual Chromium failure. The rerun visibly
skipped code entry at clean `/pair` and native synthetic credential submission
displayed TV paired. This verifies the receiving route only, not QR rendering or
official-MS​​X pairing integration. No cookie/security bypass was used.
Independent review additionally caught invalid activation recovery retaining a
no-referrer URL; a native Chrome rerun after the clean-redirect fix visibly
advanced from invalid-link recovery to credentials using a current code. Three
new regressions cover invalid ASCII/non-ASCII/Unicode links without reflecting
them in cookies or retaining them on the form URL. Empty recovery and credential
screenshots are local; no submitted code or credential appears in those images.

A requested 390x844 viewport override still reported/rendered 2560-pixel width;
it was reset. No new mobile-layout pass is claimed. `browser-verify` was not
available; the supported connected-Chrome API and inspected screenshots supplied
the form evidence. The normal lab launcher opened the official hosted runtime;
it visibly showed Data Load Error / Start Error. The final process's redacted
report observed no `/msx/pair.json` request, one synthetic authentication returning
200, and one paired session from the separate activation-form check. No runtime
pairing code or private library rendered, so the failure is delivery evidence
only; no exact TLS/network cause is inferred here. All owned tabs/listener were
closed and the viewport reset. At that checkpoint, full normal private hosted-MS​​X
delivery and physical TV acceptance remained unverified; HTTP tests/fixture routes
did not replace them. The later HTTPS evidence above resolves only the software
pairing flow, with physical TV still unverified.
No real Jellyfin/account, production host, TLS trust change or TV action occurred.
