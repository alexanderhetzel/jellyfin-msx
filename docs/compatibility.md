# Compatibility evidence

Jellyfin MSX continues the original Jellyfin/MSX client. Compatibility is
recorded per actual device, runtime, media combination and test outcome.

| Platform/device | Evidence | Status |
| --- | --- | --- |
| macOS integrated browser | Official MSX web 0.1.167; real Jellyfin authentication, browsing/posters, 720p MKV/H.264 video, pause/resume/seek/Stop/replay | Browser video passed; audible audio not independently verified |
| Philips 32PHS6605/12, SAPHI | Exact-model documentation and MTK9288 identity; current candidate profile and admission policy | Physical MSX video, audio, remote and long playback not run |
| Other MSX devices | No device evidence yet | Unverified |

The private integration lab exercised a Jellyfin release reporting 12.4.0.
This is one observed release, not a complete supported-version range.

Only one candidate profile is currently implemented. It allows documented codec/
container candidates with valid metadata and at most 1920x1080 encoded video.
4K playback/downscaling is excluded by client policy. Dolby/DTS paths require
audible speaker/ARC testing. Subtitles remain off by default; Ultra conversion
is disabled. See [model evidence](philips-32phs6605-12.md),
[browser results](msx-test-results.md) and [physical results](device-test-results.md).

New profiles/devices require explicit evidence and tests. Frontend-reported
platform/player strings cannot grant additional playback permissions. Request
device work through GitHub Issues with firmware, MSX/player version and sanitized
media properties. Never include real servers, credentials, activation/capability
URLs, private media titles or file paths.
