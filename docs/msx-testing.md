# Agent-operated MSX integration lab

For an isolated fixture with normal authentication and no operator account, see
[synthetic integration testing](synthetic-testing.md). Its deterministic HTTP
contract check is separate from the still-deferred hosted-runtime browser suite.

The overall check-selection and evidence procedure is in
[the agentic testing cookbook](agentic-testing.md). Routine agent sign-in/pairing
is test execution, not a feature ticket. With authorized stored test credentials,
the agent performs the existing pairing flow itself; human sign-in below is only
the fallback when no authorized test account is available. Public CI remains synthetic.

The target is the **official hosted MSX web runtime**, not a recreated UI. MSX's
[license](https://msx.benzac.de/info/?tab=License) allows API-based services and
examples, but prohibits hosting/copying/modifying the runtime itself. The lab
therefore launches `https://msx.benzac.de/` and supplies our portal as its start
parameter. No firmware or proprietary runtime is downloaded into this project.

The user requires one consistent test browser: use the integrated browser for
MSX, companion pairing and Jellyfin media inspection. Native Arc automation below
is historical failure analysis, not the current workflow. Never label integrated
browser results as SAPHI decoder verification.

## Start against the operator's real Jellyfin

```sh
uv sync --frozen --extra dev
JELLYFIN_URL=https://YOUR-SERVER/jellyfin .venv/bin/python tools/lab.py
```

This starts `https://localhost:18091/__lab/`, bound only to 127.0.0.1. The
operator's actual URL belongs in an ignored local environment/configuration, not
the committed runbook. No password/token is accepted by the launcher. It always
disables transcoding and burn-in. The local lab uses a 30-minute pairing window
to allow for agent/browser setup; the normal deployment retains its five-minute
default. The actual duration is shown in MSX. No server configuration or library mutation
is part of this lab.

The dashboard links to real MSX, the normal pairing form, and a redacted observation
report. The launcher exits with the server on Ctrl+C. It creates only ignored
`.lab/tls` certificate/key files; `.lab` is also excluded from Docker build context.

## One-time environment permissions

MSX automatically upgrades JSON requests to HTTPS when its own runtime is HTTPS.
Plain `http://localhost` therefore cannot drive the hosted runtime. This behavior
is documented in [MSX setup](https://msx.benzac.de/wiki/index.php?title=Setup_Start_Parameter).

The launcher generates a one-day, non-CA TLS certificate for localhost/127.0.0.1.
It **does not** install trust or disable certificate verification. The operator
must explicitly authorize local trust first. On macOS, a scoped SSL trust rule for
this exact leaf certificate can be added to the login keychain. Chromium did not
recognize the tested rule with an additional policy-string constraint; trusting
the same non-CA leaf for SSL worked. Its hostname validity remains localhost only.
Never bypass a browser's TLS warning or disable browser security to make a test pass.

Arc/Chromium can additionally prompt to allow `msx.benzac.de` access to the loopback
network. Obtain explicit approval for that permission. Without it, MSX can remain
on its loading screen and no JSON request reaches the backend.

In Arc native automation, focus the actual HTML content before sending MSX keys;
clicking an accessibility text row alone did not trigger navigation in the test.
When duplicate test tabs exist, use Arc's visible sidebar and match the displayed
TV code to the current run. Ctrl+Tab may choose an older test tab. Inspect only
relevant tabs; do not navigate unrelated user pages.
Native Arc coordinate control was unavailable even though the operator could see
and use the UI. Leaving fullscreen recovered a visible agent capture but did not
reliably fix input. Treat this as a control limitation, not a failed MSX screen.
When using the isolated browser as a fallback, keep the Arc session intact and
pair the additional test session normally. Do not read or transfer stored tokens.
Use direct DOM-backed clicks for this browser fallback (`input=2`) and inspect the
same bound tab's DOM. Mixing native-app keyboard actions with browser-tab state
was unreliable: a newly paired test returned to a fresh pairing screen. The cause
was not conclusively isolated. Direct Continue clicks and a companion-tab switch
were subsequently checked to preserve Waiting for pairing with `suspend=0`.
The launcher now disables suspend for a deterministic active lab session. It keeps
`init=1` so an initial launch deliberately uses the configured start content rather
than an unrelated cached MSX page. A deliberate reload still creates a new pairing.

An expired certificate is rejected by the launcher. Remove the old trust entry,
renew the local key/certificate, and explicitly approve trust again. Remove the
test trust after the session. For long-running unattended development, use a
properly hosted HTTPS preview rather than repeated one-day certificate approvals.

## Actual application loop

1. Open the dashboard in the integrated browser and select **Open Media Station X**. Verify MSX's
   version and a real **Pair this TV** screen. Record a screenshot/AX observation.
2. Use arrows/Enter to select Continue before pairing. Verify **Waiting for pairing**,
   then return to the current code. Check the report's endpoint counts.
3. The human signs into `/pair` once using the current code and a suitable test
   account. Credentials go only into the form; agents must not retrieve browser
   passwords, cookies or raw tokens. Do not save a password in the test scripts.
   Use a fresh GET of `/pair`, not a reload of an old failed POST. Keep one active
   form tab: opening another rotates the browser's CSRF cookie. Success must show
   **TV paired / Sign-in succeeded**, corroborated by the redacted report. If
   **Form expired** repeats, reproduce with dummy input and no password before
   asking the human to retry. Native Chromium forms require the page's
   same-origin referrer policy to preserve the Origin used by our CSRF check.
   A backend restart intentionally discards RAM sessions and requires pairing again.
4. Continue in MSX. Verify library names/posters, movie detail and series → season
   → episode by keyboard. Test Back and focus retention. Test pagination when available.
5. Open an item with multiple model-profile candidates, ideally including a
   version fitting the panel and a higher-resolution copy. Start **Try original
   (TV unverified)** and record the named profile and evidence warnings.
   Verify a real picture and audible sound, then play/pause/seek/stop controls.
6. In a browser with a DOM inspection API, inspect only the actual video element's
   `readyState`, `currentTime`, `duration`, `paused`, `videoWidth`, `videoHeight`
   and media error code. Observe changing time across two snapshots. Never log its
   `src` URL, which contains a Jellyfin token. A real advancing player, not merely
   a returned URL, is the playback pass condition.
7. Correlate the UI with `/__lab/report`: actual PlaybackInfo request, all conversion
   flags false, selected source height, redacted route/decision counts. Source
   selection alone does not prove playback. The report contains no item names/IDs,
   server URLs, capability paths, credentials or media URLs.
8. Check an incompatible-only item: visible denial and no HLS/transcoding request.
   Do not change the production library to manufacture a failure. If a suitable
   test item is absent, report the case as not exercised.
9. Disconnect the TV, verify private content is denied, and remove the temporary
   certificate trust. Save redacted results in `docs/msx-test-results.md`.

If no source matches the documented candidate/transport policy, report that
policy result rather than claiming the TV cannot play it. Never expand claimed
hardware support from desktop decoding or enable Ultra conversion for a green
test. The model profile follows `philips-32phs6605-12.md`; a physical-TV pass is
still required. A synthetic fixture remains optional, not a required replacement
for an existing 720p MKV simply because it is not MP4/AAC.

## Standalone runtime smoke check

```sh
.venv/bin/python tools/lab.py --smoke-url
```

Open the printed URL in MSX. It embeds a public test page built by the production
JSON generator, with navigation notifications and the official MSX sample video.
This tests parsing/rendering, remote keys and the browser player without backend
network/certificate dependencies. It does **not** test authentication, Jellyfin,
our PlaybackInfo resolver, version selection or the SAPHI engine.

## Rules for evidence

- Backend unit tests, renderer smoke, real Jellyfin/MSX integration and physical
  TV tests are separate result categories. Passing one cannot promote another.
- For each case retain action, visible result, error/console state and a redacted
  observation. Screenshots of real media may contain private titles; keep them
  local in `.lab/` unless the operator authorizes sharing.
- Do not retain raw network dumps, MSX JSON with capabilities or video URLs.
- The recorder aggregates HTTP response status counts by category in current
  source. This was added after an inconclusive black-screen run; that existing
  process lacks response counts and must not be credited with unrecorded statuses.
- Reset only lab-owned state. The Docker daemon/other applications belong to the
  user; do not stop or delete unrelated containers, images or data.
