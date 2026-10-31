# Remembered startup observation contract

**Implemented / automated-tested / device-unverified.** This is an offline
metadata reducer and a proposed observation procedure, not a startup repair or a
live browser-coverage pass. Issue #12 and draft PR #64 remain unaccepted. Run9's
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
