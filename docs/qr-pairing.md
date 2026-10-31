# QR companion pairing — issue #14

**Implemented / automated-tested / device-unverified — 2026-10-31.**
The native MSX pairing page includes a locally encoded PNG QR beside the readable
companion address, grouped manual code, explicit own-TV instruction, Continue
and Create new code. It uses the published 12x6 grid, non-templated `pages` and
native `space` image with aspect-preserving `fit`; no HTML/CSS injection or
proprietary runtime copying. References:
[root/template/page contract](https://msx.benzac.de/wiki/index.php?title=Content_Root_Object),
[item/image/grid contract](https://msx.benzac.de/wiki/index.php?title=Content_Item_Object).
Full waiting/success/retry layout redesign remains #16.

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

Native browser clicking brought a tab forward for screenshots; background-tab
captures sometimes timed out. One early library capture contained the outgoing
waiting scene and is not library screenshot proof. Later DOM/AX observations
confirm actual libraries; a test count or outgoing scene is not substituted for
that UI evidence. The generic `browser-verify` tool was unavailable; supported
connected-Chrome controls and inspected screenshots supplied form verification.

Local ignored evidence includes redacted QR/manual layout, waiting, blank manual
sign-in and recovery screenshots. No QR-bearing image or activation link is a
public fixture. Physical phone scan from the actual Philips screen, normal-distance
readability, overscan and remote/platform behavior remain **unchecked in #4**.
