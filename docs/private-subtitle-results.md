# Private subtitle selection — issue #22 software evidence

## Accepted software/browser scope and limits

**Implemented / automated-tested / browser-tested / device-unverified.**
Independent final review maps all four original issue22 criteria to actual
official Chrome/MSX observations and mocked boundary tests: selected-source
Off/language/index choices, authenticated bounded delivery, sampled position/
seek/Stop behavior, and clear unsupported-track recovery without conversion.
The declared simple-cue subset is two explicit lines, at most32 display-budget
units per line; this is client policy, not a font/hardware/language guarantee.
Physical Philips/audio/remote/overscan verification remains in issue4.

This acceptance does **not** erase prior intermittent Data Load Errors or claim
a causal fix. The public document-marker comparison failed and was removed.
Its proposed extended test sequence was specific to that historical comparison,
not an additional original feature criterion or a zero-transient-errors promise.
Late native subtitle denial has no specific per-track notice; manual Off/Stop
and expired-video replay recovery were observed. Private capability URLs remain
bearer credentials; already delivered cue bytes cannot be recalled.

## Final unchanged-source observation at `e4e1ef97` — 2026-10-31

Exact `e4e1ef97ab0452fb2814e458563295479e548bd0` restores production/test source
to `0dc1688`. Official MSX0.1.167(web) in connected Chrome at1920x1080; one normal
synthetic pairing, no public-shell warming, reset, re-pair or source change.
Original600-second total/180-second startup bounds were preserved.

Initial healthy preparation, retained layout rejection and return to healthy
all completed in this run. The documented generic-body DOM read returned a
complete document, diagnostic output, both script elements and init1/all other
counters0 at each stage. These script elements are not independent execution
proof; the known initialization counter establishes the request was handled.
No Data Load Error occurred in this reproduction. Body reads preceded eventual
healthy UI; this is correlation, not proof of a tool or application fix.

One normal Back-to-details/reopen retained the exact full bridge URL and context
(equality checked in RAM, neither value saved). Init increased to2. The healthy
menu was not visible at a976ms sample and was visible by9355ms. This is a sampled
upper bound, not an exact load duration. Parent Network observation retained
three bridge HTML200/text-html responses; child script/preparation response
categories were not captured, and their absence is not proof of missing requests.

At11:05:55UTC explicit stop returned supervisor exit0/stopped. All nine recorded
owned PIDs/listener18092/control were absent; Network observation disabled,
viewport reset succeeded and both owned tabs closed. The session naturally
expired during cleanup Back, showing strict401; no logout is claimed. Fixed
safe categories/counters in ignored `issue22-body-read-diagnostics.json` and
menu capture `issue22-body-read-reopen.png` support this observation only.

The same independent reviewer accepted the four original software criteria with
these precise limits, correcting its earlier over-attribution of the removed
marker proposal's sequence. Historical passes and failures below are retained;
they are not superseded by a claim of fault-free runtime operation.

## Focused marker comparison failed at `6fad503` — 2026-10-31

Exact `6fad503b2bc74046d445414b645c9984092364ab`, one normal pairing in official
Chrome/MSX, no public-shell warming, reset or re-pair. Initial healthy preparation
succeeded, then the retained layout-rejected context succeeded. Returning to
healthy preparation again ended in Data Load Error. Read-only DOM confirmed
the bridge iframe had the new document marker. The later long-context and
same-cached-context stages were not reached. **The marker did not fix reopening**;
the hypothesis is not an established cause, and the ineffective change/regression
is removed from the candidate, restoring those files to exact `0dc1688` source.

The safe retained stage evidence establishes the visible failure after the
context switch, not whether the new bridge script, SDK init request, preparation
XHR/response or content callback ran. No counter snapshot from that failed frame
was retained. Earlier limited network samples do not fill this gap. The actual
failure boundary remains unisolated; this is not evidence of a platform-wide
unsupported operation or a successful fix. Existing first-party counters could
answer script/request dispatch if captured at the failed frame; no new diagnostic
infrastructure or further lifecycle variant is introduced.

At10:52:30UTC normal Back/home/Confirm disconnect showed Disconnected. Explicit
stop returned supervisor exit0/stopped, all nine recorded owned PIDs, listener
18092 and control directory were absent, and both owned tabs closed. The original
900-second total/180-second startup bound was preserved. Viewport reset was
unavailable while the document response was paused; closed tabs remove scoped
state, no reset-success claim. Ignored captures: `issue22-marker-reopen-failure.png`
and fixed-stage-only `issue22-marker-reopen-evidence.json`. Issue22 stays open,
PR65 draft/unaccepted; no additional public run or source variant is authorized.

