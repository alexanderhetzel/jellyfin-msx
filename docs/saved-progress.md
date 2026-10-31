# Saved progress — issue #19

**Implemented / automated-tested / device-unverified.** Actual official MSX
Resume/Start over verification is pending; this source milestone is not browser
acceptance. Physical Philips/audio/remote behavior remains in #4.

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
synthetic contract model, not a real Jellyfin release test. No relay has been
activated for this source checkpoint.

Pending actual acceptance: normal private pairing and details, both native choices,
decoded picture/advancing time versus saved position, pause/seek/Stop and refreshed
progress, and watched/near-end detail handling. Retain UI/media observations and
sanitized requests separately. Automated test counts do not satisfy this gate.
