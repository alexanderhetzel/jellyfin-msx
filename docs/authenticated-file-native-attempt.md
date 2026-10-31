# Authenticated-file native attempts — issue #32

**Actual browser subset / device-unverified / native acceptance deferred.**
This attempt verified normal synthetic pairing, navigation and the outer Movie
Resume entry. It stopped **before verifying and activating the expected inner
playback control**. It did not establish an application startup failure or exercise
native authenticated File playback. The initial interpretation as a first
functional block was premature; the source comparison below corrects that claim.
There is no File policy, byte, decoder, server-version or physical-TV verdict.
A separately granted corrected attempt below ended at a required tool-observation
stage during pairing confirmation, before either playback entry. Neither attempt
supplies native File evidence or establishes an application failure.

## Revision and containment

- Exact main: `e1a6bcd93a34fcdb9e04a1b2caba541b4925800c`, after PR #77.
- One master-granted existing `resume --authenticated-file-candidate` run.
  Window: **2026-10-31 18:00:17–18:09:38 Europe/Vienna**
  (**17:00:17–17:09:38 UTC**), **561 seconds** total. The original 900-second
  total included the 180-second startup ceiling; no restart or budget reset.
- Existing cloudflared 2026.10.7 executable: 55,390,512 bytes, SHA256
  `2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343`.
  Its existing bytes were reused read-only; no download, copy or installation.
- Offline candidate preflight passed. Local and verified-public readiness each
  returned HTTP 200 and the exact candidate marker, confirmed by 17:01:39 UTC.
  The marker attests configuration, not playback. The fixed sample, strict
  MockTransport, owned supervision and sanitized environment were unchanged.
- Connected **Chrome extension**, two newly owned blank tabs, official hosted
  `msx.benzac.de` runtime. Runtime/browser versions were **not recorded**;
  historical version measurements are not assigned to this run. No IAB, Arc,
  native-app fallback, copied runtime, CDP, security prompt acceptance or OS
  trust/network change. Only public fixture credentials were used.

Selected safe observations are retained locally in the ignored ticket artifact
`.lab/reports/32-candidate-20261031T170017Z.json`. It contains fixed counters,
finite/null native fields, source revision and cleanup evidence; no raw network
capture, codes, capabilities, media URLs, headers, bodies or screenshots. Private
in-memory pairing/page observations were cleared after tab closure.

## What actually happened

| Actual action or observation | Supported conclusion |
| --- | --- |
| Normal TV-code check and credential form returned TV paired / Sign-in succeeded. Continue reached authenticated libraries. | Pairing/navigation worked in this synthetic app; no authentication bypass. An earlier safe snapshot recorded one paired session. |
| Synthetic movies opened Movie and Episode catalogue entries; Movie details displayed `RESUME FROM 00:00:08`. | The expected saved-progress **choice** was present. Episode playback was not tested. |
| The outer Movie Resume entry was clicked once. A fixture-origin iframe with the lifecycle path appeared. | Interaction entry was attempted. The fragment was not emitted. Its document was unreadable through the parent DOM, which is not evidence of a script or platform failure. |
| The expected inner `Resume saved progress` row was neither verified nor activated. | The two-step native workflow was incomplete. This is a test-coverage gap, not a proven missing inner UI or failed boot. |
| Parent native video: source absent, time 0, duration unavailable, readyState 0, dimensions 0×0, paused true, error code null. | An unloaded element was observed. Null error is **not** a decoder/error-free/compatibility pass. The selected File target was not observable because no source was present. |
| The attempt ended without another case or payload/source variant. | Actual decode/advance, audio, pause/hold, resume, backward seek, Stop and refreshed progress remain untested. No follow-up run was inferred from the remaining time. |

### Separate request/report evidence

The **last observed aggregate snapshot was 17:07:56 UTC**, before teardown. These
are not post-shutdown/final counters and do not describe every browser request:

