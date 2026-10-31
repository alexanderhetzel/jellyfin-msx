# Positive own-request authority assessment — issue #9

**Source assessment / implementation not started / runtime-unverified /
device-unverified.** This is a proposed replacement observation boundary for
the [three failed poster-authority attempts](hosted-session-check.md).
It does not relax their poster selector or establish their cause. Issue #9 and
draft PR #73 remain unaccepted. No Network authority collector or new live
command has been executed for this assessment.

## Falsifiable hypothesis and permission boundary

The normal official MSX Continue action can issue a private home/browse GET
from the owned MSX tab after the normal companion form succeeds. A positively
correlated fresh request could identify that tab's current capability without
requiring its poster to expose an absolute DOM URL. This is a hypothesis, not an
observed root-session event or a claim that the installed tool permits the
required cross-origin metadata. Its absence would be unknown, not failed auth.

The installed Cua reference, read without commands, supports tab-scoped
`send(method, params, {target, timeoutMs})` and
`readEvents({afterSequence, methods, limit, target, timeoutMs})`. Returned events
have sequence and optional source session/target/tab identifiers, plus cursor,
hasMore and truncated. Omitting afterSequence starts at the current position.
Child selectors may only come from observed Target attachments; fields must not
be manufactured or rewritten. Raw access remains scoped to the tab's current
web origin, with commands subject to platform permission checks.

