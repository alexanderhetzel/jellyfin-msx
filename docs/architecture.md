# Architecture and decisions

## M1 data flow

1. MSX loads `/msx/start.json` (also `/msx/start.json` under the MSX setup convention).
   Its content action loads `/msx/pair.json`, which creates a five-minute pairing.
2. TV displays a locally generated QR, short code and companion address `/pair`.
   The QR's independent pending-only activation secret opens the normal clean
   credential stage; it never carries the private TV session capability or grants
   library access. The operator scans only their own TV, or enters
   that code in a browser, checks it, then enters Jellyfin credentials in a
   device/cookie-bound second stage. Same-origin, CSRF-protected POSTs validate
   and authenticate against the single operator-configured Jellyfin server.
   See [the companion pairing contract](companion-pairing.md) for activation links,
   expiry, single-use grants and tab/retry recovery.
3. TV selects “Continue after pairing” with the remote. Its random capability
   identifies the session through `pairing.json`: waiting retains the QR/code,
   expiry offers public new-code recovery, and authenticated success opens
   libraries. Private `home.json` keeps its authenticated denial contract.
   No cookie support or third-party input plugin is required on TV.
4. Backend requests user views/children/details from Jellyfin. Private posters
   are fetched through an authenticated, size-bounded image endpoint.
5. `video:resolve:` requests PlaybackInfo on demand. Backend returns an authenticated
   Jellyfin stream URL; video travels directly from TV to Jellyfin. HLS is available
   only on an explicitly opted-in deployment outside the operator's no-transcoding setup.

Source boundaries: `config.py` (validated environment), `state.py` (bounded,
expiring in-memory state and rate limits), `jellyfin.py` (isolated HTTP requests),
`playback.py` (profile/selection), `msx.py` (JSON), `app.py` (routes),
`authorization.py` (optional encrypted durable renewal authority).

## Security and operational limits

TV capability URLs are bearer credentials, even though they are not Jellyfin
tokens. Use HTTPS and disable access logs on the backend and reverse proxy.
Never share a raw MSX JSON response or browser/network capture. Private endpoints
are no-store, including images. CORS permits read-only MSX requests without cookies;
knowing an opaque capability is still necessary. Browser pairing uses CSRF and
same-origin checks. Passwords are neither persisted nor sent through query strings.
Authenticated REST requests use the standard MediaBrowser Authorization header
with its Token parameter. Native video URLs use canonical `ApiKey`, replacing
any previous token query variants. Legacy `X-Emby-Token` and `api_key` are not
required by this client. Jellyfin 12 can optionally enable legacy authorization;
the client must work without that compatibility setting. See the
[isolated API matrix](jellyfin-api-compatibility.md) for exact tested versions.
The companion `/pair` page uses `Referrer-Policy: same-origin` so native Chromium
form submissions preserve their Origin for validation; off-site referrers are
still suppressed. Private capability routes retain `no-referrer`. A blanket
`no-referrer` on the form would turn native POST Origin into null and reject sign-in.

Jellyfin tokens exist in backend RAM and in the resolved video URL: native media
players cannot be assumed to attach custom Authorization headers. Those upstream
tokens are user-scoped, not short-lived item-scoped tickets. Redacting URLs and
dedicated least-privilege Jellyfin accounts are important. Removing this exposure
would require a narrowly scoped media gateway, including HLS playlist rewriting;
a redirect alone would not hide the token. That gateway is deferred.
[The native media credential decision](media-token-security.md) records the
reviewed primary header/ticket contracts, synthetic boundary regressions and
the conditional gateway design. Initial URL validation does not constrain a
native player's subsequent redirects or HLS descendants, and a portal JSON
response's referrer policy does not establish the hosted player's request policy.

Default sessions last eight hours with absolute expiry; restart requires re-pairing.
The application remains single-process/single-worker. With persistence disabled,
no SQLite or key is needed because credentials are not written to disk.
Logout locally invalidates immediately
and attempts upstream logout; expiry/restart do not guarantee upstream revocation.
Jellyfin administrators can revoke sessions. This limits M1 production readiness.

[MSX storage/startup research](msx-storage-research.md) now records public-API
synthetic marker retention in the official Chrome runtime, startup limitations
and a candidate renewal contract for #12. The optional
[durable server authorization](durable-authorization.md) implements encrypted
server records, single-use renewal and generation-bound RAM grants. The default
MSX UI does not call those APIs; automatic browser restoration and SAPHI retention
remain unverified. Real renewal secrets require an operator-controlled plugin origin,
never the shared source-preview origin used for synthetic research.

Jellyfin API calls have a total deadline below MSX's documented 30-second timeout.
Upstream redirects are not followed; returned playback URLs must remain under the
configured HTTPS server/base path. No arbitrary request-supplied server addresses.
The TV must reach Jellyfin directly, including its reverse-proxy base path and
HLS segments. NAT, certificates and server transcode permissions remain operator concerns.

## Playback contract

The [multi-device profile contract](playback-profile-contract.md) separates
immutable source-defined candidate descriptions from HD admission, operator
policy and runtime observations. Production remains fixed to the Philips
candidate below; two synthetic helper profiles prove isolation without adding
device support or a runtime selector. The contract defines trusted selection,
session/source binding, diagnostics/UI and regressions required before rollout.

