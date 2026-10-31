# Two-session contract and current-layout browser entry — issue #9

**Implemented / automated-tested / device-unverified:** a deterministic local
command checks session isolation through the current production HTTP routes.
This extends the earlier single-session contract; it does not replay accepted
feature browser flows or substitute HTTP counts for a hosted-runtime pass.

## Reproduce without a server or browser

```sh
uv sync --locked --extra dev --group build
uv run python -m tools.session_check
```

The command uses explicit loopback-origin settings, strict MockTransport and
ASGI TestClient. It never binds a listener, launches a browser, reads operator
environment configuration or contacts a real server. Both independent clients
use the normal CSRF, code and credential form stages. Only the test clock is
injected for deterministic absolute expiry; authentication state is not injected.
The media bytes are a range-delivery fixture, deliberately **not encoded video**.
Both sessions sign in to the same synthetic fixture account. This checks
independent session revocation, not different-user library entitlements.

A successful fixed-field report has `category: in-process-session-contract`,
`browser_verified: false` and `physical_device_verified: false`. It establishes:

- A and B receive distinct private capabilities and upstream native-media tokens.
- A public identifier alone cannot authenticate. A complete bearer URL does
  authenticate independent of browser cookies; this is not cookie/device binding.
- After A's normal confirmed Disconnect, retained A home, browse, detail, resolver,
  poster and native-media requests are denied even when sent by the paired B client.
- B's own content, poster, resolver and native-media range requests still work.
- A can pair again, without reviving its old capability.
- At the exact portal expiry boundary, the recovered A portal JSON, resolver and
  poster deny access. Already-issued native media remains authorized by its
  upstream token; the report explicitly says
  `native_media_revoked_by_portal_expiry: false`.

The last observation records the existing direct-URL boundary. It does not turn
unrevoked native delivery into a privacy pass, imply byte recall, or establish
real Jellyfin logout/expiry behavior. See [the native credential decision](media-token-security.md).
Real-version evidence remains owned by #32; this command does not run it.

## Failure sensitivity

```sh
uv run python -m tools.session_check --fault logout-ignored
```

This command must exit **1** with `stage: a-media-revoked`. Its trusted local
fixture acknowledges upstream logout but retains the native bearer after normal
authentication. Portal revocation is not bypassed. The **same** positive media
revocation assertion must fail: do not invert or remove it to obtain a green run.
This is an expected detector failure, not successful real-server revocation.
Only fixed result/stage names are printed; no code, private URL, token, raw body
or exception is returned. Pytest exercises the negative CLI exit as well as the
normal contract and no-configuration/no-real-transport boundary. CI runs the
normal command separately from the existing HTTP smoke.

## Browser command compatibility

The accepted native QR layout renders a grouped code on its own line. The older
browser command waited for the removed `TV code:` prose prefix and could no longer
reach normal authentication. It now reads the current standalone numeric line
inside its private closure. Missing, embedded or multiple candidate lines fail
closed; hostnames and prose are not guessed as codes. Node guards cover ordinary
and nonbreaking spaces and ambiguous candidates. No AX tree or QR pixel output
is needed to extract a code.

The [pairing browser command](browser-pairing-check.md) otherwise retains normal
forms, fixed error reports and owned-tab cleanup. Its repaired current-layout
entry point completed the separately granted focused official MSX Chrome check
below. No browser, relay or merge resource was used for the earlier local
implementation checkpoint. Do not mark hosted resource/session privacy or native
failure classification passed from these assertions.

## Focused current-layout browser checkpoint — 2026-10-31

Unchanged reviewed source `83df3d70f5f9ccf1a84d693fd9302ac62c1704a9` completed
one granted baseline `checkPairing` invocation with `fault: none`. The current
standalone grouped code was read privately; normal form submission succeeded,
Continue reached private Synthetic movies, and normal confirmed Disconnect
reached the settled Disconnected / Pair again screen. All ten existing command
stages passed, including its built-in stale-form, wrong-code and credential
checks. No separate fault variant, media, alternative-start or product-matrix
replay was run. Runtime/browser versions were not independently reread here.

