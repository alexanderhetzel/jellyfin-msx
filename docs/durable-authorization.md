# Durable server authorization — issue #12

## Opt-in MSX client — 2026-10-31

### Foreground result and synthetic observation boundary — 2026-10-31

**Diagnostic run 9 — actual entry failed / device-unverified.** At reviewed
`25ff60f` on main `e46a4de`, the single granted normal automatic entry again
settled on Load Error / Data Load Error and Request timed out. Initial local-only
`remember_asgi` snapshot had zero received requests in every category. The final
snapshot was retained **before** closing the tab or stopping the fixture:

| Category | Received | Start send returned, HTTP200 | Final-body send returned |
| --- | ---: | ---: | ---: |
| `entry_content` | 1 | 1 | 1 |
| `plugin_html` | 1 | 1 | 1 |
| `start_config`, `plugin_script`, `authorization_pair`, `authorization_renew`, `private_home` | 0 each | 0 each | 0 each |

Every aborted/incomplete counter was zero at that snapshot. Direct content entry
does not require a start-configuration request. This establishes successful ASGI
send returns for the remembered root and plugin HTML at this observer boundary;
it does not establish Chrome delivery, document completion or parsing. No own-JS
or subsequent authorization/home request was observed here. Cached execution,
earlier middleware/transport rejection, blocked parsing or off-origin SDK loading
are not distinguished by these aggregates; none is claimed as the cause.

The sanitized existing runtime logs show root Data ready, startup action,
interaction `init` request and plugin-load attempt to the correct own target.
The own-frame marker read again reached a selector deadline, leaving lifecycle,
handler, storage and callback stages unknown. No Network/CDP observation or
browser HTTP status was collected. No Retry, ForceInit, warm-up, credentials,
restart or restore matrix ran. Initial/final count-only JSON snapshots and the
inspected 2560x1249 sanitized error image are retained under ignored `.lab/reports/`.
Raw pixels remained RAM-only. The original 900-second total/180-second startup
bound was retained, never restarted. Supervisor session93439 exited zero/stopped;
cleanup at 15:57:22 UTC / 16:57:22 Vienna found all nine exact owned PIDs, listener
18092, control and own helpers absent; the sole owned tab was closed. No active
test resources remain. Startup is still unaccepted and its cause unresolved.

#### Source audit after run 9

