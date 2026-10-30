# Research record — updated 2026-10-30

The current exact-model profile decision and primary sources are recorded in
`philips-32phs6605-12.md`. That decision supersedes the initial 720p/MP4/AAC-stereo
experiment below. Documentation identifies candidates; physical MSX verification
is still required for any support guarantee.

## Reference repository and licensing

Inspected public [SerhiyRomanov/jellyfin-msx](https://github.com/SerhiyRomanov/jellyfin-msx)
at `6bba5553466cd30e52e8bf1908eaa65ff2689aea` using a shallow clone outside this
project. No LICENSE/COPYING file or source license grant was found. Public
visibility is not a license grant. No reference code/assets were copied; this
project is an independent implementation. A license for this project's original
code is now MIT by the owner's explicit choice. This applies only to the new
independent implementation; preserved upstream `master`/history is excluded.
See `NOTICE.md` for the exact provenance and license boundary.

Source inspection: Python 3.12/FastAPI, separate `app`, `msx_models` and
`jellyfin_api`; pinned FastAPI/Pydantic/httpx/anyio/uvicorn/itsdangerous; Docker
non-root user. Login uses an external MSX input plugin and includes intermediate
credentials in generated URLs. File session expiry is a TODO; Redis is a stub.
Session lookup depends on a supplied MSX identifier. Player constructs static MP4
URLs without PlaybackInfo, ignores platform/player parameters and does not attach
stream authentication. Content traversal has no paging and omits episodes from
the episode builder. No automated tests were found. These findings are tied to
that revision, not a claim about future upstream versions.

## MSX documented contracts

- [Start Object](https://msx.benzac.de/wiki/index.php?title=Start_Object): start parameter
  points to menu/content. [Setup](https://msx.benzac.de/wiki/index.php?title=Setup_Start_Parameter)
  uses a hosted `/msx/start.json` for a server address.
- [Content Root](https://msx.benzac.de/wiki/index.php?title=Content_Root_Object) and
  [Content Item](https://msx.benzac.de/wiki/index.php?title=Content_Item_Object):
  grid/list JSON with template/items, poster URLs and actions.
- [Requests](https://msx.benzac.de/wiki/index.php?title=Requests): MSX appends `v`/`t`.
- [Responses](https://msx.benzac.de/wiki/index.php?title=Responses): wrapper with
  response.status/data; application errors should use HTTP 200 with error status
  in the wrapper. Requests time out after 30 seconds.
- [Resolve Action](https://msx.benzac.de/wiki/index.php?title=Resolve_Action):
  `video:resolve:URL` resolves to response data containing `url`; useful for
  generating authenticated links on demand. Available since 0.1.107; returned
  extended properties require 0.1.145. The current one-row centered-title layout
  targets MSX >=0.1.146; tested web runtime is 0.1.167, TV version remains to verify.
- [Setup Precondition](https://msx.benzac.de/wiki/index.php?title=Setup_Precondition):
  CORS must be supported. [Extended Properties](https://msx.benzac.de/wiki/index.php?title=Extended_Properties)
  describes player triggers and resume properties. Neither establishes their
  reliability on this Philips. M1 does not rely on event telemetry.

No inspected official MSX material establishes a SAPHI-specific tested codec,
HLS, subtitle or seeking matrix. No official promise of TV cookie persistence
was found; M1 avoids it. Browser rendering can validate JSON integration but not
the actual SAPHI decoder.

## Philips compatibility evidence

The [official 32PHS6605/12 datasheet](https://www.documents.philips.com/assets/20230227/fd829d740bc24c95a11fafb6009a42e5.pdf)
lists H.264, HEVC, AAC and several subtitle formats as multimedia capabilities.
It lists a 1366x768 panel. It does not establish those capabilities inside MSX.
MP4 progressive HTTP, HLS TS/fMP4, bit depth/profile, native web subtitles,
HTTP Range seeking and TLS behavior all remain **device-unverified**.

Historical initial Ultra experiment: H.264/AAC MP4 at <=720p. This restriction
has been replaced by the model-specific HD-policy-v2 profile. H.264/AAC MPEG-TS HLS is
optional only on a different, explicitly authorized transcoding host. HEVC
was initially excluded; it is now an explicitly device-unverified candidate. Test audio
and subtitle delivery separately; USB playback is insufficient evidence.

## Jellyfin evidence and blockers

[Jellyfin codec documentation](https://jellyfin.org/docs/general/clients/codec-support/)
distinguishes Direct Play, Direct Stream and transcoding and explains that
subtitle incompatibility can require burn-in. Client capabilities determine the
delivery choice; this documentation does not certify SAPHI.
[PlaybackInfo DTO](https://github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Models/MediaInfoDtos/PlaybackInfoDto.cs)
and [controller](https://github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Controllers/MediaInfoController.cs)
document the POST body, user, DeviceProfile and transcoding flags. M1 tests mock
this contract. Real authentication, browsing and two Direct Play negotiations now
passed with the operator's release; see `msx-test-results.md` for the limits.

The operator's actual server reports 12.4.0. Real sign-in succeeded, but the first
library request exposed an authentication incompatibility. The
[Jellyfin core developer's authentication guide](https://gist.github.com/nielsvanvelzen/ea047d9028f676185832e51ffaf12a6f)
documents removal of legacy X-Emby-Token and api_key in Jellyfin 12. The corrected
client uses MediaBrowser Authorization Token for REST and canonical ApiKey only
where the native player requires a URL. Mock transport now rejects legacy-only
authentication. Actual private-library access and browser video start/pause/seek/
stop/replay subsequently passed; physical SAPHI and audible audio remain separate gates.

No proven hard blocker yet. Release-blocking unknowns: MSX/SAPHI HTTPS trust and
CORS, usable native MP4 path, Range/seek behavior, network throughput and a
compatible stored version. Ultra's no-transcoding restriction is an established
deployment constraint, not an encoder-capacity question. If no usable stored
version plays in the actual MSX engine, this deployment cannot satisfy the
mission without another player integration or hardware. Security may also require
a media gateway if user tokens in device-side media URLs are unacceptable.

Contract review additionally checked Jellyfin's
[MediaInfoHelper](https://github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Helpers/MediaInfoHelper.cs):
audio/subtitle indices are applied when the supplied MediaSourceId matches the
source. The current implementation pins the selected compatible user-item source
on all requests. Optional subtitle choices refer only to that source. The official
[condition enum](https://github.com/jellyfin/jellyfin/blob/master/MediaBrowser.Model/Dlna/ProfileConditionValue.cs)
includes Width/Height, VideoBitDepth, VideoLevel, VideoFramerate and VideoRangeType.
