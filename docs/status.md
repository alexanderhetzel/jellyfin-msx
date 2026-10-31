# Verification status — 2026-10-31

## Revocation source evidence and mocked observer subset — issue #32

**Source-reviewed / automated-tested in part / device-unverified.**
The [pinned source investigation](jellyfin-revocation-source.md) distinguishes
confirmed authentication/authorization/static-file code from the inferred
explanation of the retained original-file response. Metadata denial in the old
probe is client-normalized 401, not a measured raw upstream status: 401 and 403
both normalize to that error. Original-file 206 and byte comparison were raw.

The standalone strict observer requires a fresh bounded request denied with
401/403 and rejects a denial body containing the original fixture prefix. Mocked
regressions preserve rejection of 200/206/redirects, body bounds and safe fixed
diagnostics. This subset imports no real Jellyfin runner, version/image manifest
or matrix workflow, and changes no client playback or authorization policy.
Draft PR #52's failing real expectation is unchanged; #32 remains open and no
complete server-version range, new live result, MSX or TV pass is claimed.

Windows/Python 3.12.14 frozen build/dev sync passed. Local
`uv run --no-sync pytest -q -W error`: **540 passed / 1 POSIX skip**, no warnings;
Ruff check and format check passed (**109 files**); `git diff --check` passed.
The twelve new observer checks are MockTransport-only. Independent final review
and normal repository CI results are recorded in the subset PR; neither replaces
the retained failing real-server contract in draft PR #52.

## Saved progress — issue #19

**Implemented / automated-tested / browser-tested / device-unverified.**
Movie/episode details now offer meaningful saved-progress Resume/Start over.
Fresh authorized metadata and the selected source bound PlaybackInfo StartTimeTicks
and native resume:position; invalid/watched/near-end progress starts at zero.
Saved resume never enables conversion, including on an opted-in host. #18's
observed-only progress/Stop and generation fencing remain unchanged. No audio/
version selector or subtitle/legacy reporting support is claimed.
[Contract, scope and actual runtime observations](saved-progress.md).

Windows/Python3.12.14 locked dev/build sync passed. Full `uv run --no-sync pytest
-W error`: **518 passed / 1 POSIX skip**, no warnings. Node **45** (28 lifecycle,
12 subtitle, 5 browser guards), Ruff check/format **105 files**, diff check and
locked offline wheel/exact **25-member** source/license/template allowlist passed.
Independent source/security review found no blockers after the optional-host HLS
timeline edge was removed; committed-head/docs review accepted the source milestone.
Source bad458c then completed one granted private Chrome/MSX synthetic run:
normal pairing, movie/episode Resume, actual decoded1280x720/time, paused seek18
then13, Stop retaining13 and refreshedResume13; Start over decoded4.689315s at
5159ms after click, paused5.012135, Stop/report5 and refreshedResume5. Episode
resume11.855827s at4436ms independently corroborates saved8; requested offsets are
not treated as media observations. Near-end/watched settled beginning-only.
Separate redacted three PlaybackInfo200 requests kept conversion/DirectStream/
subtitles off. Six clean PNGs/fixed-counter JSON support independent acceptance.
The short movie ended before Pause and Stop reportedFailedtrue; no new successful
end semantic claim. Corrected case/CSS/autohide selector deadlines are tool limits.

Normal confirmed Disconnect produced paired_sessions0/logout204. At14:27:18UTC,
supervisor exit0/stopped; all9 owned PIDs/listener18092/control absent; both own
tabs closed. No CDP/Network/viewport override, new budget, operator/Ultra access,
deployment, real Jellyfin release or TV/audio pass. Final evidence/head acceptance
and CI are recorded in PR68 before merge.

## Playback recovery source milestone — issue #23

**Implemented / automated-tested / partially browser-tested / device-unverified.**
The preferred original-with-progress flow now provides fixed failure categories,
three bounded explicit playback attempts, native recovery/Stop/Back controls and
fresh authenticated policy-eligible stored alternatives. Back cancels pending
responses; cached explicit reentry resets the budget. #18 generation binding,
old-Stop acknowledgement and last-safe lease remain unchanged. Legacy/subtitle
flows retain their existing recovery scope.

`uv run pytest -q`: **491 passed / one POSIX skip**; Ruff check and format
passed (**102 files** on final documentation recheck); three Node suites **50 passed**;
diff check passed.
Offline wheel build/exact manifest (**25 entries**) and synthetic HTTP smoke passed.
The prepared synthetic recovery scenario is strict MockTransport with fixed
faults, normal pairing and pinned RAM media.
Independent review found and prompted fixes for stale Back callbacks, cached
attempt reset, malformed-success recovery and protocol-error classification.
Final independent source/security review found no remaining blocking findings;
full runtime acceptance remains pending. The reviewer independently reran the
full **491 passed / one skip**, then the latest **72 affected Python / 50 Node**
checks after cancellation fixes. Review did not operate a browser or relay.

One granted Chrome/MSX0.1.167 run on fixed `b650974` observed normal pairing,
fixed negotiation denial, three-attempt cap, Back/details reentry and native
non-media rejection. Manual recovery offered an actual stored alternative, but
selecting it negotiated without any original-media GET/decoded frame: separate
reads stayed time0/readyState0/dimensions0. Five total PlaybackInfo200, one
unplayable GET, zero lifecycle reports; no alternate playback pass. Three safe
JPEGs/sanitized numeric/action/request JSON support independent evidence review.
Stopped at that blocker: two owned tabs closed, supervisor exit0, all9PIDs/
listener18092/control absent at14:33:01UTC. No CDP/override/newbudget or real data.

After cleanup the candidate was rebased onto merged #19 (`e21d103`), preserving
Resume/Start over, source/start properties and both fixture scenarios. An explicit
alternative starts at zero. Published ordered actions now stop old media with
`quiet` before resolution, replacing an in-resolver stop hazard; this is a
candidate correction rather than an established root-cause explanation. Full
pytest **528 passed / one skip**, Node **55 passed**, Ruff/format **106 files**
and offline wheel/exact **25-member** manifest passed. Independent exact-head
source/security/union review accepted the candidate with no blockers.

A separately granted focused run on unchanged `06a297e` then observed bad-native
rejection→manualnative_unknown→explicitstoredalternative→actual1280x720 pattern,
time0/readyState1→2.669199/readyState4. Pause held24.1604 across separate reads.
NativeStop returned0/readyState0 and usable recovery; Back returned details.
Before replay: Start1/Progress7/Stop1,lastsafe24,Failedtrue,inactive. Freshcontext
same-alternative replay advanced0.017982→2.987993/readyState4; nativeStop reset0.
Final3PlaybackInfo200/1nonmediaGET/2originalGET;Start2/Progress9/Stop2,lastsafe19,
Failedtrue/inactive, conversion/DirectStream/subtitlesOff. Four clean JPEGs plus
safe numeric/action/request JSON support independent acceptance of this declared
recovery/control/cleanup/policy subset. No exact causal fix or universal recovery
is inferred. Paused screenshot and numeric samples are separate observations.

At14:43:57UTC explicit supervisorstop exit0, all9recordedPIDs/listener/control
absent, both owned tabs closed. Companion DOM read timeout and autohidden Pause
selector were tool limitations, not native error causes. No raw errorURL image,
CDP/override, sourcevariant, realserver/TV/audio or further run occurred.

The published interaction API does not expose a typed native media-error cause.
Native failure remains explicitly unknown; no pause, missing sample or tool
timeout diagnoses decoding/connectivity. Therefore the original decode-specific
criterion remains unmet and #23 stays open as a partial draft milestone. See
[the recovery contract, evidence boundaries and remaining criterion](playback-recovery.md).

## Original playback lifecycle reporting — issue #18

**Implemented / automated-tested / browser-tested / device-unverified.**
The preferred original-with-progress interaction authenticates session/source/
generation-bound reporting, requires matching public video-info properties before
numeric samples, confirms Stop or expires a last-safe 45-second lease, and uses
modern Jellyfin start/progress/Stopped APIs. Retry queues, locks, uncertain Start
cleanup and failed-Stop replacement fences are bounded. Existing subtitle bridge
and startup ownership remain unchanged; legacy Try original and subtitle playback
are explicitly unreported. [Contract and limits](playback-reporting.md).

Pre-browser Windows/Python3.12.14 full `uv run --no-sync --python
.venv/Scripts/python.exe pytest -W error`: **481 passed / 1 POSIX skip**, including
cancellation and optional-transcode scoped cleanup. Node 42 (25 lifecycle,
12 unchanged subtitle, 5 browser guards), Ruff check/format 101 files, diff check
and locked offline wheel/exact 25-member allowlist passed. Independent
source/security review resolved generation identity,
oldStop/newStart ordering, retry circuit, uncertain Start/Stop cleanup, terminal
retention, lock waiter and post-await revocation findings; independently 89 affected
Python and 25 Node tests passed. Actual source 96837f, official MSX 0.1.167 and
connected Chrome normal private original flow decoded 1280x720 and sent
authenticated Start, Progress, held Pause and Stop. Decisive paused Stop retained
position 7 rather than reset zero; fresh replay established Start 6, then actual
client close held position 11 / Progress 31 at 20.651s and delivered failed Stop 6,
inactive with unchanged position 11, by 55.536s. This brackets delivery; it does
not measure exact <=45s. Earlier near-end Stop is documented as ambiguous with
natural completion; separate ended sample yielded position 30 / Failed false.

Four secret-free JPEGs and fixed-counter/numeric JSON support the
[actual action/evidence table and limits](playback-reporting.md). No new actual
network/crash/transcode/real-server/physical TV/audio/suspension pass is inferred.
One synthetic AX fragment preview was contained by normal confirmed Disconnect
before any playback; re-pairing stayed in the same original 900-second budget.
The prior attempt's unnecessary temporary-origin CDP approval delay produced no
media acceptance. Final run used no raw CDP/Network/viewport override. Explicit
supervisor stop at 13:20:59 UTC returned exit 0; all nine owned PIDs, listener
18092 and control directory were absent; both owned tabs closed. Independent
final review inspected all four images and sanitized JSON and accepts the four
original software criteria with these limits. Final exact-head review/checks
and merge are recorded in PR67.

## Private subtitle selection — issue #22

**Implemented / automated-tested / browser-tested / device-unverified.**
Independent final review maps all four original software/browser criteria to
source-pinned actual Chrome/MSX observations and mocked boundaries. Off and
distinct source/absolute-index language choices work; HTTPS resources authenticate
every native GET; sampled switching/seek/Off/Stop preserve position and timing.
The declared two-line/32-display-unit client subset renders its W32/Han16
boundary. Retained four-line/W33 negatives explain rejection and recover to
decoded originals without conversion, truncation or timestamp changes.

