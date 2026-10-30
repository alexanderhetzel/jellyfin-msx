import copy
import json
from dataclasses import replace

import httpx
import pytest
from conftest import MOVIE, SOURCE, TOKEN, media_source
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.playback import choose_source, compatibility_reasons, compatible, profile


@pytest.fixture
def direct(portal):
    settings = replace(portal.settings, allow_transcoding=False)
    app = create_app(
        settings, transport=httpx.MockTransport(portal.fake.handle), state=portal.state
    )
    with TestClient(app, base_url=settings.public_url) as client:
        yield client


def test_default_configuration_never_advertises_transcoding():
    assert not Settings("https://portal.test", "https://jellyfin.test").allow_transcoding
    result = profile(4_000_000, allow_transcoding=False)
    assert result["TranscodingProfiles"] == [] and result["SubtitleProfiles"] == []


def test_selects_720p_after_4k_version_instead_of_first_source():
    high = media_source()
    high["Id"] = "9" * 32
    high["MediaStreams"][0].update(Width=3840, Height=2160, Codec="hevc", BitDepth=10)
    low = media_source()
    assert choose_source({"MediaSources": [high, low]}, 4_000_000)["Id"] == SOURCE


def test_incompatible_version_fails_without_transcoding():
    high = media_source()
    high["Container"] = "unknown"
    with pytest.raises(PortalError, match="Transcoding is disabled"):
        choose_source({"MediaSources": [high]}, 4_000_000)


def test_real_route_sends_direct_only_playbackinfo(portal, direct):
    response = direct.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert response.json()["response"]["status"] == 200
    body = json.loads(portal.fake.requests[-1].content)
    assert body["EnableDirectPlay"] is True
    assert body["EnableTranscoding"] is False and body["EnableDirectStream"] is False
    assert body["SubtitleStreamIndex"] == -1
    assert body["DeviceProfile"]["TranscodingProfiles"] == []
    assert portal.device.diagnostics[-1]["transcoding_allowed"] is False


@pytest.mark.parametrize("params", [{"force": True}, {"subtitle": 2}])
def test_force_and_burnin_are_denied_before_any_upstream_work(portal, direct, params):
    response = direct.get(portal.path + "/play.json", params={"item_id": MOVIE, **params})
    assert response.json()["response"]["status"] == 409
    assert not portal.fake.requests


def test_hides_transcode_and_burn_in_controls(portal, direct):
    page = direct.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    titles = [entry["title"] for entry in page["items"]]
    assert "Try original (TV unverified)" in titles
    assert not any(
        "transcode" in title.lower() or "burn subtitle" in title.lower() for title in titles
    )


def test_denied_direct_play_ignores_returned_transcoding_url(portal, direct):
    portal.fake.source["SupportsDirectPlay"] = False
    response = direct.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert response.json()["response"]["status"] == 409
    assert "Transcoding is disabled" in response.text
    assert len([r for r in portal.fake.requests if r.url.path.endswith("/PlaybackInfo")]) == 1


def test_incompatible_item_details_explain_missing_version(portal, direct):
    portal.fake.source["MediaStreams"][0]["Codec"] = "av1"
    page = direct.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    assert page["items"][0]["title"] == "Outside documented candidate profile"
    assert all(not entry["action"].startswith("video:") for entry in page["items"])
    response = direct.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert response.json()["response"]["status"] == 409
    assert not any(r.url.path.endswith("/PlaybackInfo") for r in portal.fake.requests)


@pytest.mark.parametrize("allow_transcoding", [False, True])
def test_4k_only_routes_explain_hd_copy_and_never_negotiate_or_transcode(portal, allow_transcoding):
    portal.fake.source["MediaStreams"][0].update(Width=3840, Height=2160, Codec="hevc")
    settings = replace(portal.settings, allow_transcoding=allow_transcoding)
    app = create_app(
        settings, transport=httpx.MockTransport(portal.fake.handle), state=portal.state
    )
    with TestClient(app, base_url=settings.public_url) as client:
        page = client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
        assert all(not entry["action"].startswith("video:") for entry in page["items"])
        assert "1920x1080 client limit" in json.dumps(page)
        result = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
        assert result.json()["response"]["status"] == 409
        assert "720p/1080p copy" in result.text
        if not allow_transcoding:
            assert "Transcoding is disabled" in result.text
    assert not any(r.url.path.endswith("/PlaybackInfo") for r in portal.fake.requests)


