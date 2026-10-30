# Jellyfin server API compatibility

**Implemented; real-server verification pending — 2026-10-30.** This document
describes the isolated API check for issue #32. No new MSX rendering, audible
audio, physical-device or production deployment pass follows from this check.

## Selected versions and provenance

The [official server releases](https://github.com/jellyfin/jellyfin/releases)
list stable 12.0 (September 8), 12.1 (September 15), 12.2 (October 5),
12.3 (October 23) and 12.4 (October 26). The test matrix selects **every** one
of those releases, not only the oldest and newest. No older 10.x, prerelease,
future release, vendor build or non-Linux architecture is certified.

`tools/jellyfin_versions.json` pins the official `jellyfin/jellyfin` multi-platform
image index for each release. Both independent reviewers checked the exact
registry manifest response SHA256 and `Docker-Content-Digest` against these pins
on October 30. The official Docker Hub tag metadata agreed. CI executes Linux
amd64 children; an index containing other architectures is not a test of them.

Primary contract evidence at
[v12.4 revision 83d0d0e](https://github.com/jellyfin/jellyfin/tree/83d0d0e7f76e23e2e085c8ff67d28b772d35967d):

- [AuthorizationContext](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Server.Implementations/Security/AuthorizationContext.cs)
  accepts `MediaBrowser` authorization and `Token`, then canonical `ApiKey`.
  Legacy header/query support depends on `EnableLegacyAuthorization`; the client
  does not require that option. Do not describe legacy spellings as universally
  rejected by every Jellyfin 12 installation.
- [StartupController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/StartupController.cs)
  provides the first-time wizard. The probe uses that regular API and then regular
  password authentication, never an authentication bypass or server API key.
- [UserController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/UserController.cs)
  and [LibraryStructureController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/LibraryStructureController.cs)
  define isolated user/policy and library setup.
- [ImageController](https://github.com/jellyfin/jellyfin/blob/83d0d0e7f76e23e2e085c8ff67d28b772d35967d/Jellyfin.Api/Controllers/ImageController.cs)
  does not require authentication on the image bytes GET. Our portal separately
  authenticates its capability and rechecks the user's item access before image
  retrieval. Upstream image anonymity is not the portal's privacy boundary.

These links explain API choices; only executed jobs establish tested versions.
The GPL-licensed server runs as an external test dependency. No upstream
application code or proprietary MSX runtime is copied into this project.

## Reproduction and boundaries

On a disposable Linux machine with Docker, install the existing frozen build/dev
environment as described in [build-supply-chain.md](build-supply-chain.md), then:

```sh
uv run --no-sync python -m tools.jellyfin_contract --version 12.4
```

Repeat for each exact version in the JSON manifest. The separate
`.github/workflows/jellyfin-contract.yml` does this in a bounded five-job matrix.
The normal `uv run pytest` suite remains mocked and never starts or contacts a
real server. No dependency was added, and the harness/media remain excluded
from the application wheel, Docker build context and final image.

Each command creates two fresh servers in sequence: root and `/jellyfin`.
Each has a unique internal network, container, config/cache directory and a
read-only copy of the independently generated 30-second H.264/AAC 1280x720
[fixture](../tests/fixtures/msx-public/README.md). A minimal NFO omits optional
metadata and a synthetic poster supplies an image. Internet providers and
realtime monitoring are disabled; the internal network blocks container egress.
Only the runner accesses the container's own private bridge address; no ports
are published. HTTP is limited to this disposable isolated test network.

Generated passwords and tokens remain in the probe process and disposable
server state. No operator credentials, config, library or server are read.
Container stdout logging is disabled; raw HTTP responses, exception tracebacks,
passwords, tokens, pairing capabilities and media URLs are never emitted or
uploaded. Output contains only fixed check names, version/base path, pinned
digest, fixture hash and allowlisted optional-field shape observations.

The runner limits each server to two CPUs/1 GiB, Docker operations to 180 seconds,
readiness and scanning to 120 seconds each and each workflow job to 12 minutes.
Python cleanup removes only its generated container/network/temp directories;
an `always()` CI step removes and verifies only resources labeled for that exact
run/attempt/version. Cleanup failure fails the job. Abrupt runner loss still
relies on disposal of the GitHub-hosted runner; this is not a persistent host
service or production deployment.

## Assertions and limits

Each passing row requires all of the following actual observations:

- Public identity matches the selected exact version; no redirects are followed.
- Regular wizard setup and password sign-in work; wrong passwords and anonymous
  wizard reuse are denied. Playback uses a separate **non-admin** user.
- Real library scanning supplies sources/streams and tolerates minimal optional
  metadata. An anonymous session and a second user without library access cannot
  fetch the private item; the resolver also refuses the restricted user.
- The real portal returns a poster for the allowed user and denies missing
  capability/restricted-user image requests. This does not assert that upstream
  images themselves are private.
- The production resolver negotiates Direct Play with conversion/remux disabled,
  emits the exact configured stream base path and exactly one canonical `ApiKey`.
  A real 206 range response matches the first 1024 bytes of the original fixture.
- Logout revokes the user session for both item and original-file requests.

Optional scalar shape observations are distinct from deliberately injected null
collection cases. Existing mocked `tests/test_regressions.py` covers nullable
collections, invalid shapes and missing essential decoder metadata. A minimal
real library must not be described as proof that every nullable collection was
observed on the wire. No raw metadata capture is retained.

Fresh-server API compatibility is not an in-place server/database upgrade test.
Re-run the exact fixtures on a proposed release before expanding the advertised
set; retain any failed stage as an upgrade regression. HLS, burn-in, HEVC device
decoding, arbitrary media libraries, reverse-proxy/TLS behavior and full private
hosted MSX flows are outside this API matrix. The 1920x1080 admission policy,
default no-conversion/no-video-proxy behavior and direct-token exposure remain
unchanged.

## Actual results

Initial runs failed in the harness before API observations: published ports were
unavailable on the internal Docker network. The probe now addresses the isolated
bridge directly. No supported-version claim is based on those failed runs.
Final passing runs and exact observations will be recorded here after execution.
