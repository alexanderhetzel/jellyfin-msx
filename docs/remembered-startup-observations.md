# Remembered startup observation contract

**Implemented / automated-tested / device-unverified.** This is an offline
metadata reducer and observation procedure, not a startup repair or an
application/child-target coverage pass. Issue #12 and draft PR #64 remain unaccepted. Run9's
server-side root/HTML send returns and unknown browser stages remain in
[durable authorization](durable-authorization.md#foreground-result-and-synthetic-observation-boundary--2026-10-31).
Earlier direct-root/test-ID queries also failed; dropping the later body
prerequisite alone does not justify another startup attempt.

## First conditional run — 2026-10-31

**Run10 at exact `c98ae26` / main `13ad0ba`: observation support unestablished;
startup unaccepted / device-unverified.** The single granted intended normal
official-MS​​X startup was followed by the documented `Target.getTargetInfo`
attempt. It did not produce usable root identity; the fixed recorded outcome
was unsupported. No alternate command, tab-ID substitution or identity
normalization followed. Page/Network enable, child commands and event collection
were not reached. No root/frame/resource snapshot or network stage is claimed.
The reducer was not instantiated with an invented identity. A fixed support
projection instead records root unavailable, joins withheld, initial gap and
child coverage unknown. No actual platform approval prompt was observed.
The attempt threw before root identity assignment. Its catch retained no error
text or finer reason: unsupported method, tool policy, paused document, transport
and permission causes cannot now be distinguished. The broad unsupported label
does not establish which component rejected the attempt. No retry was made to
recover the discarded exception or test an alternate API.

The initial local ASGI report was all zero. Before cleanup, remembered root JSON
and plugin HTML each had received1 / start200-send-returned1 / final-body-send-
returned1; other categories and aborted/incomplete were zero. At the final
ordinary DOM read, the UI showed Load Error / Data Load Error. No runtime timeout
log was collected, and no historical Request timed out/HTTP/paused-response fact
is imported. The support result does not explain the application's load error or
establish an external/tool/platform cause. HTML/JS/SDK/handler stages stay unknown.

Only fixed JSON reports were retained under ignored
`.lab/reports/issue12-run10-{initial-asgi,final-asgi,projection}.json`; no raw
protocol payload, identifier, URL, error string or screenshot was emitted or
retained. No Retry, ForceInit, warm-up, credentials, restart or matrix ran. The
sole owned tab was closed; normal stop returned session19886 exit0/stopped.
Cleanup at16:37:10 UTC /17:37:10 Vienna found all nine recorded owned PIDs,
listener18092, control and helpers absent. Original900-total/180-startup bounds
were preserved. Main's later fixture merge was assessed only after cleanup;
the running source was never rebased or mixed. No active test resources remain.

## Public-only controls

### Public-document capability control — 2026-10-31

A separate browser-only grant allowed one fresh tab on the public
Interaction_Plugin wiki page at the official HTTPS origin, without a relay,
startup parameter, application/plugin navigation or authentication. The expected
heading and exact origin were verified through ordinary DOM/current-URL reads
before the single intended metadata-command attempt. It returned no usable
identity: the retained error class is Error, structured code unknown and reason
unknown. None of the conservative unambiguous reason signatures matched. No
raw message/result/URL/identifier was retained or emitted, and no actual required
platform prompt was observed. This is not evidence that permission was irrelevant.

The fixed report is ignored
`.lab/reports/issue12-public-capability-check.json`. The owned tab closed in the
terminal finally path; creation through cleanup took about one second, within
the 60-second total bound. No Page/Network/Fetch/attachment/alternate command,
setting change or relay operation followed. No implicit tool behavior is assumed
absent. The control establishes failure to obtain metadata in a verified public
document context; it does not prove the underlying method is unsupported,
identify the failing component, explain run10 or establish app/child coverage.
Whether any command reached protocol wire dispatch is also unknown. Page/Network
support remains untested by this control; failure is not a universal capability claim.

### Standalone public frame snapshot — 2026-10-31

A separately granted browser-only control verified the same public wiki heading
and exact HTTPS origin, then made one `Page.getFrameTree` call without a Target
call or domain enable. The capability returned an object containing a root frame,
string URL matching the exact public wiki origin/path/single title query and
HTML MIME metadata. All seven context/return/shape/root-match booleans were true.
Error stage/class/code were none, reason expected_shape; no actual platform
prompt was observed. The own tab closed in finally in about half a second,
within the original 60-second creation-through-cleanup bound.

The projection used only `frame.url`, never `unreachableUrl`, and retained no
tree, URL, identifier or raw error. Fixed report:
`.lab/reports/issue12-public-frame-snapshot.json` (ignored). No Target/Network/
Fetch/enable/attachment/alternate command, relay, application startup, private
route, authentication or settings change followed. Implicit tool behavior is
not claimed absent. Independent protocol/security evidence review accepted this
as public-root snapshot support only. It proves neither parsing, resource loading,
SDK execution, app/child coverage, Network binding nor the cause of prior failures.

## Proposed Page-only application observation

### First attempt — run11, 2026-10-31

At fixed `c9705af` / main `e1a6bcd`, initial ordinary UI was categorized unsettled
and the intended official-MS​​X current origin was verified. The first diagnostic
helper then failed while preparing capability acquisition, before the explicit
Page command could be invoked. Actual getter invocation is unconfirmed. Retained stage capability_acquisition / class other / code
unknown / reason unknown; explicit Page command invocations0. No frame tree,
second snapshot, alternative command, Target/Network/enable/attachment/Fetch,
marker read or identity substitution followed. No actual required platform
prompt was observed. Local call stage is not a component or startup-cause diagnosis;
implicit tool behavior remains unobserved. Public settled-wiki snapshot success
is a separate supported fact, not refuted by this result.

Initial ASGI counts were all zero; the final report before cleanup again had root
JSON and plugin HTML each received1 / start200-send-returned1 / final-body-send-
returned1, other categories0, aborted/incomplete0. These are observer-boundary
sends, not browser receipt or parsing. Exploration stopped at the diagnostic
block. Terminal UI was not observed afterward: no Data Load Error, timeout log,
HTTP browser stage or screenshot is claimed for this run. No Retry, ForceInit,
warm-up, credentials, restart, matrix or source variant ran.

Finite projection and ASGI reports were retained before cleanup at ignored
`.lab/reports/issue12-run11-{initial-asgi,final-asgi,projection}.json`.
The sole owned tab closed; normal stop returned session14025 exit0/stopped.
At17:13:43 UTC /18:13:43 Vienna all nine exact owned PIDs, listener18092,
control and own helpers were absent. Original900-total/180-startup bounds held.
No active resources remain. Child-frame metadata and SDK/adapter/handler stages
remain unknown; startup remains unaccepted. No Page-method or platform cause follows.

### Local helper correction after run11

The original run11 artifact remains unchanged: class other, unknown code/reason,
local stage capability_acquisition and zero explicit Page invocations. Its raw
exception was discarded and cannot now be recovered or relabeled ReferenceError.

A concrete local call-path defect was subsequently demonstrated. The helper was
defined in one REPL call before its free `run11Tab` and `run11Origin` references
were declared in a later call. The successful public control kept tab and command
in the same call. On this installed REPL, a two-call pure JavaScript witness
failed to resolve the later binding. The matching fake-tab acquisition witness
raised ReferenceError at the recorded local phase, with getter0 and Page0.
The old classifier omitted ReferenceError and projected precisely other/unknown.
This invalidates attributing run11 to an actual capability getter or browser.
It is a reproduced local helper defect, not retrospective proof of its discarded
exception and not an application startup cause.

The source comparison uses only the recorded calls, not browser internals:

| Call-path item | Run11 versus successful public control |
| --- | --- |
| Provider and tab | Same connected Chrome extension; each created a fresh owned tab, with awaited navigation and current-origin read |
| Capability/command API | Same awaited `tab.capabilities.get("cdp")` and documented Page send signature; no reset or stale-tab recovery was performed |
| Tab and origin bindings | Run11 helper referenced values declared in a later REPL call; the public control used same-call values |
| Other helper dependencies | Run11 state/classifier were defined with its helper; the projector already existed. The repair nevertheless passes every runtime dependency explicitly |
| Page context | App UI unsettled versus verified public heading; this difference does not establish a tool readiness prerequisite or application cause |

No discarded exception, previous secret history or hidden implementation was
inspected. The local phase label alone cannot distinguish expression preparation
from entry into the advertised capability getter.

The repair passes every runtime dependency explicitly. A fake tab supplied in a
later call reached getter1 / Page1 and a finite same-frame URL/MIME projection.
Synthetic private fields did not enter output. Fixed local witness reports are
ignored `.lab/reports/issue12-local-acquisition-scope-witness.json` and
`.lab/reports/issue12-bound-snapshot-helper-witness.json`; browser actions0.
No actual browser/protocol method was used to reproduce or repair this defect.

The corrected diagnostic helper has this parameter-only call contract. `project`
is the reviewed bounded finite frame projection; `classify` is the fixed error
projection below. `phase` is a predeclared early/terminal/terminal_only enum.
Create fresh state for the owned tab; never reuse another run's tab/capability.

```javascript
async function takeBoundSnapshot(tab, origin, state, project, classify, phase) {
    const out = {phase, commandReturned: false,
        errorStage: "capability_acquisition", errorClass: "none",
        errorCode: "none", reason: "unknown"};
    try {
        if (!state.cap) state.cap = await tab.capabilities.get("cdp");
        out.errorStage = "command_invocation";
        state.attempts++;
        let raw = await state.cap.send("Page.getFrameTree", {}, {timeoutMs: 5000});
        out.commandReturned = true;
        out.errorStage = "projection";
        Object.assign(out, project(raw, origin));
        raw = undefined;
        if (!out.frameTreeObject || !out.rootFramePresent) {
            out.reason = "unusable_shape";
            state.failure = "unusable_shape";
        } else {
            out.errorStage = "none";
            out.reason = "expected_shape";
        }
    } catch (thrown) {
        Object.assign(out, classify(thrown));
        state.failure = "snapshot_unavailable";
    }
    state.snapshots.push(out);
    return out;
}
```

The error classifier retains only `typeof thrown`, name-is-string,
message-is-string and code-type, plus allowlisted classes/codes and fixed reason.
ReferenceError is explicitly allowlisted alongside standard Error/TypeError/
SyntaxError/RangeError and the prior protocol/timeout/security classes. Strings
remain thrownType string with other/unknown, without their contents. No raw
name/message, arbitrary keys, URL, identifier or exception text is emitted.
Local error stage identifies an attempted helper step, not a failing component
or protocol wire dispatch. No further browser run is authorized by this repair.

### Corrected-helper attempt — run12, 2026-10-31

At fixed `8e1ba5e` / main `e1a6bcd`, one normal startup used the parameter-bound
helper with fresh tab/origin/state and explicit projector/classifier/phase.
The early observation returned the expected frame-tree/root shape and official
root origin. Own-plugin URL/HTML MIME, about:blank, browser-error and unknown-frame
flags were false; other-frame true, budget exceeded false, child coverage unknown.
These describe the bounded early snapshot, not absence of the intended frame.
The successful call validates that the repaired local path can reach the API in
the application-root context; it establishes no child or SDK behavior.

The ordinary UI then showed Load Error / Data Load Error. The second predeclared
Page invocation threw: commandReturned false, local stage command_invocation,
class Error, thrownType object, name/message-is-string true, codeType undefined,
code unknown and reason unknown. No terminal frame metadata was obtained. The
two invocations are local attempts, not proof of protocol wire dispatch; no
unrecorded raw exception or component cause is inferred. No third call, alternate
command, Target/Network/enable/attachment/Fetch/body/marker probe or recovery ran.

Initial ASGI counts were all zero. Before stopping, root JSON and plugin HTML
each had received1 / start200-send-returned1 / final-body-send-returned1. Other
categories, aborted and incomplete were zero. No own JavaScript or subsequent
authorization/home request was observed at this server boundary. ASGI sends do
not establish browser receipt/parsing, and the failed terminal observation cannot
locate the plugin's current frame. No runtime timeout log or browser HTTP stage
was collected; previous runs' observations are not imported.

Fixed reports are ignored
`.lab/reports/issue12-run12-{initial-asgi,final-asgi,projection}.json`.
The sanitized 2560x1249 error image at
`.lab/reports/issue12-run12-bound-frame-data-load-error.png` was inspected: public
error/focus only, no URL/code/QR/secret; raw pixels stayed in RAM. Reports were
retained before closing the sole owned tab and stopping normally. Session83283
exited0/stopped; at17:40:02 UTC /18:40:02 Vienna all nine exact owned PIDs,
listener18092, control and own helpers were absent. Original900-total/180-startup
bounds held; candidate remained off. No credentials, Retry, ForceInit, warm-up,
restart, matrix, source variant or new budget. Startup remains unaccepted and
the cause unresolved. No further run is implied.

### Remaining diagnosis boundary

Independent source/evidence review found no new failing own-code, served-response
or public startup-contract difference that justifies another variant. Pair,
renewal and home response shapes align with the adapter; accepted lifecycle/
subtitle handlers already support asynchronous callbacks. Handler ordering,
exact-save, deadline/epoch and valid startup grammar have local witnesses.
The literal SDK/deferred-adapter comparison supplies no order/CSP/body fix.

A second local fake call in a later REPL cell also exercised the repaired
helper's cached-capability branch: getter1 / Page2, successful finite same-frame
projection, browser actions0. Ignored report
`.lab/reports/issue12-cached-fake-snapshot-witness.json`. This tests local helper
logic only, not a real tool capability's lifetime or the terminal Error's cause.

The earliest unresolved boundary remains attributable own-plugin HTML browser
receipt/current-document state, followed by parsing, script fetching/execution,
SDK registration and accepted-init callback delivery. Server final-body send
returns do not cross it. Run12's early missing match with unknown child coverage
and unavailable terminal tree do not establish absence. Moving that boundary
would require positive, attributable own-document/execution or accepted-init
evidence under a separately granted documented capability, or a reproducible
failing local contract test. No new discriminant is presently justified by the
retained source/artifacts; no generic observation expansion, additional granular
rerun, CommonJS/CSP/body/order/SDK timing variant or external/platform-block label
follows. Issue #12 remains open and PR #64 draft; automatic startup is unaccepted.

### Reviewed procedure and limits

This is a materially different positive observation boundary from the failed
root-identity preflight. Its first attempt stopped before the Page invocation as
recorded above; the corrected attempt returned an early snapshot but failed at
its terminal command. Any further attempt requires a new separate exclusive grant.
No new reducer, fake Target ID or network join is needed. Keep the exact reviewed
startup/client/HTML/CSP/deadlines, fixture containment and candidate-off policy.

Retain initial/final local-only ASGI reports. After one normal official-MS​​X
startup and an ordinary current-origin/UI read, take at most two standalone
`Page.getFrameTree` snapshots: early, and at the first terminal UI result/block.
If the first UI read is already terminal, take only that one snapshot.
Use no Target, Network, Page.enable, attachment, Fetch, body/resource-content call,
marker probe, injection or application variant. No Retry, ForceInit, warm-up,
credentials, restart or remaining matrix. An unsupported API/shape is a diagnostic
block: retain fixed local call-stage/class/code/reason and stop without alternates.

Project at most 64 frames with a bounded stack. Raw URLs/trees remain RAM-only.
Output fixed shape/root-context and presence booleans: exact own plugin origin/
path seen, matching HTML MIME seen, any about:blank/browser-error/other/unknown
frame seen and budget exceeded. Match only `frame.url`; never treat a failed
destination in `unreachableUrl` as an observed own document. An about:blank frame
is not attributed to the intended plugin. Missing own-frame metadata, omitted
children and exhausted budgets leave child coverage unknown, not absent. The two
snapshots remain separate facts, without session/loader/epoch or network joins.

Matching own-frame URL/MIME would be positive snapshot metadata, not proof of
own HTML bytes, body parsing, load completion, SDK/handler execution, HTTP status
or startup cause. Keep raw errors out of output; local error stage does not
identify the failing component or prove wire dispatch. Retain finite projections
and final ASGI snapshot before closing the sole owned tab and stopping the fixture.
Original maximum900-total/180-startup bounds and exact owned-process/listener/
control/helper cleanup remain mandatory. No further run is implied by this plan.

## Supported contracts and limits

The installed connected-Chrome `cdp.documentation()` was read without sending
live commands. It exposes `send(method, params, {target})` and filtered
`readEvents({afterSequence, methods, limit, target})`, returning a cursor,
`hasMore`, `truncated` and event source session/target metadata. Child selectors
must come from observed `Target.attachedToTarget` events. Its origin scope and
permitted commands still apply; documented signatures do not prove a command or
child-origin observation will be accepted. The capability requires navigating
the intended HTTP(S) page before the first CDP command. Consequently a subsequent
enable cannot guarantee capture of that navigation's first requests.

[Chrome's debugger documentation](https://developer.chrome.com/docs/extensions/reference/api/debugger)
distinguishes same-process frames sharing a target from out-of-process child
targets, supports flat child sessions and describes nonrecursive auto-attachment.
The [official protocol schema at revision92be9c2](https://github.com/ChromeDevTools/devtools-protocol/blob/92be9c279a8ff3af17009705bb357241932128e4/json/browser_protocol.json)
defines Page frame/resource snapshots and navigation notifications separately
from Network request, response and loading-finished/failed notifications.
These are protocol contracts, not evidence of which targets the installed tool
covered during any historical run. Its actual source/session/target convention
must be preserved; do not rewrite mismatched metadata into accepted identities.
All installed event-source identity fields are optional. Root identity therefore
requires a supported `Target.getTargetInfo` result and matching event metadata;
`Tab.id`, provider tab IDs and `source.tabId` are not target-ID substitutes.
Missing identity withholds attribution. Target-only identity must resolve to
exactly one observed session; multiple sessions sharing a target stay ambiguous.

Do not override `Target.setAutoAttach`: enabling/disabling changes attachment
routing and disabling detaches related targets. Do not pause targets, use Fetch
interception, inject scripts, retrieve bodies/post data, replay requests, clear
or disable cache, bypass CSP or change permissions. Missing/unsupported coverage
stays unknown. No vendor runtime internals or proprietary code are inspected.

## Offline reduction

`tools/remember_network_observations.py` consumes already-collected task-tab
metadata in RAM. It never opens a browser, sends commands or writes an event log.
Its exact public route categories cover remembered root JSON, own plugin HTML,
own JavaScript and the published SDK URL. SDK/adapter request attribution also
requires the own HTML document context. Private capability routes are excluded.

The reducer keeps four distinct positive facts:

| Fact | Evidence and limit |
| --- | --- |
| Own frame seen in a snapshot | Present own URL in a frame/resource tree; not a navigation or parsing event |
| Own frame navigation observed | Matching Page navigation notification; not script execution |
| Response observed | Request/response joined within the same observed session, redirect hop, frame and loader, with full-URL fingerprints matching |
| Loading finished/failed observed | Matching terminal event for that request; finished additionally requires its response; not SDK evaluation or authenticated UI |

Raw URLs are immediately classified; only transient correlation IDs and full-URL
digests are retained in RAM. Redirects retire the previous hop even if the next
URL is outside the allowlist. Frame/loader changes invalidate stale requests;
bounded retired-loader tombstones prevent old Document requests resurrecting an
epoch. Parent-session detach/reattach invalidates descendants; ancestry cycles
are rejected. Child sessions require an observed own-HTML attachment. An initial
about:blank attachment is insufficient. Same-process root events need no child.

Resource-tree entries never repair orphan network events or establish completion.
Cache/service-worker flags, other HTTP statuses, CSP blocking and cancellation
stay separate fixed facts. Arbitrary error text is discarded. A completed load
can still be an HTTP error or a cached response; it is not an origin-server
delivery claim. Response status200 is not document completion or authorization.

Only a complete bounded drain with the same method filter and cursor chain
exposes joined network counters. Pending pages, truncation, out-of-order events,
cursor/filter discontinuities, exhausted budgets, unsupported commands, read
timeouts or identity conflicts withhold them as null. Adverse replay metadata
is never discarded by duplicate detection. Sequence gaps between filtered events
alone are not data loss. Even an available drain retains initial-navigation-gap
and unknown-child-coverage fields; zero counts never prove absence.

Budgets are 1000 events per page before projection, 4096 processed events,
16 sessions, 64 frames, 128 requests/retired loaders and one-million saturating
counters. Snapshot tree traversal and resource scans are bounded. Output has
fixed keys, categories, booleans, counts and nulls only; it contains no URLs,
identifiers, headers, bodies, timestamps, initiators or exception text.

## Proposed single-run procedure

The first conditional attempt above stopped at its initial support boundary;
no further attempt is authorized here. A future run requires a new exclusive
master grant. Keep the reviewed
startup/HTML/JS/CSP, fixture policy, original total/startup budget and application
actions fixed. No Retry, ForceInit, origin previsit, credentials or restart matrix.

1. Retain the initial existing local-only `remember_asgi` snapshot. Create the
   owned connected-Chrome tab and perform one intended normal official-MS​​X
   startup navigation. No live CDP preflight is authorized outside this run.
2. Read the installed capability contract. If permitted, obtain root target
   identity using `Target.getTargetInfo`, enable Page/Network metadata observation
   and record only fixed support outcomes. These initial commands may miss early
   events; that gap is mandatory. A rejection/unsupported shape is not a cue to
   try hidden commands or bypass origin scope. A real platform prompt follows the
   run's global human-input gate.
3. Drain the fixed `METHODS` filter from `readEvents` with bounded pages/cursors.
   Discover only actual own child attachments. Page/Network commands may target
   those documented selectors if permitted; record late enablement or unavailable
   child coverage as unknown. Do not attach arbitrary targets or change auto-attach.
   Include root events for same-process frames. Never synthesize a child identity.
4. Retain Page frame/resource snapshots, if supported, as separate positives.
   A readable own marked HTML root can optionally provide the previously reviewed
   finite marker/readiness observations; failure remains unknown. Neither tree
   snapshots nor root probes fill missing event history.
5. Stop application exploration at the first functional result/block. Complete
   the bounded final drain, then reduce the bounded RAM pages/snapshots offline.
   Never persist or print raw protocol results. Retain only the fixed projection
   and final local-only ASGI report before stopping the temporary fixture. If the
   drain cannot finish, retain explicit partial/unknown output, not inferred joins.
6. Do not disable observation domains whose previous state cannot be established:
   the tool may already use them. Close the owned tab to end its scoped observation,
   stop the supervised fixture normally and verify exact
   owned PIDs/listener/control/helper cleanup. Record observer cleanup failures
   categorically. Prior paused-document cleanup messages remain historical facts,
   not proof of any current cause. Do not infer instrumentation had no effect.

Positive browser events could distinguish an observed response, loading terminal
or committed frame from run9's ASGI-only boundary. Missing events with late or
unavailable target coverage cannot locate the failure. No evidence here permits
an SDK-stall, tool/platform-root-cause or physical-device claim.

## Local verification

`uv run --no-sync pytest tests/test_remember_network_observations.py -q -W error`:
**37 passed**. Regressions include cross-session IDs, redirects, changed/retired
loaders, wrong frames/queries/targets, detach/reattach ancestry and cycles,
same-process frames, orphan/tree separation, late/blank child attachment,
pagination/truncation, replay metadata, event ordering, budget limits, fixed error
categories, HTTP errors/cache/service workers and secret-bearing input redaction.
The SDK category rejects query/fragment variants of the exact published URL.
These are mocked protocol counterexamples, not a live coverage pass.
