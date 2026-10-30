# Jellyfin MSX

A Jellyfin client for [Media Station X](https://msx.benzac.de/info/).

This fork continues [SerhiyRomanov/jellyfin-msx:master](https://github.com/SerhiyRomanov/jellyfin-msx/tree/master)
with companion-device sign-in, authenticated library browsing, Jellyfin playback
negotiation and diagnostics. Use MSX as the TV interface and your existing
Jellyfin server as the media source.

## Features

- Pair MSX with your Jellyfin account using a companion browser and a TV code.
  Passwords are submitted over HTTPS and are not stored by the portal.
- Browse movies, series, seasons and episodes with posters, metadata and pagination.
- Request playback through Jellyfin PlaybackInfo and select an eligible stored
  version consistently across details and playback.
- Play original files directly from Jellyfin; video does not pass through the
  portal by default. Original containers are preserved.
- Inspect redacted diagnostics explaining source selection, policy denials,
  playback decisions and the reported MSX platform/player.
- Run a modular Python/FastAPI backend locally or with Docker and Caddy HTTPS.

Transcoding is disabled by default. Optional HLS/burn-in negotiation is available
only for explicitly permitted hosts and remains unverified on physical TVs.
The tested Ultra.cc deployment is strictly Direct Play only.

## Development status and compatibility

This is a development prototype. Official MSX web playback against a real
Jellyfin server has passed video startup, pause/resume, forward/backward seeking,
Stop and replay. Physical-TV acceptance and production readiness remain open.

| Environment | Current evidence |
| --- | --- |
| Official MSX web 0.1.167 on macOS | Browsing, posters and 720p MKV/H.264 video playback/control passed; audible audio not independently confirmed |
| Philips 32PHS6605/12, SAPHI | Documentation-based candidate profile; physical MSX playback, audio and remote verification pending |
| Other MSX devices/platforms | Not yet verified; do not infer compatibility from the browser or another TV |

See the [compatibility list](docs/compatibility.md) and
[actual test results](docs/msx-test-results.md). The current implementation uses
one candidate profile with a conservative **1920x1080 admission limit**;
4K playback/downscaling is excluded. This is a current policy boundary, not a
promise about every MSX device or a proven silicon decoder maximum.

Persistent device pairing, QR/staged activation, playback progress/resume and
native track/subtitle switching are tracked in
[GitHub Issues](https://github.com/alexanderhetzel/jellyfin-msx/issues).

## Run locally

Requires Python >=3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen --extra dev
export MSX_PUBLIC_URL=http://localhost:8090
export JELLYFIN_URL=https://your-jellyfin.example.com
export MSX_ALLOW_HTTP=true
uv run uvicorn jellyfin_msx.app:create_app --factory --host 127.0.0.1 --port 8090 --workers 1 --no-access-log --no-proxy-headers
```

This is an explicit loopback HTTP development mode. The hosted HTTPS MSX runtime
requires an HTTPS portal; use the [MSX test lab](docs/msx-testing.md) for that flow.
`localhost` on a TV refers to the TV itself, so real-device use requires a
TV-reachable portal with trusted HTTPS.

## Docker and HTTPS

```sh
cp .env.example .env
# Configure your domains and Jellyfin URL in .env; never commit live values.
docker compose up --build -d
```

Caddy obtains a certificate when DNS and ports 80/443 are correctly configured.
Run one portal process/worker while sessions are RAM-only. The TV must also reach
Jellyfin directly over HTTPS. See [deployment and security](docs/deployment.md).

## Set up Media Station X

1. In MSX, open **Settings → Start Parameter → Setup**.
2. Enter only the portal **hostname or IP with optional port**. Use the lock for
   HTTPS. MSX adds `/msx/start.json`; do not enter `https://` or a path here.
3. Open the displayed companion page, enter the TV code and sign in to Jellyfin.
4. Select **Continue after pairing** in MSX, browse and choose **Try original**.
5. Use **Diagnostics** for troubleshooting and **Disconnect TV** to sign out.

Current sessions expire after eight hours and do not survive a backend restart.
Reloading the pairing start page creates a new pairing. Remembered devices are
planned, not implemented; see the Project.

## Development

Work lives in [repository Issues](https://github.com/alexanderhetzel/jellyfin-msx/issues)
and the [Jellyfin MSX Project](https://github.com/users/alexanderhetzel/projects/5).
Read [CONTRIBUTING](CONTRIBUTING.md), [development workflow](docs/development.md)
and [AGENTS.md](AGENTS.md) before making changes.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build --wheel
```

Automated tests use mocked Jellyfin data. Browser and physical-device evidence
are recorded separately; a test count is not a TV playback certificate.

Further documentation: [architecture](docs/architecture.md),
[research](docs/research.md), [verification status](docs/status.md),
[physical-device checklist](docs/device-test-checklist.md).

## License and provenance

The independently authored current implementation is **MIT licensed**. The
original upstream `master` and inherited history retain their original licensing
status and are excluded from our MIT grant. Upstream did not include a source
license at the inspected revision; its application code/assets were not copied
into the current implementation. See [LICENSE](LICENSE) and [NOTICE](NOTICE.md).

MSX is a separately licensed runtime accessed through its public API. This
repository does not distribute it and is not affiliated with Jellyfin, Benzac,
Philips or TP Vision.