Remember, lifecycle and subtitle shells all declare the same classic vendor SDK
first, without async/defer, then their same-origin adapter with defer. The
[published MSX example](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin)
also loads the vendor SDK before registering the handler. The
[HTML script rules](https://html.spec.whatwg.org/multipage/scripting.html#attr-script-defer)
make the first script parser-blocking and defer adapter execution until parsing
finishes. But [speculative parsing](https://html.spec.whatwg.org/multipage/parsing.html#speculative-html-parsing)
can fetch later resources while a script blocks the main parser. Therefore zero
observed own-script requests neither proves an SDK stall nor necessarily follows
from one. Accepted playback/subtitle ordering does not validate remembered startup.

The current shell's exact hosted SDK source is explicitly allowed by its CSP,
and the own adapter is covered by self. The declared adapter has a JavaScript
content type and no-store response, as mocked route tests verify. Other plugin
shells allow the broader vendor origin; remembered startup retains its narrower
exact path. This source comparison cannot establish the actual browser's response,
redirect chain, effective policy, resource loading or SDK behavior. No CSP,
script-order, body, nonce or timing change is justified by these counters.

Execution-only VM counterexamples distinguish own-code stages: absent SDK global
sets marker3 then raises ReferenceError; withheld SDK readiness leaves marker3
without registration; delivered readiness with missing interaction interface sets
marker7 then raises ReferenceError. None dispatches an authorization request. The
two missing-interface witnesses and existing delayed-readiness guard pass within
**24 Node tests**. They simulate no HTML parsing, fetch, cache, CSP or browser
delivery. In particular, no authorization POST does not prove no handler ran.

There is also an observation dependency: the runtime marker read located `body`
before reading its document's root attribute. The root marker is declared before
the blocking SDK; `body` appears after the scripts. A body-selector deadline can
therefore leave the root unobserved even if a committed document is accessible.
All prior marker values remain unknown. A future fixed-source observation should
target `html` directly, then obtain categorical document readiness and script-element
presence only if accessible. Distinguishing an SDK stall from document-delivery/
parse failure additionally needs covered browser-side resource completion/error
or CSP-violation evidence from the actual child document. Server counts and VM
execution cannot supply that evidence; unavailable child inspection remains
unknown. No new runtime grant or product variant follows from this audit.

The observation-plan refinement has a local **constructed DOM** counterexample,
using Python's standard-library DOM: an own marked `html` containing `head` and
no `body` makes the old body-first lookup unavailable while direct root attribute
access returns1. Count-only result is retained at ignored
`.lab/reports/issue12-head-only-dom-witness.json`. This verifies the lookup
prerequisite, not browser parsing, attachment, child-target accessibility or a
live SDK stall. It does not turn any historical unknown marker into a value.

A future connected-Chrome observation should use the exact observed own iframe
and its marked `html[data-testid="jellyfin-msx-lifecycle"]`, then documented
`getAttribute("data-jellyfin-msx-lifecycle")`. Require readable attachment, without
a body, visibility or load-complete prerequisite. Keep the raw result in RAM;
emit only a validated fixed marker bitmask (odd integer1..127), otherwise unknown.
If ordinary root-scoped read-only DOM evaluation is accessible, additionally
emit only readyState from loading/interactive/complete/unknown, body presence,
and presence of the two exact declared script elements. Do not emit their URLs,
arbitrary attributes, DOM text, runtime globals, storage, event history or errors.
An unmatched/unreadable own root stays unknown; an initial about:blank root is
not an own-document observation. Script-element presence does not imply fetching
or execution; even readyState complete does not prove successful resource loads.
The plan uses no vendor internals, CDP, injection, policy bypass or new endpoint.
It still needs an exclusive runtime grant; no additional attempt has occurred.

**Actual entry unaccepted / device-unverified.** The single normal-entry run at
`e5e2153` parsed root data, executed its startup action, dispatched interaction
`init` and logged a plugin-load attempt to the correct own HTTPS HTML target.
It then settled on Load Error / Data Load Error and Request timed out. The own
frame marker read hit a selector deadline: HTML/JavaScript/SDK/handler/storage/
callback stages remain **unknown**. This run used no Network/CDP observation and
provides no HTTP-status or paused-document evidence. Earlier runs' transport
observations cannot be attributed to it. No Retry, ForceInit, warm-up, credentials,
restart or remaining restore matrix ran. The sanitized error image was inspected;
raw pixels remained in RAM. At 15:39:51 UTC / 16:39:51 Vienna, explicit stop had
returned exit zero/stopped, all nine owned PIDs/listener18092/control/helpers were
absent and the sole owned Chrome tab was closed. The timeout's cause is unresolved.

The existing leaf-name lab counters omit this startup boundary and conflate
companion `/pair` with authorization pairing. A synthetic-only extension to the
existing `/__lab/report` adds `remember_asgi` for the `remember` scenario:

| Fixed category | Method and whole route shape |
| --- | --- |
| `start_config` | GET `/msx/start.json` |
| `entry_content` | GET `/msx/remember.json` |
| `plugin_html` | GET `/msx/remember.html` |
| `plugin_script` | GET `/msx/remember.js` |
| `authorization_pair` | POST `/api/device-authorization/pair` |
| `authorization_renew` | POST `/api/device-authorization/renew` |
| `private_home` | GET `/msx/device/{one nonempty segment}/home.json` |

Each category counts entry into the observation middleware, first response-start send returned (fixed
status allowlist plus `other`), first final-body send returned, aborted requests
and incomplete requests. Aborted means app/send raised, including cancellation,
even after final send. Incomplete means the app exited without a returned final
body send; in-flight requests are not yet classified. These counts can overlap.
Duplicate messages are still forwarded once each, but each request increments
each start/final counter at most once. Values saturate at one million. Snapshots
contain only fixed keys and counts; unknown routes/methods are ignored. The
observer retains no paths, queries, capabilities, headers, body bytes, timestamps
or exception text, never drains receive and passes original messages unchanged.
Existing lab fields retain their prior meanings; this is no production telemetry.

The observer is user middleware inside Starlette's outer ServerErrorMiddleware.
The synthetic TrustedHostMiddleware is also outside the observer: a rejected Host
can return 400 without incrementing even `received`. Thus this is not a socket
request counter. An outer-generated 500 bypasses it: received/aborted/incomplete may increase with
no observed response start even though the client receives 500. Counters reset
on backend restart and aggregate all callers, without browser attribution.
Status 200 can contain an MSX authorization-error envelope; it is not proof of
authenticated libraries. A final ASGI body send returning does not prove browser
receipt, document completion, JavaScript execution, SDK registration, storage,
callback completion or visible rendering. Off-origin SDK requests are unobserved.
Zero counts cannot exclude caching or failure before this backend. A future
diagnosis run must retain these limits and keep the startup source fixed.

### Startup-only foreground entry — 2026-10-31

**Implemented / automated-tested / device-unverified; actual entry failed above.**
The public startup document is now ordinary content with usable Retry/Pair item
definitions, without `reference` or `ready`. Its single startup action is
`[home|content:request:interaction:init@` followed by the same own plugin URL and
`]`. The published [Start Action](https://msx.benzac.de/wiki/index.php?title=Start_Action)
replaces default home, so the explicit home preserves that scene step before the
foreground content request. Unlike a ready hook, this is a startup action, not an
action attached to every content-ready notification. Private Pair/home/disconnect
pages contain no startup action, reference or ready hook.

The public contract skips the action if the context menu is open at startup or
start data is restored after a link. Those are explicit exceptions, not passes.
The [home action](https://msx.benzac.de/wiki/index.php?title=Internal_Actions)
may open the context menu if the main scene is already active. Normal fresh entry,
visible fallback and error/Back access to Retry/Pair therefore need actual runtime
verification; local JSON tests do not emulate runtime scene state or promise that
recovery navigation has passed. No ready/replace sequence, delay, background loader,
CSP/body change or ambient-module guard is combined with this design.

A second independent protocol review confirmed that the prior reference syntax
is valid but startup reference ignores its root fallback items. A proposed
ready/replace composition cannot prove one-shot dispatch from the published API:
ordered actions do not promise replacement completion before a request callback.
The chosen startup-only foreground design avoids that extra ordering assumption.
It is a product entry/recovery change, not proof of the previous timeout's cause.
The separate ambient-CommonJS early-return witness and minimal guard proposal
remain isolated; no actual ambient module or guard-only runtime fix is claimed.

### Earlier callback-order comparison with accepted lifecycle/resume — 2026-10-31

**Implemented / automated-tested / device-unverified; actual startup unaccepted.**
The bounded audit compares this client with accepted #18/#19 at main `e21d103`:

| Boundary | Comparison and result |
| --- | --- |
| Startup | #12 then used the documented public content-root reference; #18/#19 enter a private content-request action after normal pairing. Their acceptance does not validate automatic remembered startup. |
| SDK registration | Both register inside `TVXPluginTools.onReady`, then call `TVXInteractionPlugin.init`, using the same vendor SDK tag and deferred own script. |
| Delivered init | Lifecycle handles it directly with an empty `ready` callback. #12 unnecessarily waited for a separate handler-ready notification after SDK registration. That extra event-order dependency is removed. |
| Storage | Only #12 requires renewal storage. Its actual `storage.isReady` check and bounded polling remain; handler notification is not a substitute for this check. |
| Completion | Lifecycle init returns a page; its resolver completes asynchronously. #12 still returns only its terminal pair/recovery/library page after exact-save/readback and authenticated home. Absolute deadline, epoch and singleflight guards remain. |
| Authority/policy | Lifecycle playback generations/leases are separate from durable authorization. No lifecycle lease/background renewal, URL context, CSP allowance or timing variant is copied. |

The public [handler contract](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin)
defines request and readiness callbacks without promising their ordering. A
delivered request is already inside the registered SDK handler. The regression
first failed on the old extra gate, then completed both missing-record pairing
and stored-record renewal/home without invoking handler.ready. Later/repeated
ready notifications start no work. Unavailable storage still returns bounded
recovery; an explicit later request may retry storage without replaying an
uncertain renewal. The earlier test called outer SDK readiness but mislabeled a
missing handler notification as missing SDK; that test is corrected.

This is a robust request-contract repair, **not** proof that the earlier init
reached our handler or that this gate caused the HTTP-200/paused-document failure.
All failed runs, unknown lifecycle values and the prior-visit counterexample
below remain valid. No browser/relay or environment variant was used in this audit.

Its later focused runtime check at `e597045` did not pass: direct normal startup
without ForceInit/Retry/warm-up settled on Data Load Error / Request timed out
before pairing. The own-frame marker read returned a selector deadline only;
no handler entry is established. No CDP/Network/viewport override was used, so
no HTTP or explicit paused-response evidence is claimed for this run. A readable
sanitized default2560x1249 error capture was inspected; the initial overmasked
preview is excluded and raw pixels remained RAM-only. Explicit stop at
14:51:04 UTC / 15:51:04 Vienna returned exit zero/stopped; all nine owned PIDs,
listener/control/helpers were absent and the sole owned tab closed. No credentials
or full restore matrix ran. The source repair remains valid defensive callback
handling, not actual automatic-start acceptance or a proven historical root cause.

**Implemented / automated-tested / device-unverified:** `MSX_REMEMBER_DEVICES=true`
requires the external key/database configuration below and selects a public
`/msx/remember.json` startup document. The default remains ordinary RAM pairing.
The independently authored plugin shell/script live on the portal's own HTTPS
origin. Only its exact HTML route permits framing by the official MSX web origins;
other pages retain frame denial. Script policy allows our own script and the
vendor-hosted public API library; connect policy is same-origin. No proprietary
runtime is copied, and no inline/eval exception or cross-origin POST is added.

The startup document uses the startup-only foreground action described above;
its Retry control uses the same content-interaction request explicitly.
The handler is registered after outer SDK readiness; `handler.ready` is
diagnostic-only. One accepted `init` request waits for actual storage readiness,
ordinary pairing or renewal, exact save/readback and authenticated home,
then returns one terminal page through its callback. Progress pages are not pushed
against the foreground request. Explicit later controls still use `showContent`.
Unknown or simultaneous requests receive null without starting another renewal;
a later sequential explicit init refreshes authority rather than serving an old
cached library forever. There is no hidden background renewal.

Storage polling retains its five-second bound and each XHR its fifteen-second
bound. An aggregate 25-second init deadline also covers delayed SDK/storage and
sequential requests. Timeout returns recovery, blocks silent renewal replay and
invalidates the attempt's late callbacks, preventing delayed save/navigation.
Absolute deadline checks at readiness, dispatch, completion and rendering also
reject late work if the timer callback itself has not run. The deadline uses the
monotonic performance clock where available, otherwise the local wall clock.
An upstream renewal may already have committed; uncertain authority requires
explicit re-pairing. A plugin that never loads cannot run this deadline: normal
runtime request error/retry is the delivery boundary. The earlier reference-based
design ignored root fallback items; the current design retains them as ordinary
content, while their actual accessibility on error/Back remains unverified.
Actual automatic entry/reload/reopen/restart acceptance remains separate;
this callback-contract correction does not prove a fix for paused transport.

The first actual request-contract run at `cb0f162` failed normal automatic entry:
MSX displayed Data Load Error and existing sanitized runtime logs reported init
request/plugin-load attempt followed by Request timed out. No pairing/enrollment
was reached. Body-marker reads timed out. One HTML request and matching ExtraInfo
HTTP 200 were observed, without established document completion or child-target
coverage; no own-JS/SDK events were captured. Network cleanup explicitly reported
a Browser Use paused document response. The owned tab closed and explicit stop
at 12:27 Vienna time left all nine recorded PIDs/listener/control/helpers absent.
The run stopped at this first functional block, without Retry, credentials,
restart or a source change. Callback unit tests and CI remain software evidence;
they do not override this failed actual automatic-start result.

The next narrow observation variant normalizes the empty plugin body to ordinary
markup, matching the published plugin example and subtitle bridge. Hidden-body
causation is unproven; this changes no script, CSP, authentication or scheduling.
The body stays empty and the fixed lifecycle marker stays on the root. Actual
startup and observation outcomes must be attributed to the tested variant.
At exact `cde5574`, ordinary automatic startup again failed with Data Load Error /
Request timed out before pairing. The body-marker read stayed unknown. One HTML
request and ExtraInfo HTTP 200 were observed, without established document
completion/child coverage; no own-JS/SDK events appeared. Cleanup commands reported
a paused document response, then the owned tab closed. Explicit stop at 12:35
Vienna time left all nine PIDs/listener/control/helpers absent. The blank capture
is excluded; settled DOM/runtime-error/category evidence is retained. No Retry,
credentials, restart or matrix ran. This comparison ends without another source
variant, a successful startup claim or a proven external/product root cause.
Retained run-2 actions show healthz and a top-level public plugin-shell visit
before normal MSX startup, which still left fallback. A later shell visit plus
explicit Retry correlated with manual renewal. Thus prior top-level visit was
not sufficient in that run; the subtitle workflow's earlier companion visit is
only a correlation, not a warm-up prerequisite or source-fix justification.
Run-6 cleanup was verified at 11:35:24 UTC / 12:35:24 Vienna.

Normal current companion QR/manual two-stage CSRF pairing is unchanged. The
plugin uses same-origin body-only pair/status endpoints and keeps the pending
session in RAM. Pending Continue redisplays the normal waiting instructions;
authenticated Continue enrolls, verifies the exact newly stored renewal value and
generation, and only then opens private libraries. Storage contains only version,
renewal secret, absolute expiry and generation. User-scoped Jellyfin tokens and
short RAM sessions never enter this storage record.

Before each replacement write, the client checks that the complete prior record
is unchanged. It then reads back and privately compares the exact new serialized
value/generation. Silent no-op writes cannot pass on mere key presence. A losing
or uncertain request does not overwrite another context's newer record. Timeout
preserves local state and blocks automatic retry; a definitive 401 may remove
only the exact unchanged stale record. An early losing context can safely force
both contexts to re-pair; no successful durable client winner is guaranteed by
storage lacking atomic compare-and-swap. Failed verification prevents library
navigation and attempts authenticated cleanup of the just-issued RAM grant.

Only one key, `jellyfin-msx.authorization.v1`, is read/written/removed through the
public API. No enumeration/global clear or direct localStorage is used. Explicit
Create new code may clear that owned record and start normal pairing; unavailable
storage has an explicit Pair without remembering path. Missing/corrupt/expired
records never authorize a library. Clearing a lost record alone cannot revoke an
unknown server credential; bounded expiry and normal authenticated Disconnect
remain the server authority boundary.

The plugin owns startup/enrollment transiently. It has no timer, observer or
background renewal after entering libraries. Another explicit feature may replace
the interaction plugin; normal Back/private navigation does not reload bootstrap.
Public startup reload rotates the renewal and replaces old sessions, so it must
not run while another resolver still needs the old grant. Normal server
Disconnect/Confirm works independently of current interaction ownership. Any
remaining local renewal is denied and exact-record cleaned on next bootstrap.

The same portal origin/top-level MSX site/profile/partition shares a remembered
credential, as a browser device context. A second tab is not cryptographic device
isolation. Normal independently pending pairing grants remain separated; a copied
renewal is still a bearer credential. Physical installed-app framing, retention,
standby and remote behavior remain device-unverified in #4.

### Isolated synthetic restart verification

The startup-only `remember` scenario in `tools.synthetic_https` uses only
normal synthetic login, MockTransport, a private temporary directory, an external
synthetic Fernet key generated in supervisor RAM and SQLite synthetic upstream
token verifiers. It never reads operator configuration/environment secrets or an
OS credential store, and has no real-network Jellyfin fallback. The key travels
only through private owned stdin pipes, never argv/files/output. The fixture's
hashed upstream sessions survive a fresh backend process, modeling a separately
running Jellyfin without bypassing its synthetic authentication.

The local-only `--restart-backend` signal replaces the owned backend under the
same original relay lifetime (at most 900 seconds including 180-second startup).
The supervisor continuously holds the exclusive loopback listener; private Windows
socket descriptors are duplicated to exact owned child PIDs. The vendor wrapper
also holds a duplicate until its tunnel stops, including parent-EOF cleanup.
Restart never exposes a free relay port, changes the origin, extends the original
deadline or adds a public mutation endpoint. Replacement readiness is bounded by
30 seconds and the remaining original deadline. JobObject/EOF/PID cleanup and
verified-TLS/no-redirect/no-host-config safeguards remain.

Independent pre-launch security review identified and corrected an initial
released-listener gap. Actual Windows ephemeral-port tests deny competing binds
through two child-process lifecycles and the interval between them; mock tests
check vendor-stop-before-reservation-release and unchanged RAM key/deadline.
These are containment/source tests, not actual hosted MSX restoration evidence.

### First actual Chrome run and local restart correction — 2026-10-31

The later maintainer instruction explicitly selects connected Chrome for all
browser tests. One approved 900-second synthetic run reached verified HTTPS
readiness. Normal startup without `init=1` displayed the public Opening Jellyfin
fallback; only the visible Retry control loaded normal pairing. Continue then
displayed Waiting for pairing. This is **not** automatic-startup acceptance.
No credentials were submitted and no enrollment/renewal occurred in that run.

A screenshot mask initially missed the synthetic pending code's whitespace form.
The saved capture was overwritten with a conservative whole-panel mask and visually
verified; no QR/code value is retained in the report. An approved backend restart
was immediately requested to invalidate the pending session, but hit its fixed
restart-readiness timeout. The supervisor destroyed its backend, synthetic key and
temporary state and exited; all nine recorded owned PIDs, listener and control
directory were absent. Both owned tabs closed. Main-tab CDP cleanup was blocked
by a Browser Use paused-document response; closing the owned tab cleared its
tab-scoped observations/viewport. No real credentials/server or TV was involved.

A bounded local-only ephemeral-port diagnosis reproduced first Uvicorn health
success followed by restart health failure while exclusive reservation remained.
Uvicorn's installed Windows default uses Proactor/IOCP. The
[Windows IOCP contract](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-createiocompletionport)
ties completion-port association to a process and warns about sharing associated
handles. The inference was checked by selecting the standard SelectorEventLoop
through Uvicorn's custom loop factory **only in the synthetic remember backend**.
Two actual fresh Uvicorn processes then both served health, exited zero and denied
competitor binds throughout. No global event-loop/security policy or reservation,
TLS, EOF, JobObject or original lifetime guard changed. Independent affected
source review repeated six focused loop/socket/EOF/deadline tests successfully.
The following slotted run exercised the corrected real backend restart.

### Second actual Chrome run — 2026-10-31

The later focused diagnostic adds only a RAM DOM bitmask on the own plugin's
`html` element, `data-jellyfin-msx-lifecycle`: 1 = document root parsed,
2 = own adapter script entered, 4 = SDK onReady callback entered,
8 = handler registered, 16 = handler.ready entered, 32 = boot entered,
64 = showContent requested. Flags accumulate; 127 means all boundaries were
entered, not that MSX displayed the requested content. The marker has no secrets,
context, URLs, storage, logging or telemetry. It resets with each document and
does not change startup scheduling/authentication. A delayed-SDK adapter guard
checks the boundary progression.
With request/response startup, automatic content is returned through the callback;
63 can therefore cover parsed/script/SDK/handler/boot without a `showContent`
call. Bit 64 still means an actual later `showContent` request, not callback delivery.

The focused run at `fecdc4e` displayed the original fallback and one iframe with
our public HTML source. The documented own-frame/test-ID attribute query failed
with a Playwright selector deadline; no marker value was measured. The frame's
`contentDocument` was unavailable across origins. This is **unknown**, not zero,
and does not locate document loading, adapter execution or content delivery.
No HTML/JS/vendor-SDK request/response categories were captured; no Network
observation or new server telemetry was enabled. No credentials, Retry, restart
or broad matrix were exercised. The known binary's pinned hash and exclusive
bind passed after correcting a missing default binary path; one retry retained
the original startup/total limits. Explicit cleanup at 11:57 Vienna time reported
session exit zero/stopped and all nine owned PIDs/listener/control/helpers absent;
the one owned tab closed. No speculative scheduling fix is inferred.

A further focused run at unchanged source `fecdc4e` used the documented generic
own-frame body evaluation to read the same root attribute; that also hit a
selector deadline. Network was enabled before normal startup navigation.
Its untruncated main category buffer observed one HTML request but no
responseReceived/completion/failure and no own-JS/SDK events. A matching
responseReceivedExtraInfo event reported HTTP 200 in a historical buffer marked
truncated. That proves an observed response-header status, not document completion.
Parent/OOPIF event coverage was not established, so absent events do not establish
absent execution. The root fallback remained and no lifecycle value was obtained.
Network.disable explicitly reported Browser Use resolving a paused document
response; body reads themselves reported selector deadlines. No interception or
security/scheduling change was used. The owned tab closed; explicit stop at
12:10 Vienna time exited zero/stopped with all nine PIDs/listener/control/helpers
absent. Only safe category/status evidence was retained. No credentials, Retry,
backend restart or broad matrix ran; no own-code root cause follows yet.

At source `95f1405`, official hosted MSX in connected Chrome used normal startup
without `init=1`. Automatic startup displayed Opening Jellyfin. Ordinary Retry
opened pairing; normal two-stage companion login with the synthetic account and
Continue reached private Jellyfin libraries at 1920x1080. The readonly encrypted
store aggregate was one record/generation zero. No raw renewal, key, token or
private capability was inspected or printed.

Normal reload again left the fallback. Ordinary Retry and a normal navigation to
the public plugin shell eventually reached libraries without a second credential
submission. The aggregate advanced to one record/generation one. Together with
the source's exact-save/readback navigation gate, this supports a manual renewal
observation. The settled DOM showed libraries; its blank/outgoing screenshot is
excluded. It does not establish automatic restoration. The enrollment library,
masked pairing and separate pending-context screenshots were visually inspected.

A normal close/reopen again left the fallback. The local supervised backend
restart succeeded with a fresh process, same origin/key/state/reserved listener
and original deadline. Subsequent Retry did not restore libraries and the
aggregate remained generation one. Several CDP/key operations reported Browser
Use resolving a paused-document response. The cause remains unresolved; no
runtime interception, trust/security bypass or bootstrap scheduling workaround
was used. Backend restart readiness is established; post-restart MSX restoration
is not. Normal Disconnect/re-pair was not exercised.

A third owned tab with an independently pending RAM pairing capability displayed
Waiting for pairing without inheriting access. This is capability separation in
the same Chrome profile, not independent remembered-storage/device attestation.
The relay was explicitly stopped around 09:55 UTC within its original 900-second
budget. Session exit was zero/stopped; all twelve recorded original/replacement
PIDs, port 18092 listener, control directory and own relay helpers were absent.
All three owned tabs closed and the second-tab viewport override was reset.
No operator state, real Jellyfin, media playback or physical TV was involved.

### Earlier browser-availability limitation — 2026-10-31

**Historical:** an earlier maintainer instruction required the integrated browser
for application verification. Fresh inventory exposed only the Chrome extension.
The documented `cua.createBrowserTab("iab", "about:blank")` call returned
**Browser is not available: iab**. No tab or public relay was created. The browser
slot was released without a Chrome fallback, permission change or repeated call.

At that earlier stage automatic startup, actual exact-generation storage, normal
reload/reopen, MSX restoration after backend-process restart, second pending-context
denial and visible revoke/re-pair were **not accepted** for this client. API restart/
isolation and real ephemeral Windows socket/process tests are not MSX passes.
The later instruction requires connected Chrome for all browser verification;
the unavailable IAB surface is no longer a blocker. Keep the client in a draft PR
and #12 open until the required actual MSX evidence exists.
Older marker retention/QR evidence remains attributed to its original revisions.

## Server authorization milestone — 2026-10-30 (historical)

**Implemented / automated-tested / device-unverified — 2026-10-30.** This opt-in
backend milestone does not yet remember a TV. The default MSX UI still uses RAM
sessions and does not call these APIs. Issue #12 stays open for controlled-origin
plugin delivery, automatic startup, exact newly saved renewal readback and visible
official-MS​​X reload/reopen/restart/re-pair scenarios. Physical retention is #4.

## Configuration and protection

Configure an absolute `MSX_AUTHORIZATION_DB` filename in an existing private
directory and independently supply `MSX_AUTHORIZATION_KEY` through an authorized
runtime secret store. Both are required together. The Fernet key encodes 32 random
bytes as URL-safe base64; provision it without printing or putting it in argv,
source, reports or the example environment file. It is hidden from settings repr.
Keep the same key across restarts. Missing/invalid/mismatched keys and unknown or
corrupt metadata/schema fail startup; there is no plaintext fallback. Key loss or
configured Jellyfin-server change requires deliberate state replacement/re-pairing;
automatic migration/key rotation is not implemented.

Persistence requires an HTTPS public origin even with development HTTP enabled.
That validates configuration, not deployed TLS. No host, trust or proxy is created.
The default remains disabled. `MSX_AUTHORIZATION_TTL` defaults to an absolute 30
days, allows 1 second through 90 days and never slides on renewal. Records and
RAM sessions each use the existing `max_states` bound. Expired rows are pruned
on enrollment. Deleting a running database fails requests instead of recreating
it; a deliberately new database on restart grants no old renewal authority.

The vetted [cryptography Fernet implementation](https://cryptography.io/en/latest/fernet/)
encrypts/authenticates user/token/server/device/expiry/verifier/generation binding.
Passwords, raw renewal secrets and RAM session capabilities are never persisted.
The SQLite index contains opaque device identity, SHA-256 renewal verifier,
generation and expiry; these must match the encrypted payload before authorizing.
Index metadata, record counts/file sizes and Fernet timestamps are visible.
Writes, rollback journals/WAL and SQLite backups contain ciphertext/verifiers,
not plaintext upstream tokens or renewal secrets. Protect all sidecars/backups.

On POSIX, the containing directory and existing database must have private
permissions; new files use mode 0600. Windows directory/file ACLs are the operator's
responsibility and are **not** verified by the application. Protect the key
separately. Privileged directory/file replacement, clock rollback and database
snapshot rollback are outside this boundary: an old backup may restore old
renewal/revocation state. Encryption provides no rollback resistance or device
attestation. Do not automatically fail over to an old database snapshot.

## Protocol and failure contract

Same-origin JSON POST APIs require exact `Origin` matching the configured public
origin and `Content-Type: application/json`, with only the named field. The 8 KiB
body limit applies before parsing, including chunked bodies. Responses/errors are
private/no-store/no-referrer. Independent secrets, rather than cookies, authorize
these APIs. Existing companion CSRF/cookie/single-use pairing remains unchanged.
CORS remains read-only GET/OPTIONS without cookies, with no cross-origin POST.

1. Normal companion pairing precedes POST `/api/device-authorization/enroll` with
   `session` containing its authenticated RAM capability. A device ID, code or
   pending pairing is insufficient. Success returns random 256-bit `renewal`,
   absolute Unix `expires`, and `generation: 0`. The original RAM session becomes
   bound to that durable record. Repeat enrollment returns 409; disconnect/re-pair
   recovers lost secrets without accumulating replacement records.
2. POST `/api/device-authorization/renew` with only `renewal`. SQLite
   `BEGIN IMMEDIATE` verifies expiry/binding, consumes its verifier and commits a
   random replacement verifier/new generation atomically. Independent connections
   contend with a two-second lock timeout. One concurrent use wins; no replay
   grace or sliding expiry exists. Before returning authority, the backend checks
   current Jellyfin Views access, then rechecks local authorization after the await.
3. Success returns fresh RAM `session`, replacement `renewal`, unchanged `expires`
   and new `generation`. RAM lifetime is at most configured session TTL/remaining
   durable lifetime. Every private session authorization checks durable existence,
   generation, expiry and user/token binding. Rotation invalidates earlier links,
   including linked RAM grants in another process.
4. Pre-commit storage failure rolls back without a replacement. Uncertain commit,
   lost response, failed upstream verification after consumption or failed client
   storage/readback requires re-pairing. Upstream restore rejection revokes the
   new record locally. Strict single-use authority sacrifices seamless retries;
   a lost success response can leave bounded inaccessible state until expiry.
   A copied credential can win a renewal race; it is a bearer secret.
5. Disconnect commits local deletion before best-effort upstream logout. Linked
   sessions fail on their next authorization check, including after restart or
   upstream logout failure. Storage errors must not claim a completed disconnect.
   Already-authorized/in-flight requests cannot be recalled. Previously delivered
   direct media URLs retain the upstream exposure in `media-token-security.md`;
   local expiry/rotation/revocation does not itself revoke that Jellyfin token.

SQLite does not make RAM pairing/sessions/rate limits multi-worker safe. Retain
the single-process/event-loop/worker deployment assumption. Durable expiry uses
trusted wall-clock time; RAM uses monotonic time. Keep URI/body/header logging
disabled across portal/proxies. Fixed errors do not reflect credentials, database
paths or arbitrary upstream messages.

## Client and actual browser limits

The opt-in plugin above still requires runtime acceptance. Any deployment must use a stable controlled
HTTPS origin, published MSX storage API, and privately compare the **exact newly
saved renewal value and generation**. Presence alone is insufficient. Never log
that record, put it in startup/query URLs or store Jellyfin passwords/tokens in
MSX. Failed storage/uncertain rotation requires explicit re-pairing. Shared source
preview origins are unsuitable for authorization. Automatic bootstrap remains
unresolved in [storage/startup research](msx-storage-research.md).

A bounded local-delivery check used connected Chrome `Mein Chrome`, official MSX
0.1.167 and a normal 2560x1215 screenshot viewport. The unchanged harmless storage
probe loaded directly from loopback HTTP and displayed API readiness. An inline
official-MS​​X launcher rendered its Open control. Clicking it requested an HTTPS
loopback iframe although the declared interaction URL used HTTP. The frame showed
an invalid-response error; the HTTP listener received TLS bytes. No plugin storage
read/write, backend API, renewal or pairing was exercised. An initial inline launch
omitted base64 JSON encoding and showed Data Load Error; the corrected launcher
rendered before the separate iframe failure. No runtime internals were inspected.

The failed frame was captured and visually inspected at ignored
`.lab/reports/issue12-loopback-delivery.png`. Both owned tabs were closed and the
listener stopped. No credential, trust import, TLS/security bypass, production
resource, real Jellyfin or TV action occurred. This limits that plain-HTTP run;
it is neither universal MSX behavior nor an authenticated integration pass. Do
not repeat failed Windows trust imports. A working controlled HTTPS origin is
still required for full client acceptance.

## Automated evidence

`tests/test_authorization.py` covers normal CSRF pairing/enrollment/fresh restart,
session/absolute expiry, independent-store concurrency, stale-secret denial,
durable revoke/upstream-logout failure, row/ciphertext/key/server/schema corruption,
missing database, capacity/isolation, origin/JSON/body bounds, pre-commit rollback
and lost-response re-pairing. Synthetic storage/logs are checked for credential
markers. MockTransport handles every Jellyfin request. These backend tests do
not prove browser/plugin delivery, real-server compatibility or TV retention.