The [official protocol schema, revision 92be9c2](https://github.com/ChromeDevTools/devtools-protocol/blob/92be9c279a8ff3af17009705bb357241932128e4/json/browser_protocol.json)
defines Target.getTargetInfo, Page.getFrameTree and the Network request,
response and terminal metadata. The source assessment infers a conditional
root-main-frame correlation design from those fields. It does not establish
which commands, cross-origin request metadata or source identifiers this Cua
installation will expose. Missing or refused support is a concrete fail-closed
runtime barrier; no alternate debugger or origin binding is proposed.

## Own root context, current frame and fresh epoch

The first candidate supports **positive owned main-frame/root-session observations
only**. Frame-tree membership does not prove a child shares that target. Child
targets and child frames remain unsupported, and it must not promise their
coverage. This deliberately avoids changing debugger attachment routing. The
following is the source contract to review before any collector implementation:

1. Use only the newly created owned official-MS​​X tab. Confirm its current HTTPS
   origin is the official runtime origin. After the normal companion sign-in
   succeeds, obtain its CDP capability; root commands omit a child selector.
   Target.getTargetInfo must yield a bounded page target identity matching that
   tab's current URL. Never infer a target ID from Tab.id or a numeric tab ID.
2. If permitted, enable Page and Network metadata on that root and read its
   bounded Page frame tree. Keep the main frame as a **snapshot ownership fact**,
   not a navigation, response or load event. Record its current main-frame/loader
   identity and official-runtime document context. Do not seed child ownership
   from tree membership. Unsupported shapes or conflicts withhold capture.
3. Drain the same fixed method filter with bounded event pages and cursor chain,
   then take an action cursor immediately before normal Continue. Initial
   navigation was earlier and is explicitly outside coverage. Existing old
   requests or a response without a post-cursor request cannot seed authority.
   Frame/loader changes invalidate the epoch; a snapshot cannot repair a missing
   request, response or terminal join.
4. Perform the existing normal Continue and wait for the private libraries UI.
   Do not change application URLs, add a header, replay a request or set vendor
   state. Collect only bounded metadata from that exact owned tab and current
   cursor. No body or post-data command is required.
5. Accept root event identity only according to the installed source convention:
   an absent sessionId plus the independently obtained root targetId. A supplied
   child/unknown sessionId is never reinterpreted as root even if a target ID
   happens to match. Missing root source identity remains unsupported. Unknown
   child private-request evidence withholds authority; a missing root request
   does not prove the child did not request it.

The fixed filter is Target.attachedToTarget, Target.detachedFromTarget,
Target.targetInfoChanged, Target.targetDestroyed, Page.frameNavigated,
Page.navigatedWithinDocument, Page.frameDetached, Network.requestWillBeSent,
Network.responseReceived, Network.loadingFinished, Network.loadingFailed and
Network.requestServedFromCache. It does not enable discovery to obtain more
events. Delivered invalidation or unbound lifecycle metadata is adverse even if
one apparently valid candidate exists. Main-frame epoch changes remain invalid,
including a later attempted return to the old loader; no snapshot restores them.

After the normal action and terminal join, fully drain the same filter/window.
Repeat root-target and main-frame metadata checks solely as **invalidation**;
then finish a final bounded drain from the previous cursor to catch late conflict
or pending evidence. Never discard adverse metadata on replay. Close the window
only with an untruncated hasMore=false drain and no pending candidate records,
identity conflicts or new epoch. Events beyond that closed window are not claimed
as covered. Deadline, pending pages or missing support withhold the result.

Page/Network enablement may alter diagnostics already used by the tool. Do not
disable domains whose previous state is unknown. Close the owned tab at the end
to end its scope, preserving normal session logout where possible. Do not call
Target.setAutoAttach, Target.attach/detach, discovery over other tabs, Fetch,
Runtime script/state commands, cache/CSP/permission overrides or response-body
retrieval. This scope neither controls other ticket resources nor attaches an
arbitrary target. Any real platform approval follows the global input gate.

## Exact positive authority and opaque server validation

A candidate request must be a GET XHR/Fetch with a bounded canonical absolute
URL on the single configured synthetic origin, a 43-character URL-safe capability
and one of the production paths below:

- `/msx/device/{cap}/home.json`, with no query or fragment.
- `/msx/device/{cap}/browse.json?parent_id={baseline-library-id}`, with that one
  exact public fixture query and no duplicate/extra parameters or fragment.

The raw URL is private transient input, never report output. Root-session target,
request ID, main-frame ID and loader ID must agree across the request and response;
the frame must be the independently established owned main frame. loadingFinished
has no frame/loader fields: require explicit root event-source identity and join
its request ID only to that existing same-source validated record. Never fill a
missing request or response identity using a terminal event or snapshot. Join
that terminal to its request, never a cached tree entry or another redirect
hop. Response URL must equal the full request URL, status must be actual HTTP
200, MIME must be JSON and disk/service-worker/prefetch flags must be explicitly
false, with no matching cache event. Redirects, failure/cancellation, duplicate
or conflicting identities and retired epochs cannot produce authority.

Collect the whole bounded drain before accepting a unique capability. Multiple
requests using the same capability are not multiple authorities. Different
capabilities, even if one is incomplete or denied, withhold selection rather
than choosing the apparently successful one. An unbound private request from an
unknown child/session also withholds it. Public unrelated resources are never
authority candidates. Fixed support/coverage facts retain initial-gap and unknown
child coverage even when a positive request exists.

Unmatched private responses/terminals, request-ID reuse and mixed valid-positive
plus orphan/conflicting evidence also withhold it. Optional protocol fields are
not inferred. An unsupported field does not become accepted merely because an
offline fixture supplied a convenient default.

Actual HTTP200 does not prove the MSX JSON is healthy: a denied portal can wrap
an error in HTTP200. A new opaque resource-probe entry must privately validate the
observed capability by GETting its exact production home route, then follow
server-generated home/browse/detail/image/resolver links under the same scope.
Its existing healthy-shape, item/source, no-conversion, origin and authority
checks remain mandatory. Handoff to that validator stays entirely within the
collector's closure, with no public raw-capability accessor or callback result
that exposes it. It may return only a role handle stored in a WeakMap and fixed
diagnostics; the adapter must not return a raw home URL, capability or request ID.
The normal A/B retained-resource assertions and authorized-B negative predicate
remain unchanged. No cookie binding or tenant isolation is inferred.

## Bounded local counterexamples required for review

The owning issue must record acceptance before implementation. Meaningful offline
fixtures should challenge an actual post-cursor root positive join against wrong
session with reused request ID, target/frame/loader mismatch, stale cursor,
pre-action response-only replay, foreign origin, extra queries, ambiguous
capabilities, redirects outside the allowlist, loader resurrection, child-only
metadata, frame detach, cached/service-worker response, incomplete terminal,
pending/truncated drain and exhausted bounds. Error strings and payload-like
metadata must reduce to fixed output only. Tests must not contact a server,
operate a browser or reinterpret missing identities into a positive fixture.
Include explicit wrong/missing terminal event-source identity and mixed valid
positive plus orphan/conflicting private evidence. Current-root metadata checks
must invalidate a changed epoch and never repair a missing join.

Candidate ceilings are 128 events per page, 16 pages/2048 total events,
32 frame/request records and a 30-second observation deadline. Fields and raw
URLs are length-bounded before projection; unused headers/initiators/post data
are discarded. Private correlation records and URL material remain in RAM.
Only fixed stage/problem/support/coverage enums, bounded counts and booleans may
be emitted. A timeout issues no subsequent diagnostic read. These are proposed
source limits, not commands already run or hosted acceptance.

## Source consultation and independent gate

The #12 source design at commit `9bb71c9540d42f0afb3244d63d85fff7d504847f`
was consulted without private runtime files or resources:
`tools/remember_network_observations.py` Git blob
`8d0d322963f9094dd2a2e4df9b86b8074d184f80`, raw SHA256
`0dff705a442feb3c067f879b1e4421640258e6efbb7dd5706ba39840498ff1f1`.
Its tests have blob `d824367172f821dcfe7da1d0c5a17741edd6e136`.
Useful principles are complete cursor drain, session/request/frame/loader joins,
retired epochs, no snapshot-to-network repair and permanently explicit unknown
child coverage. Its public startup categories are not private authority and must
not be imported as permission evidence. This separate classifier must enforce
the exact private routes above. No source edits were made in #12's worktree.

Independent API/privacy assessment is required before implementing this design.
That assessment may narrow it or identify a concrete installed-contract barrier.
An accepted source design still requires mocked regression review, exact-head CI
and a separately granted bounded live attempt before any runtime claim. No
runtime grant, observer command or new relay is implied by this assessment.
The official-runtime observation permission and synthetic-origin validation-tab
permission are separate conditional prerequisites; success on one establishes
neither permission nor body access on the other.

## Target-identity design outcome and observation barrier

Independent pre-implementation API/privacy review accepted the refined
main-frame-only design conditionally. It required the ownership/terminal/window
closure restrictions above; it did not verify the installed runtime or authorize
activation. The collector remains **unimplemented**.

The master relayed #12's separate app preflight and later public-only control.
On a settled public official-MS​​X wiki page, the single Target.getTargetInfo
attempt threw Error before any usable root identity was retained. No structured
allowlisted code or unambiguous reason was retained; the owned tab was closed.
That is **not proof** of an unsupported method, tool policy, paused document,
transport failure or permission cause. It is not this ticket's measurement and
does not establish universal API unavailability. It does establish that this
separate run supplied no usable identity proof to justify blindly implementing
or replaying the proposed authority collector.

The installed Tab surface has no independently documented target-ID accessor;
optional event-source fields do not guarantee one, and a frame snapshot does not
replace target ownership. No source-supported replacement identity guarantee
has been identified. Therefore missing root metadata must remain unknown, with
no Tab.id/provider-ID inference, invented source identity, hidden command,
permission bypass or child-absence argument. That public-only control is a
separate worker's observation, not a capability test by this ticket. It does not
authorize a fallback Page command, new relay, private app run or further probe
in this ticket.

After the stopped third run, this branch was rebased onto actual main's PR #75
and #76 merges. Default-off candidate policy, PlayAccess fixtures, Compose,
programmatic candidate/range fixtures and their tests/docs remain preserved.
Existing poster/resource-driver code is unchanged by those rebases. Post-PR #75
checks passed 640 Python tests with one POSIX skip, 74 Node tests, Ruff/format
(120 files), both offline contracts and the exact 26-member wheel manifest.
Post-PR #76 full checks passed 657 Python tests with one POSIX skip, 74 Node
tests and Ruff/format (121 files). None is Network collector acceptance or a
replacement for missing browser metadata.

## Frame-led alternative: proof obligation not established

The master separately requested a source-only assessment of replacing target
identity with the current owned Page.getFrameTree main-frame ID, loader ID and
exact document URL, correlated to Network fields and a stable actual source
tuple. No Page command or implementation was run for that assessment.

The protocol defines frame and loader identifiers and request frame/loader
references; it does not equate frame and target identifiers. A Page root snapshot
can positively identify the commanded tab's current main frame if available.
A Network join can check equal request/response frame and loader fields, and
equal actual source tuples across request, response and terminal. Those facts
still require a binding from the observed source namespace to that root.
loadingFinished provides only requestId; it cannot supply missing frame/loader
or source-ownership proof.

The installed wrapper explicitly says omitted **send** target addresses the tab
itself. For **readEvents**, it documents buffered events, optional source fields
and an optional child-target filter. It does **not** explicitly guarantee that
omitting that filter yields only root-session events, or that every delivered
child retains complete native source/session identifiers. The native
[Chrome debugger contract](https://developer.chrome.com/docs/extensions/reference/api/debugger)
routes by Debuggee/session identifiers and distinguishes child sessions, but
that native contract alone does not establish how this wrapper projects every
optional field. No complete mapping guarantee was found in the reviewed
installed reference.

The falsifiable ownership challenge is a root snapshot plus a complete private
request/response/terminal triple from an **unbound** source tuple, even with
matching-looking frame/loader strings and exact URL fields. A stable tuple can
prevent mixing two different tuples, but cannot prove which unknown tuple is
the commanded root. Omitted source metadata also permits an undetectable mixed
root/child join; the terminal has no independent frame key. Nor can a stale
snapshot or child-tree entry repair that missing binding. This is a contract
sufficiency counterexample, not a claim that Chrome actually emitted reused
frame IDs or malformed events in any run. Treating the first candidate tuple as
root would invent the identity this alternative is supposed to prove.

Independent API/privacy assessment concludes that the reviewed contracts are
insufficient for this frame-led fallback and it must not be implemented as an
authority collector. A future explicit root-only stream guarantee, or documented
root identity with reliably preserved event namespace, could satisfy the
obligation after fresh review and cross-session/child/stale-snapshot challenges.
Until then, missing metadata remains unknown; no adapter, hidden method, identity
substitution, permission change, target inference or runtime replay is justified.
This is a completed source-assessment limit, not proof of a universal product/
tool failure or a request for human approval. A/B acceptance remains unresolved.
