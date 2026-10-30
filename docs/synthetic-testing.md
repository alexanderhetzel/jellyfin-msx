# Synthetic integration lab

**Implemented / automated-tested:** an isolated fixture for the Jellyfin API
contract consumed by the production application. Authentication runs through the
normal production pairing form, including CSRF, pending code validation and
Jellyfin login. The fixture checks both synthetic username and password, issues
random in-memory tokens and revokes them on logout. No real Jellyfin connection,
operator credentials, authentication bypass or production route is added.

This is a prerequisite milestone of [issue #9](https://github.com/alexanderhetzel/jellyfin-msx/issues/9).
The full hosted-MSX browser suite remains **deferred**. Neither fixture responses
nor byte delivery certify Jellyfin release compatibility, video decoding or a TV.

## Fresh-environment contract command

From the repository root, with Python 3.12+ and uv installed:

```sh
uv sync --locked --extra dev
uv run python -m tools.synthetic_check
```

The command must exit zero and report `category: in-process-http-contract`, with
`browser_verified` and `physical_device_verified` both false. It exercises pending
pairing, rejected CSRF followed by normal sign-in, libraries, posters, details,
pinned original PlaybackInfo, authenticated byte-range delivery, the 1920x1080
admission boundary, disconnect, private/poster/media denial and fresh re-pairing.
The media is explicitly a temporary byte fixture, **not an encoded video**.

These commands must each exit **1**, with the indicated failure stage:

```sh
uv run python -m tools.synthetic_check --fault json
uv run python -m tools.synthetic_check --fault playback
uv run python -m tools.synthetic_check --fault csrf
```

Stages are `libraries-json`, `playback` and `pairing`, respectively. JSON corrupts
the fixture's Views response; playback denies Direct Play in PlaybackInfo; CSRF
corrupts the submitted normal form field. They detect broken HTTP contracts, not
broken hosted-runtime rendering or decoder behavior. The pytest suite verifies
these exit codes. Exceptions print only an allowlisted stage, never a traceback
that could include a capability or media URL. Existing Starlette warning #30 is
visible and is not globally suppressed.

Public CI runs these isolated contracts with no browser, network server, FFmpeg,
operator secrets or account. All upstream REST uses `httpx.MockTransport`, with no
network fallback; tests also guard against real HTTP transport calls. No new
dependencies or lockfile changes are needed. Local ports are not used by this check.

## Launch the same fixture for official MSX

Generate an original synthetic H.264/AAC MP4 locally with FFmpeg on PATH:

```sh
uv run python tools/make_test_clip.py --output .lab/media/synthetic.mp4
uv run python -m tools.synthetic_lab --cert .lab/tls/cert.pem --key .lab/tls/key.pem
```

The clip generator creates a 30-second 1280x720 test pattern and tone, independently
of any operator media. Do not substitute a private file at that path. Its encoding
does not run on Ultra. The lab binds only to `127.0.0.1:18091` and requires an
existing explicitly approved, valid localhost certificate/key. It never creates,
renews or installs trust. The default TLS implementation validates certificate
loading; browser trust, identity and expiry still need verification. Follow
[the TLS instructions](msx-testing.md#one-time-environment-permissions), never
bypass warnings or disable browser security. `--http` is only for local API/form
inspection; the HTTPS hosted runtime upgrades requests and cannot use that mode.

Open the printed dashboard in the **connected Chrome extension**, the maintainer's
current override of older integrated-browser guidance. Select **Open Media
Station X**, then use the normal companion form with the current displayed code,
username `synthetic-viewer` and password `synthetic-password`. These are public,
fixture-only values and do not authenticate any real server. Do not load an OS
credential store. Synthetic tokens/capabilities/codes still must stay out of logs.

The fixture offers a synthetic movie/poster and an oversized denied candidate.
Original playback goes directly to its fixture endpoint under `/jellyfin`, which
checks the login token and selected source and supports HTTP ranges. This endpoint
is **not** a production proxy. Missing clip returns 503; unauthorized media returns
401. No series/pagination coverage is provided by this milestone.

Use `--fault json` or `--fault playback` to start a deliberately broken fixture
for future browser failure checks. There is no endpoint to mutate fixture state
or bypass pairing. Restart for another fault; restart discards all sessions.

Follow [the actual playback loop](agentic-testing.md#playback-loop) through real
controls. Retain safe time/duration/paused/readyState/dimensions/error observations
and sanitized failures. `/__lab/report` records only redacted route counts,
status counts and policy/decision evidence. `/__synthetic/report` adds original,
denied and missing-media request counts; its verification flags remain false
because the server cannot attest to browser playback. Neither contains raw URLs,
pairing codes, credentials or login tokens. Keep raw captures under ignored `.lab/`.
Stop the lab after testing and remove any temporary approved trust.

## Outstanding acceptance

The hosted runtime is an external, unpinned network dependency; its availability,
version and browser permission/TLS requirements must be recorded by the future
browser suite. Do not copy, host or modify its proprietary implementation. The
official runtime still needs actual rendering/pairing/poster/player/denial/recovery
checks, advancing time, pause/resume, forward/back seek and Stop evidence, a fresh
environment browser command and deliberate browser failure verification. No such
complete browser command or public-CI browser execution exists in this milestone.

The current Windows exact-leaf trust import limitation was already documented in
issue #8. This milestone did not retry stalled imports, create new trust, load
live credentials or run hosted MSX against the fixture. A native Chrome loopback
form denial was observed separately; it is not a hosted MSX test.

Real-server integration and physical Philips MSX/audio/remote verification remain
separate gates under [MSX testing](msx-testing.md) and the device checklist.
