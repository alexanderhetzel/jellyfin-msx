# Authenticated original playback reporting — issue #18

**Implemented / automated-tested / browser-tested / device-unverified.** Physical
Philips playback, audio, genuine suspension and OS sleep/crash remain
**device-unverified** in #4. This feature does not establish decoder support.

## Supported flow and public contract

The preferred **Play original with watch progress (TV unverified)** entry opens
the operator-origin lifecycle interaction. Its Play action uses the published
[`video:resolve:request:interaction` action](https://msx.benzac.de/wiki/index.php?title=Internal_Actions).
The authenticated resolver returns the original media URL plus a random playback
generation through the documented [resolve response properties](https://msx.benzac.de/wiki/index.php?title=Resolve_Action).
The interaction compares requested `video.info.properties` against that generation
in RAM before accepting numeric video samples. Raw info, URLs and titles are never
uploaded. [Public attached data](https://msx.benzac.de/wiki/index.php?title=Attached_Data_Examples)
separates video information from state/position/duration; numeric similarity is
not source identity. Existing [lifecycle research](msx-lifecycle-research.md)
explains stale event data and missing callbacks.

The existing **Try original** entry is an explicitly unreported compatibility
and recovery path, including servers without reporting metadata. The #22 HTML5X
subtitle bridge stays unchanged and unreported: its video callback does not prove
propagation of the native resolver generation properties. Subtitle reporting is
**deferred** until that contract is verified. Startup/enrollment interaction
ownership is unchanged; reporting never renews or replaces authentication.

## Authentication and bounds

`POST /api/playback/start` accepts the existing expiring session capability only
in its Authorization bearer header, an allowlisted item/source and optional
operator-permitted force/subtitle settings. Normal Jellyfin item access and fresh
PlaybackInfo revalidate the selected source, HD admission and no-transcoding
policy. Missing finite server duration or PlaySessionId fails closed. A second
authorization check follows awaited generation replacement. The resulting random
reporting grant binds session, item, source, upstream play session and generation.
It is kept only in client/backend RAM; neither grant is placed in telemetry URLs.
The existing interaction fragment and direct media URL remain private bearer
material; [direct-media token exposure](media-token-security.md) is unchanged.

`POST /api/playback/observations` requires that reporting grant and revalidates
the original session on every request and upstream send. JSON-only requests reject
foreign supplied origins, duplicate object keys, unknown fields, malformed values and
oversized bodies (8 KiB before parsing). Batches contain at most 16 allowlisted
observations. Positions/durations cannot expand the server-known duration (two
seconds of rounding allowance; reported ticks clamp to the known duration).
An increasing sequence and 64-entry canonical payload digest window make recent
duplicates idempotent and reject conflicts/older reordering. Old grants cannot
address a replacement generation. Terminal replay state lasts at most five
minutes, within absolute authorization expiry.

Client RAM holds at most 64 observations; ordinary progress coalesces to ten
seconds, while controls and observed ended samples flush promptly. One upload is
in flight, with a five-second timeout and at most three retries at 1/2/4 seconds.
Sampling requests run every two seconds with five-second callback deadlines,
generation checks and an absolute eight-hour ceiling. No durable offline history,
renewal, arbitrary destination, vendor private API or copied runtime is used.

Backend rates are bounded per session/global/peer; grant capacity follows
`max_states`. Per-session locks serialize report delivery and generation changes.
The old Stop must be acknowledged before a replacement can become active.
Upstream delivery has a five-second aggregate budget, a 16-entry outbox and at
most three attempts. Three consecutive failures close reporting at the last safe
position and attempt bounded failed-Stop cleanup. A Start may have reached
Jellyfin despite a lost response, so it also receives that cleanup attempt.
Unacknowledged Stop fences replacement reporting until cleanup succeeds or the
original authorization expires; it is not silently discarded with replay history.
Re-pairing can create new authority, but does not prove old upstream cleanup.

One supervised task checks leases every two seconds; all leases reconcile before
any network wait, and a rotating batch of at most eight delivery tasks bounds
cleanup work. Cancellation/shutdown stops that task. Backend restart loses RAM
grants and fails closed; it cannot guarantee delivery of a final upstream Stop.

## Observed state, control intent and cleanup

Load/Play callbacks are intent, never proof of decoded video. Two valid advancing
playing samples establish observed Start. Valid samples alone supply position
and paused state. Pause/Play/seek intent reconciles with subsequent samples for
five seconds; seek targets never become reported positions. Load's attached old
data cannot finalize a new generation. Only a matching, valid near-end snapshot
with explicit `ended=true` identifies natural completion.

Stop carries no public media identifier. It is held as intent until a fresh
generation-marked stopped sample confirms it; reset zero is never reported as
progress. If identity disappears or no confirmation arrives, the backend's
45-second valid-sample lease closes the session as abandoned/unknown at its last
safe position. Unknown visibility or missing callbacks never fabricate pause,
elapsed progress or completion. Fresh matching samples report only their actual
state. A late previous Stop followed by current playing samples cannot terminate
the new generation.

Modern authenticated Jellyfin [`Sessions/Playing`, `/Progress`, `/Stopped`](https://github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Controllers/PlaystateController.cs)
reports carry pinned ItemId, MediaSourceId and PlaySessionId. Stopped invokes
Jellyfin's play-session-scoped optional transcode cleanup; no broad encoding-job
deletion is performed. Defaults still prohibit conversion/burn-in on Ultra.
Non-ended cleanup uses `Failed=true`: Jellyfin otherwise applies its completion
threshold on Stop (and null position can imply completion). The client never
posts played/unplayed mutations; Jellyfin owns its watched/resume thresholds for
positions actually observed. No exactly-once upstream delivery or final-delivery
guarantee is claimed when requests, authorization or processes disappear.

Diagnostics contain fixed error categories and bounded decision aggregates;
report grants, raw payloads, private URLs, tokens and operator identifiers are
excluded. The synthetic lifecycle scenario adds only fixed counters and numeric
last position, behind the existing strict MockTransport and supervised HTTPS
dispatcher. It never reads operator configuration or falls back to real network.

## Verification

Mocked Python/Node regressions exercise authorization/revocation during awaited
replacement, missing metadata, early body limits, conflicts/replays, selected
source/generation, stale samples/Stop, pause/seek/end/last-safe lease, bounded
queue/retries, lost Start acknowledgements, Stop ordering/fences and cancellation.
The existing historical public exports exclude authenticated reporting controls.
These checks alone do not establish official-runtime delivery. The actual
source-pinned observations below supply that separate software evidence.

## Actual official-runtime verification — 2026-10-31

Source `96837f114f2b77b05f19ab306cd5ca6a42f2d986`, official hosted MSX 0.1.167 web,
connected Chrome extension, Windows, measured viewport 2560x1215 (no override).
The isolated synthetic lifecycle scenario used normal credential pairing, private
library/details, the preferred reporting entry and its actual Play control.
No event injection, media setters, proprietary runtime inspection/modification,
operator configuration, real Jellyfin server or Ultra conversion was used.

The following are separate observations: media state is read-only native DOM;
visible JPEGs corroborate decoded pictures and controls; the fixed aggregate
summary counts authenticated requests received by strict synthetic MockTransport.
The latter is not a real Jellyfin dashboard/session-compatibility test.

| Actual action | Media/UI observation | Separate authenticated request evidence |
| --- | --- | --- |
| Play original with reporting | Real color-bar/moving-pattern picture;1280x720,ready4,errornull,time11.941801 of30,playing | Start1,Progress1,active,pos11. The reviewed client cannot upload valid samples until public video-info generation properties match its resolver response. No raw info or marker value was retained; successful guarded reporting corroborates propagation rather than a separately logged field dump. |
| Pause and hold | Paused at16.498143; a later read held exactly16.498143 withready4 | Pausedtrue,pos16,active. Start4/Stop3 reflect earlier replays used while identifying native controls, not four distinct media sources. |
| Forward/rewind/resume | Paused seek16.498→21→16, then playing16.062029 | Subsequent active/pausedfalse,pos21. Requested seek targets were not used as observed positions. |
| End versus near-end Stop | An earlier attempted Stop near24.5s could not be separated from natural completion by the later read; reset0/ready0 followed | That generation ultimately reportedStop/pos30/Failedfalse. It is end evidence, not the decisive explicit-Stop test. Earlier ends with no accepted ended sample conservatively reportedFailedStop/pos29. |
| Decisive explicit Stop | Fresh replay advanced, paused at6.835279; after held pause the visible eject control was double-clicked. Native video becamepausedtrue,time0,ready0 | Before:Start5,Stop4,active,pausedtrue,pos7. After:Stop5,inactive,Failedtrue,pos7. Reset zero was not reported as progress. |
| Replay/new generation | A fresh Play subsequently decoded/advanced at12.603374,ready4,playing | Start6,Stop5,Progress31,active,pos11. Replacement reporting did not inherit the previous terminal state. |
| Close owned MSX tab | The actual owned client was abruptly closed, with no final-action injection | At20.651s after close:stillactive,pos11,Progress31,Stop5. At55.536s:inactive,pos11,Progress31,Stop6,Failedtrue. No position/progress extrapolation or completion occurred. |

The disappearance observation brackets delivery between 20.651 and 55.536 seconds
after close. It does **not** measure an exact<=45-second delivery time. The
45-second valid-sample lease, two-second sweep and bounded upstream delivery are
application policy tested separately with controlled clocks; scheduler/transport
delivery adds allowance. No additional runtime matrix was manufactured to replace
that honest timing boundary. Duplicate/conflict/retry/rate/authorization denial,
unknown/revoked grants and optional permitted-host transcode Stop are
**automated-tested**, not new actual browser network/crash/conversion passes.
The RAM restart fail-closed boundary is **source-reviewed**; no explicit backend
restart delivery test or actual process-restart result is claimed here.

Ignored local evidence: `.lab/reports/issue18-run2.json` retains only fixed counts,
numeric media/timing observations and incident categories. The
`issue18-{playing,paused,stopped,lease}.jpg` captures contain no credentials,
capability URLs, QR/code or operator content. `stopped.jpg` is the post-end menu,
not a screenshot of the decisive paused Stop. Physical Philips/audio/remote and
genuine suspension remain **device-unverified**.

One companion locator timed out despite a visible field; normal AX form actions
completed sign-in. Initial control locator attempts failed because glyphs were
CSS icons and some AX indices were stale; the visible DOM control layout and
saved paused image identified actual Pause/seek/eject controls. No playback failure
is inferred from those tool errors. An initial AX tool preview exposed a synthetic
session fragment; normal confirmed Disconnect invalidated that authority before
any Play/report, then normal re-pairing continued within the same supervised
budget. Raw fragments were not repeated or saved in repository/report evidence.

The preceding attempt did not enter pairing or playback: enabling raw Network
inspection while its tab was on the temporary relay origin requested a separate
DevTools permission and delayed the tool return. The master stopped that original
supervisor and verified cleanup. This run used no raw CDP commands, Network
observation or viewport override, and did not change browser/security settings.

At 13:20:59 UTC the existing supervisor was explicitly stopped and returned exit 0
within its original 900-second total budget (startup included). All nine recorded
owned process IDs, loopback listener 18092 and the control directory were absent;
both owned tabs were closed. The first synthetic authority was normally revoked;
the final synthetic authentication was discarded when the bounded backend exited,
not claimed to have been logged out through the already-closed MSX client.

Independent final review inspected all four saved images, the sanitized JSON,
the source/public API contract and automated regressions. It accepts all four
original #18 software criteria for this explicitly supported flow. It did not
operate the browser, repeat the network matrix or establish hardware/audio or
real-server compatibility. The decisive paused Stop and its report were read in
consecutive browser calls after fresh paused samples; their exact time delta was
not retained. The reviewer distinguishes that prompt confirmed Stop from the
later disappearance observation and does not infer either from the post-end
menu image alone.
