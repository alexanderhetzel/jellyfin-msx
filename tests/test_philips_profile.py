import json
from urllib.parse import urlsplit

import pytest
from conftest import MOVIE, TOKEN, media_source

from jellyfin_msx.config import Settings
from jellyfin_msx.device_profile import MODEL, PROFILE_NAME, VIDEO_CODECS, evidence_warnings
from jellyfin_msx.playback import compatible, profile, resolve, stream_summary


def test_model_profile_advertises_hd_policy_without_default_bandwidth_ceiling():
    settings = Settings("https://portal.test", "https://jellyfin.test")
    assert settings.max_bitrate is None and not settings.allow_transcoding
    result = profile()
    assert result["Name"] == PROFILE_NAME and "32phs6605-12" in result["Name"]
    codec_profile = result["CodecProfiles"][0]
    assert codec_profile["Type"] == "Video"
    assert set(codec_profile["Codec"].split(",")) == set(VIDEO_CODECS)
    assert codec_profile["Conditions"] == [
        {"Condition": "LessThanEqual", "Property": "Width", "Value": "1920", "IsRequired": True},
        {"Condition": "LessThanEqual", "Property": "Height", "Value": "1080", "IsRequired": True},
    ]
    assert "MaxStreamingBitrate" not in result and "MaxStaticBitrate" not in result
    assert result["TranscodingProfiles"] == [] and result["SubtitleProfiles"] == []


@pytest.mark.parametrize("codec", ["h264", "hevc", "vp9", "mpeg2video", "vc1"])
def test_documented_video_candidates_are_not_labelled_device_verified(codec):
    source = media_source()
    source["MediaStreams"][0]["Codec"] = codec
    assert compatible(source)
    assert "not yet verified" in " ".join(evidence_warnings(source))


@pytest.mark.parametrize("audio", ["aac", "mp3", "ac3", "eac3", "dts"])
def test_mkv_multichannel_candidates_are_not_blocked_by_old_stereo_rule(audio):
    source = media_source()
    source["Container"] = "mkv"
    source["MediaStreams"][1].update(Codec=audio, Channels=6)
    assert compatible(source)
    if audio in {"ac3", "eac3", "dts"}:
        assert "conditional" in " ".join(evidence_warnings(source))


def test_1080p_candidate_does_not_invent_other_decoder_limits():
    source = media_source()
    source["Bitrate"] = 35_000_000
    source["MediaStreams"][0].update(
        Width=1920,
        Height=1080,
        Codec="hevc",
        BitDepth=10,
        Level=153,
        AverageFrameRate=60,
        VideoRange="HDR",
        VideoRangeType="HDR10",
    )
    assert compatible(source)  # Trial candidate, not proof that HDR/60fps works.
    assert not compatible(source, 4_000_000)  # Explicit operator budget only.
    assert profile(4_000_000)["MaxStaticBitrate"] == 4_000_000


@pytest.mark.parametrize("codec", VIDEO_CODECS)
@pytest.mark.parametrize(
    "size", [(3840, 2160), (4096, 2160), (3840, 1600), (1921, 1080), (1920, 1081)]
)
def test_hd_policy_rejects_each_oversized_axis_for_every_video_codec(codec, size):
    source = media_source()
    source["MediaStreams"][0].update(Codec=codec, Width=size[0], Height=size[1])
    assert not compatible(source)  # No optional bitrate budget needed to reject UHD.


def test_optional_bitrate_environment_is_not_a_device_limit(monkeypatch):
    monkeypatch.setenv("MSX_PUBLIC_URL", "https://portal.test")
    monkeypatch.setenv("JELLYFIN_URL", "https://jellyfin.test")
    monkeypatch.setenv("MSX_MAX_BITRATE", "")
    assert Settings.from_env().max_bitrate is None
    monkeypatch.setenv("MSX_MAX_BITRATE", "20000000")
    assert Settings.from_env().max_bitrate == 20_000_000


def test_actual_720p_mkv_eac3_shape_negotiates_original_without_conversion(portal):
    import asyncio
    from dataclasses import replace

    import httpx

    from jellyfin_msx.jellyfin import Jellyfin

    source = portal.fake.source
    source["Container"] = "mkv"
    source["Bitrate"] = 2_700_000
    source["MediaStreams"][0].update(Profile="Main", Level=31, AverageFrameRate=24)
    source["MediaStreams"][1].update(Codec="eac3", Channels=6)
    settings = replace(portal.settings, allow_transcoding=False)

    async def run():
        jf = Jellyfin(settings, httpx.MockTransport(portal.fake.handle))
        try:
            return await resolve(jf, portal.device, MOVIE, False, -1)
        finally:
            await jf.client.aclose()

    url, event = asyncio.run(run())
    assert urlsplit(url).path.endswith("/stream.mkv")
    body = json.loads(portal.fake.requests[-1].content)
    assert body["EnableDirectPlay"] and not body["EnableDirectStream"]
    assert not body["EnableTranscoding"] and body["SubtitleStreamIndex"] == -1
    assert "MaxAudioChannels" not in body and "MaxStreamingBitrate" not in body
    assert "eac3" in body["DeviceProfile"]["DirectPlayProfiles"][0]["AudioCodec"].split(",")
    assert event["device_model"] == MODEL and not event["device_playback_verified"]
    assert "conditional" in " ".join(event["warnings"])


def test_unrestricted_optional_metadata_does_not_leak_into_diagnostics():
    source = media_source()
    source["MediaStreams"][0]["BitDepth"] = TOKEN
    source["MediaStreams"][1]["Width"] = TOKEN
    assert TOKEN not in json.dumps(stream_summary(source))
    assert compatible(source)
