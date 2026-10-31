# Private subtitle UI: partial evidence and resumed Chrome acceptance — issue #22

## Resumed browser contract

The later explicit maintainer instruction is now connected Chrome for **all**
browser verification and media inspection. It supersedes the temporary IAB-only
pause recorded below. No IAB retry/fallback is needed. The original partial Chrome
evidence stays valid within its limits. Final connected-Chrome placement, natural
expiry, failure recovery and Stop/completion acceptance is still pending.

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

The resumed candidate uses HTML5X's documented non-HTTP subtitle IDs. On a subtitle
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