@pytest.mark.parametrize("allow_transcoding", [False, True])
def test_4k_returned_after_hd_selection_cannot_bypass_local_policy(portal, allow_transcoding):
    original = portal.fake.handle

    def changed_source(request):
        response = original(request)
        if request.url.path.endswith("/PlaybackInfo"):
            body = response.json()
            body["MediaSources"][0]["MediaStreams"][0].update(Width=3840, Height=2160)
            return httpx.Response(200, json=body)
        return response

    settings = replace(portal.settings, allow_transcoding=allow_transcoding)
    app = create_app(settings, transport=httpx.MockTransport(changed_source), state=portal.state)
    with TestClient(app, base_url=settings.public_url) as client:
        result = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
        assert result.json()["response"]["status"] == 409
        assert "1920x1080 limit" in result.text
        assert TOKEN not in result.text and "stream.mp4" not in result.text
        assert len([r for r in portal.fake.requests if r.url.path.endswith("/PlaybackInfo")]) == 1


def test_profile_rejection_explains_unlisted_metadata_without_conversion(portal, direct):
    portal.fake.source["Container"] = "unlisted"
    portal.fake.source["MediaStreams"][0]["Level"] = 41
    portal.fake.source["MediaStreams"][1].update(Codec="truehd", Channels=None)
    page = direct.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    explanation = next(x["action"] for x in page["items"] if x["title"] == "Compatibility details")
    for reason in (
        "Container is not covered",
        "audio codec is not covered",
        "channel count missing",
    ):
        assert reason in explanation
    diagnostic = direct.get(f"/api/device/{portal.secret}/diagnostics")
    event = diagnostic.json()["events"][-1]
    assert event["event"] == "compatibility_rejection"
    assert event["versions"][0]["version"] == 1
    assert event["transcoding_allowed"] is False
    for private in (TOKEN, MOVIE, SOURCE, portal.secret, "A movie"):
        assert private not in diagnostic.text and private not in explanation
    assert not any(r.url.path.endswith("/PlaybackInfo") for r in portal.fake.requests)


def test_reason_text_never_reflects_arbitrary_upstream_fields():
    source = media_source()
    assert compatibility_reasons(source, 4_000_000) == [] and compatible(source, 4_000_000)
    source.update(Container=TOKEN, Path="/private/movie.mkv", RequiredHttpHeaders={"X": TOKEN})
    source["MediaStreams"][0].update(Codec=TOKEN, Profile=TOKEN, VideoRange=TOKEN, BitDepth=None)
    reasons = compatibility_reasons(source, 4_000_000)
    assert reasons and not compatible(source, 4_000_000)
    assert TOKEN not in json.dumps(reasons) and "private" not in json.dumps(reasons)
    assert "Video codec is not covered by the documented candidate profile" in reasons


def test_multi_version_http_route_pins_compatible_source(portal):
    original = portal.fake.handle

    def versions(request):
        response = original(request)
        if request.url.path.endswith("/Items/" + MOVIE):
            item = response.json()
            high = copy.deepcopy(item["MediaSources"][0])
            high["Id"] = "9" * 32
            high["MediaStreams"][0].update(Width=3840, Height=2160, Codec="hevc")
            item["MediaSources"].insert(0, high)
            return httpx.Response(200, json=item)
        return response

    settings = replace(portal.settings, allow_transcoding=False)
    app = create_app(settings, transport=httpx.MockTransport(versions), state=portal.state)
    with TestClient(app, base_url=settings.public_url) as client:
        result = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
        assert result.json()["response"]["status"] == 200
        assert json.loads(portal.fake.requests[-1].content)["MediaSourceId"] == SOURCE
