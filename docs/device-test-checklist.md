# Philips SAPHI acceptance checklist

All entries start **NOT RUN**. The Ultra.cc target uses Direct Play only; optional
HLS/burn-in cases below apply only to a separately authorized transcoding host.
Fill results in `device-test-results.md`; never mark
a case passed solely because the desktop MSX demo or a USB player worked.

## Record environment

- [ ] Exact model 32PHS6605/12, firmware version, MSX version (target >=0.1.146),
  MSX-reported platform/player, Ethernet/Wi-Fi, TV date/time.
- [ ] Jellyfin release, portal revision/build, reverse proxy and TLS chain.
- [ ] Dedicated test account with browse/play permissions and known media;
  transcoding disabled on Ultra.cc.
- [ ] Record source container, codecs/profiles/level/bit depth, resolution/fps,
  audio channels, bitrate, HDR status and subtitle type using existing media metadata.

## Reachability, authentication and navigation

- [ ] MSX fetches HTTPS `/msx/start.json` and JSON CORS works on this firmware.
- [ ] Code and companion address are readable; pairing by phone succeeds.
- [ ] Wrong/expired code and wrong password fail without exposing secrets on TV.
- [ ] Continue works; arrows/OK/Back reach movies, series, seasons and episodes.
- [ ] Posters and metadata load; a library with >24 children pages both ways.
- [ ] Restricted account cannot browse a forbidden item or fetch its poster.
- [ ] Disconnect invalidates old content/poster/play links; backend restart requires pairing.
- [ ] Eight-hour expiry returns an actionable re-pair message (may use test-only short TTL).
- [ ] Reopening MSX is characterized: M1 start creates a new pairing; persistence is deferred.

## Playback matrix

Use independently identified source files. For each playable case measure first
frame latency, video/audio presence and sync, pause/resume, seek forward/back by
30 seconds, seek near end, Back/Stop, replay and >=30-minute playback. Note stalls,
remote focus loss and whether native MSX playback actually started. Record the
portal correlation ID and actual Jellyfin output codecs/transcode reasons.

| Test | Expected software decision | Required hardware observation |
| --- | --- | --- |
| MP4 H.264 + AAC | Documented/platform candidate; Try original if server permits | Decode, sound, HTTP Range seeking |
| MKV H.264 + AAC | Model multimedia candidate; Try original | Actual MSX demux, sound and seeking |
| MKV H.264 + E-AC-3/5.1 | Conditional audio candidate; Try original | Internal speakers and separately ARC/bypass; no Atmos assumption |
| HEVC/H.265 including 10-bit sample | Documented codec candidate; numeric limits unverified | Actual native decode, sound and seeking |
| H.264 + AC3/DTS or multichannel AAC | Conditional/model candidate | Actual audio route, channels, sync; record failures independently |
| 1080p/high bitrate/HDR sample | Candidate if metadata/policy match; no automatic conversion | Decoder limit, downscaling and HDR behavior separately from panel/HDMI specs |
| 4K-only item, including cropped 3840x1600 | Rejected by 1920x1080 client policy before PlaybackInfo on Ultra | Clear explanation; no player launch or conversion |
| Same movie with 4K plus eligible HD version | Select and pin the HD source | Correct stored version starts; no request to decode/downscale the 4K source |
| Explicit low operator bitrate budget | Policy rejection or opted-in conversion | Must be identified as network policy, not a proven TV limit |
| Same source, Force HLS | TranscodeHLS H.264/AAC TS | Manifest/segments, seek and long playback |
| SRT selection via Burn subtitle | TranscodeHLS + burn-in | Readable synchronized text, including umlauts |
| ASS/PGS subtitle if server supports conversion | Burn-in or explicit server error | Styled/image subtitle behavior and encoder load |
| Account with transcoding disabled | Direct candidate or visible error | No silent unsupported playback |
| Server/network disconnect | Visible error or native-player failure | Recoverable return to details; no credential leak |

External WebVTT/SRT, embedded subtitle switching and fMP4 HLS remain separate,
unimplemented/untested delivery paths. Documented HEVC is now a candidate, not a
verified native MSX feature. A codec listed in Philips multimedia specifications
is insufficient to sign off the MSX combination. HLS/burn-in rows above apply
only to an explicitly opted-in host outside Ultra.cc.

## Release gates

- [ ] A compatible stored version plays directly inside the installed MSX engine.
- [ ] TLS/URL-token handling is acceptable; all URL logging is disabled/redacted.
- [ ] Verify cleanup of transcodes in Jellyfin manually after each test; M1 does
  not yet send stop/progress lifecycle events.
- [ ] Record that automatic retry after native decoder failure, watch history,
  resume and automatic transcode cleanup are deferred; do not sign off production
  readiness until M3/M4 acceptance criteria are met.

If both MP4 and HLS fail, preserve redacted evidence and investigate MSX player
integration before expanding features. Do not claim the mission achieved.
