# Saved progress — issue #19

**Implemented / automated-tested / browser-tested / device-unverified.** Actual
official MSX Resume/Start over observations below verify the scoped synthetic
software flow. Physical Philips/audio/remote behavior remains in #4.

## User behavior and limits

Movie/episode details show `Resume from HH:MM:SS` and `Start over` when Jellyfin's
UserData.PlaybackPositionTicks is meaningful for the selected eligible stored
source. The client requires at least five seconds played, less than 90% elapsed
and more than five seconds remaining. Played=true, missing/invalid/negative or
out-of-range progress, and unknown/invalid duration offer playback from zero.
These are client UX thresholds, not a claim about Jellyfin's watched thresholds.

The detail label is a snapshot. Resume rereads authorized item metadata when the
native resolver runs and uses fresh saved progress; Start over explicitly uses
zero. Opening a choice or negotiating does not clear server history or fabricate
a playback report. After a real Stop, reopen details to refresh the label.

Both choices retain the detail-selected source ID. A missing/ineligible source
fails closed instead of silently playing another cut. Item-wide saved progress
is bounded against that source's duration (falling back to item duration only
when the source omits it). Different cuts are not assumed frame-equivalent. If
PlaybackInfo returns a duration that invalidates a requested nonzero resume,
the resolver refuses playback and asks for refreshed details.

Saved resume supports original files only, even on an explicitly conversion-enabled
host. It advertises no HLS fallback, DirectStream, subtitle burn-in or conversion.
Existing optional conversion behavior outside saved resume is unchanged.

The existing native pause/play/seek/restart controls retain the selected original
and its timeline. Audio/version selection remains #20; no new selector is added.
Legacy `Try original` and HTML5X subtitle playback remain unreported and do not
promise Jellyfin saved-progress restoration. Their distinct controls are retained.

## Transport and reporting

