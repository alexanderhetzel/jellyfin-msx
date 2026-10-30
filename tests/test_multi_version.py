"""Grouped-version contracts through actual detail actions, with isolated Jellyfin data."""

import copy
import itertools
import json
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from conftest import MOVIE, SOURCE, media_source
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app


def version(source_id, container="mp4", codec="h264", width=1280, height=720, language="deu"):
    result = media_source()
    result.update(Id=source_id, Container=container)
    result["MediaStreams"][0].update(Codec=codec, Width=width, Height=height)
    result["MediaStreams"][2].update(Language=language)
    return result


def grouped_client(portal, sources, *, allow_transcoding=False, returned=None):
    original = portal.fake.handle

    def grouped(request):
        response = original(request)
        if response.status_code != 200:
            return response
        if request.url.path.endswith("/Items/" + MOVIE):
            item = response.json()
            item["MediaSources"] = copy.deepcopy(sources)
            return httpx.Response(200, json=item)
        if request.url.path.endswith("/PlaybackInfo"):
            body = response.json()
            body["MediaSources"] = copy.deepcopy(sources if returned is None else returned)
            return httpx.Response(200, json=body)
        return response

    settings = replace(portal.settings, allow_transcoding=allow_transcoding)
    app = create_app(settings, transport=httpx.MockTransport(grouped), state=portal.state)
    return TestClient(app, base_url=settings.public_url)


def detail_action(client, portal, title="Try original (TV unverified)"):
    page = client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    action = next(row["action"] for row in page["items"] if row["title"] == title)
    return action.removeprefix("video:resolve:")


def negotiations(portal):
    return [
        json.loads(r.content) for r in portal.fake.requests if r.url.path.endswith("/PlaybackInfo")
    ]


@pytest.mark.parametrize("order", list(itertools.permutations(range(3))))
def test_grouped_uhd_and_competing_hd_follow_detail_pin_to_original_container(portal, order):
    versions = [
        version("9" * 32, codec="hevc", width=3840, height=2160),
        version("8" * 32, codec="hevc", width=1920, height=1080),
        version(SOURCE, container="mkv"),
    ]
    sources = [versions[index] for index in order]
    with grouped_client(portal, sources) as client:
        action = detail_action(client, portal)
        assert parse_qs(urlsplit(action).query)["media_source_id"] == [SOURCE]
        response = client.get(action).json()["response"]
    assert response["status"] == 200
    delivered = urlsplit(response["data"]["url"])
    assert delivered.path.endswith(f"/Videos/{MOVIE}/stream.mkv")
    assert parse_qs(delivered.query)["MediaSourceId"] == [SOURCE]
    assert parse_qs(delivered.query)["Static"] == ["true"]
    (body,) = negotiations(portal)
    assert body["MediaSourceId"] == SOURCE and body["SubtitleStreamIndex"] == -1
    assert body["EnableDirectPlay"] is True
    for flag in (
        "EnableDirectStream",
        "EnableTranscoding",
        "AllowVideoStreamCopy",
        "AllowAudioStreamCopy",
    ):
        assert body[flag] is False
    assert body["DeviceProfile"]["TranscodingProfiles"] == []
    assert body["DeviceProfile"]["SubtitleProfiles"] == []


@pytest.mark.parametrize("container", ["mp4", "mkv", "avi"])
def test_equal_rank_reordering_preserves_detail_source(portal, container):
    sources = [version(SOURCE, container=container), version("8" * 32)]
    with grouped_client(portal, sources) as client:
        action = detail_action(client, portal)
        sources.reverse()
        response = client.get(action).json()["response"]
    assert response["status"] == 200
    assert urlsplit(response["data"]["url"]).path.endswith("/stream." + container)
    assert negotiations(portal)[0]["MediaSourceId"] == SOURCE


@pytest.mark.parametrize("change", ["removed", "uhd", "unknown_codec", "missing_dimensions"])
def test_stale_pin_denied_without_negotiating_another_eligible_version(portal, change):
    sources = [version(SOURCE), version("8" * 32)]
    with grouped_client(portal, sources) as client:
        action = detail_action(client, portal)
        if change == "removed":
            sources.pop(0)
        else:
            video = sources[0]["MediaStreams"][0]
            video.update(
                {"Width": 3840, "Height": 2160}
                if change == "uhd"
                else {"Codec": "av1"}
                if change == "unknown_codec"
                else {"Width": None}
            )
        response = client.get(action).json()["response"]
    assert response["status"] == 409
    assert "Reopen the item details" in response["message"]
    assert negotiations(portal) == []


def test_group_without_eligible_copy_has_no_play_and_no_negotiation(portal):
    sources = [version(SOURCE, width=3840, height=2160), version("8" * 32, codec="av1")]
    with grouped_client(portal, sources) as client:
        page = client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
        assert not any(row["action"].startswith("video:") for row in page["items"])
        assert "Version 1" in json.dumps(page) and "Version 2" in json.dumps(page)
        response = client.get(portal.path + "/play.json", params={"item_id": MOVIE}).json()
    assert response["response"]["status"] == 409 and negotiations(portal) == []


def test_playbackinfo_cannot_substitute_another_eligible_source(portal):
    sources = [version(SOURCE, container="mkv"), version("8" * 32)]
    with grouped_client(portal, sources, returned=[sources[1]]) as client:
        response = client.get(detail_action(client, portal)).json()["response"]
    assert response["status"] == 409
    assert negotiations(portal)[0]["MediaSourceId"] == SOURCE
    assert "url" not in (response.get("data") or {})


def test_subtitle_action_keeps_version_when_same_index_has_different_language(portal):
    sources = [version(SOURCE, language="deu"), version("8" * 32, language="eng")]
    with grouped_client(portal, sources, allow_transcoding=True) as client:
        action = detail_action(client, portal, "Burn subtitle: deu")
        sources.reverse()
        response = client.get(action).json()["response"]
    assert response["status"] == 200
    (body,) = negotiations(portal)
    assert body["MediaSourceId"] == SOURCE and body["SubtitleStreamIndex"] == 2
    assert body["AlwaysBurnInSubtitleWhenTranscoding"] is True


def test_pin_does_not_bypass_item_authorization(portal):
    with grouped_client(portal, [version(SOURCE)]) as client:
        action = detail_action(client, portal)
        portal.fake.deny_item = True
        response = client.get(action).json()["response"]
    assert response["status"] == 401 and negotiations(portal) == []
