# Bounded subtitle resources — issue #22

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
characters are rejected. Times remain unchanged. This is not a player placement
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