A later unused native subtitle GET received correlated HTTP401 after expiry.
No specific per-track notice appeared; manual Off/Stop and expired-video replay
recovery worked. Capability URLs remain private bearer material; delivered cue
bytes cannot be recalled. Physical Philips/audio/remote/overscan remain issue4.

Intermittent Data Load Errors during context reopening remain recorded. The
failed document-marker comparison was removed, not declared a fix. Unchanged
`e4e1ef97` completed healthy → layout rejection → healthy and same-cached-context
Back/reopen (init1→2, visible by a 9355ms sample). Generic body reads preceded the
result; no causal tool/application fix or zero-transient-failure guarantee.
The historical removed proposal's extended sequence is not an original feature
gate. [Actual actions, source pins and limits](private-subtitle-results.md) retain
both successful and failed observations.

Full Windows simple-cue source: `uv run pytest -W error` 428 passed / 1 POSIX skip.
Restoration: 87 affected tests, Node17, Ruff check/format95 files, diff and locked
offline wheel/exact22-member allowlist passed; current restored-head CI/CodeQL
green. Final documentation/head review and merge checks are recorded in PR65.

Latest cleanup at 11:05:55 UTC: supervisor exit0/stopped, all nine owned PIDs,
listener18092/control absent, Network observation disabled, viewport reset
succeeded and both tabs closed. Session naturally expired during cleanup Back;
no logout claim. Original600-second bound preserved. No operator/Ultra, vendor
code, renewal/cache, security or deployment changes.

## Authenticated hosted series navigation — issue #7

**Implemented / automated-tested / browser-tested / device-unverified:** the
trusted startup-only navigation scenario connects the existing fifty-episode
catalogue to normal production pairing/private JSON/posters/resolver and fixed
authenticated RAM original-media routes. Baseline/failure scenarios, production
app/security policies and supervisor 180-second startup/900-second total bound
are unchanged. No public action/media URL substitutions were used for acceptance.
The [actual matrix and evidence limits](series-navigation-results.md) supersede
the old renderer-only private-delivery gap for this synthetic software flow.

Official hosted MSX in connected Chrome at measured 1920x1080 reached all fifty
labels/three backend pages, Next/Previous, representative metadata and loaded
posters, retained Back focus, actual episode 50 original decoded frame/time/pause/
Stop, empty season and actual HTTP permission-error message/Back recovery.
Episode 01 original played afterward. Normal confirmed disconnect yielded zero
paired sessions. Browser route-only response samples and redacted server counters
are separate: the 401 was visible in UI and mock 403 in server counts, not retained
in the responseReceived sample; a later buffer read was truncated. No inference
from missing network events or previous public-export playback is used.

Windows/Python 3.12.14: locked dev/build sync; full `uv run --no-sync pytest -W error`
**414 passed / 1 POSIX skip**, no warnings; Ruff check/format **92 files**; diff
check; locked offline wheel and exact 20-member source/license/template allowlist
passed. Initial duplicate-origin test expectation was corrected. Independent
pre-activation review passed 52 affected checks and accepted unchanged supervisor/
auth/no-fallback/allowlisted RAM-media boundaries. Final source/evidence review and
required CI are recorded in the PR before merge. Physical Philips/audio/remote
remain unchecked in #4; this does not establish a real Jellyfin release pass.

At 08:45:18 UTC own supervisor exit 0/stopped, all 9 recorded exact helper/console/vendor
PIDs, listener 18092 and control directory were absent; both owned tabs closed,
Network observation disabled and viewport restored to 2560x1215. Code/URLs/raw
records stayed in RAM and were discarded; saved evidence is secret-free.

The maintainer-requested concurrency policy is also documented: up to three
independent issue chats/worktrees; one master-controlled shared browser/relay slot
and serialized merge slots; the global human-input gate is unchanged.

## QR-first activation layout — issue #16

**Implemented / automated-tested / browser-tested / device-unverified:** the
native pairing page gives the local QR its own area, explicit "or" companion
address, grouped code/validity and brief sign-in guidance. Only Continue after
pairing and Create new code take focus. The capability-bound pairing status
retains activation instructions while waiting, opens authenticated libraries
after sign-in and gives expired/unknown grants only public new-code recovery.
Private home/library denial, pending-only QR, CSRF and privacy headers remain.
The historical public waiting export stays code-free; no private QR is published.

[Actual layout actions, captures and limitations](qr-pairing.md) distinguish
official MSX 0.1.167 / connected Chrome at measured 1920x1080 from physical TV
acceptance. Rendered QR decode/activation, scan-only waiting, normal synthetic
sign-in/Continue, confirmed disconnect, grouped manual entry and the two-control
native focus were exercised. Natural expiry at 313 seconds showed one-button
TV recovery and credential-free QR rejection. A changed grouped code, normal
manual entry/sign-in and Continue reached settled private libraries. Actual
rendering exposed disabled-teaser dimming;
the final nonselectable native space restores full-opacity code text. Codes,
activation links and raw QR images stayed in RAM; retained images are masked.
Physical Philips/phone scan/readability/overscan/remote checks stay unchecked in #4.

Windows/Python 3.12.14: locked dev/build sync passed; full `uv run pytest -W error`
with isolated `--basetemp` / `cache_dir` **411 passed / 1 POSIX skip**, no warnings;
`uv run ruff check .` and `uv run ruff format --check .` **92 files** passed;
five existing Node browser-driver guards and `git diff --check` passed. Offline
wheel build and exact **20-member** source/license/template allowlist passed.
The first full run found an outdated synthetic code-format assumption (14 helper
failures, 397 passes / 1 skip); adapting that existing helper restored the full
suite. No dependency, operator/Ultra, media/audio or physical-device change/pass.
Two sanitized browser response observations record only the pairing-status route
category, 200 and JSON MIME type, separately from screenshots and mocked headers.
Both own paired sessions disconnected normally; own tabs closed and viewport
restored. The final supervisor exited 0/stopped; seven recorded owned helper PIDs,
vendor process, listener/control directory were absent at 08:30 UTC. Independent
review/required CI are recorded against the final PR head; review of masked images
does not independently decode hidden QR/code pixels or repeat live browser actions.

## QR companion pairing — issue #14

**Implemented / automated-tested / device-unverified:** native MSX pairing now
displays a locally generated PNG QR for an independent pending-only activation
secret, with readable address/grouped code fallback. The image route revalidates
pending state and has its own bounded peer/global budget; normal authentication,
exact-origin CSRF, stage binding and no-store/no-referrer remain unchanged.
Segno is the only added runtime dependency; Pillow/zxing-cpp decode in development
only. Independent dependency review matched all 85 new locked artifact hashes
to official PyPI and verified their licenses; existing versions did not change.

[Actual QR browser observations and privacy boundaries](qr-pairing.md) record
corrected official-MS​​X 1920x1080 rendered screenshot decode, clean activation
sign-in/code skip, scan-only Waiting, normal credentials/Continue to private
libraries, used-QR recovery, confirmed own disconnect and grouped-code fallback.
Natural five-minute pending expiry then returned credential-free manual recovery;
actual Create new code/Return, changed grouped code, normal sign-in and Continue
reached libraries again. The final settled library screenshot was inspected.
The first actual render caught an invalid native root structure which HTTP tests
had missed; `pages` fixed it. Codes/QR URLs/raw images stayed in RAM; only masked
or secret-free screenshots were retained. Full pairing-layout work stays #16;
physical phone/Philips scan, distance/overscan/remote checks stay unchecked in #4.

Windows / bundled Python 3.12.14: locked dev/build sync passed; full
`uv run --no-sync --python .venv/Scripts/python.exe pytest -W error` with isolated
`--basetemp` and `cache_dir` **408 passed / 1 POSIX skip**, no warnings; required
uv Ruff check/format passed (**91 files** in the final local invocation), five
existing Node browser-driver guards and whitespace check passed.
Offline wheel build and exact **20-member** tracked-source/license/template
allowlist passed. Initial default sandbox tests failed on OS temp/cache access;
isolated temporary/cache directories and reviewed execution resolved that
environmental failure. Initial helper title assumptions also failed with the
new titleless native image; action lookup now handles native page/image items.
No local Docker, real Jellyfin, media/audio or physical-TV pass is claimed.
The final bounded synthetic relay exited 0/stopped, all nine recorded owned PIDs,
listener and control directory were absent at 08:08 UTC; own tabs closed and MSX
viewport restored. Final-head independent evidence review and CI are recorded in
the linked PR; no browser-request trace was retained or inferred from unit tests.

## Two-stage pairing software acceptance — issue #13

**Implemented / automated-tested / device-unverified:** the remaining normal
official hosted-MS​​X pairing-to-private-libraries criterion is supported by the
already reviewed #9 HTTPS runs. The [acceptance mapping and provenance](companion-pairing.md#software-acceptance-evidence--2026-10-31)
combine PR #45's receiving protocol/security regressions with PR #57's actual
manual pairing → Continue → libraries and PR #58's corrected ten-stage positive
connector execution, fresh CSRF/login denials and settled own disconnect.
PR #59 repeats normal pairing before authenticated recovery. Source baseline:
`31aeeb4c0cf300daa2172cd7b6be81692dba7902`; the pairing security/state protocol is
unchanged, and the current presentation was already exercised by those runs.

This follow-up reconciles existing evidence; it changes no runtime, helper,
dependency or authentication policy and starts no new public relay. The local
fixed-field positive/fault reports and sanitized settled disconnected screenshot
were inspected. That screenshot proves the final screen only; earlier browser
actions remain attributed to their original worker and durable results. The old
loopback Data Load Error below is historical, not a remaining #13 software gate.
QR rendering is #14, pairing layout #16, the broader browser matrix stays #9,
and real-server/mobile/physical-TV acceptance remains unverified or deferred.

Current Windows/Python 3.12.14 audit: `uv sync --locked --extra dev --group build`
passed; `uv run pytest -W error` **398 passed / 1 POSIX skip**, no warnings;
`uv run ruff check .` passed; `uv run ruff format --check .` **88 files** passed;
`node --test tools/browser_pairing_check.test.mjs` **5 passed**; Node syntax and
`git diff --check` passed. These are current automated regression/guard checks,
separate from the reused actual browser results. No new browser or wheel-build
pass is claimed by this documentation-only follow-up.

