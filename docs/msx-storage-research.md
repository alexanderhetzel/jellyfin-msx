# MSX storage and startup research — issue #11

This research owns the browser storage/startup contract. Persistence implementation
belongs to #12. Physical Philips comparison belongs to the final hardware gate #4.
No browser result establishes SAPHI storage retention.

## Observed storage lifecycle — 2026-10-30

**Browser-tested / device-unverified:** official MSX 0.1.167 (web), connected
Chrome extension, existing profile `Mein Chrome`, Windows. The running Chrome
executable reports 156.0.8078.80; the probe's reduced user agent reports
Chrome/156.0.0.0. Top-level origin: `https://msx.benzac.de`; plugin origin:
`https://raw.githack.com`. The same profile and origin pair was retained across
the observations; browser partitioning was not disabled or inspected directly.
The public API reported storage type `default`. No cookie/permission setting was
changed. This characterizes this origin pair/profile, not a dedicated operator
origin or browser-process restart.

The pinned plugin revision for the storage matrix is
`2206a290fab803d7d343ac293289caedfb9deb0f`. The probe was loaded by clicking an
ordinary MSX `content:request:interaction:init@…` control from a public inline
launcher (`input=2`, `init=1`, `suspend=0`, `animate=0`). It does not initialize or
write the marker when opened. All storage mutations below used actual MSX clicks.

| Action | Public-API readback / visible result |
| --- | --- |
| Open probe before writing | ABSENT; no mutation attempted |
| Click Write synthetic marker | PRESENT; separate last write outcome PRESENT |
| Click Reload content (`reload:content`) | PRESENT; same plugin instance |
| Navigate to harmless MSX page, Back, click Read marker | PRESENT; same plugin instance; focus returned to navigation row before reading |
| Close both owned MSX and standalone probe tabs; create a new MSX tab; click Open probe | PRESENT before any write; new plugin instance and No mutation attempted |
| Click Write corrupt marker | CORRUPT; explicit re-pair message |
| Toggle injected unavailable adapter; attempt Write | UNAVAILABLE (injected), including the separate failed-write outcome |
| Toggle adapter back | Prior CORRUPT value remains; failed injected write did not replace it |
| Click Remove probe marker | ABSENT; separate remove outcome ABSENT |

The entire Chrome process was not restarted. Browser data clearing, quota denial,
OS restart, app update and physical standby were not exercised. Injected failure
is application behavior, not proof of Chrome's response to genuine storage denial.

Screenshots were captured and visually inspected for absent, write/readback,
reload/readback, Back/readback, reopen-before-write, corrupt, injected-unavailable
and cleanup states. Sanitized images remain under ignored `.lab/reports/` with
`issue11-` prefixes. Text and controls were readable, without clipped main labels,
and MSX selection/focus outlines and scroll position were visible. The normal
browser window changed size during the run (captures include 2174x1241 and
2560x1249); no viewport override was applied. A Back/read screenshot caught a
transient busy overlay; the subsequent stable reopen screenshot independently
shows PRESENT. Faint probe-only diagnostic HTML is visible behind MSX at the
top left; this is a cosmetic probe limitation, not a spotless-layout claim.
Wheel scrolling and DOM-backed clicks worked. Keyboard `body.press` failed in
the automation API; the down chevron is an indicator rather than an actionable
control. Neither establishes a physical remote-control defect.

