# QR companion pairing — issue #14

## QR-first activation layout — issue #16, 2026-10-31

**Implemented / automated-tested / browser-tested / device-unverified.**
The native 12x6 page gives the QR a four-by-four area, followed by an explicit
"or" manual alternative: the configured companion hostname plus `/pair`, a
grouped code, validity and a short code/sign-in instruction. The own-TV scan
instruction stays beside the QR. Only Continue after pairing and Create new code
take remote focus. Nonselectable native `space` items keep instructions and code
bright without extra focus stops. No arbitrary HTML/CSS, external URL shortener,
QR service, vendor artwork or runtime copy is used.

Continue now uses the capability-bound `pairing.json` route. Pending sessions
retain the same QR/code instructions under Waiting for pairing; paired sessions
reach authenticated libraries. Missing/expired grants receive only a public
Pairing or session expired screen with one Create new code control, never a code,
QR or library. The existing private `home.json` still denies invalid grants with
its 401 response envelope. State is refreshed on Continue; there is no automatic
polling/countdown or implicit authorization from scanning. The companion's normal
TV paired success message remains the instruction to Continue on the TV.

The historical public waiting exporter deliberately uses the code-free pending
`home.json` view. It does not export the new QR-bearing waiting page. Committed
public fixtures remain byte-for-byte consistent and secret-free.

Actual verification used connected Chrome on Windows and official unmodified
MSX **0.1.167 web**, measured **1920x1080**, through the approved isolated synthetic
HTTPS supervisor (each run at most 900 seconds including startup). No operator
configuration, credentials, media or real Jellyfin/Ultra server was used.

- A first native disabled teaser dimmed the code to 25% opacity. Actual rendering
  exposed this problem; the final native space has full-opacity white code text.
  Read-only DOM measurements found a 44px-high code line at this viewport.
- The final rendered QR occupied 552x552 screenshot pixels and independently
  decoded in RAM to the intended synthetic-origin pending activation URL. Opening
  it reached clean `/pair`, blank credentials and no manual-code field.
- Native Return on Continue before sign-in displayed Waiting for pairing with the
  same usable QR/manual instructions. Normal synthetic credentials displayed TV
  paired; native Continue reached Jellyfin libraries / Synthetic movies. Scanning
  alone did not authorize libraries. Own-session Disconnect was confirmed normally.
- Native Right selected Create new code with the visible white frame; Left
  returned to Continue. Grouped manual code entry reached clean blank sign-in.
- That device remained pending through its original five-minute lifetime. At
  313 seconds, native Continue showed Pairing or session expired with only Create
  new code. Reopening its decoded QR showed clean manual recovery without
  credentials. Native Return on the retry control produced a different grouped
  code; normal manual entry, credentials and Continue reached private libraries.
  The settled final library screenshot was inspected and retained.

QRs, codes and decoded activation links stayed in process memory. Only masked or
secret-free screenshots were retained under ignored `.lab/reports/`. Browser
snapshots were redacted before output. One initial pre-readiness load displayed
Data Load Error; a normal reload after verified HTTPS readiness recovered. Early
loading/outgoing screenshots were not accepted as settled evidence. A locator
wait timed out despite its diagnostic reporting the visible success text; a
fresh native state confirmed TV paired. The generic `browser-verify` command was
unavailable; supported connected-Chrome actions and inspected screenshots supplied
the form evidence. HTTP privacy/denial properties are separate mocked regressions.
For natural-expiry Continue and manual-recovery Continue, browser Network response
events were reduced in RAM to a fixed pairing-status route category (grant omitted),
HTTP 200 and `application/json`. Those two sanitized observations are retained;
no raw browser request trace or media/audio result is claimed.

Settled ignored captures: `issue16-final-pairing-redacted.png`,
`issue16-final-waiting-redacted.png`, `issue16-final-new-code-focus-redacted.png`,
`issue16-manual-signin.png`, `issue16-companion-success.png`,
`issue16-companion-expired.png`, `issue16-msx-expired.png` and
`issue16-final-manual-libraries.png`. Fixed-field browser response evidence is
`issue16-request-evidence.json`. The separate earlier `issue16-qr-libraries.png`
is an outgoing/masked frame and is not retained-library proof. The initial
pre-correction capture is historical only. QR/code pixels remain masked even in
reviewed captures; decoding/full-opacity/grouped-value observations come from the
implementation agent's in-memory screenshot/DOM inspection, not the masked image.

Both own paired sessions were disconnected through normal confirmation. The two
created tabs closed, Network observation stopped and the temporary MSX viewport
override cleared (measured 2560x1249 again). The first owned relay stopped before
the contrast correction restart; its three recorded parent/helper PIDs, listener
and control directory were absent. The final supervisor exited 0/stopped within
its original 900-second bound; all seven recorded owned Python/console PIDs,
vendor tunnel process, listener 18092 and control directory were absent at
08:30 UTC. No trust, DNS, production or security setting was changed.

Physical Philips arrows/OK/Back, normal-distance readability, overscan and phone
scan from the actual screen remain explicitly **unchecked in #4**.

## Historical QR delivery milestone — issue #14

