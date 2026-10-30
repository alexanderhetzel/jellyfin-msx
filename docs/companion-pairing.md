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

## Activation link contract and privacy

`/pair?activation=…` accepts the device's independent random pending-only secret,
never its private session capability. Valid links skip manual entry. QR rendering
and MSX exposure of the link belong to #14; this milestone implements the receiving
route. Activation validates pending state twice, before a 303 redirect and when
rendering credentials at clean `/pair`. A transient HttpOnly `pair_activation`
cookie carries only that activation secret, expires no later than pending expiry,
and is deleted after the handoff. Its `SameSite=Lax` permits a cross-site top-level
GET redirect; it does not authorize a POST. The credential CSRF cookie remains
HttpOnly, `SameSite=Strict`, Secure outside explicit HTTP development, and scoped
to `/pair`. Every POST requires the exact configured Origin and double-submit
CSRF validation. Grant-to-CSRF binding is additionally checked server-side.

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

## Evidence and remaining acceptance

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

A requested 390x844 viewport override still reported/rendered 2560-pixel width;
it was reset. No new mobile-layout pass is claimed. `browser-verify` was not
available; the supported connected-Chrome API and inspected screenshots supplied
the form evidence. The normal lab launcher opened the official hosted runtime;
it visibly showed Data Load Error / Start Error. The final process's redacted
report observed no `/msx/pair.json` request, one synthetic authentication returning
200, and one paired session from the separate activation-form check. No runtime
pairing code or private library rendered, so the failure is delivery evidence
only; no exact TLS/network cause is inferred here. All owned tabs/listener were
closed and the viewport reset. Full normal private hosted-MS​​X delivery and physical TV
acceptance remain unverified; HTTP tests/fixture routes do not replace them.
No real Jellyfin/account, production host, TLS trust change or TV action occurred.