Delivery used the source renderer's
[documented development endpoint](https://raw.githack.com/) for our already public
HTML, not a new service deployment. Its ordinary repository confirmation was
accepted through the UI; no anti-phishing cookie/header bypass was used. A
standalone HTML response was verified as `text/html`. Only our probe and public
API examples were inspected; the proprietary MSX runtime was never copied,
hosted or modified. No credentials, capabilities, certificate imports, browser
security bypasses or operator-server requests were involved.

## Public API and probe

The independently authored `tools/msx_storage_probe.html` uses the vendor-hosted
[plugin API](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference),
not a copy of the proprietary application. An
[interaction plugin](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin)
receives MSX requests and returns content for MSX itself to render and control.
The probe accesses `TVXServices.storage` after `TVXPluginTools.onReady` and checks
readiness. It uses `get`, `set` and `remove` for exactly one synthetic key:
`jellyfin-msx.research.issue11.marker.v1`. No enumeration, global clear, direct
browser storage calls, credentials or actual authorization are involved.

The marker is a fixed versioned synthetic string. Other values are classified
as corrupt. A deliberate adapter-unavailable switch exercises application failure
handling; it does **not** disable browser storage or establish a genuine browser
quota, permission or storage-denial result. The last mutation outcome and fresh
readback are separate, so thrown/injected mutation failures remain visible even
when a later read succeeds. A silent no-op write of the same already stored
marker cannot be detected by immediate readback; retention evidence comes from
the separate close/reopen read-before-write test, not a promise of durable writes.

[Start Action](https://msx.benzac.de/wiki/index.php?title=Start_Action) documents
startup `action`/`data`, replacement of the default `home` action, and skipping
the start action when stored content is restored after returning from a link.
[URL Parameters](https://msx.benzac.de/wiki/index.php?title=URL_Parameters)
documents `init=1` as ignoring stored content state and `suspend=0` as preventing
automatic suspend/resume. These conditions must accompany browser observations.
The plugin instance timestamp is diagnostic state, not a device ID. The earlier
matrix revision also displayed a startup-commit counter, which remained zero
with the manual launcher; it is not used as evidence that a startup hook ran.

[Storage caveats](https://msx.benzac.de/wiki/index.php?title=Tips_%26_Tricks)
describe platform-specific wrappers and retention problems. A storage type and
successful immediate readback are not promises of persistence, secrecy or encryption.

## Candidate restore contract for #12

The following is a design contract, not an implemented persistence feature:

1. Keep a public, non-secret bootstrap URL in MSX setup. A startup interaction
   plugin reads its own versioned credential record through the public storage
   API after an explicit Continue interaction, then renews authorization with the
   backend over HTTPS. Automatic plugin bootstrap is **unresolved** in this
   configuration; #12's goal of returning directly to a library remains an
   additional observable requirement, not a pass inferred from this manual path.
   Restored views and
   every private request must still pass backend authorization; cached content
   and a public MSX device identifier never authorize access.
2. Host that plugin on a stable HTTPS origin controlled by the operator. Origin,
   top-level site, profile/partition and platform changes may lose storage.
   A shared third-party source preview origin is unsuitable for real secrets.
3. After normal companion pairing, issue a cryptographically random device
   renewal secret, independent of Jellyfin tokens and short-lived route
   capabilities. Keep only a verifier/hash with device/account binding, absolute
   expiry and revocation state in durable backend storage. Do not store Jellyfin
   passwords or tokens in MSX storage. Secrets travel in HTTPS request/response
   bodies, never in the public start URL, query, diagnostics or logs. Do not log
   renewal bodies. Existing capability URL privacy requirements remain in force.
4. Renewal grants a new short-lived session only after validating the record,
   expiry, revocation and account authorization. Rotate renewal secrets with
   bounded crash/retry handling; do not accidentally create an unlimited replay
   grace period. #12 must specify transaction/concurrency behavior and validate
   the actual public API request/response path before shipping it.
5. Missing, malformed, unsupported-schema, unreadable or failed-write state
   produces an explicit non-durable/re-pair path. Never infer authorization from
   marker presence or silently substitute a device ID. Network failure offers
   retry without deleting a valid credential; definitive expiry/revocation
   requires re-pairing. Bounded readiness/renewal timeouts must leave a usable UI.
6. Disconnect revokes the backend device credential before best-effort deletion
   of its owned local key, and immediately denies its private sessions. Local
   cleanup failure must not retain authority. Backend restart must preserve
   revocations/expiry; clearing server state must fail closed. Session loss and
   upstream Jellyfin-token lifecycle remain separately specified backend concerns.

Persistent device storage is a bearer-secret exposure boundary. Other scripts on
the plugin origin, malicious origin content, browser-profile access, a compromised
device and the MSX/plugin trust chain may expose it. It is not a hardware keystore.
Use a narrowly trusted origin, least-privilege Jellyfin account, bounded expiry and
server revocation. A copied credential remains replayable until revoked/expired;
rotation mitigates but does not establish device attestation. Do not claim a
device-bound secret or resistance to a compromised TV.

## Startup limits and reproduction

Automatic plugin requests during startup were not demonstrated: early inline
startup/reference attempts timed out, and a fetched JSON root with a direct
`content:request:interaction:init@…` startup action reached **Data Load Error**.
The fetched root's content name appeared in the MSX window title, distinguishing
it from the inline launcher. A load-and-commit startup variant remained at the
launcher. The negative fetched root is reproducible at revision
`a020c61b18ed5ff84b0417c153e0bd4275cb58c4` (`tools/msx_storage_start.json`,
plugin revision `2206a290…`). No proprietary runtime internals were inspected
to assign a cause. This does not establish that automatic startup is universally
unsupported, nor that the same result occurs on an operator-controlled origin.

The final probe separates the public startup action from the storage entry:
`tools/msx_storage_start.json` uses `content:data` to display a distinctive
startup-executed launcher, then an actual **Open storage probe** interaction
loads the plugin. The root also has a distinct fallback headline/control so
startup execution is observable independently of plugin storage. The final
plugin hides its diagnostic background when embedded; storage operations and
the unique marker key are unchanged from the initial matrix.

**Final visual recheck:** fetched root revision `b8515be7…` and HTML `aa8765c…`
displayed **Startup action executed - open the storage probe** on initial load
and again after closing/reopening the owned MSX context. This is an actual
`content:data` startup action, distinguishable from the root's fallback page.
Clicking Open storage probe first showed ABSENT; Write then showed PRESENT;
Reload content retained PRESENT. After closing both owned contexts and reopening,
the startup launcher ran again and the manually opened probe read PRESENT with
a new plugin instance and No mutation attempted. Final Remove returned ABSENT.
Screenshots `issue11-startup.jpg`, `issue11-startup-reopen.jpg` and
`issue11-final-{absent,present,reload,reopen,cleanup}.jpg` were saved and visually
inspected. Main labels and focus were readable and unclipped, and the diagnostic
background text was absent. The final reopened tab had no captured console
errors/warnings. Normal renderer loading briefly displayed a busy indicator;
an early final-absent capture was replaced after loading completed. No marker
was left after the final cleanup. No other browser/MSX keys were inspected.

To reproduce, serve only the independently authored HTML and JSON over a public
test HTTPS origin with frame loading and JSON CORS allowed. Keep the plugin URL
in the root pinned to the intended source revision. The research preview root is
`https://raw.githack.com/alexanderhetzel/jellyfin-msx/b8515be7aae4488c71ecad619b30fd3b6131aca3/tools/msx_storage_start.json`.
It pins final HTML revision `aa8765c98927f9f38cb8b1059634c6b22ffe2c71`.

```text
uv run python -m tools.msx_storage_probe PUBLIC_HTTPS_ROOT_URL
```

Open the printed official-MS​​X URL through connected Chrome. Observe the startup
headline, click Open storage probe, inspect ABSENT/PRESENT before writing, and run
the matrix above with MSX controls. Scroll the list using the mouse wheel; each
wheel action may move one selection. Keep mutation outcome and fresh readback
visible in screenshots. Close all owned probe contexts before the reopen test.
Remove the exact probe key and verify absence at the end; never clear an origin.

The helper accepts only HTTPS URLs without URL credentials. Supply only public
probe URLs: it cannot determine whether an arbitrary URL path contains a secret.
The shared renderer sees source URLs and serves arbitrary repository HTML; it
provides no credential isolation or production availability guarantee. Repeat the
test on the deployment-controlled origin before relying on that origin's
storage/loading behavior in #12.

## Later physical comparison — #4

Use the same reviewed probe and record TV model, firmware, MSX version/platform,
probe revision, delivery origin and exact actions. Write only the synthetic marker.
Read it after content reload, navigation Back, app exit/reopen and standby/wake;
record present/absent/error and whether the startup action ran again. Re-pairing
must remain available when it did not. Record power-cycle separately if tested.
Clear-data and app-update cases require an appropriately authorized test scope
that preserves existing user settings; never factory-reset or change firmware as
an implicit research step. Clean up only the probe key and verify absence.

Shared API syntax, JSON rendering and application decisions are expected to match
on compatible MSX versions, subject to the target engine supporting the plugin.
Storage readiness, lifetime, partitioning, plugin loading, app restoration and
standby behavior require physical comparison. Browser UA/platform overrides do
not substitute for that evidence.
