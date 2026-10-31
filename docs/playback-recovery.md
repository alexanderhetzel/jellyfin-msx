# Playback recovery — issue #23

**Implemented / automated-tested / device-unverified; browser acceptance pending.**
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
Before a replay/replacement or Back, the plugin issues public `player:stop`.
Back invalidates pending start/catalogue responses so they cannot reopen playback
or recovery. No reliable Stop callback is inferred: disposal can leave the server
to close the generation at its last safe position under the existing 45-second
lease, with `Failed=true`. Replacement still requires the previous server Stop
acknowledgement before a new reporting grant is published. No lifecycle state
machine, completion, profile, session, auth or token-origin boundary is widened.

## Verification and remaining acceptance

Local checks on 2026-10-31: `uv run pytest -q` **491 passed / one POSIX skip**;
`uv run ruff check .` passed; `uv run ruff format --check .` **101 formatted**;
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

No browser or relay has been started for this milestone. Pending master-granted
Chrome acceptance must exercise actual negotiation denial/Retry limit/Back,
native unsupported-source manual recovery, explicit alternative followed by a
visible advancing frame, and safe return/reentry. Record UI actions/media state
separately from sanitized request/report counters. Never capture a native error
notice containing a private media URL. Network-loss emulation, if separately
needed, must remain tab-scoped and restored; a tool timeout is not media evidence.

Original four-criterion mapping: diagnostic distinction **partial** (native cause
unavailable); remote recovery/alternatives **implemented and automated-tested,
runtime pending**; finite retries/cleanup **automated-tested, runtime pending**;
no Ultra conversion/alternate-origin credentials **preserved and automated-tested**.
Physical Philips, audio, hardware remote and OS connectivity remain deferred to
#4 and related device issues. No full #23 acceptance or merge readiness is claimed.
