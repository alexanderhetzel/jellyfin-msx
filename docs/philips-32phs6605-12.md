# Philips 32PHS6605/12: documentation-based playback candidates

Research and implementation decision, 2026-10-30. Scope is this model, not all TVs.
No physical MSX playback has been verified yet.

**Current client decision: HD-only, at most 1920x1080 encoded video. 4K playback
and 4K-to-HD downscaling are not supported by this client.** A stored eligible
720p/1080p version is required on the direct-only Ultra deployment. This is an
enforced admission policy, not a claim that a public chip datasheet establishes
the exact decoder maximum.

## Sources and their limits

- [Model user manual](https://www.documents.philips.com/assets/20230227/9e5696eeba3d4657b72aafb600fb5f51.pdf),
  printed pp. 63–64, sections 21.3–21.7: 1366x768 panel; multimedia lists AVI/MKV,
  H.264, HEVC, VP9, MPEG-1/2/4 and WMV9/VC1. Audio list includes AAC, MP3,
  WAV, WMA and WMA Pro. This is a multimedia list, not an MSX codec matrix.
- The same manual, printed pp. 46–47, discusses Dolby Digital Plus streaming
  and HDMI ARC/bypass. That is conditional audio-output evidence, not proof of
  E-AC-3/Atmos decoding through MSX or its internal speakers. DTS-HD is also
  mentioned in the sound section without an MSX container/channel matrix.
- [Exact-model datasheet](https://www.documents.philips.com/assets/20230723/249fb05d4a624c758fd8b0480100aeac.pdf),
  p. 3: confirms the main multimedia list. It does not list AV1, unlike an
  ambiguous entry in the manual; AV1 is therefore not advertised.
- [MSX platform support](https://msx.benzac.de/info/?tab=PlatformSupport) identifies
  the TP Vision App Gallery/Smart TV Alliance SDK path, separately from HbbTV.
  The installed TV's actual platform/player still needs to be recorded.
- [Smart TV Alliance 3.0 specification](https://smarttv-alliance.org/devwebsitedownloads/safe/SmartTVAlliancev3.0specification.pdf),
  sections 3.4.1–3.4.5: HTML5 streaming baseline includes MP4/TS, AVC and
  HE-AAC/AC-3. This is platform evidence; the historic conformed-device list does
  not individually certify the 2020 model or the installed MSX implementation.
- [TP Vision service manual, 3122 785 21051, 2020-09-01](https://device.report/m/cc7730a85a9545711ae63ea97f9b3459333adc89806b4cee3960591433cef941.pdf)
  (manufacturer document on a third-party mirror), cover: explicitly includes
  32PHS6605/12 in chassis TPM20.7E LA, platform MTK9288. The shared product table
  also covers Full-HD models; its 1920x1080 panel entry must not be assigned to
  this model. The IC data-sheet section on printed p. 34 describes an audio
  amplifier, not a video decoder or its resolution limit.
- [Official TPV service bulletin SCC2107138V01, revision 1.6](https://gsp.tpv-tech.com/AYS/CSPAPI/Upload/SymptomCureQuestion/SCC2107138V01_One%20button%20recovery%20revision_1.6_20231027072714.pdf)
  independently maps TPM20.7E LA to MT9288. Only documentation was read; no
  recovery procedure, firmware download or device modification was performed.
- [Whale developer device mapping](https://developer.whaletv.com/partnerportal/DeviceMapping/index.jhtml)
  lists Philips MT9288, Linux, 2020. Its general
  [media specification](https://developer.whaletv.com/partnerportal/MediaSpecification/index.jhtml)
  provides streaming combinations and HD ABR requirements, but is not an
  exact-model or installed-MSX UHD certification. ABR limits must not silently
  become limits for progressive original-file playback.

HDMI accepts 1080p, but HDMI timing is not a decoder limit. Panel resolution is
not the maximum compressed-video input resolution. No inspected exact-model
source specifies a general MSX bitrate, frame-rate, H.264 level, channel-count
or bit-depth ceiling. The previous 720p/30fps/level-3.1/AAC-stereo limits were
engineering assumptions and are removed as device restrictions.

The inspected exact-model, chassis and platform sources do not establish 2160p
file decoding/downscaling through MSX. No public MT9288 decoder capability table
was found in the targeted chipset/datasheet search. Absence of a published maximum
does not justify admitting arbitrary resolutions. The HD-only policy above
therefore supersedes the earlier unrestricted-resolution candidate profile.
1920x1080 is a conservative application boundary within the documented HD/Full-HD
context, not a proven compressed-video maximum derived from HDMI or panel size.

## Implemented contract

The named profile represents **documentation-based candidates**, not a tested
support guarantee. Multimedia/platform candidates can be offered to Jellyfin
PlaybackInfo and tried as original files. MKV and multichannel Dolby candidates
are no longer rejected by the old MP4/AAC-stereo rule. E-AC-3, AC-3 and DTS carry
an explicit conditional-audio warning. Unsupported/unlisted metadata is described
as outside this candidate profile, never proof that the TV cannot play it.
Implemented container candidates are MP4, MKV, AVI and MPEG2-TS (`ts`/`mpegts`
aliases). Codec names do not by themselves establish additional containers such
as ASF or MPEG-PS. WAV in the music list does not establish a particular PCM
bit-depth/AV combination, so no PCM candidate is inferred from it. WMA version 1
is not advertised because the model's list starts at version 2.

The `philips-32phs6605-12-hd-policy-v2` profile enforces width <=1920 and height
<=1080 before negotiation and on the returned PlaybackInfo source. Required
Width/Height conditions communicate the same boundary to Jellyfin for every
advertised video codec. A cropped 3840x1600 file is also excluded; the decision
uses both encoded dimensions, not a file name or a misleading "2160p" label.
4K-only items expose no play action and make no PlaybackInfo request on Ultra.
An eligible stored HD copy is selected and pinned when present. No level,
frame-rate, SDR-only or stereo-only ceiling is invented.
An optional operator bitrate budget is separate from device capability and is
unset by default. Remote sources needing headers/opening remain blocked because
the current transport cannot safely satisfy them. Essential stream metadata is
still required. Original-container stream URLs preserve MKV/AVI/etc.; a .mp4
suffix must not misrepresent every original file.

Transcoding, remuxing and burn-in remain disabled on Ultra. No automatic
conversion is introduced to make a candidate play. Subtitles stay off by default;
USB subtitle formats do not establish native MSX subtitle support.

## Evidence required before promising support on this TV

Record firmware, MSX version/platform/player, speaker/ARC output and the exact
media properties. Exercise original MP4/H.264/AAC, MKV/H.264/AAC and the current
MKV/H.264/E-AC-3 candidate separately; test HEVC and VP9 separately as well.
For each combination record picture, sound, start, pause, seek and stop. Only a
physical-TV pass can promote a candidate to verified for this TV. A desktop pass
or Jellyfin SupportsDirectPlay flag cannot do that.

Editing the profile does not automatically restart the lab; a restart discards
RAM sessions. After the operator requested the next step, the lab was explicitly
restarted with HD-policy-v2 and fresh human pairing succeeded. An existing 720p
MKV/H.264/E-AC-3 source subsequently passed MSX web video startup, pause/resume,
forward/back seek, Stop and replay. Audible audio and physical SAPHI playback
were not established. Runtime evidence
must identify the profile actually loaded. Old-profile results remain historical.
