# Pending-code expiry and normal recovery � issue #9

**Implemented / automated-tested with mocks / actual browser subset /
recovery deferred / device-unverified.** This independent test entry covers the unused pending TV
code's lifetime, not authenticated-session/native-token expiry or A/B authority.
The required fixture scope is explicitly baseline with the authenticated-file
candidate **off**. Use the existing supervisor's baseline selection without its
candidate flag; verify its fixed ready scenario before calling this entry. The
driver requires the exact two-field normal health payload and rejects a candidate
delivery marker. Health mode alone does not attest the supervisor's scenario.
It uses the existing baseline fixture and normal forms/controls. No production
code, TTL, public scenario, endpoint or service changes are included.

The existing [pairing](browser-pairing-check.md) and
[failure/recovery](browser-failure-check.md) runbooks already record limited
CSRF/login/JSON/playback detector runs. They are historical observations, not
new passes. The latter uses the intentional legacy Try original path; this
expiry milestone neither repairs nor verifies the preferred outer/inner Play
workflow. Overall #9 remains open.

## Temporal and UI contract

`Settings.pairing_ttl` is 300 seconds. `State.pair` starts the server's monotonic
lifetime while creating the normal pairing response. The driver reads only its
own currently displayed unused code into private RAM and waits at least **305
monotonic seconds after that read**. Creation precedes reading; the read is not
misreported as the exact server birth time. No live clock injection is offered.

The caller must provide the **original** supervised run's UTC deadline. The
driver converts remaining wall time once to a monotonic deadline, rejects more
than 900 seconds remaining and requires at least **485 seconds after code read**:
305 wait, 120 recovery and 60 cleanup. Phase checks never spend the cleanup
reserve. Waits are at most five seconds, with a finite iteration ceiling;
regressing/nonfinite or nonadvancing clocks cannot manufacture elapsed lifetime.
The external supervisor's original <=900 total / <=180 startup limits remain
mandatory. Insufficient budget fails before the expiry wait.

The 180-second recovery/cleanup allowance is checked again immediately after
waiting, including final timer overshoot. Each UI operation also has an actual
at-most-15-second deadline within the remaining foreground budget; checking the
clock only before/after an unbounded await would not enforce the reserve.

Only after waiting does a newly opened companion form receive the old code,
exactly once. Clean Step 1 must contain one code field, no credentials and no
prior expired/CSRF/verified/success state and an empty normal status message.
The submitted result must show the
specific invalid/expired message and no credential/verified/success state.
A stale message or other failure is not expiry evidence. The normal TV Continue
then shows Pairing or session expired; Create new code supplies the next code.
Normal companion reload/code check/correct fixture sign-in, TV Continue to
libraries and confirmed Disconnect establish recovery. A random expired numeric
code may recur; digit inequality is not required as proof of a new pending state.

No playback, poster/capability URL extraction, CDP, private Network identity,
vendor cache or proprietary runtime source is involved. Reports and yielded
progress contain fixed stages, bounded elapsed seconds, checks and cleanup facts
only. No code, credentials, raw error, DOM, QR/AX image or private URL is emitted.

## Resumable command, not a long blocking call

Load `tools/browser_pairing_expiry_check.mjs` through the documented connected
Chrome extension session only after an explicit exclusive runtime/relay grant.
`pairingExpirySteps({ origin, newTab, deadlineUtc })` returns an async iterator.
`newTab` must create a blank owned tab, and `deadlineUtc` must be the original
supervisor deadline, formatted by `Date.toISOString()`; never restart its budget.

Retain the iterator privately. Each `await iterator.next()` performs at most one
bounded UI operation or <=5-second wait before returning fixed progress. The
controller may batch at most three known wait steps per cell (each operation has
an at-most-15-second bound), keeping cells shorter than 60 seconds even when
wait calls are slow. It must stop batching when a different stage is yielded.
Do not await the entire
iterator in one tool call or assume a progress callback yields control. A final
done result contains the pass/failure report, not private state.

On cancellation call `await iterator.return()` and complete cleanup until done.
The current implementation has **no yields in finally**, so that call completes
bounded owned-tab closure in one step. Check the returned cleanup facts and
independently verify owned-tab absence. A possible post-submit session is reported
as deferred to bounded-service teardown unless normal Disconnect was confirmed;
process teardown is not normal logout. Any unconfirmed tab close fails the result.
The master must still verify fixed server counters, exact owned PIDs, listener
and control cleanup before slot release. No activation is implied by this file.

