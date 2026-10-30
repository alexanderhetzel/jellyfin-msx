# Native media credential decision — issue #25

**Implemented / automated-tested / device-unverified — 2026-10-30.** Retain
direct original-file delivery as the default. This explicitly accepts disclosure
of a user-scoped Jellyfin session token to the MSX runtime and selected player.
It is suitable only where the operator accepts that trust boundary and can
protect the Jellyfin endpoint and its logs. No item-scoped or short-lived media
credential is implemented. Do not substitute an administrator/server API key.

A narrowly scoped gateway is **necessary if withholding the upstream token from
the runtime/player is a requirement**. It is not required for the current direct
delivery policy and is **deferred**, not silently introduced by this decision.
A redirect service, opaque resolver or header transport alone cannot meet that
withholding requirement. This research changes no playback or authentication
behavior and does not establish a new browser, audio or physical-TV pass.

## Actual authority and disclosure paths

The following are fictional schematic examples, not usable credentials or
retained captures. `SYNTHETIC_USER_TOKEN` denotes an account session, not an
administrator key; `CAPABILITY_PLACEHOLDER` denotes the independent portal grant.

| Hop | Authority and exposure |
| --- | --- |
| Companion sign-in → portal → Jellyfin | Password is submitted in the same-origin CSRF-protected POST body over HTTPS. The portal authenticates only to the configured server. The returned user/token stays in backend RAM. |
| MSX → portal private routes | `/msx/device/CAPABILITY_PLACEHOLDER/play.json?item_id=ITEM_PLACEHOLDER` authenticates the random expiring capability. The path itself is a secret. A TV ID, CORS permission, item ID or PlaySessionId does not replace it. |
| Portal → Jellyfin metadata/PlaybackInfo | The standard `Authorization: MediaBrowser ... Token="SYNTHETIC_USER_TOKEN"` header carries the user session. The resolver rechecks item access and the selected source before returning media. |
| Resolver response → MSX → player → Jellyfin | Response data contains a URL shaped like `https://jellyfin.test/jellyfin/Videos/ITEM_PLACEHOLDER/stream.mp4?Static=true&MediaSourceId=SOURCE_PLACEHOLDER&ApiKey=SYNTHETIC_USER_TOKEN`. Native requests go directly to Jellyfin; the portal does not fetch the file. |
| Optional HLS | With explicit transcoding opt-in, a validated initial `.m3u8` URL carries the same token. The player fetches playlists and descendants directly. Default Ultra policy rejects this path. |

Source evidence: `app.py` pairing/play/image routes, `jellyfin.py` headers/fetch,
`playback.py` resolve/authenticated_url, and `state.py` expiry/logout. Private
posters are already fetched through authenticated, size-bounded portal routes;
this does not mean video is proxied. Eight-hour absolute portal expiry or restart
removes local access, but does not guarantee upstream token revocation. Logout
invalidates locally and attempts upstream logout; upstream failure does not
restore local access. A previously issued direct URL can remain usable while
Jellyfin accepts its token. Item/source pinning and the HD admission policy govern
portal negotiation; they do not shrink the upstream token's account authority.

