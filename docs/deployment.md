# Deployment and diagnostics

## Configuration

| Variable | Meaning |
| --- | --- |
| `MSX_PUBLIC_URL` | Externally reachable portal origin, HTTPS required by default; no path |
| `JELLYFIN_URL` | Operator-controlled Jellyfin URL, optional base path, no credentials/query |
| `MSX_ALLOW_HTTP` | `true` only for isolated development; default `false` |
| `MSX_MAX_BITRATE` | Optional operator/network budget in bits/sec; unset/empty by default. Not a TV decoder limit; validation accepts positive integers up to 1 Gbit/s |
| `MSX_ALLOW_TRANSCODING` | Default `false`; keep disabled on Ultra.cc. Opt-in only on a host where conversion is permitted |
| `MSX_DOMAIN` | Compose/Caddy DNS name; must match public origin |

Secrets are entered in the browser form, not configuration. The eight-hour session
TTL, five-minute pairing window and bounded 256-state store are currently code
defaults. No persistent session volume exists. Run exactly one worker/replica.

## HTTPS and network

The supplied Compose deployment exposes Caddy on ports 80/443 and keeps the
portal private on the container network. A certificate trusted by this TV is
required; never solve TLS failures by disabling validation or enabling public HTTP.
The actual firmware trust store and MSX start-parameter HTTPS discovery must be
tested. Caddy has no request access log and excludes `http.log.error`, whose proxy
errors otherwise include request URIs. TLS/startup logs remain available.
This follows Caddy's [global log options](https://caddyserver.com/docs/caddyfile/options#log)
and [HTTP error logging implementation](https://github.com/caddyserver/caddy/blob/master/modules/caddyhttp/server.go).
Preserve that policy in other proxies,
CDNs, load balancers and Jellyfin's proxy: capabilities and video query tokens
must not be captured in URL logs. Never enable uvicorn access logs.

Before deployment, validate the Caddyfile with the actual selected Caddy image.
In an isolated smoke test, stop the portal and request a path containing a fake
marker (never a real capability); verify that the marker does not appear in Caddy
logs. This error-path check remains required even if normal access logs are empty.

The portal does not trust forwarded IP headers. Behind Caddy, rate limits are
shared by clients using that proxy; this is conservative for a small TV deployment.
Five pairing POST attempts per peer/minute, plus a global bound, prevent an
unbounded code/password guessing endpoint. A production multi-user service needs
an explicit trusted-proxy and distributed-state design.

The browser form uses same-origin POST and CSRF protection. Configure the actual
public origin exactly; an alias/port mismatch will reject submissions. No third-
party scripts, fonts, input plugins or analytics are loaded. MSX JSON permits
cross-origin GET without credential cookies; private responses still need a
256-bit capability. Root pairing data is public but contains no library access
until the human approves the displayed code.

## Stream security and lifecycle

Only posters/control JSON pass through FastAPI. Stream URLs contain the signed-in
user's Jellyfin token because header support cannot be assumed in SAPHI's player.
That token can access the user's other permitted media. Treat TV network captures,
MSX action JSON and resolved URLs as secrets. A dedicated non-admin account with
limited libraries is appropriate. If that exposure violates your requirements,
stop before rollout and design a token-hiding media gateway. It cannot be solved
by redirecting to Jellyfin.

Disconnect removes the local session before requesting upstream logout, including
when Jellyfin is down. Upstream failures are shown on TV. Session expiry/process
restart do not revoke the upstream session automatically; use Jellyfin session
management when needed. No periodic playback progress or stop report exists yet.
Check Jellyfin for abandoned transcodes after tests and stop them administratively.
This is an M1 limitation, not a verified production lifecycle.

## Diagnostics

TV Diagnostics records the last 20 playback decisions/errors for this session.
Each decision includes a random correlation ID, experimental profile, chosen route,
source video/audio codec and dimensions, forced/burn-in flags and sanitized MSX
platform/player strings. It does not contain item IDs/names, server/stream URLs,
tokens, pairing codes or capabilities. Client-supplied platform/player values are
diagnostic hints only; they cannot expand codec permissions.

For structured data, `/api/device/CAPABILITY/diagnostics` is authenticated by the
same private capability. It is intended for controlled operator inspection; do
not paste its raw URL into tickets or terminal logs. The TV view avoids needing it.
Events describe the decision, not actual decoder success. HLS source codecs in
diagnostics describe the input; confirm output codecs in Jellyfin's own session
or FFmpeg diagnostics. Redact those logs before sharing.

## Troubleshooting

- No JSON: verify DNS, HTTPS chain, `/healthz`, `/msx/start.json`, CORS and MSX version.
- Pairing fails: reopen form, check code expiration and origin; wait after rate limiting.
- No library: check account library permissions; re-pair after token revocation.
- Direct fails: record firmware/MSX/player/diagnostic ID and check for a compatible
  stored version. On Ultra.cc, do not enable conversion or burn-in to work around it.
- Multi-version item: candidates prefer AVC and a source fitting the panel,
  consistently pinned across details/playback. This preference is not a decoder
  limit. Check selected-height, named model/profile, evidence warnings and policy reasons.
- Optional HLS on a separately opted-in host: check transcode permission, output
  codecs, manifest/segment access, base path, bandwidth and TLS.
- Seek fails: test progressive MP4 Range and HLS separately; do not infer seek
  support from successful initial playback.

`docker compose config` can validate syntax without starting deployment. A Docker
image build and Caddy certificate issuance need a running daemon/network and are
separate acceptance checks. Local software tests cannot establish either one.
