# Durable server authorization — issue #12

## Opt-in MSX client — 2026-10-31

**Implemented / automated-tested / device-unverified:** `MSX_REMEMBER_DEVICES=true`
requires the external key/database configuration below and selects a public
`/msx/remember.json` startup document. The default remains ordinary RAM pairing.
The independently authored plugin shell/script live on the portal's own HTTPS
origin. Only its exact HTML route permits framing by the official MSX web origins;
other pages retain frame denial. Script policy allows our own script and the
vendor-hosted public API library; connect policy is same-origin. No proprietary
runtime is copied, and no inline/eval exception or cross-origin POST is added.

The published [multiple-action/startup contract](https://msx.benzac.de/wiki/index.php?title=Internal_Actions)
shows the public fallback content, then loads the interaction plugin. Its public
readiness callback reads `TVXServices.storage`, then shows normal pairing or
renews authorization. Storage readiness polling after `handler.ready` is bounded
to five seconds, requests to fifteen seconds and one operation per plugin instance.
Vendor/plugin readiness itself has no timeout; the public fallback content remains.
Actual automatic startup and
normal reopen acceptance must be recorded separately; these API choices alone
do not establish an MSX integration pass.

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