**Implemented / automated-tested / device-unverified — 2026-10-31.**
The native MSX pairing page includes a locally encoded PNG QR beside the readable
companion address, grouped manual code, explicit own-TV instruction, Continue
and Create new code. It uses the published 12x6 grid, non-templated `pages` and
native `space` image with aspect-preserving `fit`; no HTML/CSS injection or
proprietary runtime copying. References:
[root/template/page contract](https://msx.benzac.de/wiki/index.php?title=Content_Root_Object),
[item/image/grid contract](https://msx.benzac.de/wiki/index.php?title=Content_Item_Object).
At that checkpoint, the waiting/success/retry layout redesign remained #16;
the later software milestone is recorded above.

## Authority and privacy

The image URL carries only the device's independent random pending-only activation
secret. It never carries the private TV capability. Every image fetch revalidates
the pending device and fails closed after original expiry, removal, pairing or
an in-flight claim. A separate image peer/global request limit bounds encoding.
Local Segno encoding writes only a BytesIO buffer; no QR service, files or cache.
The QR encodes the normal operator-origin `/pair?activation=…` receiving route,
which hands off to clean `/pair` and the existing cookie/device-bound credential
stage. Scanning is not library authorization: the user must intentionally sign
in and then select Continue on the TV. The UI says to scan only from one's own TV.

No-store/private and no-referrer apply to images and activation receiving
responses. Normal exact-origin POST, CSRF, body/guess budgets, single-use grants
and fixed cleared recovery forms remain. See [receiving-route limitations](companion-pairing.md#activation-link-contract-and-privacy):
browser history, screenshots, copied links and proxy logs are not erased by
these headers. Disable URI/body/header logging at every hop and keep QR-bearing
screens private. No operator/Ultra server, credentials or media were used here.

## Actual browser observations

Connected Chrome extension, Windows, official unmodified MSX web runtime at
`https://msx.benzac.de`, isolated approved temporary synthetic HTTPS relay, normal
strict MockTransport Jellyfin authentication. MSX viewport measured **1920x1080**;
companion used the browser's default desktop viewport. No mobile or physical
phone/TV pass is claimed. All codes, activation URLs and unredacted QR screenshots
stayed in local process memory; screenshots were masked before local file/output.

- The first native run showed Content Not Available: non-templated root `items`
  were ignored. Reading the actual root contract and moving them into `pages`
  fixed this actual integration failure; HTTP tests alone had not detected it.
- The corrected actual MSX screenshot independently decoded through zxing-cpp
  to the intended synthetic-origin activation URL. This decoded URL, held in RAM,
  opened clean `/pair` with blank Jellyfin credentials and no manual-code field.
- Before credentials, actual remote Down/Return on Continue showed Waiting for
  pairing. Native normal synthetic credentials displayed TV paired; TV Continue
  displayed Jellyfin libraries and Synthetic movies. No scan-only library grant.
- Reopening the used decoded QR returned fixed invalid/expired/used manual-code
  recovery, with no credentials. Own-session Disconnect required its normal
  confirmation, then displayed Disconnected / Pair again.
- Pair again created a fresh visible grouped code; entering it through the normal
  companion code form displayed clean blank credentials. The companion address
  wrapped readably over two lines at the long synthetic hostname; the own-TV
  instruction and Continue/new-code controls fit in the inspected native layout.
- That second device was deliberately left pending through its original five-minute
  lifetime. Reopening its decoded QR then showed clean manual recovery with no
  credential fields. After waking the normal MSX screen saver, native Create new
  code selection plus Return produced a different code. Grouped manual entry,
  normal credentials and TV Continue again reached private libraries. The final
  settled library screenshot was inspected and retained. An initial click only
  selected the new-code row; reading the still-old code correctly failed. Return
  activated the selected control and the settled changed code recovered normally.

Native browser clicking brought a tab forward for screenshots; background-tab
captures sometimes timed out. One early library capture contained the outgoing
waiting scene and is not library screenshot proof. Later DOM/AX observations
and the final settled capture confirm actual libraries; a test count or outgoing scene is not substituted for
that UI evidence. The generic `browser-verify` tool was unavailable; supported
connected-Chrome controls and inspected screenshots supplied form verification.

Local ignored evidence: `issue14-msx-qr-redacted.png`, `issue14-msx-waiting.png`,
`issue14-companion-manual-signin.png`, `issue14-companion-expired-recovery.png`,
`issue14-msx-libraries.png`, all under `.lab/reports/`. The separately named
`issue14-msx-library-transition-waiting.png` preserves the outgoing-frame limitation.
The recovery image's eight-digit example is the static placeholder, not a code.
Response headers/denial/request isolation are independently checked by mocked
HTTP tests; no raw browser request trace or final live request-count report was
retained. No media playback/audio is claimed by these pairing actions.

Own-session Disconnect/Confirm finished before cleanup; both created tabs were
closed and the temporary MSX viewport override cleared (measured 2560x1215 again).
The final synthetic supervisor exited 0/stopped; all nine recorded exact owned
PIDs, listener 18092 and control directory were absent at 08:08 UTC. An earlier
relay expired during the browser-permission stall without a QR test; another was
stopped after the invalid root-page observation. No security or trust bypass.

No QR-bearing image or activation link is a
public fixture. Physical phone scan from the actual Philips screen, normal-distance
readability, overscan and remote/platform behavior remain **unchecked in #4**.
