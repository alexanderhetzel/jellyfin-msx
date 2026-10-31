# Series navigation verification

## Authenticated hosted software acceptance — 2026-10-31

**Implemented / automated-tested / browser-tested / device-unverified:** the
remaining #7 software flow was exercised in official hosted MSX using normal
production two-stage CSRF pairing, expiring session capabilities, private
navigation/posters/details, PlaybackInfo resolution and authenticated original
episode media. No public-export navigation, poster or media URL substitutions
were used in this run. The older renderer-only limitation below is historical.
Physical Philips/audio/remote acceptance remains unchecked in #4.

The source exercised was `c20e8b64000b8c5628f89e0056f0c8fa55e141d6`, based on
`72b3e1976a863d8f165fc83f04e2817f3881bf42`. Only the isolated lab adds a trusted
startup `navigation` scenario using the existing strict `NavigationJellyfin`.
Its original-file fixture route admits only the frozen fifty episode IDs and
checks login token, selected source and Static flag. All approved media is the
checksum-verified synthetic clip snapshotted in RAM; no directory, operator
configuration, real server/account, secret store or network fallback is used.
The old fixture synopsis still mentions the public renderer probe; that is
inherited synthetic text, not a description of this run's actual URL plumbing.
The production application and its authentication/media policies were unchanged.

The approved supervisor retained exclusive loopback binding, verified HTTPS with
no redirects, isolated child environment, EOF/Windows JobObject cleanup,
180-second startup and original **900-second total** bound. Public readiness
initially waited while local readiness was already true; verified public readiness
passed before pairing at approximately 08:40 UTC. No resolver, trust, browser
permission or TLS security setting was changed.

Reproduction after authorization and with the reviewed binary available:

```sh
uv run python -m tools.synthetic_https --activate-public-synthetic --seconds 900 --scenario navigation
```

Open the ready service's public pairing launcher in the official hosted runtime,
use the normal companion form and synthetic credentials from the lab runbook,
then Continue. This is a supervised manual browser recipe, not a complete
unattended E2E command. Shared browser/relay use requires the master's exclusive
slot during an orchestrated run. Never reuse old relay addresses.

### Actual actions and observations

Connected Chrome extension on Windows, existing `Mein Chrome` profile, official
unmodified runtime at `https://msx.benzac.de`; measured **1920x1080** viewport.
The runtime/browser version was not independently reread in this follow-up;
earlier runs recorded MSX 0.1.167 web. No physical parity or audible-output claim.

| Flow | Actual observation |
| --- | --- |
| Normal pairing → Continue | Current code stayed in RAM; normal code check and credential POST reached TV paired, then private Jellyfin libraries / Synthetic television. No state injection or public fixture callback. |
| Series → seasons → episodes | Correct series/season labels and loaded gradient posters. Native arrows traversed all fifty distinct episode labels across 24/24/2 backend records and MSX's four-poster pages. Not every episode detail was opened in the browser. |
| Next / Previous | Next reached 25–48, then 49–50 with no further Next. Previous returned to 25–48 and 01–24; new backend pages start at their first item. |
| Detail / Back / metadata | Episode 24 and 50 details showed correct title, 2026, Episode and synopsis. Real Back retained Episode 24 at 24/26 and Episode 50 at 2/4; inspected screenshots also showed loaded posters. |
| Original Episode 50 | Real Try original invoked the private resolver and native original endpoint. URL-free boolean checks confirmed the intended synthetic origin, episode 50 original path and authenticated source. Browser response observations recorded resolver JSON/200 and original MP4/206. |
| Native player | Actual visible test-pattern frame; 1280x720, duration 30, readyState 4, error null, paused false, time 8.134782 → 16.153150 seconds. Real pause icon produced paused=true at 21.222331. Escape Stop returned to detail with paused=true, time=0, readyState=0 and decoded dimensions zero. |
| Empty season | No items available / Libraries, then Back retained empty-season focus at 2/4. |
| Restricted season | Actual upstream mock 403 travelled through production HTTP error handling. MSX displayed Data Load Error plus **401 Error: Jellyfin denied access. Check permissions or pair again.** This resolves the old callback-wrapper observation for the normal synthetic HTTP flow; no polished error/retry UI is claimed. |
| Denial recovery | First Back dismissed the error notification; second restored restricted-season focus at 3/4. Season 1 reopened; Episode 01 played its own authenticated original path at 1280x720/readyState4/error-null/time4.779449, and a recovery frame was inspected before Stop. |
| Own-session cleanup | Normal Disconnect TV / Confirm disconnect displayed settled Disconnected / Pair again. Server report showed zero paired sessions and one successful upstream logout. |

Snapshots sometimes showed an outgoing/empty transition before the requested
screen settled. Subsequent DOM observations and inspected settled screenshots,
not the outgoing frame, support the results above. The native media time was
read-only; no player state was assigned. No raw QR, code, bearer URL or request
trace was written or emitted. Retained screenshots start at secret-free libraries.