| Recorder | Last observed values |
| --- | --- |
| Portal endpoint counts | pair.json 1, pair 3, browse.json 1, detail.json 1 |
| Mock upstream categories | authentication 1, library 3; no PlaybackInfo category observed |
| Fixed synthetic media-handler counts | empty |
| Lifecycle summary | Start 0, progress 0, Stop 0, position 0, inactive, not paused, failed_stop false |
| Synthetic negotiation summary | successful negotiations 0, requested start 0 |

The recorder does **not** count `/api/playback/start`; whether that endpoint was
invoked is unknown. Zero negotiation/media counters, especially without exercising
the inner action, cannot diagnose the candidate policy, transport, byte target or
decoder. No native MIME/range result was collected. Earlier in-process byte/range
tests remain authored-model evidence. Synthetic token denial cannot establish
real Jellyfin revocation, and HTTP readiness cannot establish native playback.

## Concrete source comparison, no runtime variant

The current init handler returns a Playback content page containing the
`Resume saved progress` row. The separate `portal-video` resolver handler calls
`telemetry.start`; the init handler itself does not. The local Node tests also
exercise init and resolution separately. The accepted [#18 observations](playback-reporting.md#actual-official-runtime-verification--2026-10-31)
explicitly distinguish the preferred entry from its actual Play control; the
[#19 source and observations](saved-progress.md) retain this content/resolver flow.

Git object comparison is concrete and reproducible:

- `lifecycle.html` is blob `a56afdacc16a66e48362665668540633c1a6a0f3` in accepted
  #18 (`c4a453e`), #19 (`e21d103`) and this run. SDK/script order, defer and owner
  shell did not change in the candidate milestones.
- #19's lifecycle JS is blob `465737e35516cf80cd917bf992104f1e7ae37105`.
  Recovery #69 changed that JS to `d7294ac0ed77baecdaa41f19d87f57d4bb860a7f`;
  this run has that same blob. Candidate #75–#77 did not introduce another bridge
  variant. Both inspected versions separate init content from resolver invocation.

This identifies an omitted validation step, not a causal application regression.
The run collected no child-frame script/debugger evidence. No SDK, CSP, body,
script-order/timing or security-guard change follows from these observations.
Independent frame facts from another scoped run must remain separate evidence.

## First attempt: disconnect and teardown

**Normal Disconnect was not performed.** Its control was absent in the inspected
stopped state; no further navigation or direct forced logout was attempted under
the early-stop instruction. That does not prove the control globally unreachable.
Process teardown is not normal Logout or token-revocation evidence.

The owned stop command returned stop-requested; retained supervisor execution
returned stopped with exit code 0 at 17:09:38 UTC. All nine observed owned PIDs
`25708, 12704, 33396, 14116, 35488, 44236, 21184, 42376, 43940` were absent at
cleanup verification. Port 18092 had no listener and the owned control directory
was removed. Both owned runtime/pairing tabs were closed and their absence
verified without emitting other tab metadata; other tabs remained untouched.
The master independently verified process/listener cleanup and accepted slot release.

## Separately granted corrected attempt — same unchanged product

The [corrected finite procedure](https://github.com/alexanderhetzel/jellyfin-msx/issues/32#issuecomment-6546689652)
explicitly waits for the unique visible inner `Resume saved progress` row, clicks
it once and permits a bounded ordinary loading window. The
[independent evidence/plan review](https://github.com/alexanderhetzel/jellyfin-msx/issues/32#issuecomment-6546703112)
accepted that procedure without granting activation. The master then granted one
new run for that concrete omitted step. It was not an automatic retry, source
variant or reset of the closed first budget.

Exact product remained `e1a6bcd93a34fcdb9e04a1b2caba541b4925800c`; only evidence
docs were dirty. The second run used the same existing supervisor, pin/clip,
strict synthetic transport, candidate option and Chrome extension. Window:
**2026-10-31 18:28:03–18:34:24 Europe/Vienna** (17:28:03–17:34:24 UTC),
**381 seconds**, including readiness confirmed by 17:29:29 UTC. Local/public
statuses and exact candidate markers were again 200/true before runtime navigation.

Safe selected observations are in the ignored
`.lab/reports/32-candidate-corrected-20261031T172803Z.json`:

| Actual observation | Limit |
| --- | --- |
| A tab handle declared inside a conditional was not retained across REPL cells. The same owned blank tab was rebound through its observed ID before any runtime navigation. | A local binding error, not application evidence; no new tab/run/budget or repeated app action. |
| Official MSX pairing screen and normal code-check form were observed; the sign-in fields later became visible without invalid/expired text. | An earlier broad login-phase catch had no retained exact subcall/error. Its subsequent snapshot had pair count 2 and no upstream authentication; no earlier credential submission was observed by those counters. |
| One completed submit of the now-visible fixture credential form was observed. Immediate success booleans were false during transition. | Earlier phase invocation details are unknown. A later settled browser confirmation was not obtained; transient false is not a sign-in failure. |
| The required subsequent pair-confirmation observation returned the fixed failure outcome, class `other`, before its first safe confirmation output. | Exact failing subcall, invocation and underlying cause are unknown; the raw error was discarded. No actual platform prompt was observed. |
| Safe pre-stop aggregate capture recorded paired_sessions 1, pair.json 1, pair 3 and authentication 1. Media counts were empty, negotiations and lifecycle counts zero. | The mock backend accepted the normal login. This does not substitute for settled browser confirmation. Library, outer Resume and inner Play were not reached. |

The aggregate was captured between the recorded 17:34:22 and 17:34:24 UTC clock
checks, **before** stop; it is not a post-shutdown response. The run ended at this
required-observation stage without another case, diagnosis or native attempt.
No native media fields from the first run are copied into the second record.
File URL/MIME/ranges, decoded video, audio, resume, pause, seek, Stop and refreshed
progress are all **unexercised** in this second run.

### Source-only call-site assessment

The failed confirmation cell contained these ordered calls: pair-tab AX observation,
pair-tab read-only DOM evaluation, runtime-tab AX observation and a Continue
locator count. The first safe output would have followed the first two calls;
none appeared. Invocation and completion of each subcall are unknown. It retained
no per-call invocation counters, so even the exact failing subcall cannot be
reconstructed. `other` is a coarse classifier result,
not proof of an unsupported browser capability, DOM contract or platform fault.

Inspection found no helper or future-cell free reference in that failed phase:
its two tab handles were top-level bindings and later closed successfully. A
separate **pure local two-cell fake-object witness**, with zero browser calls,
confirmed that top-level bindings persist while a variable declared inside try
does not; accessing the latter yields a classified ReferenceError. That explains
the earlier blank-tab recovery and a later guarded-cleanup correction. It does
**not** explain the critical confirmation failure. No concrete product or browser
adapter fix, or reason for another replay, follows from the retained evidence.
No source/SDK/CSP/body/timing or security-guard change was made.

### Second cleanup: teardown only

Normal Disconnect was **not performed**: navigation had not reached its controls
when the required observation failed. No forced logout was substituted. The stop
command returned stop-requested; retained supervisor execution returned stopped,
exit 0, at 17:34:24 UTC. All nine owned PIDs
`44704, 44216, 45196, 6816, 37556, 41264, 30712, 27052, 26888` were absent;
listener 18092 and the owned control directory were absent. Both owned tabs closed
successfully and their absence was verified with other tab metadata suppressed.
Other tabs were untouched, and local private values were cleared using guards.
The master independently verified the nine-process/listener cleanup and accepted
slot release. This is teardown evidence, not normal Logout or token revocation.

## Remaining acceptance

Any later native attempt needs its own explicit scope/grant and must verify the
expected inner action before drawing a startup conclusion. No further attempt is
authorized or proposed from the second run's unknown observation error. The native candidate
gate, real File exact-cut bytes/MIME/ranges and missing/invalid/revoked-token denial,
server-version qualification and physical Philips acceptance remain **deferred**.
#32 stays open/In progress; PR #52 and its strict original Videos failure remain
unchanged. The operator candidate remains off by default; this attempt grants no
rollout, real-server test or retry.
