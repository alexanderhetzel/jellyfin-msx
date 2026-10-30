# MSX and companion visual design — issue #15

**Implemented / automated-tested / browser-tested / device-unverified — 2026-10-30.**
The browser software milestone presents Jellyfin MSX consistently across native
MSX content and the companion code/sign-in/success pages. Physical Philips
viewing-distance readability, overscan and remote behavior remain unchecked in
final hardware issue #4. This does not complete the hosted private integration
work in #7/#9/#12/#13 or the pairing layout/QR work in #14/#16.

## Presentation contract

`presentation.py` defines the dark blue surface `#182632`, dark background/ink
`#101820`, light foreground `#f4f7fa` and green accent `#b8f16a`.
The companion uses a system sans-serif, 18px base text, 1.55 line height,
bounded content width, explicit field labels and 3rem minimum input/button height.
Headings, stage labels, status/recovery text and links share spacing across code,
sign-in, retry and success. Empty status blocks are hidden. Status meaning remains
in the words, not just a color. Password retry fields remain blank.

The native MSX template keeps its 12x6 grid, full-width one-unit list rows and
three-unit-wide separate poster cards. Native fonts, text sizing, uppercase list
titles, paging, control labels and white focus outline remain runtime-owned.
Only documented native properties are used: template `color`, root `extension`
and a trusted constant-only `{txt:COLOR:TEXT}` product label. No HTML/CSS is
injected into MSX and no runtime code is copied, hosted or modified.
Untrusted titles still pass through the existing expression-delimiter sanitizer.

