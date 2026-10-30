# Series navigation renderer milestone — 2026-10-30

**Implemented / automated-tested / browser-tested / device-unverified:** isolated
series catalogue, production empty-state row and application-derived public
navigation graph for part of [#7](https://github.com/alexanderhetzel/jellyfin-msx/issues/7).
Issue #7 remains open for the normal hosted private flow and its permission-error
delivery. This public renderer result is not complete client integration.

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

The actual observed probe/map revision is
`0c5d12a71f7cffd1346d8fdd4fd24b6d265faf62`. Public media/poster bytes remain pinned
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
content:request:interaction:init@https://raw.githack.com/alexanderhetzel/jellyfin-msx/0c5d12a71f7cffd1346d8fdd4fd24b6d265faf62/tests/fixtures/msx-navigation/probe.html
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
| Denial recovery | Real Back restored restricted-season focus at 3/4; season 1 reopened and settled posters/episodes rendered. |

Clicking an AX text node initially only selected the row; the observed DOM control
opened it. A stale AX Back index and a pseudo-icon text locator failed before the
observed rendered Back-button selector worked. Enter with hidden player controls
first revealed them; the actual pause icon click produced the paused state.
These tool/selection outcomes are not physical remote-control failures.

Some immediate screenshot captures showed the preceding screen or black poster
placeholders while the new DOM was already available. These are not settled-image
passes. Later screenshots confirmed loaded gradient posters and the actual empty
state. The adapter's public scope text/request IDs remain visible faintly behind
the runtime; they contain no private data. No raw network capture is retained.

Sanitized local evidence is under ignored `.lab/reports/`: `issue7-seasons`,
`issue7-episode24-detail`, `issue7-episode24-back`, `issue7-episode50-detail`,
`issue7-episode50-frame`, `issue7-episode50-paused`, `issue7-episode50-back`,
`issue7-empty-settled`, `issue7-denied`, `issue7-denied-recovery`,
`issue7-recovered-episodes-settled` and `issue7-observations.json`. Back images
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

**Deferred:** normal hosted pairing → authenticated private series → private
poster/detail/resolver/file and correct permission failure/recovery in that same
flow. The controlled private HTTPS-origin limitation from #9/#12/#13 remains;
this fixture neither resolves it nor establishes dynamic authorization transitions.
Physical Philips/audio/remote/firmware evidence remains in final device gate #4.
Keep #7 open until its full requested flow is actually verified.
