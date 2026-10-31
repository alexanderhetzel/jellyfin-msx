# Bounded subtitle resources — issue #22

## Private subtitle menu implementation — 2026-10-31

**Implemented / automated-tested / partial browser-tested / device-unverified;
issue22 open, PR65 draft.** With the existing opt-in enabled, source-pinned
preparation validates up to eight tracks within twelve seconds. Default remains
Off. Rejected tracks explain their unsupported format/layout and retain original
playback/Back; no conversion, burn-in, silent truncation or timing change.

The declared simple-cue subset allows at most two explicit lines, each at most
32 display-budget units (Unicode East Asian W/F counts two, others one).
Combining marks, Unicode C categories and line/paragraph separators are excluded.
These are conservative client admission rules, not certified glyph metrics,
language coverage or hardware limits. Whole-track rejection preserves all
accepted text/times; any unsupported cue rejects the whole track.

Actual `0dc1688` Chrome evidence showed the exact W32/Han16 boundary fully
visible, distinct DE18/EN12 selection at unchanged paused time, seek timing and
Off/Stop. The preserved failed four-line text and separate W33 negative each
explained rejection and recovered to decoded original video. HTTPS callback
delivery rendered DE7 umlauts/two-line text in `3cee411`. These observations
support the tested subset, not four-line wrapping or universal platform support.

Official vendor-hosted HTML5X uses credential-free CORS and its native panel.
Distinct language keys retain absolute indices, including duplicate languages.
The bridge validates each fixed resource and returns its own-origin HTTPS URL
through the published callback. The later native GET authenticates again.
Actual unused-track selection after expiry produced a correlated GET401 and
native track error; there was no specific per-track notice. Manual Off/Stop and
expired-video replay recovery worked. No renewal/cache; delivered cues cannot
be recalled. Fixed numeric frame-local counters record attempted handoff only,
never identifiers, URLs, payloads or errors.

**Remaining integration blocker:** repeated healthy preparation after other
source contexts produces Data Load Error. A public-document-marker comparison
at `6fad503` did not fix it and was removed. Failed-frame SDK/init/XHR/callback
stages were not captured; no root cause or platform-wide limitation is proven.
See [source-pinned actual actions and limits](private-subtitle-results.md).
The full software feature remains unaccepted.