### Separate sanitized request and automated evidence

The live browser Network sample retained only route categories/status/MIME:
17 private browse JSON/200, 33 private poster PNG/200, 3 private detail JSON/200,
2 private resolver JSON/200 and 2 original MP4/206 responses, plus home/disconnect
responses. It did **not** retain the 401 in that responseReceived sample. A later
full-buffer query was truncated and is not complete network evidence. The specific
401 message is observed UI evidence. Independently, the live redacted server
report counted one mock upstream library403, 57 library200, 33 poster200,
two PlaybackInfo200, one authentication200 and one logout204. Both negotiations
enabled Direct Play and disabled DirectStream/transcoding with subtitle index -1.
These counters corroborate requests; they do not by themselves prove decoding.

Sanitized local evidence is in ignored `.lab/reports/issue7-private-*`: `seasons`,
`episode24-detail`, `episode24-back`, `final-page`, `episode50-back`, `empty`,
`denied`, `denial-back`, `play-frame`, `paused`, `recovery-frame`, `disconnected`
and `observations.json`. Process identity-only cleanup records are separate.
Browser observation stopped, the viewport override cleared (measured 2560x1215),
and both owned tabs closed. At **08:45:18 UTC**, the supervisor had exited 0/stopped;
all nine recorded exact owned helper/console/vendor PIDs, listener 18092 and control
directory were absent, within the original total lifetime. Raw in-memory network
records and code/tab bindings were discarded. No production resource or TV action.

Windows/Python 3.12.14: locked dev/build sync, `uv run --no-sync pytest -W error`
**414 passed / 1 POSIX skip**, Ruff check/format **92 files**, whitespace check,
locked offline wheel build and exact **20-member** package allowlist passed.
New mocked tests cover private paging/media/source/ranges/auth/logout and reject
request-driven scenario selection; the actual helper EOF test includes navigation.
The first added assertion accidentally duplicated the origin in its expected
private prefix; correcting the assertion restored the suite. An independent
pre-activation source/security review passed 52 affected tests/Ruff and confirmed
unchanged supervision/security boundaries. Final-head review and CI are recorded
in the linked PR. These automated checks remain separate from actual UI evidence.

## Historical public renderer milestone — 2026-10-30

