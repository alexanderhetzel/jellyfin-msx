# Hosted two-session authority check — source preparation

**Implemented / automated-tested with mocks / hosted-runtime-unverified /
device-unverified.** This entry extends issue #9's
[local HTTP session contract](session-boundary-check.md) with a narrowly scoped
hosted-browser command. It changes no application route, authentication, playback
policy or public fixture scenario. Issue #9 remains open.

## Intended observation

`tools/browser_session_check.mjs` exports `checkSessions({ origin, newTab, fault })`.
The connector must create blank **owned Chrome extension tabs**, without automatic
page snapshots. Use the existing supervised baseline synthetic relay only after
the master grants its exclusive browser/relay slot. No listener, relay, browser
navigation or CDP command was used to validate this new entry during source prep.

The command identifies the configured public synthetic service, opens the official
hosted MSX runtime and normally pairs A and B to the same fixture account using
the CSRF-protected form. It reads the current grouped code into a private closure,
selects Continue and Synthetic movies, and reads only standard rendered DOM image
URLs. The known public fixture movie ID selects the own private poster. A QR
image's pending activation grant is never treated as a TV session capability.

An owned observer tab captures same-capability home, browse, detail, poster and
legacy Try original resolver links. The resolver supplies the native original
URL. Each target is validated against the captured origin/capability, expected
route and item/source; forced conversion, foreign targets, unknown parameters and
duplicate authorities fail closed. URLs, bodies, request IDs and upstream tokens
stay in private closures/WeakMap plans; returned handles contain only fixed roles.

After normal confirmed A Disconnect, fresh ordinary observer-tab GET navigations
must deny A's six retained targets. B's own six targets must still serve. A newly
paired session must serve with distinct authorities while all old A targets stay
denied. Cleanup attempts normal Disconnect for authenticated owned sessions,
disables the observer only on its bound origin, and closes every owned tab.
Unconfirmed cleanup fails the command and must be reconciled with the supervised
service's fixed counters and process/listener/control cleanup before slot release.

`fault: "authorized-target"` deliberately substitutes **B's authorized native URL**
at the unchanged A media-denial predicate. A fresh actual HTTP 200/206 must fail
that predicate; the report labels the authorized-B positive-control target.
This demonstrates detector sensitivity, not an actual A logout leak or an
upstream-ignored-logout server experiment. The latter remains a separate local
counterexample in `tools/session_check.py`. Do not retry a failing functional step
as a new matrix or silently downgrade unknown evidence to a pass.

## Observer contract and authorization dependency

`tools/browser_resource_probe.mjs` uses the Cua CDP wrapper documentation read
without browser actions on 2026-10-31:

```javascript
await cdp.send(method, params, { timeoutMs: 2000 });
await cdp.readEvents({ afterSequence: cursor, methods, limit: 128, timeoutMs: 250 });
// { cursor, events: [{ method, params, sequence, source }], hasMore, truncated }
```

Navigate the new observer tab to the intended HTTPS origin **before** its first
CDP command. The platform's current-origin restrictions and permission checks
still apply. Existing global CDP availability does not authorize a new tunnel
origin. Permission refusal/unavailability returns a fixed failure; there is no
force option, alternate origin binding or substitute network client. If actual
platform approval needs the maintainer, stop under the run's human-input gate.
Source readiness does not promise unattended per-origin authorization.

The command enables only Network observation, with a 64 KiB total payload buffer,
16 KiB per-resource buffer and zero post-data preview. It never disables cache,
overrides request headers, intercepts requests or enables durable messages. The
primary [Chrome DevTools protocol definition](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/json/browser_protocol.json)
defines `Network.enable`, `Network.getResponseBody` and the observed Network
events; wrapper signatures above come from the installed Cua capability reference.

Existing events are drained in bounded pages before taking the action cursor.
After the action, at most 24 pages of 128 events are read using the same filters
and advancing cursor. Truncation, stale events, redirects, ambiguous requests,
missing root Document responses and unknown cache flags fail closed. Only an
exact URL/method/request-ID-correlated root Document GET response counts.
Disk/service-worker/prefetch flags must all explicitly be false, with no matching
cache event. This is positive evidence for these specific observer-tab requests;
missing root events prove nothing about child targets, SDK traffic or requests
made by the hosted MSX runtime. No all-target/OOPIF absence claim follows.

`Network.getResponseBody` is conditional: portal JSON always needs a completed
bounded body; binary denials need a completed bounded body only for HTTP 401/403.
Authorized binary 200/206 observations fail a denial without buffering the video.
Unavailable, oversized or malformed/noncanonical base64 bodies are unknown and
fail. Denial bodies cannot contain the committed public clip's 32-byte prefix or
PNG signature anywhere within the bounded bytes. There is no fallback to page
text or a guessed status. A permission or body-access barrier remains a runtime
dependency to report, never an assertion to bypass.

Reports distinguish actual `http_status` from wrapped MSX `portal_status`.
Portal errors often use HTTP 200 with `response.status: 401`; that is not raw
HTTP 401. Wrapped denials require JSON MIME, a data-less error wrapper and no
additional payload fields. Fixed output includes role/category, finite MIME,
numeric statuses, freshness and pass/failure; raw events, bodies, headers,
URLs, QR images, pairing codes and browser exceptions are never emitted.

## Evidence limits

Mocked Node tests cover correlation/freshness failures, bounded body access,
prefix rejection, separate HTTP/MSX statuses, foreign/duplicate authorities,
permission refusal, redaction and the unchanged denial predicate's actual-200
counterexample. They execute no browser and contact no server. A future granted
run must separately record exact reviewed source, UI actions, sanitized observed
statuses, detector failure and owned-resource cleanup. Until then this command
has no hosted acceptance result.

Run the offline guards with `node --test tools/*.test.mjs`; repository CI runs
the same command using the runner's Node installation, with no npm dependencies.
Also run `uv run pytest -W error`, `uv run ruff check .` and
`uv run ruff format --check .`. These commands cannot certify the CDP or UI
integration. In particular, native URLs must retain production's DeviceId and
PlaySessionId fields; their exact full query shape is covered by the mock guards.

A full capability URL is deliberately bearer authentication independent of
cookies. Same-account A/B results do not prove tenant isolation or device binding.
Native GET availability is not decoded playback, audible sound or physical TV
evidence. Portal expiry does not guarantee revocation of issued native URLs;
the existing local expiry counterexample remains unchanged. No real Jellyfin
version/logout guarantee (#32), source/version acceptance (#8), startup result
(#12), or native cause classification (#23) is inferred. Accepted earlier media,
QR and navigation evidence is referenced instead of replayed.
