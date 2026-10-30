# Playback profile and compatibility contract

Issue #34, reviewed-source contract researched on 2026-10-30.

**Implemented / automated-tested / device-unverified:** the single production
default remains `philips-32phs6605-12-hd-policy-v2`. Immutable candidate descriptions
now separate codec/container candidates and ranking preferences from the shared
1920x1080 application admission policy. Two synthetic descriptions exercise the
pure selection/PlaybackInfo helpers; they are test fixtures, not extra devices.
**Deferred:** exposing additional production profiles or a profile selector.

## Evidence and trust

The [official MSX request contract](https://www.msx.benzac.de/wiki/index.php?title=Requests&oldid=3579)
describes URL substitutions for platform, player and display dimensions. The
[web URL parameters](https://www.msx.benzac.de/wiki/index.php?title=URL_Parameters)
also allow the web platform identifier to be set. The
[official Play Plugin](https://www.msx.benzac.de/wiki/index.php?title=Play_Plugin&oldid=3444)
offers runtime player selection. These are useful observations about the caller's
runtime, not authenticated hardware/decoder attestations. The application must
never use them to expand candidate codecs, dimensions, bitrate budgets or
conversion permissions. A session capability authenticates access, not the
truth of the platform/player fields supplied by its holder.

The [exact-model Philips datasheet](https://www.documents.philips.com/assets/20230723/249fb05d4a624c758fd8b0480100aeac.pdf)
(version 5.0.1, issue date 2024-03-24, p. 3) separately lists panel resolution,
HDMI display inputs, multimedia formats and music formats. That separation does
not establish arbitrary AV mux/codec combinations or MSX decoder maxima. HEVC
and VP9 appear in its multimedia list; neither is thereby a physical MSX pass.
The [model evidence](philips-32phs6605-12.md) retains exact-model/manual, qualified
platform and conditional speaker/ARC evidence with their limitations. No new
chipset, audio, MSX platform or decoder-capability claim is introduced here.

The sources above were read as documentation only. No proprietary runtime code
was copied, hosted or modified; no TV, firmware, operator server or credentials
were used. The MSX Info platform-support URL returned its dynamic shell to the
research tool, so it is not new confirmation of an installed platform.

## Separate decisions

| Input | Owner and effect | Cannot establish |
| --- | --- | --- |
| Versioned candidate description | Reviewed server source: identity, evidence document, candidate container/video/audio sets, conditional audio and warnings | Successful decoding or every Cartesian product of listed codecs/containers |
| Preferred codec and size | Ranking among otherwise eligible stored sources; current Philips preference remains AVC, then within 1366x768, then size | A decoder maximum or permission to exceed admission |
| HD admission | Shared application policy: encoded width <=1920 and height <=1080, including cropped UHD and optional-conversion paths | Hardware/chip limits or permission for 4K/downscaling |
| Operator bitrate/conversion settings | Separate network/hosting restrictions; no bitrate cap by default, conversion/burn-in disabled by default | Device capability or authority from request hints |
| Platform/player strings; display hints | Platform/player are untrusted, bounded observations in existing diagnostics; display hints are not recorded or used | Profile selection, playback permission or physical verification |
| PlaybackInfo support flags | Necessary server negotiation result, revalidated against the pinned source and local rules | Visible picture, audible sound or remote behavior |

Essential container/video/dimensions/audio/channel metadata and transport-opening
checks remain mandatory for direct candidates. A profile cannot disable them.
Optional conversion retains its existing separate opt-in behavior; this milestone
does not qualify that path for a new profile or change its admission checks.
Both production detail and resolve paths still use the same fixed Philips
default. `CandidateProfile` and keyword-only helper arguments are trusted Python
test seams, not request/config deserializers or a production registry. Do not
pass HTTP fields, arbitrary JSON or client-provided codec lists into them.

## Selection contract before another production device

The safe current behavior is the existing explicitly named Philips candidate
deployment. It is not a generic profile for an unidentified TV. Unknown devices
have no supported profile today; use on another device is unverified and does
not change admission. No `MSX_PLAYBACK_PROFILE` environment setting, request
`profile` parameter or multi-device UI is supported by this milestone. Unknown
query parameters have no selection effect; existing platform/player parameters
are observations only.

A later rollout must satisfy these requirements in its owning issue:

1. Add a reviewed, versioned server-side allowlist entry with model/runtime scope,
   primary evidence and explicit candidate/conditional limitations. Never invent
   limits from panel size, HDMI timing, a browser pass or absence of documentation.
   Keep global HD admission and operator policy separate. A profile revision
   changing admission requires its own explicit reviewed policy decision.
2. Initially select one allowlisted profile through trusted deployment settings.
   Absence preserves the current Philips default only for that documented
   deployment; an explicit unknown/empty/invalid selection fails startup. Never
   silently fall back from a misspelled selection, union multiple profiles or
   auto-select using user-agent/platform/player/display hints.
3. If multiple devices share a deployment later, bind an explicitly approved
   selection to authenticated server-side session state. Any companion change
   needs normal same-origin/CSRF protection and server allowlist authorization.
   A displayed device suggestion or client platform claim is not approval.
4. Bind each detail action to the effective profile revision and exact source ID;
   resolve must reauthorize the item and recheck the profile/source against fresh
   metadata. A profile change invalidates stale details and subtitle indices;
   reopening details is required. Durable renewal must preserve/revalidate this
   binding or invalidate it; it must not restore broader permissions by default.
5. Thread that one resolved profile through details, selection, rejection reasons,
   PlaybackInfo, returned-source validation, subtitle admission and diagnostics.
   Remove hardwired model labels only with actual official-MSX UI verification.
   Do not expose the helper test seam as a partially connected runtime selector.

These are rollout requirements, not claims that session profile switching,
revision binding or environment selection has been implemented in #34.

## Diagnostics and UI contract

Current diagnostics expose the fixed profile name/basis, bounded platform/player
observations, sanitized stream properties, warnings and
`device_playback_verified=false`. They record a decision, not decoder success.
The detail UI retains “Try original (TV unverified)”, the named Philips candidate,
conditional-audio warning and HD rejection explanation. No UI was changed or
browser-tested for this contract milestone.

Before a new profile is exposed, diagnostics must identify the effective
allowlisted ID/revision, evidence basis/reference, application admission and
operator restrictions separately from observed runtime/player information.
Use fixed server-owned values and bounded fields, no private media titles/paths,
tokens, capability URLs or raw captures. A profile-wide verified boolean must
not be promoted from a single media test. Show the effective model/candidate
status and useful rejection/recovery instructions in the UI; a user must not
infer that a profile or player switch guarantees playback or enables conversion.

Maintain separate evidence records:

- **Implemented / automated-tested:** mocked transport and policy/selection/HTTP
  tests, with actual commands/results in [status](status.md).
- **Browser-tested:** actual official MSX version/player/OS, media properties,
  visible actions, picture/time and separately observed sound. Existing browser
  evidence remains in [compatibility](compatibility.md); it is not inherited by
  a new profile or runtime.
- **Device-unverified**, until an exact physical combination passes: model,
  firmware, MSX/platform/player, profile revision, container/video/audio/resolution,
  speaker/ARC path, start/picture/sound/sync/pause/seek/Stop/long-play results and
  redacted diagnostics in [device results](device-test-results.md). Failures and
  untested combinations remain explicit. HEVC and conditional Dolby/DTS retain
  candidate status until that evidence exists.

## Required regression proof

`tests/test_profile_contract.py` uses two synthetic profiles with different
containers/codecs/preferred sizes. The same version pool selects an AVC/MP4
720p source for A and HEVC/MKV 1080p for B, independent of ordering. Cross-profile
sources are denied; each generated PlaybackInfo declaration uses its own codec
sets but the same required HD conditions. Mutating an output cannot alter another
call or the immutable description. Separate operator bitrate restrictions still
apply. Missing essential metadata, remote-opening sources and either oversized
axis remain rejected; even optional conversion cannot admit unknown/oversized
dimensions. Request profile/platform/player/display hints leave actual production
negotiation fixed to Philips and cannot admit UHD.

A later runtime rollout additionally needs real route tests with two sessions,
opposed profiles and the same multi-version item: details/resolve/PlaybackInfo/
returned-source/subtitle consistency; stale profile revisions and reordered,
removed, duplicate or newly ineligible sources; source and subtitle absolute-index
pinning; profile A must never leak permissions into B. Test unknown config,
client hint spoofing, expired/revoked grants, item denial, malicious URLs and all
default conversion prohibitions. Preserve mocked transport for the normal suite.
Then verify actual UI in official MSX and retain physical acceptance separately.
The synthetic helper tests do not substitute for these future route/UI/device
requirements or certify a second hardware profile.