The current profile is `philips-32phs6605-12-hd-policy-v2`, based on exact-model
multimedia documentation and qualified platform streaming evidence. Its candidate
containers/codecs and conditional Dolby/DTS warnings are defined in
`device_profile.py`; evidence and limits are in `philips-32phs6605-12.md`.
Candidates are not physical MSX passes. A conservative client admission policy
enforces at most 1920x1080 encoded video: 4K playback/downscaling is excluded.
This is not an asserted silicon decoder maximum. Selection, PlaybackInfo codec
conditions and returned-source validation all enforce it. No undocumented H.264
level, frame-rate, bit-depth or channel ceiling is asserted. The former 720p/AAC-stereo
rule was an assumption, not a device limit, and is superseded. An optional bitrate
budget limits operator/network policy, not TV capability, and is unset by default.
Missing essential container/codec/dimension/audio metadata and unsupported source
opening mechanisms still block negotiation. PlaybackInfo support flags are checked
but do not prove successful decoding. `MSX_ALLOW_TRANSCODING=false` is the default:
no transcoding/subtitle-encode profile is advertised, forced/burn-in requests are
rejected before contacting Jellyfin, and an upstream HLS URL is never used.
No DirectStream/remux path is advertised. Optional HLS and burn-in remain available
only when an operator explicitly enables transcoding on a suitable host.

“Try original” selects by server response and local policy. It cannot detect a decoder
failure inside SAPHI. With transcoding disabled the only fallback is a compatible
stored version. Force-HLS and subtitle-burn controls are hidden by default.
PlaybackInfo error, unsupported source, off-origin URL or denied transcoding returns
a visible MSX response error. Player controls are MSX's standard controls.

[Subtitle research](msx-subtitle-research.md) selects external UTF-8 WebVTT via
official HTML5X as a constrained browser-tested candidate for #22. Raw SRT/ASS
and tested embedded MP4 text did not render; paused-switch/seek placement and
missing-track notices have limitations. Production subtitles remain Off. The
opt-in [resource/bridge implementation](subtitle-resources.md) authenticates and
bounds a two-line, short-text external WebVTT subset and offers source-pinned
HTML5X controls. Actual Chrome delivery, boundary text, selection/seek/Off/Stop,
rejected-layout original recovery and native-fetch expiry denial support #22's
software criteria. Intermittent hosted Data Load Errors and missing native
per-track error notices remain documented; no cause/fix or physical pass is
inferred. See [source-pinned browser evidence](private-subtitle-results.md).

M1's legacy resolver records playback *decisions*, not proof that video started.
The preferred original-with-progress flow now uses authenticated generation-bound
[playback reporting](playback-reporting.md). Requested samples must echo the
native resolver's public generation marker; only observed advancing samples
establish Start. Stop confirmation or a 45-second last-safe lease ends reporting.
The legacy Try original and HTML5X subtitle entries remain unreported. Resume and
automatic fallback remain separate work. Source-pinned official-runtime Chrome
observations now verify the supported original flow; physical device behavior
and genuine suspension remain unverified.

[Lifecycle research](msx-lifecycle-research.md) records actual public MSX callbacks
and requested state samples. Control events carry previous state; initial load,
Back, natural completion and media failures do not imply a reliable Play/Stop
pair. Its bounded authenticated telemetry/reconciliation contract is implemented
for the #18 original-with-progress flow, with separate actual-runtime acceptance.
Research acceptance includes the recorded
unavailable suspension precondition and conservative disappearance lease; it does
not require successful suspend emission. Genuine suspend/resume and physical
Philips ordering remain unverified. #18 must verify its own authenticated
transport, generation correlation and reporting/disappearance behavior.

Candidate sources are ranked to prefer AVC and a source fitting the panel, then
the highest resolution within that size or smallest above it. This is a selection
preference, not a maximum decoder resolution. Each detail playback action carries
the selected source ID. The resolver rechecks item access and validates that exact
source against fresh metadata; a missing or newly ineligible source requires
reopening details. Reordering equally ranked versions cannot silently switch
files or subtitle indices. Legacy resolver requests without a source ID still
select from current metadata. PlaybackInfo and original-container delivery use
the same selected source ID; original-container URLs retain MKV/AVI/etc. rather than
labelling every file MP4. If no source qualifies,
direct-only mode reports that condition instead of converting media. This also
avoids ambiguous subtitle indices across files; Jellyfin applies stream indices
to a matching MediaSourceId. Nullable collections normalize to empty, and invalid collection
shapes become visible upstream errors (`jellyfin.normalize_contract`). Pairing
request bodies are bounded to 8 KiB before form parsing (`middleware.PairBodyLimit`).

## Agent-operated development loop

`tools/lab.py` starts the real portal on loopback and connects to an operator-selected
real Jellyfin server. No test-specific authentication bypass or stored credentials
are added. A separate local dashboard launches the official hosted MSX web client
and exposes redacted endpoint counts, negotiation flags and playback decisions.
Actual browser actions and media state must corroborate those observations.
The lab refuses non-loopback origins and transcoding. It does not change OS
certificate trust automatically. Expired local certificates require explicit renewal
and trust; `.lab/` is excluded from both Git and Docker build context.