## Simple-cue evidence at `0dc1688` — 2026-10-31

Exact `0dc1688b73abe4d30ad56d3787265fda2b2df2a1`, official hosted MSX/connected
Chrome at 1920x1080, strict fixed synthetic subtitles scenario and original
900-second total/180-second startup bounds. No source changed during this run.

Both the verbatim retained four-line/long-line fixture and the separate 33-W
single line showed Subtitles unavailable, with the fixed explanation of two
short plain-text lines and unsupported long/complex layouts. Play without
subtitles decoded1280x720 original video, readyState4/no media error, at8.062778
and4.684656 respectively. The explanation overlay consumed the first click;
the next normal activation started playback. No rejected text was truncated or
claimed to have rendered.

After those contexts, reopening healthy preparation produced Data Load Error.
Normal Back returned to details; normal Disconnect/Confirm showed Disconnected.
Public-start recovery and a fresh normal pairing, within the same relay budget,
allowed healthy preparation. **Reliable reopening remains unaccepted.**

Fresh-player DE18 loaded at paused5.93667. Its exact32-W first line and16-Han
second line were fully visible with left/right/bottom margins. EN12 selection
retained paused5.93667; native seek11 displayed EN B within8–16, lower-centred
with margin. Off retained paused11 and disabled all three tracks. These support
the tested simple-cue policy, not universal font/language/platform limits.

DE7 had never been selected in that player and remained native readyState0,
while EN12/DE18 were2. At natural session age248s, ordinary DE7 selection changed
it to3/error, still paused11 with no captions. Sanitized Network events included
a subtitle response401/application-json and a matching GET request, correlated
by the transient request ID in RAM only. The request buffer was truncated, but
the matching GET event was retained. No private URL/ID/header was saved. Bridge
totals after Stop remained init1/video1/subtitle3/fetch3/HTTP2003/URLcallback3/
denied0/null0: the denial was the **later native GET**, not a fresh bridge call.

No immediate per-track failure notice appeared; the normal player guidance to
choose a language or Off remained. This UX limitation is separate from the
observed authentication denial. Native Off disabled every track at the same11;
Stop returned to the menu, and expired video replay showed the persistent fixed
recovery page. Already loaded cue data is still not revocable.

At10:43:13UTC explicit stop returned supervisor exit0/stopped, all nine recorded
owned PIDs/listener18092/control were absent, and both owned tabs closed. CDP
disable/reset was unavailable while the document response was paused; closed
tabs remove scoped state, no reset pass claimed. First session was normally
disconnected; second naturally expired. No relay/budget extension or security
change. Captures: `issue22-fourline-rejected.png`, `issue22-fourline-original.png`,
`issue22-longline-rejected.png`, `issue22-longline-original.png`,
`issue22-simple-boundary-wide.png`, `issue22-simple-en-b.png`,
`issue22-simple-off-11.png`, `issue22-unused-expired-track.png`,
`issue22-simple-expired-recovery.png`; fixed numeric/sanitized categories only
in `issue22-simple-counters.json` and `issue22-simple-network.json` (ignored).

## Historical marker proposal — tested, failed and removed

