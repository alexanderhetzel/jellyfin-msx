# Playback recovery — issue #23

**Implemented / automated-tested / partially browser-tested / device-unverified.**
This is a partial software milestone. The original native decode/timeout/network
distinction criterion remains unmet where the published native interaction API
does not expose a reliable cause. The issue must remain open; a passing mocked
category test is not native failure evidence.

## Evidence and diagnostic boundaries

The official [Plugin API Reference](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference),
[attached-data examples](https://msx.benzac.de/wiki/index.php?title=Attached_Data_Examples)
and [public declarations](https://msx.benzac.de/ts/tvx-plugin-module.min.d.ts)
were read on 2026-10-31. Video samples expose state, position, duration, speed and
ended; documented events contain no typed native media-error code. Generic
handler `onError` is documented for debug evaluation without a native error
schema. No vendor implementation was copied or inspected for this change.
The [earlier actual offline observation](msx-lifecycle-research.md) showed that a
generic unsupported-source notice can also accompany a network fetch failure.

| Fixed category | What establishes it | What it does not establish |
| --- | --- | --- |
| `negotiation_denied` | Selected-source or PlaybackInfo denial before a stream URL is released | A decoder failure |
| `upstream_timeout` | Portal HTTP transport timeout while contacting configured Jellyfin | A native media timeout |
| `upstream_connectivity` | Portal HTTP network transport exception | TV network status or a decoder limitation |
| `portal_timeout` / `portal_connectivity` | The interaction plugin's own start XHR timeout/error | The native player's media failure cause |
| `app_connectivity` | Received, generation-correlated published `app:disconnect` observation | Proof a particular media request failed |
| `native_unknown` | User explicitly requests recovery without a supported native cause signal | A detected failure, decoder diagnosis or timeout |
| `authorization`, `request_limited`, `request_failed`, `request_timeout` | Fixed authentication, rate, protocol/schema or portal-deadline boundary | Any inferred native cause |

Server diagnostics retain only bounded fixed categories, random diagnostic IDs,
status and alternative counts. Client XHR categories appear in the recovery UI;
they cannot be uploaded during an outage and are not advertised as persistent
server diagnostics. No raw error string, title, source/item ID, URL or credential
is added. Missing callbacks, zero duration, paused/stalled video and automation
timeouts never become decode/network categories or trigger automatic playback.

## Remote-operated recovery contract

The preferred original-with-progress page always offers recovery, Stop and Back
to details. Its native player content button opens the same MSX-rendered recovery
page. A failed portal start shows a fixed category and explicit Retry. Native
failure recovery is manual: dismiss any native notice, return to content and
choose recovery. Subtitle and legacy original paths retain their existing scope.

Recovery fetches fresh item metadata through an authenticated, same-origin,
body-limited POST. Up to eight distinct alternatives are offered only when they
pass the unchanged original-file candidate/HD/bitrate checks. The original source
is excluded; a failed catalogue request says the choices could not be checked,
not that none exist. Stored candidates are labelled unverified. Choosing one pins
its exact source for fresh item-access and PlaybackInfo validation; it never
automatically switches, converts, burns subtitles or changes credentials/origin.

There are at most three explicit play attempts per loaded context, including the
first attempt. There is no automatic playback retry loop. A deliberate return
through details and fresh `init` resets that budget, including cached same-fragment
plugin reentry. Existing finite observation-upload retries are separate.
The rebased candidate orders public `quiet` before `video:resolve` for every play
row, rather than stopping from inside an already pending resolver. Back also
uses `quiet`, which avoids the documented no-media info notice. This sequencing
change has the scoped successful focused runtime evidence below; the earlier
failure and causal limitation remain separately recorded.
Back invalidates pending start/catalogue responses so they cannot reopen playback
or recovery. No reliable Stop callback is inferred: disposal can leave the server
to close the generation at its last safe position under the existing 45-second
lease, with `Failed=true`. Replacement still requires the previous server Stop
acknowledgement before a new reporting grant is published. No lifecycle state
machine, completion, profile, session, auth or token-origin boundary is widened.

## Verification and remaining acceptance

Local checks on 2026-10-31: `uv run pytest -q` **491 passed / one POSIX skip**;
`uv run ruff check .` passed; `uv run ruff format --check .` **102 formatted** on final recheck;
the three Node client suites **50 passed**. The locked dev environment was synced
with the existing Python 3.12.14 interpreter. An initial bare `uv run` could not
resolve a stale global Python link; explicitly selecting that interpreter and
syncing locked dev extras resolved local tool setup without dependency changes.
The offline wheel build and exact wheel/source manifest check passed (25 entries),
as did `uv run python -m tools.synthetic_check` (HTTP-only, browser/device false).

Regressions cover observed server categories/redaction, authorized fresh
alternatives and denied/oversized/missing metadata, no negotiation during lookup,
early body/origin/schema/auth denial, generic protocol errors, bounded play
attempts and uploads, same-context reentry, stale Back/start/catalogue callbacks,
aborted callback settlement and invalid successful start payload recovery.
The #18 lifecycle replacement/last-safe/security tests remain green.

The prepared `recovery` synthetic HTTPS scenario uses only strict mocked Jellyfin,
normal pairing, fixed authenticated sources and checksum-pinned RAM media. One
source returns fixed non-media bytes; its eligible stored alternative returns
the reviewed clip. Other items deterministically deny or fail negotiation by
timeout/network exception. It adds no public fault controls, real transport,
operator configuration, TLS override or relay-supervision change.

## Actual partial Chrome run — 2026-10-31

One master-granted run used unchanged `b650974c0d5895dbadc946f90c9a45a798955f6b`,
official MSX 0.1.167 web and connected Chrome. It used the normal code-check and
credential pairing form with the isolated synthetic account, then the actual
library/details/preferred playback controls. No CDP, network/viewport override,
real Jellyfin, operator media, production deployment or hardware was used.

| Actual UI/media observation | Separate sanitized request evidence | Result |
| --- | --- | --- |
| Negotiation denial rendered the fixed category, Retry and Back. Three attempts led to `Play attempt limit reached`. | Exactly three denied PlaybackInfo requests at this stage. | Scoped denial/attempt cap observed. Native `Video URL is missing` warnings also appeared; a click while a notice was active could dismiss it without executing the row. |
| Back returned usable details; reopening displayed a fresh Play control. | Later authorized item requests; saved notes retain the actual UI transitions. | Reentry observed. Repeated native Back traversed the accumulated content history; no claim of a short history stack. |
| The non-media source produced a native unsupported-source notice. Safe read: time0, paused, readyState0, dimensions0, duration/error unavailable. | One authenticated unplayable-media GET. | Expected native rejection; cause remains unknown to the production interaction API. Notice URL was stripped before text output, and the notice was never captured as an image. |
| Manual recovery displayed `native unknown` and a stored-alternative control; the actual control was selected. Separate later media reads stayed time0/paused/readyState0/dimensions0. | Five total PlaybackInfo HTTP200 responses (three denied, failed native source, attempted alternative); no original-media GET and no lifecycle Start/Progress/Stop. | **Alternative playback blocked; no decoded frame or advancing time.** Successful negotiation does not establish playback. |

The run stopped at that first functional blocker. Visible Stop was selected and
both owned tabs closed. Supervisor stop returned exit0 at14:33:01UTC; all nine
recorded owned PIDs, listener18092 and control directory were absent. No new run,
budget or midrun source variant followed. Three secret-free JPEGs, fixed-counter
JSON, sanitized numeric/action notes and cleanup JSON remain in ignored
`.lab/reports/issue23-*`. A keyboard locator deadline is a tool limitation; it is
not a player/network failure. No TV/audio/remote pass follows from pointer controls.

Independent evidence review found the images readable and secret-free and
confirmed no alternative media request/frame. The original diagnostic distinction
remains unmet; active-playback cleanup/replay was not reached in this run.

## Rebased candidate and focused verification boundary

After cleanup, #19 merged as `e21d103`. The candidate preserves its strict resume
boolean, fresh source-bound start ticks, validated `start_position` and derived
native `resume:position`. A chosen alternative explicitly sets resume=false,
force=false and subtitlesOff; a nonzero returned offset for that fresh source is
rejected rather than inheriting item-wide saved progress from another version.
Resume and Start over labels remain distinct. Both resume and recovery synthetic
scenarios, source helper changes, docs and tests are retained.

Bounded source diagnosis found an actual sequencing hazard: the old handler
issued public `player:stop` while its `video:resolve` response was still pending.
Stopping/ejecting during resolution is a plausible explanation for a negotiated
alternative with no subsequent media request, **not a proven runtime cause**.
The public [ordered actions and quiet contract](https://msx.benzac.de/wiki/index.php?title=Internal_Actions)
support moving the stop before resolution. Regression checks enforce that no
ejection occurs inside the pending resolver and that alternatives start at zero.
The [main action contract](https://msx.benzac.de/wiki/index.php?title=Actions)
requires playback properties in action-related `data` for ordered actions;
the candidate places completion/next/previous/recovery-button properties there.
No vendor internals were inspected or new infrastructure added.

Rebased checks: full pytest **528 passed / one POSIX skip**; all **55 Node** tests
passed (38 lifecycle,12 subtitle,5 browser guards). Current lint/format/build and
independent union review are recorded with the candidate PR head. A focused rerun
requires a new master grant and exact reviewed head. It must verify explicit
alternative selection actually reaches original-media GET, decoded advancing
frames and safe Stop/Back/replay; it must not manufacture native cause signals.

## Focused candidate run — 2026-10-31

A separate explicit master grant authorized one run of unchanged
`06a297ebf8df330001f18a3c1a9a3b6bcf54fd9d`, after the prior run's verified cleanup.
Normal pairing and authenticated library/details entry succeeded. The source was
not modified during the run. Official MSX remained 0.1.167 web in connected
Chrome; no raw CDP, network/viewport override, media state setter, native callback
injection, real server or operator data was used.

| Actual UI/media observation | Separate sanitized request/report evidence | Result |
| --- | --- | --- |
| Native non-media source displayed unsupported-source notice; two native Back actions returned usable content. Manual recovery showed `native unknown` and an eligible stored alternative. | One non-media native GET. | Expected rejection and explicit recovery choices observed. URL was removed before text output; no error-notice screenshot. No native cause code inferred. |
| Selecting the alternative displayed the generated test pattern. Native read moved from time0/readyState1 to2.669199/readyState4,1280x720,duration30,playing/no error. | First original-media GET; authenticated Start and advancing progress followed. | Actual stored-alternative video playback observed. No audible-audio/TV claim. |
| Real Pause held time24.1604 across separate reads, readyState4. Native eject returned recovery content and video time0/readyState0/dimensions0. Back to details was usable. | Before replay: Start1,Progress7,Stop1,last safe24 seconds,paused=true,Failed=true,active=false. | Pause/explicit Stop/Back observed. The reset native zero was not reported as lost progress or successful completion. |
| Fresh preferred context offered the same alternative; explicit selection replayed from0.017982 to2.987993,readyState4,1280x720. Native eject again returned video time0/readyState0. | Final: three PlaybackInfo200,one non-media GET,two original GET; Start2,Progress9,Stop2,last safe19 seconds,Failed=true,active=false. All negotiation flags retained original/DirectStreamOff/conversionOff/subtitlesOff. | Fresh-generation replay and bounded prior-session cleanup observed. No repeated bad-source attempt, profile expansion or automatic fallback. |

Four secret-free JPEGs show decoded playback, held pause, usable details and
replay. Fixed aggregate JSON and safe numeric/action observations are retained
under ignored `.lab/reports/issue23-run2*`. The first companion DOM read timed out;
the already successful paired session was corroborated by the backend and actual
libraries. A Pause selector initially missed autohidden controls; a real video
click revealed them, then the native Pause was used. These are tool/control
visibility limitations, not media/network diagnoses. The native player overlay
uses the generic resolver request label; no title/label polish is claimed.

Both owned tabs were closed; explicit supervisor stop returned exit0. At
14:43:57UTC all nine recorded PIDs, listener18092 and control directory were absent.
No further run or budget was started. This run supports the declared recovery
subset but does not prove the exact causal explanation of run1 or universal
recovery. Native decode/timeout/connectivity distinction still lacks a supported
API signal and remains unmet in the original issue.

Original four-criterion mapping: diagnostic distinction **partial** (native cause
unavailable); remote recovery/alternatives **observed for the declared synthetic
subset on the focused candidate**; finite retries/cleanup **automated-tested,
attempt cap observed in run1 and active Stop/replay observed in run2**;
no Ultra conversion/alternate-origin credentials **preserved and automated-tested**.
Physical Philips, audio, hardware remote and OS connectivity remain deferred to
#4 and related device issues. No full #23 acceptance or merge readiness is claimed.

Final independent source/security review found no remaining blocking findings.
It independently ran the full 491-pass/one-skip suite and latest 72 affected
Python/50 Node checks, plus Ruff/format/diff. Review found and verified corrections
for stale Back callbacks, same-context attempt reset, malformed-success recovery,
protocol-error classification and immediate aborted-catalogue callback settlement.
After rebase the independent reviewer reran exact candidate528-pass/one-skip,
55 Node, Ruff/format106/diff checks and verified the #19 source/resume/fixture
union and ordered-action data placement. It inspected all four focused-run
images and numeric/action/request/before-replay/cleanup JSON and accepted the
declared manual-recovery/control/cleanup/policy subset. The native cause
distinction remains unmet; network loss/native timeout/TV/audio/hardware remote
were not tested. No reviewer browser or relay operation occurred. PR69 remains
a partial draft; no full acceptance or merge readiness is claimed.