An independently authored transient interaction bridge uses only the published
[interaction interface](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin)
and [HTML5X ID interface](https://msx.benzac.de/wiki/index.php?title=HTML5X_Plugin).
It loads from the portal origin; capability/item/source context is a client-side
fragment, never a vendor-host HTTP query. The constant vendor player URL has only
`id=portal-video`. The bridge requests the ordinary source-pinned play resolver
over same-origin XHR and supplies its media URL through the public callback.
Putting the resolved `ApiKey` URL into vendor `?url=` would disclose it in the
vendor HTTP request and is deliberately excluded. Direct video's existing
client/player token tradeoff still applies; subtitles withhold upstream tokens.

Bridge HTML permits framing only by exact official MSX origins, same-origin XHR
and scripts from self plus the vendor-hosted library. No inline script, arbitrary
URL fetch, telemetry, logging, storage, renewal or background timer. Async replies
are discarded if fragment context changes. Private responses remain no-store and
no-referrer. Fragment URLs and screenshots remain private bearer material.

Interaction ownership with #12: remember bootstrap/enrollment owns startup and
pending pairing, with no continuing background work after authenticated home.
The explicit authenticated subtitle action may replace that interaction plugin.
Normal private Back and server Disconnect/Confirm do not reload remember.
Never restore/rotate remember authority while subtitle playback uses the current
grant; an explicit later public remember startup owns restoration. The subtitle
bridge never reads/writes persistent credentials or assumes automatic restoration
of the previous plugin. Final combined integration is subject to current-main review.

Synthetic verification uses a trusted startup-only `subtitles` scenario on the
existing bounded supervisor: normal pairing/auth, three local VTT tracks with
German/English/duplicate German, plus missing/malformed startup negatives whose
original recovery uses the same reviewed clip and strict authenticated Range
endpoint. No public mutation API, operator configuration, network fallback or
supervisor lifetime/listener change. Node guards test the first-party bridge;
they do not substitute for MSX execution. Wheel/context allowlists include the
reviewed first-party bridge HTML/JS and continue excluding all test tools/media.

## Historical backend milestone — 2026-10-30

**Implemented / automated-tested / device-unverified.** Opt-in backend contract,
not completed native selection. Default `MSX_ENABLE_SUBTITLE_RESOURCES=false`;
normal MSX UI remains Off. Issue #22 stays open for controlled-origin private
hosted MSX delivery, remote selection, placement, timing/seek/Off/Stop and clear
recoverable error notices. No new browser or TV pass is claimed. Earlier public
rendering limits remain in [research](msx-subtitle-research.md).

## API and source admission

Requires HTTPS portal and Jellyfin. Schematic paths use placeholders:

- GET `/api/device/CAPABILITY/subtitles/ITEM_ID/SOURCE_ID`: `default: off`, a list
  of `{index, language}` and a fixed unsupported-format explanation.
- GET `/api/device/CAPABILITY/subtitles/ITEM_ID/SOURCE_ID/INDEX.vtt`: UTF-8
  `text/vtt`, or real HTTP error/fixed JSON explanation. Never a redirect.

Every request authenticates the existing expiring random capability/generation,
reauthorizes user-item access, and requires exactly one eligible source matching
SOURCE_ID. Duplicate sources or missing/ineligible HD/direct metadata fail closed.
Tracks need a unique absolute integer Index (0–10000), external/text flags,
vtt/webvtt codec and local absolute POSIX `.vtt` Path. Windows, remote, ambiguous
and missing paths are deliberately excluded. Path is inspected, never fetched
by the portal or returned. SRT/ASS, embedded and image tracks are rejected.
Invalid languages become `und`; duplicate languages retain separate indices.
No arbitrary title/metadata becomes an action or URL.

Only the configured-server/basepath fixed
`Videos/ITEM_ID/SOURCE_ID/Subtitles/INDEX/Stream.vtt` route is fetched, using
server-side MediaBrowser Authorization, CopyTimestamps=true, zero start and no
VTT time map. DeliveryUrl is ignored. No PlaybackInfo, encoder/burn-in negotiation,
video proxy, arbitrary URL, redirect following or online subtitle proxy fallback.
Upstream response bodies/locations/headers and tokens never become error details.

## No-conversion evidence and limits

Inspected Jellyfin revision `a46fa4559daaea352257d0196b56e392c18dd09c`:
[SubtitleController](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/Jellyfin.Api/Controllers/SubtitleController.cs)
delegates Stream.vtt to
[SubtitleEncoder](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/MediaBrowser.MediaEncoding/Subtitles/SubtitleEncoder.cs).
GetReadableFile uses the sidecar extension; external `.vtt` takes the readable-file
path, and same-format GetSubtitles returns input without format conversion.
Jellyfin may decode character encoding. This supports the admission rule, not a
live server/version pass. Metadata/file changes between checking and reading
cannot be locked by this client. Opt-in operators must maintain accurate metadata;
modified upstream implementations are not certified. No upstream source copied.

## Bounds and privacy

Four concurrent requests per single-process app, 30 per device/minute, eight
seconds including metadata/fetch, one MiB buffered bytes. Non-200, compressed and
non-VTT responses fail closed. Strict UTF-8 plain WebVTT subset: exact header,
10000 cues, four text lines/cue, 1024 characters/line, 4096 characters/original
cue block, ordered non-overlapping positive intervals within 24 hours. Cue IDs
are removed. Markup, cue settings, STYLE/REGION/NOTE, timestamp maps and control
characters from upstream are rejected. The current candidate adds only generated
fixed cue settings after validation; both input/output stay within one MiB. Times
remain unchanged. This is not a player placement
or synchronization pass. Invalid subsets never trigger extraction/conversion.

Capability/generation/expiry is checked after awaits before releasing buffered
data, including logout during upstream fetching. Delivered bytes cannot be
recalled. No cache, renewal or browser storage. No-store/private, no-referrer,
nosniff; credential-free CORS only for exact `https://msx.benzac.de` and
`https://www.msx.benzac.de`, including errors. CORS is not authentication.
The player receives a bearer-resource URL: keep it private in logs/captures and
never place it on shared source-preview origins. Subtitle upstream tokens stay
server-side; direct video's [separate token tradeoff](media-token-security.md)
is unchanged. Existing deployment log exclusions apply to `/api/device/` too.

## Evidence boundary

`tests/test_subtitles.py` uses only MockTransport. It checks absolute-index/
language mapping, access/source isolation, revoked/expired grants, logout during
fetch, hostile metadata, fixed route/headers, redirects, malformed/type/size
failures, parser limits, concurrency and deadline. It does not execute a real
Jellyfin/encoder, MSX or TV. This milestone adds no controls/form or public preview.