## Hosted JSON/playback/access recovery — issue #9

**Implemented / automated-tested / device-unverified:** a trusted startup-only
`--scenario failures` selects authenticated strict mocked JSON/access/unreachable
libraries and a PlaybackInfo-rejected item. Baseline remains the default; no
public mutation endpoint, request-selected scenario, operator configuration,
network fallback, production behavior or dependency changed. The supervisor's
180-second startup and original 900-second total lifetime are preserved.

[The extended connector command and actual results](browser-failure-check.md)
record a 21-stage positive official-MSX Chrome run, specific visible failures and
Back/home recovery, healthy native decoded 1280x720/time advancement/error-null,
and Stop paused/time-zero/readyState-zero. JSON and playback variants each failed
the same ordinary healthy-recovery assertion with a matching fresh denial. The
upstream network error was a controlled MockTransport exception, not a real relay
outage. Initial stale browser-ID refusal and independent-review corrections are
recorded. All owned tabs closed; failed RAM sessions ended with service cleanup.
Exit 0 / stopped and all exact helper/listener/control cleanup were verified within
the original budget. The final Disconnected / Pair again screenshot was inspected.

Local full pytest **398 passed / 1 POSIX skip** with `-W error`; focused **38 passed**;
Node guards **5 passed**; syntax/diff and Ruff passed after removing one unused
import; format **88 files** passed. Independent review repeated source/guard/
mocked checks and inspected local evidence; browser execution/cleanup remain
worker-observed. Issue #9 remains open for expiry, actual relay/network outage,
series/pagination, source/resource/cross-session coverage and complete standalone
automation. Audible sound and physical Philips behavior remain unverified.

## Connected Chrome pairing assertions — issue #9

**Implemented / automated-tested / device-unverified:** the reusable
[pairing connector command and actual results](browser-pairing-check.md) use
supported connected-Chrome Tab APIs, read-only DOM checks and real normal forms
in the official hosted MSX runtime. Final positive execution passed ten stages:
synthetic identity, runtime startup, stale-CSRF/wrong-code/wrong-credential denial,
code and clean sign-in recovery, normal pairing, MSX Continue and own disconnect.
Deliberately broken positive CSRF and login paths each failed at normal-pairing
with the matching fresh denial category; neither reached authenticated Continue.
These are actual browser assertions, separate from local guard/HTTP tests.

The driver suppresses raw errors/body text, retains codes only in its closure and
closes only owned tabs. Dedicated origins avoid expiring a user's pending form via
the deliberately rotated shared cookie. Independent review found and resolved a
stale-error attribution flaw; an earlier outgoing-scene screenshot and failed
settled-frame trial are recorded. The corrected disconnected screenshot was
inspected. Local Node guards **5 passed**, syntax/diff passed; `uv run pytest -W
error` **394 passed / 1 POSIX skip**, Ruff passed and format **85 files** passed.
The dedicated approved relay stopped within its original 900-second lifetime;
exit 0, absent listener/control directory and all exact owned helpers were verified.
No production code, dependencies, authentication policy, operator data or security
settings changed. The command requires the browser connector; it is not an
unattended public-CI or standalone shell E2E driver. Expiry, JSON/playback/network
faults, series/source/resource-isolation coverage remain open in #9; audio and
physical Philips behavior remain unverified.

## Partial hosted synthetic HTTPS browser observations — issue #9

**Implemented / device-unverified:** a separate worker-owned tab in connected
Chrome operated official MSX 0.1.167 through the approved temporary synthetic
HTTPS relay. [Actual actions, media observations and limitations](msx-synthetic-https-results.md)
record normal two-stage CSRF pairing, authenticated libraries/details, actual
1280x720 decoded moving frames and advancing time, pause/resume, forward/back
seek, Escape Stop, replay, visible oversized-source denial, own-session disconnect,
stale-route 401 and start-page recovery. Audio and physical TV remain unverified.
Separate tabs shared the browser profile; cookie-context isolation is not claimed.
The worker did not operate the user's session or stop/restart the relay early.
No complete browser command, failure-sensitivity matrix or real-server pass is
claimed; #9 remains open. The accompanying evidence change is documentation-only;
the readiness implementation checks below still apply, not a new automated
browser test result.

## Approved synthetic HTTPS readiness follow-up — issue #9

**Implemented / automated-tested / device-unverified:** after explicit human
approval for synthetic-only temporary Cloudflare exposure, three bounded starts
failed readiness and cleaned up. The local backend returned the expected health
JSON; the OS resolver and connected Chrome initially could not resolve assigned
names, although public HTTPS DNS queries returned answers. The unchanged OS
resolver later resolved those names naturally. No resolver, TLS or browser
security settings changed.

The startup window is now 180 seconds inside the original 900-second total
lifetime. Regression cases cover delayed readiness, shorter total budgets,
readiness probes crossing the deadline and owned cleanup. `uv run pytest -W error`
passed **394 tests / 1 POSIX skip**, Ruff passed, formatting passed **83 files**,
and independent affected-diff review found no blockers after repeating the 34
focused tests. One further approved attempt reached actual local and verified
public HTTPS health readiness after its initial DNS failure cleared naturally.
Only the fixed health endpoint was requested; no MSX pairing session was created
or paired by the worker. This is HTTPS delivery evidence, not an actual hosted-MSX
rendering/playback pass. The original issue #9 browser matrix remains open.

## Temporary synthetic HTTPS local preparation — issue #9

**Implemented / automated-tested / device-unverified:** a separate opt-in
synthetic public-origin factory and Windows-owned helper supervisor, with
[exact commands, binary provenance, containment and pending activation scope](temporary-synthetic-https.md).
The real operator lab remains loopback-only. Public preparation uses explicit
same-origin strict mocked Jellyfin, normal two-stage CSRF pairing, random RAM
tokens, no operator/environment/credential-store configuration and only the
checksum-verified committed clip snapshotted into RAM. No production source,
runtime dependency, persistence or default authentication policy changed.

The official cloudflared 2026.10.7 asset metadata/digest was re-read, the local
download matched SHA256, and only version/help were executed. Safe `--check`
reported prepared/approval-required/tunnel-not-started. The future opt-in command
has exclusive owned loopback reservation before tunnel startup, isolated config/
environment, hidden helpers, bounded raw-log filtering, verified-HTTPS no-redirect
relay health, 45-second startup and 900-second lifetime limits, EOF watchdogs,
Windows descendant Job Object containment and exact owned-process cleanup.
The lifetime is followed by bounded shutdown; no process-name scan or broad kill.

Windows/Python 3.12.14: locked dev/build sync passed; `uv run pytest -W error`
**391 passed / 1 POSIX skip**, no warnings; `uv run ruff check .` passed;
`uv run ruff format --check .` **83 files** passed; `git diff --check` passed.
Offline wheel build with explicit `.venv/Scripts/python.exe` and the exact
tracked-source/license/template allowlist passed. All helper/config/binary/media
files remain excluded from production artifacts. Normal synthetic HTTP check
passed. Tests include a real owned local-only backend listener and harmless
Python helper processes, including occupied-port refusal, startup/runtime/stop/
interrupt failure cleanup and abrupt Windows wrapper/descendant termination.
An initial test incorrectly expected LF instead of Windows CRLF; that test
assumption was corrected. No real tunnel was used to pass any test.

Independent source/security review repeated the full warning-free suite, Ruff/
format/diff, offline wheel and exact 19-member manifest with no blocking findings;
it verified primary Cloudflare/Microsoft sources and did not run the vendor
executable, a tunnel, browser, real server, credentials, trust or hardware actions.

**Deferred:** activation requires a new explicit human decision for temporary
public exposure. No public tunnel, allocation/relay request, HTTPS companion or
official-MSX private-flow test occurred. No trust import/bypass, live configuration,
operator account/media, production resources or TV action occurred. Local helper
tests and preflight are not hosted integration evidence. Issue #9 remains open;
its original browser matrix and real-server/final-device gates are preserved.

## Supported TestClient dependency — issue #30