Treat the runtime, selected player/plugin, browser extensions/debug tooling and
device diagnostics as credential recipients. A copied media URL can be replayed
with the user's Jellyfin permissions, including outside this portal. Transport
encryption protects the network hop, not either endpoint or local captures.
Never send private URLs to public playlist converters, shared preview origins,
third-party resolve services, analytics or issue reports. The official
[M3U/PLS converter documentation](https://msx.benzac.de/wiki/index.php?title=M3U%2FPLS_Files)
describes an online service for public playlists; it is not our HLS path.

## Referrer, redirect, playlist and log boundaries

**Implemented:** portal responses use `Cache-Control: no-store, private` and
`Referrer-Policy: no-referrer`, except the companion form's `same-origin` policy
required by normal Chromium POST/CSRF behavior. These are portal response
policies. They do not scrub the URL delivered in JSON or set a universal policy
on the hosted MSX document, player/plugin or Jellyfin response. The
[Referrer Policy specification](https://w3c.github.io/webappsec-referrer-policy/)
defines policy delivery and request-client behavior; an API JSON response is
not proof of the request policy used by a different document's media element.
Actual referrers for every supported player remain **unverified**. Never rely on
them to remove `ApiKey` from the request target.

**Implemented:** backend HTTP requests disable redirects and environment-derived
proxies. The initial media URL must match the configured scheme, authority and
base path; dot traversal and known encoded dot/slash forms are rejected. Existing
token query spellings are replaced with one canonical `ApiKey`. No arbitrary
request-supplied server is accepted. This is validation of the initial URL, not
a promise about every proxy's URL normalization or a sandbox for a hostile
operator-configured server.

**Outside backend enforcement:** native-player redirects and HLS descendants.
A same-origin initial response can redirect or refer to another host. Depending
on the response/player, a destination query or referrer can carry credentials;
do not claim a leak occurs on every redirect, or that all players refuse it.
A resolver redirect to a token-bearing URL exposes that URL to its recipient.
The backend's `follow_redirects=False` does not control the player's network stack.
Configure direct delivery without unexpected redirects or external media targets;
checking that deployment remains an operational gate, not a new pass here.

[RFC 8216](https://www.rfc-editor.org/rfc/rfc8216.html), especially sections 4.1,
4.3.2.4, 4.3.2.5 and 4.3.4, permits relative/absolute playlist resource URIs,
keys, maps and nested playlists. For example, `variant.m3u8?ApiKey=SYNTHETIC_USER_TOKEN`
is token-bearing; `segment.ts` does not automatically inherit the parent URL's
query. Credentials may be repeated in child URLs or supplied by another player
mechanism. We neither fetch nor rewrite manifests and cannot attest their child
destinations/authentication. Optional HLS therefore trusts Jellyfin's full media
graph; a safe master URL alone is insufficient evidence.

**Implemented, with deployment limits:** application HTTP-client URL logs are
suppressed at normal configured levels; lab evidence retains allowlisted policy
fields/status counters, and generated negotiation fields omit upstream media
URLs/tokens/source IDs. The `platform`/`player` query labels are untrusted,
length-bounded text retained in diagnostics, not a general-purpose secret scrubber;
never submit credentials or private URLs in those labels. The public MSX
attached-info contract can also include a media URL: future telemetry must
allowlist safe fields instead of forwarding raw player data (see
[lifecycle research](msx-lifecycle-research.md)).
Packaged Uvicorn disables access logs; `deploy/Caddyfile` has no access-log
directive and excludes proxy error request-URI logging. These controls cover the
portal, not the separate Jellyfin host, its reverse proxy/CDN, player logs or
administrator-enabled tracing. No-store is not a logging control. Do not enable
raw headers/bodies/URI logging or persist network captures on either side.
Jellyfin's own
[reverse-proxy guidance](https://jellyfin.org/docs/general/post-install/networking/reverse-proxy/)
warns that request-path logging can expose authentication parameters. Protect or
disable such logs at every media hop, including error paths. Chosen-host marker
verification remains in deployment acceptance; this research does not certify it.

## Header and short-lived ticket options: primary evidence

Inspected 2026-10-30. MSX documentation is mutable; the cited current public
contract is evidence, not a guarantee about undocumented platform extensions.
No proprietary runtime implementation was copied or inspected.

| Option | Primary evidence and decision |
| --- | --- |
| Plain MSX video/resolver | Published [Internal Actions](https://www.msx.benzac.de/wiki/index.php?title=Internal_Actions) documents URL playback and a resolver response containing `url`. [Extended Properties](https://www.msx.benzac.de/wiki/index.php?title=Extended_Properties) has no general HTTP Authorization-header property. Those reviewed interfaces establish no portable custom-header injection contract. Absence in these interfaces is not proof that every platform/player extension lacks one. Retain query auth for the current path. |
| Browser media/custom plugin | The [HTML media-element interface](https://html.spec.whatwg.org/multipage/media.html#media-elements) provides `src`/CORS mode, not an arbitrary request-header setter. Fetch/MSE or a platform-specific/custom player could attach headers in a different architecture, subject to CORS, Range/seek and HLS descendant support. This is not implemented or browser/device-verified. It still discloses the upstream token to that code, so it is not token withholding. |
| Jellyfin Authorization | Pinned [AuthorizationContext](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/Jellyfin.Server.Implementations/Security/AuthorizationContext.cs) parses standard MediaBrowser `Token` and canonical `ApiKey`, then looks up a device/user session or server API key. Legacy spellings are configuration-dependent. Changing the carrier does not change token authority. |
| PlaybackInfo IDs / Quick Connect | Pinned [VideosController](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/Jellyfin.Api/Controllers/VideosController.cs) accepts PlaySessionId as a playback parameter; it is not an item-limited authorization exchange. [UserController](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/Jellyfin.Api/Controllers/UserController.cs) exchanges Quick Connect authorization for an AuthenticationResult, not a media-only ticket. [Quick Connect documentation](https://jellyfin.org/docs/general/server/quick-connect/) describes sign-in. Neither supplies the required short-lived item-scoped native media grant in the reviewed contract. Do not claim no extension could ever implement one. |

## Minimal controls and conditional gateway contract

Retain HTTPS, configured origin/base path, item/source authorization, bounded
expiring private capabilities, no-store, existing logging exclusions and
credential-free policy diagnostics. Use a dedicated non-administrator account
with only needed libraries/playback permissions and no conversion privileges on
Ultra. Never use a server-wide API key to avoid pairing. Revoke leaked upstream
sessions through authorized Jellyfin administration; this ticket does not revoke
or modify real accounts. Keep direct URLs private, including when reporting a
failure. Controlled plugin origins are required for future real secrets; shared
synthetic source previews are unsuitable.

If upstream-token withholding becomes mandatory, implement a separately reviewed
opt-in gateway that actually serves bytes, not a redirect: mint a random,
short-lived playback grant after normal session/item/source checks, bind it to
one session/user/item/source/generation, check expiry/logout/revocation on every
request, and keep the Jellyfin token server-side. The gateway URL itself remains
a bearer credential exposed to the player and needs log exclusions. Bound grants,
concurrency and byte/rate/time limits; support validated Range/HEAD/seek and
streaming backpressure without buffering full files. Fetch only fixed
operator-origin resources, refuse redirects by default, and never accept an
arbitrary destination URL. If HLS is supported, recursively validate/rewrite every
playlist, segment, key, map and alternate rendition and strip upstream tokens
from all client-visible locations, responses and errors. Define ongoing-playback
expiry/renewal behavior; a one-use ticket breaks subsequent Range/segment requests.
Recheck TLS/base-path/normalization, cross-session denial, replay, expiry and
failure logging with synthetic tests and actual supported players. This is a
conditional design, not an implemented gateway or release claim.

## Evidence and acceptance limits

`tests/test_media_security.py` runs the actual routes with MockTransport. It
checks direct/HLS resolver credential delivery, metadata Authorization headers,
absence of file/playlist fetching, no-store/referrer headers, diagnostic/log
marker exclusion, all five common backend redirect statuses, and cross-origin,
HTTP downgrade, off-basepath and protocol-relative initial HLS denial without
reflecting upstream URLs. `test_playback.py` additionally covers basepath
preservation, token replacement and URL rejection; `test_lab.py` checks redacted
recorder/dashboard output. These are backend contract checks, not packet captures
from a player or live Jellyfin. Captured test logs are process-test evidence only.

Issue #25's research/security decision is satisfied by this trace, primary
contract review, conditional gateway decision and synthetic regression evidence.
Actual deployment logging/referrer/redirect verification, private hosted browser
integration and physical playback remain their separate acceptance gates. No
new browser runtime action, operator credential, media request, production
resource, account change or TV action was needed for this milestone.
