"""Synthetic candidate descriptions are not supported hardware profiles."""

import copy
import json
from dataclasses import FrozenInstanceError, replace

import httpx
import pytest
from conftest import MOVIE, media_source
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.device_profile import PHILIPS, CandidateProfile, evidence_warnings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.playback import choose_source, compatible, profile

SYNTHETIC_AVC = CandidateProfile(
    name="synthetic-avc-test-only",
    model="Synthetic A (no hardware)",
    basis="synthetic_test_only",
    evidence_document="tests/test_profile_contract.py",
    containers=("mp4",),
    video_codecs=("h264",),
    audio_codecs=("aac",),
    conditional_audio=frozenset(),
    warnings=("Synthetic A: no device support claim",),
    preferred_size=(1280, 720),
)
SYNTHETIC_HEVC = replace(
    SYNTHETIC_AVC,
    name="synthetic-hevc-test-only",
    model="Synthetic B (no hardware)",
    containers=("mkv",),
    video_codecs=("hevc",),
    audio_codecs=("eac3",),
    conditional_audio=frozenset({"eac3"}),
    warnings=("Synthetic B: no device support claim",),
    preferred_size=(1920, 1080),
    preferred_video_codec="hevc",
)


def source_for(candidate, size=(1280, 720)):
    source = media_source()
    source["Id"] = candidate.name + str(size[1])
    source["Container"] = candidate.containers[0]
    source["MediaStreams"][0].update(Codec=candidate.video_codecs[0], Width=size[0], Height=size[1])
    source["MediaStreams"][1]["Codec"] = candidate.audio_codecs[0]
    return source


def test_two_synthetic_profiles_select_independently_from_the_same_versions():
    avc720, avc1080 = (source_for(SYNTHETIC_AVC, size) for size in ((1280, 720), (1920, 1080)))
    hevc720, hevc1080 = (source_for(SYNTHETIC_HEVC, size) for size in ((1280, 720), (1920, 1080)))
    item = {"MediaSources": [hevc720, avc1080, hevc1080, avc720]}
    before = copy.deepcopy(item)
    for sources in (item["MediaSources"], list(reversed(item["MediaSources"]))):
        assert (
            choose_source({"MediaSources": sources}, None, candidate_profile=SYNTHETIC_AVC)
            is avc720
        )
        assert (
            choose_source({"MediaSources": sources}, None, candidate_profile=SYNTHETIC_HEVC)
            is hevc1080
        )
    assert item == before
    # Default calls still apply Philips' ranking, never the most recent test profile.
    assert choose_source(item, None) is avc720
    assert not compatible(hevc720, candidate_profile=SYNTHETIC_AVC)
    assert not compatible(avc720, candidate_profile=SYNTHETIC_HEVC)


@pytest.mark.parametrize("candidate", [SYNTHETIC_AVC, SYNTHETIC_HEVC])
def test_candidate_negotiation_isolated_from_mutable_output_and_operator_policy(candidate):
    body = profile(candidate_profile=candidate)
    direct = body["DirectPlayProfiles"][0]
    assert body["Name"] == candidate.name
    assert direct == {
        "Container": candidate.containers[0],
        "Type": "Video",
        "VideoCodec": candidate.video_codecs[0],
        "AudioCodec": candidate.audio_codecs[0],
    }
    conditions = body["CodecProfiles"][0]["Conditions"]
    assert [(c["Property"], c["Value"], c["IsRequired"]) for c in conditions] == [
        ("Width", "1920", True),
        ("Height", "1080", True),
    ]
    assert body["TranscodingProfiles"] == [] and body["SubtitleProfiles"] == []
    body["DirectPlayProfiles"][0]["VideoCodec"] = "av1"
    conditions[0]["Value"] = "3840"
    assert profile(candidate_profile=candidate)["DirectPlayProfiles"][0] == direct | {
        "VideoCodec": candidate.video_codecs[0]
    }
    assert profile(candidate_profile=candidate)["CodecProfiles"][0]["Conditions"][0] == {
        "Condition": "LessThanEqual",
        "Property": "Width",
        "Value": "1920",
        "IsRequired": True,
    }
    assert profile()["Name"] == PHILIPS.name
    source = source_for(candidate)
    assert compatible(source, candidate_profile=candidate)
    assert not compatible(source, 1_000_000, candidate_profile=candidate)
    assert profile(1_000_000, candidate_profile=candidate)["MaxStaticBitrate"] == 1_000_000
    warnings = evidence_warnings(source, candidate_profile=candidate)
    assert warnings[0] == candidate.warnings[0]
    warnings.clear()
    assert evidence_warnings(source, candidate_profile=candidate)[0] == candidate.warnings[0]
    with pytest.raises(FrozenInstanceError):
        candidate.name = "changed"


@pytest.mark.parametrize("candidate", [SYNTHETIC_AVC, SYNTHETIC_HEVC])
@pytest.mark.parametrize("mutation", ["width", "height", "missing", "audio", "remote"])
def test_profiles_cannot_relax_hd_or_essential_metadata(candidate, mutation):
    source = source_for(candidate)
    if mutation == "width":
        source["MediaStreams"][0]["Width"] = 3840
    elif mutation == "height":
        source["MediaStreams"][0]["Height"] = 2160
    elif mutation == "missing":
        source["MediaStreams"][0].pop("Width")
    elif mutation == "audio":
        source["MediaStreams"][1].pop("Channels")
    else:
        source["IsRemote"] = True
    assert not compatible(source, candidate_profile=candidate)
    with pytest.raises(PortalError):
        choose_source({"MediaSources": [source]}, None, candidate_profile=candidate)
    if mutation in {"width", "height", "missing"}:
        with pytest.raises(PortalError):
            choose_source({"MediaSources": [source]}, None, True, candidate_profile=candidate)


@pytest.mark.parametrize("oversized", [False, True])
def test_request_hints_cannot_select_profile_or_expand_admission(portal, oversized):
    settings = replace(portal.settings, allow_transcoding=False)
    app = create_app(
        settings, transport=httpx.MockTransport(portal.fake.handle), state=portal.state
    )
    if oversized:
        portal.fake.source["MediaStreams"][0].update(Width=3840, Height=2160)
    hints = {
        "item_id": MOVIE,
        "profile": SYNTHETIC_HEVC.name,
        "platform": "untrusted-4k",
        "player": "untrusted-decoder",
        "width": 3840,
        "height": 2160,
    }
    with TestClient(app, base_url=settings.public_url) as client:
        result = client.get(portal.path + "/play.json", params=hints).json()
        assert result["response"]["status"] == (409 if oversized else 200)
    negotiations = [r for r in portal.fake.requests if r.url.path.endswith("/PlaybackInfo")]
    if oversized:
        assert not negotiations
    else:
        body = json.loads(negotiations[-1].content)
        assert body["DeviceProfile"] == profile()
        assert not body["EnableTranscoding"] and not body["EnableDirectStream"]
        assert portal.device.diagnostics[-1]["profile"] == PHILIPS.name
        assert not portal.device.diagnostics[-1]["device_playback_verified"]
