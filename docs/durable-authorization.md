# Durable server authorization — issue #12

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

No production plugin is included. A future plugin must use a stable controlled
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