**Implemented / automated-tested / browser-tested / device-unverified:** isolated
series catalogue, production empty-state row and application-derived public
navigation graph for part of [#7](https://github.com/alexanderhetzel/jellyfin-msx/issues/7).
At this historical checkpoint, issue #7 remained open for the normal hosted
private flow and its permission-error delivery, now exercised above. This public
renderer result itself is not complete client integration.

## Provenance and reproduction

`tools/navigation_fixture.py` extends the strict in-process synthetic transport.
Normal production CSRF pairing establishes authentication; no state injection,
auth bypass or real upstream transport is used. A series has a fifty-episode
season, an empty season and a restricted season. Episode IDs are distinct;
production requests 24/24/2 records with normal StartIndex/Limit/parent parameters.

`tools/public_navigation_fixture.py` traverses the actual application responses,
fetches every episode detail and poster, and negotiates six boundary episodes
(1, 24, 25, 48, 49, 50) within the existing resolver rate budget. It replaces
private content URLs with public interaction request IDs, poster URLs with the
independent gradient and video resolvers with the same public synthetic clip.
Diagnostics/disconnect become scope notices. It refuses private-origin, capability,
credential/code and resolver markers before writing. The generated graph has 59
pages, including a duplicate offset=0 browse result reached through Previous.
No fifty-playback or production private-source-delivery pass is claimed.

`tests/fixtures/msx-navigation/probe.html` is an independently authored public-API
adapter that loads the generated map from its own commit directory. Its bounded
report contains only public request IDs. It uses the vendor-hosted, unmodified
plugin library and documented
[interaction handler](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference)
and [content request actions](https://msx.benzac.de/wiki/index.php?title=Internal_Actions).
No proprietary runtime is copied or modified. This shared preview origin is only
for public substituted fixtures, never credentials, capabilities or renewal data.

The full navigation/player matrix used probe/map revision
`0c5d12a71f7cffd1346d8fdd4fd24b6d265faf62`. The final cosmetic revision
`db8959789c29776a0f096c7aea9f12c42b7a2f51` hides standalone diagnostics when embedded;
series/posters, empty state and denial/Back were visually rechecked there.
Public media/poster bytes remain pinned
to reviewed #9 assets at `998bc0829b2df06db568443803a6fb4533e23f40`; encoding,
hashes and licensing provenance are in [the movie probe evidence](msx-public-fixture-results.md).

```sh
uv sync --frozen --extra dev --group build --no-build-isolation
uv run python -m tools.public_navigation_fixture --output .lab/public-navigation
uv run pytest tests/test_navigation_fixture.py
```

Launch the official runtime in connected Chrome with `start` set to the URL-encoded
action below and `input=2&init=1&suspend=0&animate=0`:

```text
content:request:interaction:init@https://raw.githack.com/alexanderhetzel/jellyfin-msx/db8959789c29776a0f096c7aea9f12c42b7a2f51/tests/fixtures/msx-navigation/probe.html
```

This is a manual fixture recipe, not a complete automated browser assertion command.
Our source is commit-pinned; the runtime, vendor library and preview service are
external network dependencies. No certificate, trust, browser-permission,
production-library, Ultra, server-account or firmware change was performed.

## Actual official MSX observations

Windows, connected Chrome extension, existing `Mein Chrome` profile, official
MSX **0.1.167 web**, top origin `https://msx.benzac.de`, public fixture origin
`https://raw.githack.com`, normal **2560×1271** content screenshots. Browser version
was not independently reread. No viewport/partition/storage override was applied.

| Action / observation | Actual result and boundary |
| --- | --- |
| Synthetic television → series → seasons | Correct controls, title/footer metadata and gradient posters visibly rendered. |
| Arrow keys through season 1 | All episode labels 01–50 reached across MSX's own four-poster pages and the backend's three pages. DOM snapshots corroborated visible labels; representative screenshots were inspected. Not every detail was opened in the browser. |
| Next / Previous | First Next reached 25–48; second reached 49–50 with no further Next. Previous returned to 25–48 and then 01–24. New page requests start at their first item. |
| Episode 24 detail → real Back control | Correct episode/year/type/overview, then retained Episode 24 focus at 24/26. |
| Episode 50 detail/play | Correct detail; actual standard player showed the substituted public clip. Visible test-pattern frame, 1280×720, duration 30, readyState=4, no media error. Time advanced from 5.20 to 10.16 and 15.10 seconds. |
| Pause / Stop / Back | Real pause control yielded paused=true at 19.04 seconds; Stop/eject returned to Episode 50 detail. Back restored Episode 50 focus at 2/4. Audible output was not verified. |
| Empty season / Back | Settled view showed No items available and Libraries; Back retained empty-season focus at 2/4. |
| Restricted season | Export contains the actual production 401 wrapper generated by mock upstream 403. Returned through the interaction content callback, MSX showed **Content Not Available / Content is missing**, not the application's permission message. This is a negative adapter/delivery observation, not normal private HTTP denial acceptance. |
| Denial recovery | Real Back restored restricted-season focus at 3/4; season 1 reopened and settled posters/episodes rendered. During the final recheck, the first Back dismissed the active warning; the second returned to seasons. |

Clicking an AX text node initially only selected the row; the observed DOM control
opened it. A stale AX Back index and a pseudo-icon text locator failed before the
observed rendered Back-button selector worked. Enter with hidden player controls
first revealed them; the actual pause icon click produced the paused state.
These tool/selection outcomes are not physical remote-control failures.

Some immediate screenshot captures showed the preceding screen or black poster
placeholders while the new DOM was already available. These are not settled-image
passes. Later screenshots confirmed loaded gradient posters and the actual empty
state. Initially the adapter's public scope text/request IDs were faintly visible
behind the runtime. The final iframe-only visibility change removed that background
without changing the public API. Its first launch timed out with Data Load Error;
one ordinary reload succeeded, then actual series/poster/empty/denial checks passed
within the stated limits. No private-HTTPS workaround or raw network capture was used.

Sanitized local evidence is under ignored `.lab/reports/`: `issue7-seasons`,
`issue7-episode24-detail`, `issue7-episode24-back`, `issue7-episode50-detail`,
`issue7-episode50-frame`, `issue7-episode50-paused`, `issue7-episode50-back`,
`issue7-empty-settled`, `issue7-denied`, `issue7-denied-recovery`,
`issue7-recovered-episodes-settled`, `issue7-final-seasons`, `issue7-final-empty`,
`issue7-final-denied`, `issue7-final-recovery` and `issue7-observations.json`. Back images
establish the focus/label boundary, not fully loaded posters. Some screenshots
have a `.png` suffix although the browser returns JPEG bytes; readers detect it.

## Automated evidence and remaining acceptance

Offline tests traverse the complete public graph, compare deterministic committed
output, assert unique episodes and correct Next/Previous targets, empty state,
denial wrapper, credential markers and no real transport fallback. Separate normal
private HTTP tests cover actual permission denial without session destruction,
six boundary PlaybackInfo negotiations and revocation denial for browse/detail/image.
Wheel/source allowlist checks exclude fixtures/tools/public media; CI additionally
checks the actual filtered Docker context and final image.

**Historically deferred at this checkpoint:** normal hosted pairing → authenticated private series → private
poster/detail/resolver/file and correct permission failure/recovery in that same
flow. The controlled private HTTPS-origin limitation from #9/#12/#13 remains;
this fixture neither resolves it nor establishes dynamic authorization transitions.
Physical Philips/audio/remote/firmware evidence remains in final device gate #4.
The authenticated synthetic follow-up above addresses this #7 software flow;
real-server and physical-device verification remain separate.