A timed-out tab creation can still resolve later: pending creations therefore
make tabs_closed false and fail the result. A late-arriving owned handle is closed
by its retained continuation. The controller must track every newTab resolution,
retain any in-flight next() outcome before cancellation, and reconcile pending
creation/late closure before slot release; an iterator's done flag alone does
not prove a nonexistent or closed tab. No unresolved creation is silently counted
as cleanup success.

## Local evidence and limitations

The seventeen Node checks use an independent stateful companion/TV model and mock the
Node monotonic clock **only inside offline tests**. The retained-code-valid
counterexample advances to credentials after the modeled lifetime, making the
same ordinary denial assertion fail; there is no driver fault-specific throw.
Other checks challenge stale denial plus credentials, CSRF instead of expiry,
dirty initial forms, frozen waits, post-read insufficient budget, cancellation,
redaction and failed owned-tab cleanup. New code digits deliberately recur in
the positive model. These are detector guards, not actual browser passes.
Stalled navigation and late-created tab cases use offline timer mocks; additional
cases cover recovery refusal, cancellation after possible credential submission
and a final expiry timer overshooting the reserved recovery budget.
At exactly the cleanup-reserve boundary, no foreground operation is scheduled.

The initial mock run failed because the fake text model put the code and controls
in one string despite the locator's anchored code row. Modeling separate visible
rows corrected that fixture; ten focused tests then passed. Independent review
then identified unbounded awaits and the missing post-wait budget check; both
were corrected and the expanded tests passed. Review also caught the zero-action
allowance edge, now rejected before scheduling; seventeen focused tests passed,
including refusal of a candidate delivery marker.
## Granted browser observation � 2026-10-31

The one expiry-only baseline/candidate-off run used reviewed head
`b43ad558bb9cf275ec18bdaef1cc6ddab0742b5c`. The original supervisor window was
18:28:56�18:43:56 UTC; execution stopped and cleanup completed at 18:37:14 UTC.
The published official MSX runtime was controlled through the granted Chrome
extension. No runtime source variant, clock override or live retry was used.

**Actual browser observation:** after 307 monotonic seconds following the private
unused-code read, a fresh companion Step 1 had an empty status and no credentials.
Exactly one old-code submission showed the specific invalid/expired denial;
credentials remained absent and no CSRF, verified or success state was accepted.
The subsequent normal TV Continue action executed, but the expected
`Pairing or session expired` notice was not confirmed. The driver failed at
`expired-tv-notice` and stopped immediately. The precise observation failure's
cause is unknown; this does not establish a product defect or a recovery pass.
The source audit confirmed that the single Continue control targets
`pairing.json`, whose expired/unknown branch returns this headline and only the
public new-code action. Its content payload disables cache/reuse/preload.
`uv run --no-sync pytest -q tests/test_pairing_layout.py` passed **3 tests**,
covering the action target, expiry recovery payload and secret absence.
The browser click resolved, but no retained visible-state/cardinality or request
observation distinguishes rendering, locator or delivery causes. The offline
driver model assumes the headline becomes visible; it cannot establish that
hosted-runtime behavior. No concrete source defect was found in this audit.
Create new code, fresh sign-in, library recovery and normal Disconnect were
**not attempted / deferred**. Authenticated-session/native-token expiry and
physical MSX playback remain outside this evidence.

**Sanitized server corroboration:** pairing statuses `[400]`, authentication 0,
PlaybackInfo 0, paired sessions 0 and logout 204 responses 0. These counters
corroborate the denied submission without proving the missing TV notice.
The fixed result recorded three passed checks (synthetic identity, normal
pending lifetime elapsed and expired unused-code denial), final status failed,
session cleanup not required, tabs closed and pending tab creations 0.
An independent inventory found all three owned tabs absent. The supervisor
returned stopped/exit 0; all nine captured owned PIDs, the port 18092 listener
and the supervisor control directory were absent before slot release.

Ignored local evidence: `.lab/reports/issue9-expiry-entry-result.json`,
`issue9-expiry-server.json`, `issue9-expiry-tabs.json` and
`issue9-expiry-cleanup.json` in the same directory. Overall #9 remains open and
PR #73 remains draft; this partial observation does not accept the full ticket.
