# Public MSX playback lifecycle research — issue #17

**Implemented / browser-tested / device-unverified:** an independently authored,
synthetic-only interaction probe and the observations below. **Implemented
separately:** native-original authenticated collection and Jellyfin reporting in
the [#18 contract and actual Chrome evidence](playback-reporting.md).
**Deferred:** genuine application
suspension/resume, abrupt-exit delivery guarantees and physical Philips comparison
(#4). The original research criteria are satisfied by the observed contract,
recorded unavailable cases and conservative fallback (acceptance audit below).
This is not a watch-history implementation or a successful suspension test.

## Public API basis

The vendor's [Plugin API Reference](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference)
documents interaction `handleEvent`, `requestData("video", callback)` and the
video/app event names. The
[attached-data examples](https://msx.benzac.de/wiki/index.php?title=Attached_Data_Examples)
and public [TypeScript declarations](https://msx.benzac.de/ts/tvx-plugin-module.min.d.ts)
describe the video container and its numeric state, position, duration, speed and
ended flag. Video events carry the **previous** active data; a seek also carries
its requested target. A load carries new video info separately. Treat these as
control/lifecycle observations, not decoded-frame acknowledgements.

The [interaction-plugin guide](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin)
defines its noninteractive role: our HTML returns content and MSX renders the
controls. Only the vendor-hosted `https://msx.benzac.de/js/tvx-plugin.min.js` is
loaded. No proprietary runtime was inspected, copied, hosted or changed. Public
declarations and the vendor's documented observer example were read as interface
evidence; no example implementation was copied.

The API's named callbacks include load/play/pause/stop/seek/restart/speed/volume
and application suspend/resume/sleep/awake/connect/disconnect. It does not document
a periodic progress callback or an exit-delivery guarantee. Requested samples are
explicitly labelled `snapshot`, never an emitted progress event. The probe records
load/play/pause/stop/seek/restart/speed and those six app callbacks. Volume, resize,
custom and settings callbacks are outside its allowlist: absence claims below
apply only to collected names. Unknown callbacks are discarded.

## Probe and actual environment

`tools/msx_lifecycle_probe.html` keeps the last 240 sanitized records in iframe
RAM. Each record contains a local sequence, elapsed milliseconds, a fixed kind/
name and allowlisted finite numbers/ended boolean. It discards URLs, titles,
properties, credentials, device IDs and arbitrary payloads. It logs only those
synthetic records and exposes them in its own diagnostic DOM and an MSX list.
Nothing is sent to a backend or persisted in storage. Polling runs at most once
per two seconds, one request at a time, with a five-second callback deadline and
late-response suppression. Periodic sampling stops after ten minutes; callback
event handling continues for the iframe lifetime. Close the tab to stop it all.

Observed on 2026-10-30: official MSX **0.1.167 web**, connected **Chrome extension**,
Windows, existing profile **Mein Chrome**. Chrome 156.0.8078.80 was recorded in
the preceding #11 run; this run did not independently query the executable
version. Top-level origin `https://msx.benzac.de`, plugin/media origin
`https://raw.githack.com`. Browser partitioning was neither disabled nor inspected;
this is the existing profile/origin pair, not a controlled dedicated deployment.
Screenshots were 2560x1215 and 2560x1249, without a viewport override.

The synthetic clip is 30 seconds, H.264 Main/yuv420p, 1280x720, **24 fps**, AAC-LC
stereo/48 kHz; provenance and SHA256 are in
[the public fixture results](msx-public-fixture-results.md). Audio was not verified;
the browser extension reported tab muting in its own tab metadata. No audio claim
is inferred from this video/event test.

First run: probe `8c6a459` (four-row page with valid/missing media in one playlist),
`input=2&init=1&suspend=0&animate=0`. Final probe:
`8608cde7d254267b0e1269d9439652194c214690`, same flags except `suspend=1`;
missing media moved to a separate content page. Both pin media at
`998bc0829b2df06db568443803a6fb4533e23f40`. Preview delivery used the already
authorized development HTTPS source renderer, not new hosting resources. No
credentials, capability URLs, pairing codes, real Jellyfin traffic, OS trust/TLS
changes, Ultra conversion or production deployment were involved. The shared
preview origin is unsuitable for real secrets.

## Actual actions and public callback evidence

Sequences below refer to the locally saved console records, not DOM video state.
Screenshots separately corroborate visible pictures/controls/content. Times and
positions from the public API are coarse integer seconds in this observation.

| Actual control/action | Public API observation and interpretation |
| --- | --- |
| First Play | Run 1 #8 `video:load`, prior state=1/position=0/duration=0; #9/#10 requested samples state=2, position=1 then 3, duration=30. No collected `video:play` accompanied initial load. A real test-pattern frame was inspected. Load alone cannot mean playback started. |
| Pause | Run 1 #13 pause carried old playing state=2/position=7; samples subsequently state=3/position=8. Final #45 pause carried position=15; samples #46–#59 held state=3/position=16 over about 26 seconds. Screenshot shows the paused frame and Play control. |
| Resume | Run 1 #26 play carried old paused state=3/position=8. Final #60 similarly carried state=3/position=16. Immediate samples may still contain the previous state. |
| Forward, rewind | Run 1 #28 seek old position=8, target=13; samples advanced to 14 and 16. #31 rewind old position=18, target=13. Final #61 target=21 then #62 target=16. These are requested targets, not proof of seek completion; reconcile with later samples. |
| Explicit Stop/eject | Run 1 #32 stop carried position=18; #33 still reported playing/18 about 0.33 s later; #34 at about 2.33 s after Stop reported state=1/position=0/duration=0. Final #63 stop likewise preceded state=1 samples. Returned content was usable; replay produced another load and advancing samples. |
| Natural completion | Run 1 samples reached 29/30; #64 next load carried prior position=30/duration=30/ended=true. MSX advanced to the missing row, then #65 pause and zero-duration state=3. Final single-valid-media configuration reached #19 load with prior ended=true/30 and restarted the valid clip; another completion repeated this pattern. No collected stop or restart callback was required for these automatic transitions. This is playlist-specific behavior, not universal exit-on-end. |
| Back during playback | First Back hid the player overlay; second Back returned to content. Final #70–#74 samples continued playing at positions 1,3,5,7,9. Clicking Exit probe content returned to the launcher; reopening retained the same plugin sequence. No collected stop accompanied those navigation actions. Back/content exit cannot be treated as Stop. |
| Missing public media | Run 1 auto-next produced load then pause with zero duration; native accessibility text said media could not play, screenshot was black rather than a clear application error notice. Stop recovered content. Final #77 load carried the previous valid clip's position=15/duration=30, then #79 pause carried zero duration. Subsequent samples stayed state=3/position=0/duration=0; #136 explicit Stop recovered the usable missing-media page. A pause event alone does not distinguish user pause from failure. |
| Duplicates/order | No duplicate collected callback was observed for a single tested Pause/Play/Seek/Stop click. Repeated identical snapshots and repeated loads at natural ends occurred. Sequence reflects receipt order in one iframe only. The sample after Stop and rapid seek/Stop demonstrate stale data; no exactly-once delivery or global ordering promise follows. |

### Network loss and recovery

Run 1 used tab-scoped Chrome DevTools network emulation through the connected
browser capability. The first offline replay still rendered/advanced from cached
media: this did not establish a failed fetch. After stopping, disabling only that
tab's cache and repeating offline, a real Media request failed with
`net::ERR_INTERNET_DISCONNECTED` (not canceled). Collected #97 load was followed
by #98 pause, then zero-duration snapshots changed from state=2 to state=3.
The saved offline screenshot shows an MSX Error notice saying the source is not
supported, with the public synthetic URL. This differs from the black
missing-media screenshot and does not diagnose a decoder incompatibility.
No collected `app:disconnect` accompanied this scoped fetch failure. This does
not test a real OS link loss, prove navigator online/offline signaling or exercise
loss after a long uncached stream has begun. Network emulation and cache override
were both restored; no browser security or OS network setting was changed.

### Suspension and abrupt exit limitations

[URL parameters](https://msx.benzac.de/wiki/index.php?title=URL_Parameters)
document `suspend=0` off, `suspend=1` visibility handling and `suspend=2` system
handling. Final testing used `suspend=1`. Opening an ordinary temporary tab and
returning did **not** produce collected suspend/resume callbacks. Read-only DOM
observations reported both documents visible/hidden=false even while Chrome tab
metadata marked MSX inactive and the other tab active. Bringing that other tab
forward normally did not change this. This automation environment did not create
the required visibility precondition, so genuine suspension remains **unverified**.
No visibility setter, synthetic event dispatch or fabricated app callback was used.
Temporary tabs were closed. This is not a Philips standby result or evidence that
MSX cannot suspend.

The bounded follow-up on 2026-10-30 confirmed that the owned MSX and comparison
tabs were in the same normal window. The connected management tool rejected
`tabs.update` with `active` as unsupported; no equivalent workaround was used.
The documented window-create operation then isolated only the owned MSX tab in a
new normal window. Ordinary minimization succeeded and a separate metadata read
confirmed `minimized`. Nevertheless, document reads still returned
`hidden=false` / `visible`, samples advanced and naturally reloaded the clip, and
no collected suspend/resume callback appeared. Restoring the window to `normal`
gave the same visibility result. The restored screenshot shows an actual frame,
not a hidden document. Playback was stopped; both owned tabs and the isolated
window were closed, leaving the pre-existing user tab/window intact. No runtime
events, visibility values or player state were injected. Sanitized evidence is
retained in ignored `issue17-suspend-followup-{minimized,restored}.json` and
`issue17-suspend-followup-restored.jpg`; an independent reviewer inspected them.
The [terminal technical report](https://github.com/alexanderhetzel/jellyfin-msx/issues/17#issuecomment-6534404792)
remains accurate: genuine suspension is technically unverified.

Closing a probe tab destroys its collector. No acknowledged final delivery after
destruction can be inferred from the last saved console row. Process kill, OS
sleep/wake and crash were not exercised. Do not rely on unload or an app callback
to send a final stop. Genuine browser suspension remains unverified; physical
ordering/suspension comparison remains #4. Recording this unavailable precondition
and defining the fallback satisfies the original research criterion; successful
suspension emission was not an additional research acceptance requirement.

## Candidate authenticated telemetry contract for #18

This is a design, **not implemented or browser-validated transport**. The synthetic
preview never receives an authentication grant. Before production use, validate
the plugin's real HTTPS POST/header/CORS path on an operator-controlled origin.

1. After normal authentication and authorized item/source negotiation, the backend
   issues a random expiring playback grant bound to the existing session, user,
   selected item/source and one playback generation. A TV/device ID or client
   event never creates authority. Send that grant in an Authorization header over
   HTTPS to a fixed operator endpoint, never a URL, public JSON, telemetry field,
   console or access log. Check session expiry/logout/revocation on every request.
   CORS is narrowly configured for the real plugin origin, without cookies; it
   does not replace authentication. No arbitrary destination or Jellyfin URL.
2. Candidate POST body: schema version, server-issued playback ID/generation and
   at most 16 observations. Each observation has a positive bounded sequence,
   elapsed time, kind (`event` or `snapshot`), enumerated name and finite bounded
   state/position/duration/speed/ended/seek target. Reject unknown fields, raw
   attached info, strings/NaN/infinities/negative positions and oversized numbers.
   Enforce 8 KiB **before JSON parsing**, a JSON content type, bounded nesting and
   per-session/global rates. Verify position/duration against server-known media
   bounds with a documented small rounding allowance; never trust client duration
   to expand an item or source's authorization. No free-form diagnostics/URLs.
3. Keep at most 64 pending observations per playback in client RAM, one upload in
   flight and a five-second request deadline. Coalesce ordinary progress to one
   latest sample per ten seconds. Reserve terminal/control observations before
   dropping superseded progress. Retry at most three times with bounded backoff
   (1/2/4 seconds); do not build a durable offline history or endless queue. Keep
   the last accepted safe position if an upload cannot be acknowledged.
4. Backend retains a high-water sequence plus a bounded recent window of 64
   sequence-to-payload digests per playback generation and acknowledges accepted
   sequence values. A replay inside that window is idempotent only if its
   canonical sanitized payload digest matches; reject conflicting reuse. Reject
   older-than-window observations without applying them (do not claim to detect
   their content conflicts). Reject old generations. Do not apply late events from an old
   source or iframe to a new playback. Client elapsed time and receipt order are
   diagnostics, not trusted wall time. A replay/new load requires explicit
   generation correlation, especially because load's attached data is for the
   **previous** video. This probe intentionally does not implement that binding.
5. Maintain separate requested and observed states. Load/play means requested
   activity. Establish observed playback from valid samples with known duration
   and advancing position; do not synthesize progress from wall time. On pause or
   seek, poll and reconcile within five seconds; stale snapshots must not undo a
   newer terminal control intent. A seek target is not an observed position. On
   Stop, use the last valid prior position rather than the reset zero. When a load
   carries previous ended=true, finalize the matching old generation before
   starting the new one. Never mark completion merely from a near-end position,
   transport success, zero duration or a pause event.
6. No reliable exit/disconnect event is assumed. If samples/heartbeats disappear,
   expire the active playback after a candidate 45-second lease, retain the last
   observed position, mark the reason **abandoned/unknown**, and reconcile safely
   on the next authenticated contact. Do not mark watched or claim natural
   completion. Suspension/network errors may delay timers; resumption requires
   authorization and a fresh sample before reporting active playback. Backend
   restart/session expiry fails closed; never infer a stop delivery guarantee.
   Unknown visibility does not itself fabricate a pause or advance position. If
   fresh valid samples keep arriving, report only their observed state/position;
   if they cease, expire the lease without extrapolating progress. Delayed timers
   or absent suspend callbacks therefore cannot keep an abandoned session alive
   indefinitely. #18 must test this policy and choose final timing constants.
7. Retain only bounded operational state and aggregate error counters. Disable
   request URI/body/header logging; exceptions must use fixed codes. Do not write
   operator titles/IDs, grants, media URLs or arbitrary upstream errors to logs.
   Tests for #18 must cover authorization, cross-session/source/generation denial,
   early body limits, replay/conflicts/reordering, duplicate terminal events,
   missing starts/stops, stale snapshots, ended handoff, expired leases and bounded
   retry/queue/rate behavior with mocked Jellyfin. Actual plugin transport remains
   a separate observable acceptance requirement.

All time/size/rate choices above are proposed application policy, not measured
MSX timing guarantees. Keep no-transcoding, HD admission, private-route auth and
direct-media privacy boundaries unchanged. Physical Philips results must later
record firmware/MSX/media combination and actual control/event order in #4.

## Reproduction, evidence and acceptance

The fetched launcher is pinned at
`32aaa0f1d765d16214e86bfec072a788963840b1/tools/msx_lifecycle_start.json`; it pins
the final probe source separately. From a checkout with frozen dev dependencies:

```sh
uv run python -m tools.msx_storage_probe https://raw.githack.com/alexanderhetzel/jellyfin-msx/32aaa0f1d765d16214e86bfec072a788963840b1/tools/msx_lifecycle_start.json
```

This existing generic helper prints a launch URL, not an E2E assertion command.
The fetched pinned launcher and its Open interaction were rechecked in the
official runtime after the full matrix; `issue17-pinned-launch.jpg` records the
result. All owned probe/temporary tabs were closed afterwards.
Open it in connected Chrome, click Open lifecycle probe, then the real Play
control. Inspect a real frame and the `MSX17` sanitized console records. Pause,
wait for separate held samples, resume, forward/rewind, Stop/eject, replay and
Back twice. Read received events renders a snapshot of the most recent 18 rows;
it does not refresh itself. Reopen it for newer rows. Let the 30-second clip end
without input and record the next load's prior ended state separately. Open the
missing-media scenario, Play, then Stop for recovery. No media property setter
or event injection is needed. Controls auto-hide; click the video to reveal them
and inspect the current overlay before using its icons.

For the visibility test change only the launch query to `suspend=1` in a fresh
owned tab. Open/activate another ordinary tab, observe actual document visibility
and collected app callbacks, then return. If the tool still reports visible,
record the precondition failure; do not claim suspension or spoof visibility.
For a scoped offline scenario, first load the public plugin normally, then use
the browser's tab-scoped network emulator. Cached playback is a separate case;
a failed fresh Media request must corroborate any fetch-loss claim. Restore
network and cache settings before closing all owned test tabs. OS/device
connectivity and standby are separate tests.

Local ignored `.lab/reports/issue17-run1.json` and `issue17-run2.json` retain only
the probe-filtered console entries (including the public source URL, not private
network captures). `issue17-{pause,seek,events,completion,offline,back}.jpg` are
initial captures; `issue17-final-{frame,pause,events,missing,recovery}.jpg` and
`issue17-back-content.jpg` document final-source UI. The initial completion image
shows the post-completion missing-media state, not a frozen last valid frame.
The final events image shows received Play/Seek rows and separately labelled
samples, with readable labels/focus. Missing-media image is black; it must not be
represented as a visible application error notice. Tool clicks on already-hidden
icons timed out; no state change or playback failure is inferred from those tool
errors. No raw private traffic or operator identifiers are retained.

## Research acceptance audit — 2026-10-31

The owning issue asks to **record** lifecycle behavior and define a safe contract
before Jellyfin reporting. Its observable milestone explicitly permits unavailable
cases with conservative fallback rather than injected events. The earlier decision
to keep research open until genuine suspension passed added a success gate beyond
that wording. This audit changes that interpretation, not the original criteria
or the retained technical observations. Independent review mapped all four:

| Original research criterion | Retained evidence and boundary | Result |
| --- | --- | --- |
| Inspect public API, test actual Chrome emission, define candidate TV contract | Public API/declarations; actual Load/Pause/Play/Seek/Stop callbacks, separately labelled requested progress and visible screenshots. No Philips emission inferred. | Met. |
| Record duplicates, missing events, order, suspension and network behavior | Ordered records show missing initial Play, stale state, repeated snapshots/loads, Back without Stop, cached offline playback and failed fresh Media fetch. Same-window/minimized-window attempts record unavailable visibility precondition and absent collected app callbacks. | Met as research with recorded limits; successful suspension remains unverified. |
| Define bounded authenticated sanitized backend telemetry | Session/source/generation-bound grant, body/queue/retry/rate bounds, allowlist and bounded replay-digest window. | Met as design; no production collector/transport pass. |
| Record fallback/reconciliation before reporting | Requested versus observed state, no fabricated progress, stale-event/end-generation reconciliation, last safe position, candidate 45-second lease and authorization/fresh sample on return. | Met as design; #18 owns implementation and verification. |

No missing suspension fact blocks safe #18 implementation under that conservative
contract: it must work when callbacks are absent and timers are delayed. #18
still owns authenticated transport, source/generation correlation, Jellyfin
start/progress/stop reporting, bounded retries and disappearance recovery, with
mocked regressions and actual official-runtime verification. The 45-second lease
and other policy constants are design choices, not measured MSX guarantees.
Genuine suspension, OS sleep/crash, final-delivery guarantees, audible audio and
physical Philips behavior remain unverified. Neither the historical 206 Python
tests nor this public probe establishes authenticated production transport,
private source delivery or an all-client integration pass. Research closure must
not be represented as any of those passes. No browser or relay was launched for
this acceptance audit.

Independent review inspected the final source/public API contract, both ordered
record sets and six saved UI images. It identified the high-water-only replay
ambiguity; the bounded digest window above resolves that design gap. The reviewer
independently ran the existing 206 tests and Ruff/format/diff checks, but did not
operate the browser, test authenticated transport, or verify audio/hardware.
