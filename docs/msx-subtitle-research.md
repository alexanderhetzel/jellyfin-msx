# Official MSX subtitle research — issue #21

**Implemented / automated-tested / browser-tested / device-unverified**, 2026-10-30.
External UTF-8 WebVTT via official HTML5X is the constrained candidate for #22.
No production delivery, stable placement, embedded-selection, audio or Philips
pass is claimed. Failed combinations never enable Ultra burn-in. Hardware is #4.

## Public interfaces and reproduction

Official [HTML5X documentation](https://msx.benzac.de/wiki/index.php?title=HTML5X_Plugin&oldid=2990)
specifies WebVTT, language selection and a subtitle panel. CORS stays true:
false uses an online proxy, prohibited for private content. The
[extended properties](https://msx.benzac.de/wiki/index.php?title=Extended_Properties)
define buttons; our probe uses the subtitle icon and
`panel:request:player:subtitle`. Only the vendor-hosted
`https://msx.benzac.de/plugins/html5x.html` runs. No proprietary player source was
read, copied, hosted or modified.

[Tizen](https://msx.benzac.de/wiki/index.php?title=Tizen_Player) has Samsung-specific
SRT/text-track options. These do not establish Chrome/Philips support; USB lists
likewise do not establish installed MSX behavior ([model evidence](philips-32phs6605-12.md)).
[WebVTT](https://www.w3.org/TR/2026/CRD-webvtt1-20260520/) defines UTF-8 timed text,
not ASS rendering or PGS/VobSub decoding. The reviewed HTML5X interface provides
no bitmap renderer. Images are unsupported by the selected contract, not proven
impossible everywhere. No PGS/VobSub fixture was played.

Observed root `209fe9e07e483162fd756dca82e8e88de89b99e9`:

```sh
uv sync --frozen --extra dev --group build
uv run python -m tools.msx_storage_probe https://raw.githack.com/alexanderhetzel/jellyfin-msx/209fe9e07e483162fd756dca82e8e88de89b99e9/tests/fixtures/msx-subtitles/index.json
```

Open the printed URL in connected Chrome. This launches manual research, not an
automated browser suite. Select WebVTT, Pause, Subtitles, English/Off, rewind/
forward, Back to hide controls, Stop. Repeat raw/embedded/missing cases. Plugin
panel on native playback is intentionally an unsupported-interface probe.
Natural completion can advance the list; distinguish this from manual selection.

Generator `tools/public_subtitle_fixture.py` pins assets at
`fc20e096d7c0d7c16ed09d440f1aee81a477988e`, original video at
`d0c6fe2ab74f643756f9d7ea8119298b238d8f2f`. Independently authored cues and
local remux command/hashes/indices: [README](../tests/fixtures/msx-subtitles/README.md).
AV packets copied locally; no operator media, real Jellyfin, AV encode or Ultra
operation. Wheel/container allowlists exclude all fixtures.

Environment: official MSX **0.1.167 web**, Windows, connected Chrome extension,
existing **Mein Chrome** profile. Chrome **156.0.8078.80** is preceding research's
version, not independently reread. Normal screenshots **2560x1271**, no viewport
override. Profile/partition/security settings unchanged; partition behavior not
independently tested. Runtime/player `https://msx.benzac.de`, source preview
`https://raw.githack.com`, media/raw-text redirects to
`https://raw.githubusercontent.com`. Flags `input=2&init=1&suspend=0&animate=0`.
Commits pinned, hosted services unpinned. Never place private secrets/grants on
shared previews. No trust-store/TLS bypass, deployment or library mutation.

## Actual observations

Visible UI controls caused all changes; DOM/media inspection was read-only.
No playback/time/track/DOM/vendor-runtime setters. Retained network evidence is
only public fixture origin/path, method, status, MIME, CORS, Range and redirect
status, queries removed. No raw capture/private headers retained. An initial
broad event print included vendor bootstrap parameters; those were not retained
or used as evidence. Later output/export allowlisted public fixture paths only.

| Case | Actual result and limit |
| --- | --- |
| German VTT | `de.vtt`: 200, text/vtt, CORS `*`; preselected DE rendered. At paused **3 s**, `DE A 0–8: Grüße, ÄÖÜ äöü ß` readable lower in video. At **13 s**, both B lines readable with controls hidden. |
| Timing/seek | Playing German reached B near 10–11 s. Pause settled **23.289179**; rewind moved **18 → 13 → 8 → 3**. B at 13/A at 3 matched intervals. English forward **3 → 8** showed adjacent A/B at opposite edges; **13** showed only B. Sampled timing, not frame-accurate sync. |
| Switch | Actual panel Off/Deutsch(DE)/English(EN), checkmark. English fetched `en.vtt`: 200 text/vtt/CORS `*`; changed cue/EN label at same paused **3 s**. |
| Placement limit | German initially lower/readable. Paused English switch put text against bottom; paused seek put B at **top edge** at 13. Fresh recheck paused near 8, selected EN, actual Play, controls hidden: **12.043064**, paused false, B at **bottom edge/minimal margin**. Play did not establish stable placement. Controls overlap/dim cues. No safe-margin/polished pass. |
| Off | Actual Off at paused 13 removed cue/language indicator without changing observed frame. |
| Raw SRT | Raw redirect, 200 text/plain/CORS `*`; DE selected, no cue at **7.513566**, paused true, video readyState 4, track readyState **3/ERROR**. Negative for tested HTML5X/Chrome combination, not universal platform claim. |
| Raw ASS | 200 text/plain/CORS `*`; no cue at **7.599044**, paused true, video readyState 4, track readyState 3. No styling/animation fidelity claim. |
| Embedded/native | Verified German default mov_text absolute stream **2**, subtitle ordinal **0**. Video **4.812482**, readyState 4, textTracks **0**, no caption. Plugin-panel request produced Data Load Error / Commit player request failed. Back dismissed error, Stop recovered menu. No undocumented native API tested. |
| Embedded/HTML5X | Same file played, no caption, textTracks **0**, panel **only Off**. External setup does not extract embedded text. MP4/mov_text/Chrome result does not settle MKV/SRT/ASS elsewhere. |
| Missing VTT | Request observed, no successful response/status captured: no 404 claim. Track readyState 3; no caption **19.694591**, paused true, video readyState 4. Still DE, no specific missing-caption explanation. Stop recovered menu. |
| Sources/requests | Distinct pinned original/embedded MP4, Range bytes=0-, 301 raw redirect, 206/CORS `*`; later ranges observed. Only de.vtt initially; en.vtt requested on selection. No private source/auth delivery exercised. |

Ignored `.lab/reports/issue21-*.jpg`: `vtt-a-umlauts`, `vtt-b-clean`, `track-menu`,
`vtt-english`, `vtt-forward-english`, `vtt-english-13`, `vtt-english-resumed`,
`vtt-off`, `raw-srt`, `raw-ass`, `embedded-native-panel-error`,
`embedded-native-no-cues`, `embedded-html5x-off-only`, `missing-vtt`,
`final-recovery-menu`; plus `issue21-public-network.json`. Immediate snapshots
sometimes lagged actions; later screenshots/state underpin reported outcomes.
AX click initially selected only; DOM label activated. Glyph/body-Escape timed
out; observed control classes/Back worked. Tool failures are not TV failures.
No audible output or physical test.

## Secure contract for #22 — deferred implementation

External WebVTT is a **candidate** with placement/failure-notice limits. Default
Off. Require an eligible external UTF-8 VTT sidecar; explain raw SRT/ASS, embedded
and bitmap unsupported paths. Future conversion/extraction requires separate
bounded design/tests. ASS-to-text loses layout; bitmap paths need renderer/OCR/
burn-in. No silent Ultra encoder/burn-in or operator-library mutation.

Serve a **narrow subtitle resource** through the portal with existing random
expiring capability and upstream token kept server-side; no video proxy or
token-bearing redirect. Reauthorize item access and pin **MediaSourceId + absolute
subtitle Index** each request. Reject changed/missing source, invalid/duplicate/
negative index, non-subtitle, embedded/image/raw unsupported format and missing
metadata. Never substitute array position/text-track ordinal (fixture 2 vs 0);
live Jellyfin mapping is unverified. Stale details require reopening, never
another version's same-numbered stream.

Pinned [Jellyfin SubtitleController](https://github.com/jellyfin/jellyfin/blob/a46fa4559daaea352257d0196b56e392c18dd09c/Jellyfin.Api/Controllers/SubtitleController.cs)
defines source/index stream routes and timestamp options, but can invoke a
subtitle encoder. A .vtt URL does not establish no-conversion behavior. Initial
#22 admits only already external VTT and verifies its read path makes no
conversion/burn-in request; whole cues from zero, original timebase, no HLS
timestamp map/resume offset. Unsupported extraction fails clearly.

Configured origin/base path only, server-side standard auth header, no redirects,
arbitrary URLs or unvalidated DeliveryUrl. Return UTF-8 text/vtt, no upstream
token, no-store/private, no-referrer, nosniff, existing log exclusions. Initial
design limits **1 MiB / 8 s** plus bounded concurrency/cue/text lengths; reject
invalid encoding, HTML responses/malformed VTT. Do not pass arbitrary HTML,
STYLE/external-resource constructs through a generic proxy. #22 implements/tests
exact parser limits and positioning.

Explicit `html5x:cors=true`; credential-free CORS for exact official HTTPS
runtime/player origin, never Origin as authentication. No online subtitle proxy.
Player receives a bearer-resource URL: expire/revoke with session, keep private
in UI/logs/captures. Withhold **upstream Jellyfin token**, not all capabilities
from the authorized player. Direct video retains its separate
[token tradeoff](media-token-security.md).

Map safe labels/language to source/index; duplicate-language tracks cannot
overwrite language-keyed properties. Treat labels as data. Off removes selection;
preserve position instead of reloading on switch. Verify actual pause/resume/
seek/switch/Off/Stop. Denied/expired/missing/oversized/malformed tracks need clear
recoverable notice with Off/video controls: DE alone is inadequate. Private
auth/revocation/index isolation, malformed handling and stable placement are
**not verified** by this public probe. #22 owns implementation/browser acceptance;
#4 installed Philips comparison. HD1080/no-default-video-proxy/Ultra defaults unchanged.