The authenticated `/api/playback/start` JSON accepts a strict boolean `resume`;
it does not accept a caller-supplied position. Resume is rejected with explicit
force/subtitle settings. The backend validates the selected source and fresh
progress, sends PlaybackInfo `StartTimeTicks`, and returns numeric
`start_position` in seconds. The bridge rejects malformed/out-of-duration values
and nonzero Start over responses. Its native resolver returns that position as
the documented [`resume:position` property](https://msx.benzac.de/wiki/index.php?title=Extended_Properties),
alongside the existing public generation marker. The vendor's
[resolver contract](https://msx.benzac.de/wiki/index.php?title=Resolve_Action)
allows extending video properties this way. No MSX local resume key or custom
display-position override is used; no media currentTime setter is injected.

Requested start/seek positions never enter reporting as observations. The
[#18 contract](playback-reporting.md) still requires matching generation-marked,
advancing native samples for Start and fresh samples for progress. A confirmed
Stop retains last-safe position rather than the player's reset zero. Only an
observed end is successful completion; other terminal paths remain Failed=true.
Existing expiry/revocation, old-Stop-before-new-Start and bounded retry rules apply.

## Verification

Mocked tests cover Movie/Episode detail choices, fresh progress, explicit zero,
malformed/watched/near-end values, source reorder/pinning/removal, different cuts,
returned-duration mismatch, conversion denial on an opted-in synthetic host,
authorization loss and observed seek/Stop. Node tests check native resolver
properties, invalid position rejection, and unchanged generation correlation.

The opt-in `resume` synthetic HTTPS scenario supplies four fixed authenticated
items (movie, episode, near-end and watched), the same reviewed original clip,
per-login RAM progress, and fixed numeric reporting/negotiation summaries. It
uses strict MockTransport and the existing supervised relay. Existing baseline,
failure, navigation, subtitle and lifecycle scenarios are unchanged. This is a
synthetic contract model, not a real Jellyfin release test.

## Actual official-runtime observations — 2026-10-31

Source `bad458c48a4abbfa1ea6051bd7981fa31a7461a5`, official hosted MSX in the
connected Chrome extension, Windows/profile Mein Chrome, unmodified viewport.
The runtime/browser version was not independently queried in this run; #18's
earlier version record is not a new measurement. One master-granted supervised
HTTPS run used the existing reviewed binary/clip and its original 900-second
total budget (180-second startup bound included). Normal companion code/credential
stages and actual Continue reached private libraries; no public substitutions or
authentication bypass were used. Codes, QR and capability/media URLs were not
emitted or retained. Only native UI controls changed playback.

| Actual UI/media observation | Separate redacted request/report observation |
| --- | --- |
| Movie details showed Resume from 00:00:08 and Start over. Resume decoded 1280x720, readyState4/error null, retained time14.400717. | Negotiation1 requested start8; authenticated Start1, progress and Stop1. |
| The short movie naturally finished before the attempted Pause. Reopened details offered only beginning playback. | Last position30, inactive, Failed=true. No successful-ended report is claimed; near-end/Stop reconciliation is not a new #18 completion pass. |
| Episode details showed the same saved8 choice. After native Resume click, a loading sample was0 at304ms; decoded time11.855827 at4436ms, then paused12.688884 at5318ms. A later sample held12.688884. Real test-pattern frame was inspected. | Negotiation2 requested8; Start2. Paused report position13 (public API uses coarse seconds). Requested8 and measured native time are separate evidence. |
| Native forward while paused landed18; native rewind landed13, readyState4/no error. | Authenticated progress separately moved to18, then13 with paused=true. |
| Native Stop cleared media (paused, time0/readyState0). Back to details showed Resume from 00:00:13. | Stop2 retained13, inactive/Failed=true, rather than the player's reset0. |
| Start over → Play from beginning decoded at4.689315 at5159ms after click, then paused5.012135 at5533ms. Real frame near5 was inspected. | Negotiation3 requested0; Start3, paused report5. |
| Stop and Back refreshed the episode choice to Resume from 00:00:05. | Stop3 retained5, inactive/Failed=true. |
| Near-end and watched catalogue items settled on beginning-only details, no Resume choice. | No extra negotiation; total stayed3. One immediate transitional near-end read was empty; settled visible content is the evidence. |
| Normal Disconnect TV → Confirm disconnect completed; own tabs closed. | paired_sessions0, logout HTTP204; three PlaybackInfo HTTP200, each DirectPlay=true, DirectStream=false, Transcoding=false, subtitle index-1. |

Six secret-free PNGs and numeric/fixed-counter `observations.json` are retained in
the ignored local `.lab/issue19-evidence/` for independent inspection. Images show
initial choices, resumed paused frame, refreshed13 choice, beginning paused frame,
and settled near-end/watched details. Request summaries are separate from pixels
and media DOM measurements; no missing Network events are used as evidence.
The near-end/watched screenshots look identical because those fixtures share a
display title; their distinct cases rely on the recorded catalogue actions and
settled states, not distinguishable pixels. Independent evidence review inspected
all six images/JSON and accepted the four scoped software criteria without
repeating browser actions. Source pinning/clamping and unsupported track/version
limits rely on the reviewed mocked tests/source, not a new runtime selector pass.

Initial exact-text attempts used AX-uppercased labels/CSS glyphs that were not DOM
text. Player Pause also auto-hid while the short movie advanced; fresh visible
DOM/classes corrected those tool selector deadlines. These are not application
failure, decoder failure or physical remote evidence. No restart, manual warmup,
source variant, extra run budget, CDP, Network observation or viewport override
was used. No Data Load Error appeared in the observed flow; this does not resolve
the separately documented intermittent startup issue.

Explicit supervisor stop at **14:27:18 UTC** returned exit0/stopped. All nine
recorded owned PIDs, listener18092 and control directory were absent; both owned
tabs closed and no browser override needed restoration. The master received the
slot release before further work. No operator/Ultra, real Jellyfin release,
audible audio, hardware, genuine suspension or optional HLS/subtitle/track-switch
acceptance follows from these observations.