The source generated identical bridge document URLs, varying only private
fragments. The [HTML navigation standard](https://html.spec.whatwg.org/multipage/browsing-the-web.html#navigate)
uses same-document navigation when URLs match except their fragment; the bridge
registers its SDK handler during initial script readiness. This supports a fresh
document discriminator as a comparison, but did not establish the vendor's internal failure
cause. Browser Use paused-response tooling remains a separate observation.

Issue22 defined the proposal before behavior: each generated detail action
received a public non-auth marker, with private context in the fragment.
The regression failed old source and checked distinct document URLs, unchanged
private fragments and no private access from the marker. The focused actual
comparison failed as recorded above; the ineffective source/test change was
removed. It is not a pending fix or an established cause.

The simple-cue admission policy was defined in owning issue #22
and [the resource contract](subtitle-resources.md): two short lines with a
conservative display-unit budget; reject whole unsupported tracks rather than
discarding or rewriting text/times. It preserves the failed fixture as an
explicit negative. Its actual boundary/wide-glyph, rejection/original recovery
and later unused native-fetch denial evidence is recorded at `0dc1688` above.
The broader feature remains unaccepted because reopening fails.

## Earlier HTTPS comparison at `3cee411` — 2026-10-31

**Implemented / automated-tested / partial browser-tested / device-unverified;
issue open, PR draft.** The single reviewed HTTPS comparison used exact
`3cee41185827a881009b42b079b4a3a13e3c61c6`, official hosted MSX in connected
Chrome, measured 1920x1080, normal pairing and the unchanged strict synthetic
subtitle scenario. Public readiness succeeded within 180 seconds; the total
supervisor allowance stayed 900 seconds. No source changed during the run.

| Actual action | Result |
| --- | --- |
| Start Off, pause, choose DE7 | HTTPS track source assigned; selected native track loaded (`readyState=2`). At paused5.305378, German umlauts and both lines visibly rendered with bottom margin. |
| DE7 → EN12 | Settled selection retained paused5.305378. Immediate reads sometimes preceded completion; the settled read establishes the switch. |
| Native seek forward | EN B rendered at10 seconds within8–16, EN C at20 within16–25; both lower-centred with visible margins, without the historical top-edge failure. |
| Rewind, choose alternate DE18 | At paused5, the distinct alternate source/index was selected. **Failed layout:** long second line did not wrap and clipped at the right; the fourth input line reached/clipped the bottom. No four-line/wrapping pass. |
| Off | At the same paused5, all three tracks disabled and a controls-free image showed no captions. |
| Stop, replay | Stop returned to subtitle menu. Replay decoded1280x720/readyState4 at6.875956 with all tracks disabled initially. |
| Completion / expired replay | Replay returned to the subtitle menu; no original video autoplay was observed. Subsequent replay after natural expiry showed persistent Playback unavailable/Pair again/Back, also after the temporary information notice disappeared. A late native subtitle GET racing expiry was **not exercised**. |

After Stop, own counters were init1/video1/subtitle3/fetch3/HTTP2003/URLcallback3,
unknown0/null0. After replay and expired replay: video3/subtitle6/fetch6/ok6/
URLcallback6/unknown0/null0. Counter handoff is an attempt, while actual caption
images/native loaded state establish this run's successful delivery. This
controlled comparison establishes data-URL rejection as the prior delivery
problem for the tested callback shape, not universal support for every URL kind.

At 10:24:17 UTC explicit stop returned supervisor exit0/stopped. All nine
recorded owned PIDs, listener18092 and control directory were absent. Viewport
reset succeeded and both owned tabs closed. The session had naturally expired;
no logout is claimed. No renewal, cache, proxy, vendor code change or security
override. Previously delivered cue bytes remain ordinary delivered data and
cannot be recalled; a native GET after preflight must still authenticate.

Ignored, secret-free captures: `issue22-https-de-a.png`, `issue22-https-en-b.png`,
`issue22-https-en-c.png`, `issue22-https-de18-wrap.png`, `issue22-https-off-5.png`,
`issue22-https-expired-recovery.png`; fixed numeric categories only in
`issue22-https-counters.json`. The alternate capture proves the failure, not
readability of its clipped text. No hardware/audio/remote/overscan result.

The admitted four-line/long-line subset is too broad for this actual runtime.
Any narrower fail-closed client policy must preserve all accepted text/times,
explain rejection and recover to Off/original, be documented as a client policy
rather than a decoder limit, and receive independent review plus an affected
actual Chrome check. No guessed numeric font/layout limit is accepted here.

## Historical resumed browser contract

The later explicit maintainer instruction is now connected Chrome for **all**
browser verification and media inspection. It supersedes the temporary IAB-only
pause recorded below. No IAB retry/fallback is needed. The original partial Chrome
evidence stays valid within its limits. Later source-pinned sections above
supersede the pending checks recorded during this historical preparation stage.

## Callback-dispatch evidence at `1497273` — 2026-10-31

The diagnostic-only run used exact
`1497273a7bda07b31153474fd83e55cf5ca3b42a`, normal pairing, official hosted MSX
in connected Chrome at 1920x1080, strict subtitle fixtures and a 600-second total
bound including the unchanged 180-second startup allowance. Normal public
readiness succeeded; no source changes or expiry repeat occurred during the run.

Before playback, the hidden first-party bridge counters were init1 and all
others0. After startup: video1, subtitle3, unknown0, subtitleFetch3, subtitleOk3,
subtitleDataCallback3, subtitleNullCallback0, denied0 and other0. This establishes
known subtitle dispatch, authenticated HTTP200 responses and attempted data-URL
callback handoff. It does not prove native acceptance or rendering. After a
second playback start, DE7 then EN12 selection and Stop: video2, subtitle6,
fetch6, ok6, dataCallback6, unknown0/null0. Active-player counter reads sometimes
timed out; the final after-Stop read succeeded. No exact per-selection delta is
claimed. German and English each had native track readyState3 and opaque-ID src,
at the same paused 4.346121. Captions and layout still failed.

At 10:15:36 UTC normal Disconnect/Confirm showed Disconnected; viewport reset
succeeded, both owned tabs closed, explicit stop returned exit0/stopped, and all
nine recorded PIDs/listener18092/control were absent. The original 600-second
bound was preserved. Only fixed numeric categories were saved in ignored
`issue22-dispatch-counters.json`; no IDs, URLs, cue text or credentials.

This evidence justifies one minimal next comparison: return the fixed absolute
authenticated HTTPS subtitle URL through the same callback object, after the
same preflight. Published HTML5X documentation promises HTTP/HTTPS URLs and IDs,
not data-URL results. The native player must authenticate its subsequent GET
again. Expiry/revocation between preflight and that GET can still deny playback;
there is no hidden renewal or cache, and already delivered cue bytes cannot be
recalled. This comparison is not a caption pass and does not yet establish that
URI type rather than payload shape caused rejection.

## Diagnostic run at `2473dbb` — 2026-10-31

**Partial browser evidence; caption delivery failed.** Exact source
`2473dbbfae23914ad7d2c2129706e622b93b275b`, official hosted MSX in connected
Chrome at measured 1920x1080, same strict synthetic subtitles scenario and
unchanged 900-second/180-second startup bounds. Initial public DNS resolution
failed; normal readiness succeeded within the bound. Public bridge-shell
navigation without a fragment preceded prompt first preparation in two normal
pairings; it remains a correlation, not a proven startup fix.

Playback initially displayed `Track URL is missing or invalid`. DE7 at paused
12.924185 and EN12 at paused 15.549597 selected the expected native track, but
each selected track had `readyState=3` and its DOM `src` attribute remained the
opaque subtitle ID. No caption rendered. This does **not** distinguish a rejected
data URL from missing dispatch or a response-contract mismatch. The sanitized
top-tab response sample captured only bridge HTML 200, not subtitle requests;
absence in that limited sample proves neither dispatch nor lack of dispatch.
Data-URL delivery, placement, umlauts and wrapped/four-line layout have no pass.

Off disabled all three tracks at the same paused 12.924185; Stop returned to
the subtitle menu. Missing and malformed fixtures each showed Subtitles
unavailable, and Play without subtitles decoded actual 1280x720 original video
at 2.931524 and 4.60287 seconds respectively (`readyState=4`, no media error).
After visiting those sources, reopening healthy preparation stalled into Data
Load Error. Ordinary Back at session age 241 seconds showed the strict 401
expired-session explanation. Public start and a second normal pairing recovered.

In the second session, Stop retained the loaded subtitle submenu. At natural
session age 246 seconds, replay showed the persistent Playback unavailable page
with Session expired or video unavailable, Pair again and Back. Pair again
opened a fresh public pairing page. This **passes that video-resolver expiry
recovery path**, not late subtitle-fetch recovery or the whole issue.

At 10:07 UTC explicit stop completed with supervisor exit0/stopped. All nine
recorded owned PIDs, listener18092 and control directory were absent. Both owned
tabs closed. CDP disable/viewport reset was unavailable while the document
response was paused; closing the owned tabs removes their scoped diagnostic
state. No successful viewport reset is claimed. No timer extension, new relay,
operator/Ultra account, vendor modification or security override.

Ignored synthetic captures: `issue22-dataurl-track-failure.png`,
`issue22-missing-original.png`, `issue22-reopen-load-error.png`, and
`issue22-expired-playback-recovery.png`. Only the last captures the successful
native expiry recovery. The next diagnostic candidate preserves the data-URL
callback unchanged and adds bounded, frame-local numeric counters for known
request categories, subtitle XHR status categories and callback settlement.
No IDs, context, URLs, subtitle text or raw errors enter those counters. This
must establish actual dispatch before considering a URL-type comparison.

## Resumed Chrome run — 2026-10-31

**Partial browser evidence only; issue open / PR draft.** The bounded run used
exact committed head `2f4189fad53e68460a60c636543abb2fa03b5eb5`, strict synthetic
subtitles transport and the original 900-second supervisor bound. Connected
Chrome used the official hosted MSX runtime and a 1920x1080 viewport. Two normal
synthetic pairing flows reached private libraries, movies and source-pinned
details. The first session was normally disconnected before the second pairing.

The interaction frame initially stalled after its HTML response, without an
observed script/preparation request. A fresh owned MSX tab had the same symptom.
Opening the public bridge shell without a capability fragment in the companion
tab preceded the pending preparation appearing about 187 seconds after pairing.
This is a correlation, not an established startup fix. Raw CDP reported a paused
document response; no Fetch, debugger, security or vendor-runtime override was used.

Actual playback decoded 1280x720 video (`readyState=4`, no media error) at
27.966928 seconds. All three subtitle tracks were disabled, confirming default
Off. Natural completion returned to the subtitle menu at item 1/4, rather than
advancing to the original-playback item. **No subtitle was selected in this run**;
the data-URL handoff, new cue placement and wrapped/four-line rendering remain
unverified. Historical caption observations below used the earlier URL handoff.

After the synthetic session's natural 240-second lifetime, replay displayed
`Video URL is missing`, overwriting the bridge's fixed information notice.
This is a failed expiry-recovery criterion. A subsequent source-only recovery
candidate uses published native content/panel actions; it was not loaded or
tested during this run. Node guards do not establish its actual ordering against
the native error message. The ignored capture
`issue22-natural-expiry-replay.png` records this synthetic warning only.

At 09:41 UTC the supervisor exited 0 with `stopped`; a stop request found no owned
run. All nine recorded owned PIDs, the port 18092 listener and control directory
were absent. Both owned tabs were closed and the shared slot released. The second
session had naturally expired; no second-session logout is claimed. No lifetime
extension, detached helper, new relay, real server or operator credentials.

The earlier data-URL candidate used HTML5X's documented non-HTTP subtitle IDs. On a subtitle
resolver request, the first-party bridge validates the existing authenticated
resource through same-origin XHR, then supplies its already-authorized bytes as an
in-memory `text/vtt` data URL. Fresh denial/missing/type/size failures show a fixed Off/Stop recovery notice;
no timer, renewal, persistence, arbitrary URL or online proxy is introduced.
This callback/data-URL behavior must be tested, not inferred from Node guards.
The data URL avoids a second native bearer fetch after validation. FileReader/Blob
support is feature-detected; unsupported clients get the fixed failure without a
bearer-URL fallback. One-MiB server output expands to at most1,400,000 data-URL
characters, with another context check after asynchronous conversion. Strict
resource denial is preserved. Already delivered captions cannot be recalled.
There is no persistence; decoded player tracks are ordinary delivered cue data.
Only the trusted synthetic subtitles scenario has a fixed
240-second session lifetime to exercise natural expiry within a 900-second run;
production settings and other scenarios are unchanged.

## Historical preparation pause

**Implemented / automated-tested / device-unverified; not accepted for merge.**
The private menu/bridge has partial actual connected-Chrome evidence. The later
fixed-layout candidate has no browser pass. The latest maintainer replacement
requires the integrated browser for further testing; its documented launch is
unavailable, as reported by the master after the next worker's fresh attempt.
No Chrome fallback/repeated unavailable launch. Issue #22 stays open; PR draft.

## Source and environment

The run used local implementation `5376a9d7be24123d5d40faafcc257acb573b889f`.
Its production source is unchanged in rebased
`6ef403c1adc592194dcee82cb2bd255b1af4693c`; rebase retained #7's navigation
dispatch and fixed item-media allowlist. Post-run generated cue settings/output
size rejection and explicit completion/next/previous policy need IAB verification.

2026-10-31: official unmodified MSX **0.1.167**, `https://msx.benzac.de`, connected
Chrome extension, inventory profile **Mein Chrome**, measured **1920x1080**.
Browser version was not independently reread. This is Chrome, not IAB/Philips,
isolated cookie-context, audio or live-Jellyfin evidence. Two worker-created tabs;
approved bounded synthetic HTTPS supervisor, strict MockTransport, committed
1280x720/30-second generated clip and fixed external VTT cues. No operator
configuration/account/credentials/media/renewal store or network fallback. Initial
public-name resolution failed; normal readiness later succeeded within the
original budget, with no DNS/TLS/security change. Vendor runtime/library stayed
hosted and unmodified; only published APIs were used.

## Actual actions before browser-policy replacement

| Action | Observed result / limit |
| --- | --- |
| Own TV code, normal synthetic sign-in, Continue | Sign-in succeeded, private libraries/movies/source-pinned details displayed. Click already activated Continue; an extra Enter found no old control. |
| Subtitle detail action | Own-origin interaction bridge returned preparation page. HTML5X constant `id=portal-video`, no token-bearing vendor URL query. Frame media read:1280x720, readyState4, error null. |
| Initial playback/panel | Real moving frame; encoded22.5s screenshot had no captions. Panel showed Off checked, DE7, EN12 and alternate DE18 as distinct choices. |
| Pause / DE7 | Settled **3.15736**, paused true; German umlauts/two-line A visibly rendered. Four sanitized browser response observations across selections: private subtitle category, **200**, **text/vtt**. Browser headers were not recorded; header guarantees remain separately mocked checks. |
| DE7 → EN12 / seek | Same paused **3.15736**, English mode showing. Actual forward controls moved to **8** then **13**; EN B screenshot matched its8–16 interval. |
| Placement failure | DE second line touched bottom; EN B after paused seek was **top-edge flush**. Stable placement/safe margin is **not accepted**. |
| Alternate DE / rewind / Off | DE18 eventually showing, others disabled; rewind settled8. Off removed visible language indicator while UI still displayed8. No separately settled cue-free image retained. Immediate reads sometimes preceded completed actions; later reads underpin these results. |
| Natural completion during inspection | Advanced into separate Play without subtitles item(2/4). Eject/explicit replay recovered. Later completion override is unverified; no desired-mode-retention pass. |

Native cue lists did not serialize through the supported read-only DOM scope;
screenshots establish text, not inferred cue-array contents. Raw CDP frame/media
inspection was temporarily unavailable while Browser Use resolved a paused
document response; supported frame-locator media reads worked. Hidden-control/
body-key attempts timed out; fresh visibility checks and actual control clicks
worked. The documented input wrapper performed Escape. No DOM/media setter,
vendor-internal call, runtime script modification or security bypass.

## Cleanup and unchecked criteria

After the replacement instruction, only cleanup continued: Stop, Back to normal
private home, Disconnect TV/Confirm; Disconnected observed. Both owned tabs
closed. Network observation/temporary viewport override were cleared before
closing; no later Chrome test/final viewport measurement. Closed tabs remove
their CDP state. Supervisor exit0/stopped; all **nine** recorded exact owned
helper/vendor/console PIDs, listener18092 and control directory absent. Original
900-second bound preserved; no detached helper or browser/security change.

Missing/malformed notice → original playback, denied/expired/cross-session
resource UI, delayed track-error notice, full active timing/Stop/replay and new
layout are **unchecked in IAB**. Mocks do not fill these gaps. Physical Philips/
remote/overscan remains #4. Platform unavailability alone creates no new human
input gate.

Ignored local captures: `issue22-track-panel.png`, `issue22-private-de-a-clean.png`,
`issue22-private-en-b-13.png`; earlier default/controls-overlaid views prove only
their named partial state. `issue22-private-network.json` retains category/status/
MIME only. No retained pairing codes, private fragment/resource/media URLs or
raw QR pixels. All screenshots contain only synthetic media/menu labels.

## Generated layout candidate — pending connected Chrome

Upstream cue settings/markup/STYLE/REGION remain rejected. After validation, only
the fixed `line:70%,end position:50%,center size:90% align:center` is added. The
[WebVTT grammar](https://www.w3.org/TR/2026/CRD-webvtt1-20260520/#webvtt-cue-settings)
supports these settings; timestamps/text stay unchanged. This is no rendering
pass. Wrapped/four-line cues need actual coverage too; text bounds do not promise
every cue fits. Input and generated UTF-8 output are each at most one MiB. Review
found added settings could exceed that limit on valid9000-cue input; explicit
output rejection and regression now cover it.