Fixed result evidence completed at 15:46:39 Vienna. Separate allowlisted server
observations recorded paired_sessions=0, logout HTTP204 count=1 and PlaybackInfo
request count=0. The final 2560x1249 capture was inspected and a local QR decoder
reported no code present before display. No pairing code, QR pixels, private URL,
token, raw AX/body or response trace was emitted. The four blank-initialized owned
tabs closed through the unchanged command's cleanup; no user tabs were operated.

The single supervisor started at 15:44:34 with its original 15:59:34 deadline;
startup stayed inside that 900-second total. After the command it stopped with
exit 0. At 15:47:09 all nine recorded exact helper/launcher/console/vendor PIDs,
listener 18092 and control directory were absent. The shared slot was released
immediately. No CDP, Network/viewport override, security change, new source variant,
new budget, operator configuration or real-server access was used.

Sanitized local evidence remains ignored under `.lab/reports/`:
`issue9-pr70-entry-result.json`, `issue9-pr70-server.json`,
`issue9-pr70-image-guard.json`, and `issue9-pr70-disconnected.png`.
The image proves the final disconnected view, not intermediate QR readability or
media playback. This focused pass establishes current-layout command entry,
normal sign-in/Continue/disconnect; the two-session resource command above remains
in-process HTTP evidence, not a new hosted resource-isolation pass.

After that checkpoint, the branch was rebased onto
`bc4599a12f0a746c4e3c5b035013f9ae82855c05`, preserving #19 saved progress and
the accepted #23 recovery subset at `7204161`, plus the three-active-ticket
coordination rule. The #9 browser driver, session command/tests and CI step are
byte-identical to the focused source. Baseline, failures, navigation, subtitles,
lifecycle, resume and recovery scenarios remain present. No further runtime run
or claim about the combined recovery/native-classification matrix was made.

Affected source integration validation passed: `uv run pytest -W error`
**532 passed / 1 POSIX skip**; all three explicit Node suites **57 passed**;
Ruff and formatting **109 files** passed; normal session CLI passed; locked
offline wheel build and exact **25-member** production allowlist passed.
The later coordination merge changed only two instruction documents, so source
validation was not needlessly repeated for that documentation-only rebase.

## Reconciliation with accepted feature evidence

The audit starts from main `e21d10307ee4ed166b9e0939168a8da4713ee6ef`:

| Original #9 area | Accepted evidence already recorded | Remaining boundary |
| --- | --- | --- |
| Native pairing layout and pending expiry | [QR flow and natural expiry](qr-pairing.md), #16 | Repaired reusable command needs focused current-layout execution; do not replay the QR product acceptance as new evidence. |
| Authenticated series, pagination, focus and episode original | [Private navigation at source c20e8b6](series-navigation-results.md), #7 | Real-library/version coverage remains separate; no public substitution is relabelled private. |
| Observed playback events and saved progress | [Lifecycle](playback-reporting.md), #18, and [saved resume at source bad458c](saved-progress.md), #19 | Physical behavior, unobserved failure classes and complete automation are not inferred. |
| Private caption delivery and expiry | [Source-pinned subtitle evidence](private-subtitle-results.md), #22 | Delivered bytes cannot be recalled; this is not a blanket private-resource revocation pass. |
| Pairing and deliberate JSON/playback/CSRF failures | [Pairing](browser-pairing-check.md) and [failure recovery](browser-failure-check.md), #9 partial milestones | Old historical runs do not automatically certify changed entry points or #23 native classification. |
| Logout and two-session resource authority | This new in-process command | Hosted post-disconnect poster/media and cross-session request observations remain unverified by this command. |

#8 real multi-version cases, #12 startup/restoration and #23 native classification
remain explicitly open with their owners. Complete reproducible hosted coverage,
actual relay outage, real-server qualification and physical-TV/audio checks are
not established by this milestone. Issue #9 stays open unless its original
remaining criteria are separately accepted; no aggregate test count closes it.