**Implemented / automated-tested / device-unverified:** the dev extra adds
HTTPX2 2.16.0 for Starlette 1.10.0 TestClient's supported client path. Application
HTTPX 0.28.1, FastAPI, Starlette and all existing dependency versions stay locked
unchanged. No warning is suppressed; CI now runs the entire Python 3.12/3.13
suite with `pytest -W error`. Production source and request/security behavior
are unchanged. [Dependency evidence](build-supply-chain.md#testclient-update--issue-30)
records the four added lock packages and client-object boundary.

Windows/Python 3.12.14: `uv sync --locked --extra dev --group build` passed;
`uv run pytest -W error` **360 passed / 1 POSIX skip**, with no warnings;
`uv run ruff check .` passed; `uv run ruff format --check .` **79 files** passed.
The full suite includes HTTP/origin/CSRF/chunked pairing bodies, early body-limit
parser denial, subtitle streaming/size/deadline/revocation and upstream failure
regressions. `uv run --no-sync python -W error -m tools.synthetic_check` passed;
offline wheel build with explicit `.venv/Scripts/python.exe` and exact tracked
source/license/template allowlist passed. The initial unqualified `uv lock`
failed on a stale external Python 3.15 link; selecting the bundled Python 3.12.14
explicitly resolved the lock without modifying the global Python installation.
No browser, physical TV, real Jellyfin, credentials, production deployment or
OS trust change occurred. Independent source/security/dependency review of
`841dacfe2676c15e78c9186dfcbc3708b19a2df1` found no blockers and independently
reran the full Windows suite/Ruff and corroborated primary package lineage,
Starlette's optional dependency contract and all eight artifact hashes.
Actual [Linux CI](https://github.com/alexanderhetzel/jellyfin-msx/actions/runs/41134339048)
passed Python 3.12 and 3.13 with **361 tests each**, using `pytest -W error`,
plus Ruff, synthetic HTTP, wheel manifests and installed-wheel encryption/restart/
rotation/replay-denial smoke. Docker build/context/image allowlists, non-root
runtime, `pip check`, proxy configuration, packaged HTTP smoke and full-history
secret scan passed. Pytest emitted no warnings; existing pip root-build notices
in the Docker logs remain visible and are not Python test deprecations. No local
Docker run, browser or physical device pass is inferred. The following
documentation-only change still requires final-head review and CI before merge.

## Playback profile contract — issue #34

**Implemented / automated-tested / device-unverified:** immutable candidate
descriptions separate codec/container/ranking data from the shared HD admission
policy. Production remains fixed to the existing Philips candidate; no runtime
selector, new hardware profile or UI change was introduced. The
[profile contract](playback-profile-contract.md) defines trusted future selection,
unknown-selection rejection, session/profile/source binding and evidence,
configuration, diagnostics, UI and regression requirements before rollout.
Two synthetic test-only profiles demonstrate independent source ranking and
PlaybackInfo declarations, HD/metadata/operator restrictions, output isolation
and production hint-spoofing denial. Browser/physical acceptance and selectable
production profile rollout are explicitly deferred; no new Jellyfin-version or
upstream media-revocation result is claimed.

Windows/Python 3.12.14: `uv sync --locked --extra dev --group build` passed;
affected profile/Philips/direct-only tests **86 passed**; full `uv run pytest`
**360 passed / 1 POSIX skip**, existing warning #30; `uv run ruff check .`
passed, `uv run ruff format --check .` **79 files** passed; `git diff --check`
passed. Initial Ruff line-length finding was corrected by formatting before the
full checks. No real Jellyfin, credentials, browser, TV, conversion, deployment,
TLS trust, dependency or proprietary runtime change occurred. Primary official
MSX request/player documentation and the exact-model manufacturer datasheet were
read; source links, versions and limits are recorded in the contract.
Wheel build (`uv build --wheel --no-build-isolation`) and exact tracked-source/
license/template allowlist check passed. Independent review reran the full suite,
Ruff/format and whitespace checks and corroborated the primary evidence without
blocking source/security findings. Its small diagnostic-description clarification
was corrected and output-mutation HD isolation strengthened; the affected
**15 tests** and Ruff/format passed again. Reviewer did not operate MSX, a TV,
real Jellyfin or a container. Required GitHub container/check gates still apply
before merge; no local Docker execution is inferred.

## Consistent visual design — issue #15

**Implemented / automated-tested / browser-tested / device-unverified:** shared
dark surfaces/light text/green product label in native MSX and companion pages,
readable code/sign-in/retry/success hierarchy, preserved native MSX controls and
visible keyboard recovery focus. [Design and actual evidence](visual-design.md)
records final public fixture pin, measured 1920x1080 official MSX and 390x844 /
1280x900 companion screenshots, native key/form actions and scope limits.
Physical readability/overscan/remote acceptance was explicitly preserved in final
issue #4; no TV or full hosted private pairing pass is inferred.

Windows/Python 3.12.14: `uv sync --locked --extra dev --group build` passed;
`uv run pytest` **345 passed / 1 POSIX skip**, known warning #30;
`uv run ruff check .` passed and `uv run ruff format --check .` **76 files** passed.
`uv build --wheel --no-build-isolation` and the exact tracked-source/license/template
wheel allowlist check passed, including the presentation module and excluding
tools, fixtures and local helper/reports. An initial 345-test pass exposed
Ruff formatting/line-length findings, subsequently corrected; the final full run
and both Ruff checks passed. Public-export and pairing affected checks also passed.
No dependency, real server/account, production, trust or runtime-code change.
Independent review inspected source/security/export boundaries and all sixteen
named visual captures with no blocking findings; it did not repeat browser
actions. Final denial capture is the denied-detail view, distinct from the opened
timed notice observed during actual actions. Owned tabs/listener were closed and
viewport overrides cleared, with original 2560x1215 dimensions restored.


## Opt-in subtitle resource milestone — issue #22

**Implemented / automated-tested / device-unverified:** disabled-by-default
[bounded WebVTT catalogue/resource](subtitle-resources.md), exact source/absolute
index admission, reauthorization/revocation, fixed upstream route, token withholding,
UTF-8 plain-cue validation and deadline/size/concurrency limits. Normal MSX UI
remains Off; #22 remains open for actual controlled-origin hosted private delivery,
selection, placement, recovery and seek/Off/Stop. No new browser or TV test ran.

Windows/Python 3.12.14: frozen dev/build sync passed; `uv run pytest` **333 passed,
1 POSIX skip** (known warning #30); Ruff check and format check **74 files** passed.
First affected run: 60 passed, one test assumed a non-subtitle Audio mutation
would leave the source eligible. Production correctly rejected the incompatible
source; the assertion now accepts that fail-closed result. No real server,
credentials, TLS trust, deployment, vendor-runtime change or library mutation.
After additional rate/preflight/chunk/transport/parser-bound checks, the full
suite passed **338 tests / 1 skip**, Ruff/format passed. Offline wheel build with
explicit `.venv/Scripts/python.exe` and exact source/license/template allowlist
passed. Independent review found Unicode digits admitted in timestamps; restrict
the grammar to ASCII with a regression. Review also found an ambiguous double
timing line could be mistaken for a cue ID; arrow-bearing IDs/payload now fail
closed. Final local full suite: **345 passed / 1 skip**, Ruff check/format passed,
offline wheel/exact allowlist and `git diff --check` passed. Additional malformed
item-Type, duplicate-source, mismatched-item and metadata-revocation regressions
pass. Docker is absent locally; Compose/container verification is a required CI
gate. The independent reviewer did not execute a live MSX browser or TV.

## Subtitle research — issue #21

**Implemented / automated-tested / browser-tested / device-unverified:** public
UTF-8 VTT/SRT/ASS fixtures, locally remuxed embedded mov_text, official HTML5X
matrix and [source/request evidence and secure #22 contract](msx-subtitle-research.md).
Actual MSX 0.1.167/connected Chrome displayed German umlauts/two-line VTT,
DE→EN/Off and sampled backward/forward cue changes. Paused switching/seeking
showed unstable placement; resumed English remained against the lower edge.
Raw SRT/ASS did not render despite 200 responses; native/HTML5X embedded text
had no tracks/cues, plugin panel on native produced recoverable Data Load Error.
Missing track left DE indicated without a specific notice while video played.
These are researched limits, not a polished production subtitle pass. Existing
production behavior is unchanged; #22 owns private delivery and #4 physical TV.

Windows/Python 3.12.14: frozen dev/build sync, full `uv run --no-sync pytest`
(**271 passed, 1 POSIX-only skip**, known warning #30), Ruff check/format
(**72 files**), offline wheel build with `.venv/Scripts/python.exe`, wheel source/
license/template allowlist and `git diff --check` passed. A subsequent committed-
matrix consistency regression passed with all **3 affected tests**. Independent
source/security/evidence review reran **272 passed / 1 POSIX skip**, Ruff/format
72 and offline wheel/allowlist, inspected twelve captures and filtered request
evidence, and accepted the constrained research scope. It found two premature
captures (recovery menu and embedded Off-only panel); separate settled UI checks
replaced those ignored files and the reviewer confirmed both. The reviewer did
not operate the live browser or a TV. Required final-head CI remains the merge gate.
Initial FFmpeg null-output extraction failed because no subtitle encoder was
selected; explicit SRT output successfully extracted all four embedded cues.
Only local synthetic remux occurred, no AV encode/Ultra request. Publication
review accepted public-only assets/provenance and package exclusions. No real
credentials, private grant publication, trust/TLS change or deployment occurred.

## Series navigation renderer milestone — issue #7

**Implemented / automated-tested / browser-tested / device-unverified:** isolated
fifty-episode catalogue, 24/24/2 pagination, empty/restricted seasons, explicit
production empty-state row and deterministic application-derived public graph.
The [actual evidence and reproduction](series-navigation-results.md) separate
normal private mocked HTTP tests from public substituted rendering/video.

Official MSX 0.1.167 in connected Chrome visibly traversed all fifty labels,
both Next/Previous boundaries, episode 24/50 details, Back focus, empty-season
focus and denial recovery. Episode 50's substituted clip showed a real frame,
advancing time, pause and Stop. Returning the exported production 401 wrapper
through the public content callback instead showed generic Content Not Available,
not the permission message. **Issue remains open** for normal hosted private
authentication/delivery and its actual HTTP error behavior. No TV or audio pass.

Windows/Python 3.12.14: frozen dev/build sync, `uv run --no-sync pytest`
(**269 passed, 1 POSIX-only skip**, known Starlette warning #30), Ruff check/format
(**67 files**), locked offline wheel build with explicit `.venv/Scripts/python.exe`,
`tools.package_check wheel` exact source/license/template allowlist and
`git diff --check` passed. The first exporter attempts failed on missing synthetic
folder-item poster authorization and the real twelve-resolver rate budget; adding
the fixture item contract and sampling six boundary negotiations fixed preparation.
One metadata assertion incorrectly expected a stripped separator and was corrected.
Independent publication review passed 52 affected tests/Ruff/wheel/allowlist and
accepted the public source boundary. Independent source/evidence review also reran
269 tests/one skip and Ruff/format, inspecting the saved focus, paused-frame, empty,
negative-denial, recovery and settled-poster evidence. A narrow final iframe-only
visibility fix removes the probe diagnostics from behind MSX. Its first launch timed
out; one ordinary reload succeeded, and affected series/poster/empty/denial/Back
screens were rechecked. Final-head approval and CI are recorded in the PR before
merge. No real server, credential, trust-store, production resource,
proprietary-runtime change or physical-device action occurred.

## Reproducible build-input milestone — issue #27

**Implemented / automated-tested / device-unverified:** official Python
and Caddy index digest pins, exact Hatchling/build-group lock, hash-checked uv
bootstrap, binary-only/hash-checked container dependency downloads, offline project
build/runtime installation, explicit wheel/context file allowlists, synthetic
exclusion canaries and source-byte/SHA256 manifests. CI retains SHA Actions,
read-only token and credential-free checkout, adds installed-wheel/Fernet/SQLite
smoke and actual filtered-context/final-image inspection. Weekly update PRs cover
runtime/build, bootstrap, Actions and Docker. See the
[input provenance, commands and update contract](build-supply-chain.md).

Windows/Python 3.12.14: `uv lock --check`, frozen sync with dev/build groups,
`uv run --no-sync pytest` (**266 passed, 1 POSIX-only skip**, known Starlette
warning #30), Ruff check and format (**63 files**) passed. Offline wheel build
with explicit `.venv/Scripts/python.exe`, license/NOTICE/template/source manifest
and synthetic exclusion canaries passed; the synthetic HTTP contract passed.
An initial build selected the base interpreter through `UV_PYTHON` and lacked
Hatchling; explicit build-interpreter selection corrected the command. Initial
canary inspection exposed Hatch's `packages` overriding include filters; replacing
it with include patterns/path rewriting fixed the actual wheel. An existing
literal `.lab` guard was retained alongside the context allowlist. These failures
were observed and corrected, not counted as passes. A separate temporary Windows
environment then installed the actual wheel outside the checkout using hashed,
binary-only runtime exports; Fernet/SQLite restart/rotation/replay smoke passed.
Docker is absent locally. Initial Linux CI exposed a clean editable install's
missing dynamic `editables` backend requirement and context allowlist failures.
Explicit `dev-mode-dirs = ["src"]` avoids that unneeded backend dependency.
The payload now excludes consumed Dockerfile/.dockerignore metadata; directory
admission is followed by recursive exclusions before individual files are
admitted, preventing parent exceptions from admitting local descendants.
Independent review also required mismatch diagnostics to log only unexpected
file counts, never arbitrary names containing a canary substring; a regression
covers that privacy boundary. Verified official Gitleaks 8.30.1 Windows x64 release checksum;
`gitleaks git . --log-opts=--all --redact --no-banner` scanned 67 commits and
reported no leaks. No browser, MSX, TV, real server, production deployment,
credential or trust-store action occurred for #27.

GitHub CI on reviewed `9889adba11d24a22898eefa67ef83224b2b475e1` passed Linux
CPython **3.12.15 and 3.13.17, 267 tests each**, Ruff/format, synthetic HTTP,
offline wheel/source/license/template/canary manifests and isolated hash-checked
installed-wheel smoke. Docker passed actual filtered-context export, pinned-image
build, selected Caddy configuration validation, UID 10001, final filesystem/source
manifest, `pip check`, installed Fernet/SQLite smoke and health/start/pair HTTP
smoke. Full-history redacted secrets and Python/Actions CodeQL checks passed.
Independent review accepted that source head, independently reran the preceding
265-test suite/one skip and the final 10 affected tests/Ruff/format/diff checks,
and resolved the diagnostic privacy finding. The reviewer did not run Docker;
container evidence is CI. The final follow-up suppresses HTTP smoke response
bodies so generated synthetic form fields are not printed, and records these
results; its final-head checks must still pass before merge. None of this is an
MSX integration, physical-device or production deployment pass.

## Cryptography dependency refresh — issue #27 / PR #44

**Implemented / automated-tested locally / device-unverified:** the existing
Dependabot update was refreshed from 50.0.0 to 50.0.2 and brought onto current
main. The supported constraint is now `cryptography>=50.0.2,<51`; the committed
lock selects 50.0.2. Official PyCA release notes and current GitHub advisories
GHSA-m2h6-j472-rp4c, GHSA-jwv3-5hgf-82ww and GHSA-g6cj-pr64-35w5 put old 48.0.1
inside affected version ranges. Their X.509 verification and PKCS#7 EnvelopedData
APIs have no identified call path in this project's Fernet/InvalidToken usage;
that is not a declaration that the old dependency is unaffected. The update also
obtains the current patch's bundled OpenSSL fixes. Version 49 removed Intel macOS
and 32-bit Windows wheels; no support for those platforms is asserted here.

Windows/Python 3.12.14: `uv lock --upgrade-package cryptography==50.0.2`,
`uv sync --frozen --extra dev`, `uv run --no-sync pytest` (**262 passed, 1 POSIX
skip**, known Starlette warning #30), Ruff check/format (**59 files**),
`uv build --wheel` and `git diff --check` passed. The build-milestone dependency
smoke also passed against this environment: template/app construction, Fernet
roundtrip/expiry/tamper denial and actual SQLite restart/rotation/replay denial,
all synthetic/offline. This local smoke used the editable environment, not an
isolated installed wheel. Independent review accepted exact head
`43e4c5e85779e9e3233b902fa12ea4b7a5523a32`: 53 cryptography artifact URLs/hashes
match official PyPI; 48.0.1 ↔ 50.0.2 Fernet wire/TTL/expiry/tamper/wrong-key
compatibility passed both directions; the reviewer reran the full Windows suite
and Ruff. Linux CPython 3.12/3.13 tests, wheel, Docker/proxy/health/start/pair,
full-history secret scan and Python/Actions CodeQL checks all passed on that
head. With no unresolved review threads and actual required checks passed,
PR #44 was explicitly squash merged as `e30e1cd6f68e7652ba1d325ef175c9e398c09bf0`.
No real account/database, MSX, TV or production action ran.

## Initial two-stage companion pairing milestone — issue #13

**Implemented / automated-tested / device-unverified:** manual code validation
precedes credentials, with bounded single-use device/CSRF-bound RAM grants,
absolute pending expiry checked before/after authentication, fixed recovery,
fresh blank password retries, explicit code restart and independent pending-only
activation links. Strict POST Origin/CSRF, 8-KiB body protection and bounded code/
credential attempts remain. A temporary Lax activation cookie supports cross-site
top-level GET redirects; the sign-in CSRF cookie remains Strict. See the
[pairing/security/evidence contract](companion-pairing.md). QR rendering is #14.

**Actual companion browser evidence:** connected Chrome native controls verified
invalid-code recovery without credentials, valid-code progression, wrong-password
cleared retry, successful synthetic pairing, old-tab CSRF recovery and explicit
code restart. A labeled local activation-route fixture exposed a Strict-cookie
redirect failure; changing only that pending-only handoff to Lax visibly fixed
cross-origin link entry, clean credential URL and successful native sign-in.
The recovery link's visited-color contrast was corrected and actual keyboard
focus/full-heading screenshots inspected. No `browser-verify` skill/tool was
available; the supported Chrome API supplied these observations. A phone viewport
override did not apply and was reset; no mobile-layout pass is claimed.

**Historical blocker at that milestone (superseded above):** the actual normal official-MS​​X launcher showed
Data Load Error / Start Error before pairing UI. Final-run sanitized counts show
no pair.json request, one mock authentication/200 and one paired session from the
separate companion activation check. Source JSON and the explicit activation
fixture are not MSX integration. Controlled-host full pairing/private libraries
and physical TV remain unverified. Activation redirects do not erase browser
history or substitute for log exclusions. No real account/server, deployment,
runtime modification, TLS trust retry/security bypass or TV action occurred.

Windows / Python 3.12.14: `uv sync --frozen --extra dev` passed;
`uv run pytest`: **262 passed, 1 skipped**, known Starlette warning #30;
`uv run ruff check .`: passed; `uv run ruff format --check .`: **59 files formatted**;
`uv build --wheel` and `git diff --check`: passed. All upstream tests use mocks.
The first adapted suite exposed the old shared five-POST budget across two
two-stage recovery flows; separate five-attempt code/login budgets and a bounded
ten-POST envelope corrected it. A new expiry-during-auth test initially changed
the TestClient facade rather than its actual transport; a fresh client against
the intended mocked app corrected that test harness and passed the logout check.
Independent security review found invalid activation recovery would retain the
no-referrer query URL and fail native Chromium Origin validation. Invalid links
now redirect with a non-secret sentinel before rendering the code form. Native
Chrome visibly verified invalid link → clean code recovery → valid code → blank
credentials; non-ASCII/Unicode invalid-link regressions also pass. The reviewer
independently ran the preceding 259-test suite/Ruff, inspected sanitized form/
focus images and assessed the Lax/Strict boundary, grant consumption and privacy
limits. Its top-of-heading screenshot rendering was inconclusive; the primary
agent and master inspected the full heading. The reviewer did not operate Chrome,
real Jellyfin or a TV.

## Durable server authorization milestone — issue #12

**Implemented / automated-tested / device-unverified:** disabled-by-default
encrypted SQLite authorization under an external runtime Fernet key, server/user/
device/expiry/verifier/generation binding, atomic single-use renewal, bounded
absolute expiry and generation-bound RAM sessions. Local disconnect revokes
before upstream logout. Same-origin JSON POST/body limits and existing normal
CSRF/single-use pairing remain enforced. See the
[protocol and recovery contract](durable-authorization.md).

**Deferred / issue remains open:** the default MSX UI does not call these APIs.
Controlled-origin plugin delivery, automatic startup, exact new renewal save/
readback, and visible official-MS​​X reload/reopen/backend-restart/re-pair acceptance
are unverified. Physical Philips retention remains in #4. A unit/HTTP contract is
not an MSX restoration pass. Single-worker deployment is unchanged.

Windows/Python 3.12.14: `uv lock` added cryptography 48.0.1 and its locked
dependencies; `uv sync --frozen --extra dev` passed. `uv run pytest`: **240 passed, 1 skipped**,
known Starlette warning #30; `uv run ruff check .`: passed;
`uv run ruff format --check .`: **57 files already formatted**;
`uv build --wheel` and `git diff --check`: passed. All upstream tests use mocks.
New evidence includes normal CSRF pairing then restarted app renewal, independent
connection races, storage locking/write rollback, corruption/key/server/schema
denial, bounded expiry/capacity/isolation and local revoke despite upstream failure.
The first run had 18 new cases pass and one test fail because a test-owned SQLite
connection was not closed on Windows; explicitly closing test connections fixed
the harness. No product authorization pass was inferred from that failure.

Actual connected-Chrome delivery check: an unchanged harmless loopback HTTP probe
loaded standalone, but official MSX 0.1.167 requested an HTTPS iframe and showed
an invalid-response frame. The failed frame screenshot was visually inspected;
no storage/backend/renewal operation ran. An initially malformed inline launcher
was corrected to the public base64 JSON format before observing the separate
iframe failure. Both owned tabs/listener were closed. No real credentials,
Jellyfin, certificate/trust retry, security bypass, production resource or TV
action occurred. This is negative delivery evidence, not a browser integration pass.

The Windows skip checks POSIX directory/file modes; Windows ACLs are an operator
requirement. WAL and SQLite-backup plaintext marker scans pass. Independent final
source/security/documentation review found no blockers for the backend milestone,
independently ran 239 passing tests/one POSIX skip and Ruff/format/diff checks,
and inspected the negative-delivery screenshot. It also reviewed the final nested
JSON fixed-error/default-disabled delta and independently passed that new test.
The reviewer did not operate Chrome, contact a real server or verify a TV.

## Native media credential decision — issue #25

**Implemented / automated-tested / device-unverified:**
[security decision and threat trace](media-token-security.md), with synthetic
direct/HLS URLs and primary MSX, HTML, Jellyfin authentication, HLS and referrer
contracts. Direct delivery remains the default and exposes a user session token
to the runtime/player. A scoped byte-serving gateway is required only when
withholding that upstream token is a requirement; implementation is deferred.
Redirects do not hide it. Initial URL validation cannot constrain native-player
redirects/HLS descendants; portal response policy does not prove player referrers.
No runtime behavior, production account or server configuration changed.

Windows / Python 3.12.14: `uv sync --frozen --extra dev` passed with the bundled
interpreter selected through `UV_PYTHON`; the first unqualified sync attempted
uv-managed Python 3.15.2 and failed on its expected target-directory link, before
the explicit interpreter resolved setup. `uv run pytest`: **217 passed**, known
Starlette warning #30; `uv run ruff check .`: passed;
`uv run ruff format --check .`: **54 files already formatted**;
`uv build --wheel` and `git diff --check`: passed. New mocked checks cover five
backend redirect statuses, initial HLS destination rejection, header/query
credential boundaries and diagnostic/log marker exclusion. Existing base-path,
token-replacement and redacted lab regressions also passed (51 focused tests).
No real Jellyfin, credentials, native-player packet capture, browser/TV test,
deployment log verification, TLS/trust change or production resource was used.
This is research acceptance, not a new private-hosted integration/device pass.
Independent source/security review checked the primary contracts and research
acceptance and independently reran 217 tests, Ruff/format and diff checks. Its
diagnostic-wording finding was corrected: only generated negotiation fields
omit upstream credentials; arbitrary bounded platform/player labels are not a
secret scrubber. The reviewer did not operate a browser, private server,
deployment or physical device.

## Public MSX lifecycle research milestone — issue #17

**Implemented / browser-tested / device-unverified:** independently authored
240-record synthetic interaction probe, commit-pinned public launcher and
[actual callback matrix / candidate telemetry design](msx-lifecycle-research.md).
Official MSX 0.1.167 in connected Chrome emitted actual load, pause, play, seek
and stop callbacks from real controls. Requested progress samples are explicitly
separate from emitted events. Initial load lacked a separate play callback;
Stop data and an immediate sample were stale; natural completion carried the
previous ended=true state on the next load. Back/content exit kept playing.
Missing media and a real tab-scoped offline fetch failure produced load/pause
with zero duration, without a collected app:disconnect. Cached media continued
offline. Network/cache overrides were restored. Screenshots and sanitized ordered
records are retained locally; no runtime events/player state were fabricated.

**Deferred runtime evidence:** genuine browser suspension/resume. With
documented suspend=1, actual tab changes still exposed visible documents in this
automation environment; no collected suspend/resume callback established the
required precondition. Physical comparison stays in #4. Abrupt-close final
delivery is not guaranteed; the proposed lease fallback is design only.
No production telemetry endpoint or Jellyfin reporting was added. Real plugin
authenticated transport needs a controlled HTTPS origin and separate validation.

**Research acceptance audit — 2026-10-31:** independent review mapped all four
original #17 criteria to the retained evidence and conservative contract. The
criterion asks to record behavior, and its milestone explicitly permits
unavailable cases with fallback. Requiring successful genuine suspension before
closing research exceeded that scope. The bounded same-window/minimized-window
follow-up is now recorded in the research document: metadata confirmed minimized,
but the document remained visible and no collected suspend/resume callback proved
the precondition. That technical limit remains unverified, with no new runtime
pass. The research contract is sufficient to begin #18; implementation, actual
authenticated transport, generation correlation and reporting/disappearance tests
remain #18 acceptance. Unknown visibility never fabricates progress; fresh valid
samples supply observations and missing evidence expires the candidate lease.
No browser/relay or production behavior was changed by this documentation audit.

**Historical automated checks — 2026-10-30 / Windows / Python 3.12.14:** frozen dev sync passed;
`uv run pytest`: **206 passed**, existing Starlette warning #30;
`uv run ruff check .`: passed; `uv run ruff format --check .`: **51 files already
formatted**; `uv build --wheel`: passed. These check the existing application and
do not exercise JavaScript or replace actual callback evidence. No real server,
credential, TLS/trust change, production resource or physical-TV action occurred.
Independent source/API/evidence review checked both ordered record sets and six
saved screenshots, and independently reran 206 tests and Ruff/format/diff checks.
Its replay-conflict finding was corrected by specifying a bounded digest window;
the reviewer did not operate the browser or verify audio/hardware.

**Current audit checks — 2026-10-31 / Windows / Python 3.12.14:**
`uv sync --locked --extra dev --group build` passed;
`uv run pytest -W error`: **428 passed / 1 POSIX skip**, no warnings;
`uv run ruff check .` passed; `uv run ruff format --check .`: **95 files** passed.
These are current application regressions for a documentation-only change; they
add no browser, suspension or hardware evidence. Final documentation diff review
and required current-head GitHub checks remain merge prerequisites.

## Actual public MSX renderer/player milestone — issue #9

**Implemented / browser-tested / device-unverified:** independently encoded public
synthetic clip, public application-derived fixture exporter, commit-pinned JSON
and assets, and the [precise runtime/evidence matrix](msx-public-fixture-results.md).
Export preparation uses normal synthetic production CSRF pairing, then replaces
every private navigation/media action before publication. No auth bypass or
private capability/code/token is published. Runtime playback uses a clearly
substituted public video and does not establish private app/source dispatch.

Actual official MSX 0.1.167 in connected Chrome rendered library/movie/detail and
HD denial notices. A real 1280x720 frame and advancing time were inspected.
Actual Pause held 16.316064 for 38.085 seconds; Play resumed. Forward/rewind,
near-end seek to 29.929254 of 30, Stop/Replay and Back/focus were observed with
real controls, never media setters. A gradient poster eventually rendered after
initial black captures; cold-load timing/cause remains unresolved. Missing public
media had no frames/native inaccessible-media text; screenshot lacked a clear app
error notice. Actual Stop recovered a usable library with selected-row focus.
Audio was not independently verified. Early and revised source/asset revisions,
failed tool captures and safe media observations are recorded in the matrix.

**Automated-tested on Windows / Python 3.12.14:** locked dev sync succeeded;
`uv run pytest`: **206 passed**, existing Starlette warning #30;
`uv run ruff check .`: passed; `uv run ruff format --check .`: **51 files already
formatted**; `uv build --wheel`: passed; `git diff --check`: passed. Local FFmpeg
7.1 fully decoded the committed synthetic clip (720 frames) to null without error.
New regressions check public nested actions/leak guards, deterministic export,
committed snapshot provenance and no real upstream network fallback. CI remains
offline/synthetic; these counts do not substitute for the actual UI evidence.
Independent final source/security/evidence review repeated all 206 tests and
Ruff/format/diff checks, verified the clip checksum and inspected six saved
frame/poster/control/recovery captures plus sanitized observations. No blocking
findings remained. The reviewer did not operate the browser, verify audio, fully
decode media, contact a real server, change TLS trust or test a physical device.

**Deferred:** normal hosted app pairing/private source delivery, dynamic browser
JSON/PlaybackInfo/CSRF/authorization failures, series/pagination, browser session
isolation/logout and the complete browser assertion command/CI. Issue #9 remains
open. No live credentials, real Jellyfin, certificate/trust retry, TLS bypass,
production deployment or physical-TV action occurred. Real-server/device gates
remain separate; storage acceptance stays in #11.

## MSX public storage/startup research — issue #11

**Implemented:** an independently authored synthetic-only interaction probe,
hosted startup JSON and launch helper, plus the
[storage evidence, candidate renewal contract and physical comparison checklist](msx-storage-research.md).
No persistent authentication feature or production session behavior changed.

**Browser-tested / device-unverified:** official MSX 0.1.167 in connected Chrome
156 (running executable 156.0.8078.80), same existing profile and MSX/shared
source-preview origin pair. Actual MSX clicks exercised missing, write/readback,
content reload, navigation away/Back, close/reopen read-before-write, corrupt,
injected-unavailable/failed-write recovery and exact-key cleanup. The marker
remained PRESENT across the tested lifecycle and became ABSENT after cleanup.
Screenshots were saved locally and visually inspected for readable labels,
selection and clipping. The record identifies source revisions, actual viewport
conditions and the early diagnostic-background cosmetic issue.
The final probe hides that background; affected screenshots were rechecked.
A distinctive public startup action launcher appeared on load and reappeared
after closing/reopening. The manually opened final probe then read PRESENT
before any write, with a new plugin instance; final cleanup read ABSENT.

**Limits:** automatic plugin bootstrap was not demonstrated; the tested direct
startup request reached a visible load error. The selected usable candidate
requires explicit interaction before storage/renewal. This does not satisfy
#12's direct-return goal. Unavailability was injected, not an actual browser
storage denial. The shared preview origin must never hold real renewal secrets.
No browser-process restart, TV, standby, clear-data, app-update, credentials,
operator-server request, certificate/trust change or TLS bypass occurred.

**Automated-tested on Windows / Python 3.12.14:** `uv sync --locked --extra dev`
succeeded; `uv run pytest`: **197 passed**, existing Starlette warning #30;
`uv run ruff check .`: passed; `uv run ruff format --check .`: **47 files already
formatted**; `uv build --wheel`: passed; `git diff --check`: passed. These checks
do not establish MSX integration; the observations
above come from the actual official runtime.

Independent final source/security/evidence review repeated all 197 tests and
Ruff/format checks and inspected final reopen/cleanup screenshots. It identified
an overly broad write-success claim; the research now explicitly distinguishes
thrown/injected failure from undetectable same-value silent writes. Retention is
supported by separate reopen-before-write evidence. No reviewer browser/server/
TV operation was performed.

## Synthetic integration prerequisite — issue #9

**Implemented:** [isolated synthetic lab and contract command](synthetic-testing.md),
using the unchanged production authentication/CSRF/routes and a strict mocked
Jellyfin transport with random login tokens. Synthetic original-file range delivery
and token revocation run only in the lab; no production media proxy or auth bypass.
Existing lab recorder accepts injected transport, defaulting to its real transport.
CI runs the contract command without external services or operator credentials.

**Automated-tested on Windows / Python 3.12.14:** `uv sync --locked --extra dev`
succeeded; `uv run pytest`: **197 passed**, existing Starlette warning #30;
`uv run ruff check .`: passed; `uv run ruff format --check .`: **45 files already
formatted**; `uv build --wheel`: passed. `uv run python -m tools.synthetic_check`
passed normal pairing, browse/poster/detail, original negotiation/byte-range
delivery, HD denial without another negotiation, disconnect/revocation and
re-pairing. Its temporary media bytes are not video. Deliberate `--fault json`,
`--fault playback` and `--fault csrf` executions each exited 1 at libraries-json,
playback and pairing, respectively; subprocess regressions assert those exits.
An initial test collection failed because repository tools were not importable
from pytest's entry point; explicit repository-root pythonpath fixed that check.
Independent review caught an invalid checksum in the initial PNG fixture; it was
replaced with an independently generated valid RGB PNG and a chunk/checksum plus
decompression regression. Byte equality alone had missed the invalid image asset.

**Browser observation:** connected Chrome extension rendered the native companion
form on loopback HTTP. Entering a dummy invalid code and synthetic credentials,
then clicking Pair this TV, displayed the expected pairing-failed message with
cleared fields. Local screenshot retained under ignored `.lab/reports/`.
This verifies form submission/denial only, not successful browser pairing or MSX.
No `browser-verify` tool/skill was available; the supported browser API was used.
The temporary HTTP process was stopped after inspection; no TLS trust was changed.

**Deferred / device-unverified:** no hosted-runtime fixture playback/rendering,
generated clip decoding, actual player pause/seek/Stop, browser fault verification,
fresh-environment browser command or public-CI browser execution is claimed.
The known Windows exact-leaf import limit was not retried; no new certificate,
trust, live account, real-server or physical-TV action was performed. Issue #9
remains open for its full browser acceptance. Real-server and physical gates stay
separate. The fixture is not an actual Jellyfin release-compatibility check.

## Multi-version source-pinning software milestone — issue #8

**Implemented:** detail playback actions now carry the selected `media_source_id`.
After checking current item authorization, the resolver validates that exact
stored version and pins it through PlaybackInfo and original-container delivery.
If it disappeared or became ineligible, playback fails before negotiation and
asks the user to reopen details. Legacy unpinned resolver calls retain current
selection. This corrects a real gap: two equally ranked versions could previously
switch when Jellyfin changed their order between details and Play, including a
different subtitle language at the same numeric index on optional conversion hosts.

**Automated-tested on Windows / Python 3.12.14:** `uv sync --locked --extra dev`
succeeded; `uv run pytest`: **186 passed**, one existing Starlette TestClient
deprecation (#30); `uv run ruff check .`: passed; `uv run ruff format --check .`:
**41 files already formatted**; `uv build --wheel`: passed. Seventeen added route regressions follow actual
detail actions across UHD + competing HD permutations, original MP4/MKV/AVI
delivery, reordered equal candidates, removed/ineligible pins, all-ineligible
groups, substituted PlaybackInfo responses, item denial and overlapping subtitle
indices. All automated transport is mocked. Independent source/test review found
no open blockers and independently repeated the full suite and Ruff checks.

**Official-browser renderer check:** official MSX 0.1.167 in the maintainer's
authorized Chrome extension session rendered the actual synthetic FastAPI detail
response. Private/media actions were replaced with harmless notices; clicking
the visible original-play row displayed its notice. This verifies rendering and
activation only. It is not live source delivery, video decoding or a TV pass.

**Deferred / device-unverified:** real grouped-media and physical Philips
acceptance remain open in #8. The configured public Jellyfin endpoint passed TLS
verification and identified version 12.4.0 without credentials. A first local
HTTPS dashboard rendered, but its MSX launch stayed at splash; native-window
inspection then hit a browser-control policy stop. On the resumed extension-only
run, the same explicitly approved temporary leaf could not be reinstalled:
Windows certificate-store API and certutil imports stalled and were cancelled.
No certificate dialog was observed, no TLS bypass was used, and no live credentials
were loaded or submitted. Final read-only checks found zero matching temporary
trust entries and no listener on the lab port. No live grouped-media, PlaybackInfo,
conversion, subtitle or physical-device result is inferred from these attempts.
The historical real playback evidence below belongs to the earlier environment.

## Hosting qualification research — issue #3

**Implemented:** [dated hosting decision and rollout runbook](hosting-qualification.md),
including official Ultra Python/systemd/port/HTTPS evidence, current public-service
policy constraints, unknown secret-injection/logging guarantees, and the source's
origin-only boundary. The selected application deployment shape is the existing
single-worker Compose/Caddy package on a controlled Linux host with a dedicated
HTTPS origin. No particular host was provisioned or production service started.

**Automated-tested on Windows / Python 3.12.14:** `uv sync --locked --extra dev`
with the bundled interpreter succeeded; `uv run pytest`: **169 passed**, one known
Starlette TestClient deprecation (#30); `uv run ruff check .`: passed;
`uv run ruff format --check .`: **40 files already formatted**; `uv build --wheel`:
passed. These commands used the existing uv executable from the development
checkout; no operator credentials or real Jellyfin requests were used.

An isolated subprocess loaded the newly built wheel unpacked into a temporary
directory (not the editable source) and served loopback HTTP. Health returned
the expected status/version/device-unverified fields; start returned the exact
HTTPS pairing URL, CORS for the official MSX origin and `no-store`. A configured
public path prefix was rejected. The process was stopped afterward. Initial
smoke-harness attempts incorrectly imported the wheel as a zip and expected CORS
without an Origin header / an exact Cache-Control string; correcting those harness
assumptions produced the pass. No product code changed. This is a Windows wheel
smoke, not the Linux Compose, public HTTPS or MSX runtime check.

Independent documentation review found no blocking findings, checked the official
provider/MSX sources and local configuration/packaging boundaries, and passed
`git diff --check`. The reviewer did not repeat browser, service or TV tests.

**Deferred / device-unverified:** production DNS/TLS/startup, chosen-host reboot
recovery, proxy error-path marker check, and actual TV HTTPS/start discovery.
No Docker CLI was available on PATH in this Windows ticket environment; the
historical Docker evidence below is not a new local execution. No browser form or
MSX application test was performed for this documentation-only milestone. Issue
#3 remains open for outstanding rollout/device verification; no hardware pass is
inferred from the automated suite.

## Earlier publication and integration evidence

Development is now tracked in [repository Issues](https://github.com/alexanderhetzel/jellyfin-msx/issues)
and the [Jellyfin MSX Project](https://github.com/users/alexanderhetzel/projects/5).
The current publication/setup work is [issue #2](https://github.com/alexanderhetzel/jellyfin-msx/issues/2).
This file preserves dated evidence; it is not a parallel backlog. See
`development.md` and `agentic-testing.md` for workflow and check selection.

Local publication checks passed: 169 tests, Ruff, locked package validation,
MIT/NOTICE/template presence in the built wheel, Compose validation, a Docker
image build, isolated container health/start/pair smoke checks as UID 10001,
and validation with the actual Caddy image. Caddy reported a formatting warning;
actual certificate issuance and failure-path log redaction remain deployment
work. Gitleaks found no leaks in the reviewed source and inherited Git history.
Remote Actions and main protection are verified separately during publication;
local checks alone do not establish them.

Routine agent pairing was also exercised with an operator-authorized test account:
credentials loaded only inside the test process from the local OS secret store,
normal GET/CSRF-protected POST to the companion form returned success, and actual
MSX Continue opened authenticated libraries. No password, token, account value or
activation code was written to source/reports. Credential submission in this run
used the normal HTTP form path, not native browser typing. No authentication
bypass or new product feature was introduced.

## Current M2a status: application testing in progress

### First real Jellyfin playback in official MSX web — 2026-10-30

**Browser video path passed:** fresh human pairing, real private-library access,
posters, details, PlaybackInfo, original-file playback, pause/resume, forward/back
seeking, Stop and replay. This used the integrated browser and official MSX
0.1.167 with the running `philips-32phs6605-12-hd-policy-v2` profile. The selected
source was an existing MKV with H.264 1280x720/8-bit and two E-AC-3 6-channel audio
streams. No file, account policy or real Jellyfin setting was changed.

Video observations: an actual frame rendered, time advanced from 4.3748 to
29.4338 seconds with readyState=4 and no media error. Pause held at 73.2087 across
separate observations; Play resumed. A forward jump landed at 116 seconds and
continued to 132.3544 with readyState=4. Rewind moved 136.2956 to 107, then resumed
to 121.5698 with readyState=4. Stop returned to details and left the video paused
at zero/readyState=0. Replay reached 9.0322 seconds at 1280x720/readyState=4 with
no error. Controls were operated through actual MSX DOM clicks, never by setting
video currentTime/play state from script.

Redacted lab observations corroborate two PlaybackInfo requests, both HTTP 200,
both Direct Play, EnableDirectStream=false, EnableTranscoding=false and subtitles
off. A separate existing oversized source displayed the 1920x1080 rejection and
no play control; PlaybackInfo count remained two. Back returned to the poster
list retaining the selected item's focus. The sanitized report is retained under
ignored `.lab/reports/msx-real-playback-2026-10-30.json`; it contains no library
titles/IDs, capability paths, media URLs or credentials.

**Still open:** audible audio was not independently verified by the available
browser tooling (the video was not muted). Physical Philips playback/audio,
remote arrows/OK, 1080p/HEVC variants, near-end and long playback, subtitle
delivery and populated series navigation remain unverified. A body ArrowLeft
automation action failed in the browser-control API; this is not evidence of an
MSX keyboard/TV-remote failure. Initial stale browser handles were recovered by
resetting only the automation binding; no service restart/re-pair was needed.
The paired MSX session and backend are retained for continuation.

### Current source profile — 2026-10-30

The user's device-specific research request supersedes the original assumed
720p/MP4/AAC-stereo gate. Current source uses
`philips-32phs6605-12-hd-policy-v2`, with cited exact-model and qualified
platform evidence in `philips-32phs6605-12.md`. It offers original-file candidate
trials, labels MSX verification as pending, warns about conditional Dolby/DTS
audio and preserves original-container stream URLs. It now enforces an explicit
HD-only client admission policy: width <=1920 and height <=1080. 4K playback and
downscaling are excluded; an eligible stored HD copy is required on Ultra. This
boundary is not presented as a proven MT9288 decoder maximum. The earlier
unrestricted-resolution candidate decision is superseded. No level, frame-rate,
stereo or default bitrate ceiling is invented. An explicit operator bitrate
budget is separate. Ultra conversion remains disabled.

The 4K correction passed **169 automated tests**, Ruff and format checks. Cases
cover oversized width/height across all advertised video codecs, cropped UHD,
4K-only detail/play routes making no PlaybackInfo request, and a returned 4K
source failing validation after an HD selection. The limit also applies with
optional transcoding enabled: the independent reviewer identified that fallback
bypass and verified its correction. Missing dimensions cannot bypass the policy
via HLS. The reviewer independently reran all 169 tests and Ruff/format checks
and found no open blockers. No reviewer browser/server interaction occurred.
The manufacturer service manual
identifies this model as TPM20.7E LA / MTK9288; the official TPV bulletin confirms
the chipset mapping. These sources establish identity, not an MSX 4K decode pass.
The actual FastAPI 4K-only detail response, with mock Jellyfin and harmless
replacement diagnostics action, was rendered in official MSX 0.1.167 in the
integrated browser. Clicking the rejection row displayed the HD limit, stored-copy
instruction and disabled-transcoding message, visually readable across two lines
at 1280x720. No play control was present. An initial incorrect inline launch
format produced a 404; switching to the documented `content:json:` start loaded
the fixture successfully. This is a renderer check, not upstream/video/hardware
verification. The existing real-server process was not restarted.

Before the 4K correction, **124 automated tests passed**, Ruff clean and 33 Python files formatted. New
tests cover the actual 720p MKV/H.264/E-AC-3/5.1 metadata shape, no conversion
flags, original `.mkv` URL, unknown numeric decoder limits, operator budgets,
conditional warnings and diagnostic redaction. An initial independent review
identified unsupported inferred container/audio mappings; these were removed.
Final follow-up review found no open blockers and independently reran all 123
tests and Ruff. A final huge-number metadata guard then passed the primary
agent's full 124-test run and the reviewer's seven focused tests. No reviewer
UI/server/hardware interaction was performed. Updated wheel build and Compose
syntax validation also passed.

The new detail JSON was generated through real FastAPI routes with mocked
Jellyfin data, with media/private actions replaced by harmless rendering notices,
then opened in official MSX 0.1.167 in the integrated browser. The model-specific
candidate row, trial label and clickable conditional-audio warning rendered.
This is a renderer check, not real Jellyfin playback or a physical-TV pass.

After the operator requested the next step, the real-server lab was restarted
on 2026-10-30 to load `philips-32phs6605-12-hd-policy-v2`.
Only the old companion success tab remained; no authenticated MSX tab was open.
The restart discarded old RAM sessions as designed. A fresh official MSX session
was opened in the integrated browser with a fresh companion GET and
pre-filled TV code. Human sign-in succeeded and the real playback run above
followed. The MSX tab must not be reloaded to preserve its active pairing.
Earlier policy denials below do
not establish incompatibility of the TV or of the operator's media.

### Historical runtime observations before the profile correction

The operator supplied and authorized their real Ultra.cc Jellyfin endpoint.
Its public API is reachable. Real companion sign-in succeeded and Arc showed
the success page, corroborated by redacted backend observations. The first actual
MSX library request returned 401: the old token header is removed in Jellyfin 12.
The client now uses MediaBrowser Authorization Token and canonical ApiKey for
native video URLs; strict mocked tests and independent review passed. Fresh real
sign-in after restart succeeded. The operator's screenshot now confirms the actual
Jellyfin libraries menu with movie/series entries and focus rectangle; a fresh
agent AX observation also read it. Library overview access is confirmed.
The earlier black agent capture was a capture/control limitation, not a confirmed
application failure. Direct DOM browser control subsequently traversed movies,
two detail pages, Back, library chooser and the empty series library. Two real
posters loaded and rendered. Both existing movies were rejected by the conservative
profile; the visible message explained the stored-version requirement and disabled
transcoding. No PlaybackInfo request was observed for these denials. The operator
was preparing a 720p test file. At that earlier stage no actual Jellyfin playback
pass had been observed and the then-active session was retained.
The initial form retry made no upstream authentication request. Real browser
reproduction identified a no-referrer/Origin:null conflict in native form POSTs.
The /pair page now uses same-origin referrer policy; private routes keep
no-referrer. A repeat native form submission passed CSRF and reached code
validation, without contacting Jellyfin. Pairing also has
explicit failure recovery and a separate success page. The local lab gives codes
30 minutes; the production default is still five minutes.

The official MSX 0.1.167 web runtime has actually been operated. It exposed a list
layout defect that was corrected and visually rechecked. Arc loaded the local
HTTPS pairing JSON after the operator approved localhost network access. In the
isolated browser, keyboard navigation started the official MSX sample video;
picture, advancing video time and pause were observed. Seek, actual Jellyfin
playback and all SAPHI decoding remain unverified. Details are recorded in
`msx-test-results.md`; the repeatable lab runbook is `msx-testing.md`.

Ultra transcoding and burn-in are disabled by default, including PlaybackInfo
flags and advertised profiles. Source selection searches all versions for a
compatible stored copy. The local lab refuses transcoding and non-loopback
origins, retains only redacted policy evidence, and excludes TLS files from Git
and Docker. Automated tests mock Jellyfin and cannot certify real MSX playback.

Checks at that earlier revision: `.venv/bin/pytest -q`: **113 passed** (one upstream Starlette
deprecation warning); `.venv/bin/ruff check .`: passed;
`.venv/bin/ruff format --check .`: 29 files formatted. Independent reviews of
pairing recovery and the subsequent referrer-policy fix found no blockers;
the reviewer reran all 113 tests and Ruff. Browser verification was performed
by the primary agent, not independently repeated by the reviewer.
The Jellyfin 12 header/URL fix also passed independent review and all 113 tests.
The later redacted HTTP-status counters passed an independent review and six
focused lab tests; they were not loaded into the process active at that earlier
stage. The current restarted run includes these counters, as shown above.
Updated wheel build (`UV_CACHE_DIR=/tmp/jellyfin-msx-uv-cache uv build --wheel`)
and Compose validation (`docker compose --env-file .env.example config --quiet`)
both passed on 2026-10-30.

Docker is now running and the official Jellyfin image was pulled; no local
Jellyfin container was started. Docker application build/start and Caddy TLS
runtime are still unverified. A temporary localhost leaf certificate was trusted
with the operator's approval for this active test; its trust must be removed
when testing finishes.
The earlier automation limitation was concrete: native Arc captures/AX could disagree,
AX reads sometimes omit content, and coordinate input returns no available window.
The operator confirmed a visible library menu, resolving the apparent black-screen
application failure. A separate paired browser tab with direct DOM clicks now
provides a working application test loop. Movie browsing, details, posters,
negative compatibility and Back cases passed. A 1366x768 viewport also rendered
the two posters, focus rectangle and metadata; the temporary override was reset.
At that stage eligible test media was the blocker. The current real browser run
above supersedes that blocker; no physical-device playback claim follows.

## Historical M1 verification — 2026-10-29

**M1 software milestone is implemented and automated-tested. It is not a
production-ready or hardware-verified Jellyfin client.** No real Jellyfin
server, credentials or physical Philips TV were available.

### Implemented and tested at M1

| Capability | Evidence |
| --- | --- |
| MSX start, pairing, home, paginated browsing, details, resolve, diagnostics | Actual FastAPI route integration tests with httpx.MockTransport |
| Companion browser authentication and one-time TV code | POST/CSRF/origin/code-expiry/rate-limit tests; password not persisted |
| Expiring bearer sessions, separation, logout during upstream failure | `test_portal.py` and `test_regressions.py` |
| Private poster retrieval and explicit user-item authorization | Denied item/image, image type/size and unknown capability tests |
| Movie → detail and series → season → episode links | Browser-independent navigation integration test |
| PlaybackInfo profile and Direct Play candidate | Body assertions and codec/resolution/bitrate/null metadata tests |
| HLS fallback including second negotiation and forced mode | Full route tests with real-server-style no-URL-until-forced fixture |
| Subtitle burn-in, no-subtitle source pinning, multi-version consistency | PlaybackInfo source/index assertions and detail-label regression |
| Malformed upstream/error/timeout handling, base paths and URL restrictions | Unit and endpoint tests, no external server calls |
| Request body protection | Actual/chunked requests and ASGI test proving early stop before parser |
| Redacted diagnostics, no-store, CORS without TV cookies | Route response assertions |

Executed on macOS arm64, Python 3.13.3:

```text
.venv/bin/pytest -q                 96 passed
.venv/bin/ruff check .              All checks passed
.venv/bin/ruff format --check .     24 files already formatted
uv build --wheel                   Passed; pairing template packaged
docker compose --env-file .env.example config --quiet   Passed
```

The suite currently emits one upstream Starlette deprecation warning about its
httpx-based TestClient. Tests pass; no warning is suppressed. `uv sync --extra dev`
installed locked dependencies. The sandbox blocked uv cache access, then `uv run`
hit a macOS system-configuration panic; checks ran directly from `.venv` instead.
Building the wheel required the permitted non-sandboxed execution path.

Browser verification used the actual localhost service with a deliberately
nonexistent Jellyfin domain and no credentials. Pairing form rendered at desktop
1280x720 and mobile 390x844. Mobile document width equaled viewport width (390),
all visible inputs/button were 352 px wide; no horizontal overflow, clipping or
console warnings/errors observed. These are form-layout checks only.

An independent review found and verified corrections for shared-state threadpool
access, nullable metadata, source/subtitle consistency, oversized form bodies,
protocol-relative media URLs, blank passwords and Caddy error-URI logging. Final
review: no open M1 code blockers; 96 tests and Ruff independently rerun.

### Unverified at the historical M1 checkpoint

- Actual MSX rendering, setup HTTPS discovery, focus/Back behavior and native player.
- Jellyfin authentication, REST shape and transcoding against an actual server release.
- H.264/AAC MP4, MPEG-TS HLS, subtitle burn-in, seeking and long playback on SAPHI.
- Docker image build/start and Caddy configuration/runtime/TLS issuance. Docker CLI
  exists, but daemon is not running. Compose syntax passed; Caddy runtime is untested.
- Proxy log exclusion in error paths: configured and reviewed against official docs;
  fake-marker outage test must run against the chosen Caddy image before deployment.
- Python 3.12 and Linux: CI matrix defined, not executed locally or remotely.

### Deferred at M1 (later profile/runtime work described above)

Automatic retry after a native decoder failure, audio/alternate-version selection,
native/external subtitles, HEVC Direct Play, watch progress/history, playback
resume, lifecycle event reporting, abandoned-transcode cleanup, automatic upstream
revocation on expiry/restart, persistent sessions and multiple workers/replicas.

Resolved video URLs expose the user's Jellyfin token to the TV player. A media
gateway is needed if that tradeoff is unacceptable. The backend does not proxy
video in M1. This is documented behavior, not a claim of item-scoped stream tokens.

Next gate: deploy to a controlled HTTPS host with the operator's server and run
`device-test-checklist.md`, recording results in `device-test-results.md`.
No production-compatibility claim is justified until those results exist.

No Git repository or remote existed at kickoff. No branch, commit, push, issue,
PR or external deployment was created; `git diff --check` is not available here.