Public vendor references, read during implementation:
[content root](https://msx.benzac.de/wiki/index.php?title=Content_Root_Object),
[content item](https://msx.benzac.de/wiki/index.php?title=Content_Item_Object),
[colors](https://msx.benzac.de/wiki/index.php?title=Colors),
[inline expressions](https://msx.benzac.de/wiki/index.php?title=Inline_Expressions),
[selection](https://msx.benzac.de/wiki/index.php?title=Selection_Object).
The initially guessed Content Reference page had no content; the actual linked
object references above supplied the contract.

Calculated sRGB contrast for configured companion colors: text/background
16.64:1, text/surface 14.34:1, accent/background 13.49:1, secondary
`#c5d2de`/background 11.63:1 and field border `#8a9bad`/surface 5.41:1.
These ratios do not certify every native runtime pixel or physical TV rendering.
Keyboard focus uses a three-pixel accent outline; the accent button uses a light
outline instead. Links retain their accent after visiting.

## Public preview provenance

Final public fixture/source pin: `89e7d2ddbee4266a594e153c383f923dfd5b8bca`.
Initial non-accented label checks used `66fe7e122da7c331b3d4611b542f81637ff5374f`;
all changed native views were rechecked at the final pin. Synthetic poster/media
assets remain pinned to `998bc0829b2df06db568443803a6fb4533e23f40`, with
independent provenance in [the public fixture evidence](msx-public-fixture-results.md).

`tools/public_msx_fixture.py` exports actual application responses from isolated
normal synthetic authentication. The new waiting preview requests the normal
pending home route and replaces every private action with a harmless scope
notice before export. It never exports the pairing response, code, activation
link or session capability. Public waiting controls do not pair a TV or create
a new code. The index adds an embedded waiting preview; private/authenticated
delivery and dynamic transitions are explicitly outside this public graph.
The series graph was regenerated for the shared template/label; its prior full
navigation evidence remains historical, not a new #7 integration pass.

Reproduction (offline export and comparison):

```sh
uv sync --locked --extra dev --group build
uv run python -m tools.public_msx_fixture https://raw.githack.com/alexanderhetzel/jellyfin-msx/998bc0829b2df06db568443803a6fb4533e23f40/tests/fixtures/msx-public --output .lab/public-msx
uv run pytest tests/test_public_msx_fixture.py tests/test_navigation_fixture.py
```

Launch the vendor-hosted runtime at `https://msx.benzac.de/` with the URL-encoded
`start` action below and `input=2&init=1&suspend=0&animate=0`:

```text
content:https://raw.githack.com/alexanderhetzel/jellyfin-msx/89e7d2ddbee4266a594e153c383f923dfd5b8bca/tests/fixtures/msx-public/index.json
```

## Actual browser evidence

Windows, connected Chrome extension, existing **Mein Chrome** profile; browser
version was not independently reread. Official MSX **0.1.167 web**, top origin
`https://msx.benzac.de`, public substituted fixture origin `https://raw.githack.com`.
No storage/profile/partition, certificate trust, security policy or production
setting changed. Runtime and preview service are external unpinned services;
our fixtures/assets are commit-pinned.

The browser-scoped viewport capability's requested 1920x1080 override still
measured 2560x1215. The supported tab `cdp` capability applied
`Emulation.setDeviceMetricsOverride` with `{width, height, deviceScaleFactor:1,
mobile:false}` for MSX **1920x1080** and companion desktop **1280x900**; companion
mobile used **390x844**, `mobile:true`. Read-only `document.documentElement`
clientWidth/clientHeight and actual screenshots confirmed those sizes.
Mobile scrollWidth equaled clientWidth (390). This is Chrome device emulation,
not a physical phone/browser certification. Overrides are cleared with
`Emulation.clearDeviceMetricsOverride` and browser viewport `reset()` during cleanup.

| Surface/action | Actual observation |
| --- | --- |
| MSX libraries/waiting | Settled dark rows, green product label, readable primary labels and white selected-row frame at 1920x1080. Five actual Down keys and Return opened waiting; Down selected Create new code; Back restored index focus 6/6. |
| MSX posters/details | Actual Up/Down/Right/Return/BackSpace keys opened movies, details and oversized denial. Back restored the selected poster (1/4 or 2/4). Gradient poster, native separated title/footer and green product label visible; no primary label clipping in inspected screens. |
| MSX denial/recovery | Return showed the existing HD-only/no-conversion notice. Back navigation recovered posters and libraries. This is public denial presentation, not a new private HTTP-denial or playback pass. |
| Public delivery | On a normal reload, CDP Network.responseReceived observed HTTP 200/application-json for the final pinned public index (with vendor-added version/time query). Only that public URL/status/type were retained, no raw network capture. |
| Companion code/recovery | At 390x844 and 1280x900, native invalid-code submission displayed fixed recovery, blank code input and no credentials. Labels/button/help fit; no horizontal overflow. The visible eight-digit example is the static placeholder, not a pending code. |
| Companion credentials | A disposable loopback-only fixture created an ordinary pending device and redirected through the normal activation receiving route to clean `/pair`. Blank credentials rendered at both widths. It did not bypass CSRF or authenticate automatically. Valid manual-code advancement was not newly exercised here; existing #13 evidence/tests remain separate. |
| Companion retry/focus | Native wrong-password submissions displayed fixed sign-in failure and cleared username/password fields. Tab navigation reached Use a different TV code with visible outline; Return reopened manual entry. The mobile retry page scrolls vertically to accommodate the message; it does not overflow horizontally. |
| Companion success | Native synthetic credential submission at each width showed TV paired, Pairing complete and the exact Continue after pairing instruction used in MSX. Screenshots contain no submitted credentials or private grants. |

The loopback-only helper was ignored, absent from product routes/builds and used
only `httpx.MockTransport`. It used HTTP on `localhost:18095`; no hosted-MS​​X-to-
private-companion flow is claimed. No real account/server was used. Existing
no-store/private, CSP, CSRF, body-limit, referrer-policy and cookie boundaries
remain covered by the unchanged security regressions.

Native `Tab.pressKey(null, ...)` supplied the observed MSX/companion keys.
An initial Playwright body-key press timed out and raw CDP Input was unsupported;
neither is an application/TV remote failure. The generic `browser-verify` tool
was unavailable; supported connected-Chrome controls and inspected screenshots
provide the visual form evidence. Windows default text decoding initially
corrupted the title separator; explicit UTF-8 template loading corrected it and
the clean title was observed after restarting the owned synthetic service.

Ignored `.lab/reports/` screenshots: `issue15-final-tv-libraries`,
`issue15-final-tv-waiting`, `issue15-final-tv-posters`, `issue15-final-tv-detail`,
`issue15-final-tv-denial`, `issue15-final-tv-recovery`, `issue15-mobile-code`,
`issue15-mobile-error`, `issue15-mobile-credentials`, `issue15-mobile-retry-focus`,
`issue15-mobile-success`, `issue15-desktop-code`, `issue15-desktop-code-error`,
`issue15-desktop-credentials`, `issue15-desktop-retry-focus`,
`issue15-desktop-success` (all JPEG). Public-only request metadata is in
`issue15-public-request-evidence.json`. Earlier non-final captures are retained
separately. Raw initial loading/resize frames are not settled-image evidence.
The retained final denial image shows the denied-detail rows after the timed
notice disappeared; the opened HD/no-conversion notice is an actual UI/AX action
observation, not a claim about the content of that retained image.

Independent review inspected all sixteen named screenshots and the source,
export/security boundaries and evidence claims. It found no blocking source or
visual findings; the denial-image distinction above records its evidence nuance.
The reviewer did not repeat live browser actions. The owned synthetic listener
and three browser tabs were closed. Both tab emulations and the browser-scoped
override were reset; both pages measured the original 2560x1215 afterward.

**Deferred / device-unverified:** physical Philips normal-distance readability,
overscan, arrows/OK/Back and platform font/rendering parity remain in #4.
Nothing here establishes audio, media decoding or complete private integration.
