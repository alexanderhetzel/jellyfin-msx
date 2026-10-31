# Authenticated original playback reporting — issue #18

**Implemented / automated-tested; actual runtime verification pending.** Physical
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
the original session on every request and upstream send. JSON-only, exact-origin
requests reject duplicate object keys, unknown fields, malformed values and
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
These checks do not establish official-runtime delivery. Actual Chrome actions,
media observations, sanitized request evidence and cleanup will be recorded here
after the master grants the shared browser/relay slot.
