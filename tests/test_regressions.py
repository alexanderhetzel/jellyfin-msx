import asyncio
import copy
import json
import re

import httpx
import pytest
from conftest import LIBRARY, MOVIE, SOURCE, TOKEN, code_stage, media_source

from jellyfin_msx.jellyfin import normalize_contract
from jellyfin_msx.middleware import PairBodyLimit
from jellyfin_msx.playback import compatible


@pytest.mark.parametrize("field", ["Container", "MediaStreams"])
def test_nullable_source_metadata_fails_closed(field):
    source = media_source()
    source[field] = None
    assert not compatible(source, 4_000_000)


def test_nullable_codec_metadata_uses_hls(portal):
    portal.fake.source["MediaStreams"][0]["Codec"] = None
    response = portal.client.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert response.json()["response"]["data"]["url"].split("?")[0].endswith("master.m3u8")
    assert portal.device.diagnostics[-1]["mode"] == "TranscodeHLS"


@pytest.mark.parametrize("field", ["Width", "Height"])
def test_nullable_dimensions_cannot_bypass_hd_policy_via_hls(portal, field):
    portal.fake.source["MediaStreams"][0][field] = None
    response = portal.client.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert response.json()["response"]["status"] == 409
    assert not any(r.url.path.endswith("/PlaybackInfo") for r in portal.fake.requests)


def test_nullable_collections_and_invalid_shape():
    assert normalize_contract({"Items": None, "User": None}) == {"Items": [], "User": {}}
    assert normalize_contract({"MediaSources": [{"MediaStreams": None}]}) == {
        "MediaSources": [{"MediaStreams": []}]
    }
    from jellyfin_msx.errors import PortalError

    with pytest.raises(PortalError):
        normalize_contract({"Items": ["wrong type"]})


def test_nullable_image_tags_dont_crash_library(portal):
    portal.fake.children[LIBRARY][0]["ImageTags"] = None
    response = portal.client.get(portal.path + "/browse.json", params={"parent_id": LIBRARY})
    assert response.json()["items"][0]["title"] == "Test Movie"
    assert "image" not in response.json()["items"][0]


def test_no_subtitles_always_pins_source(portal):
    response = portal.client.get(
        portal.path + "/play.json", params={"item_id": MOVIE, "force": True}
    )
    assert response.json()["response"]["status"] == 200
    body = json.loads(portal.fake.requests[-1].content)
    assert body["MediaSourceId"] == SOURCE
    assert body["SubtitleStreamIndex"] == -1


def test_multiple_versions_use_same_source_for_subtitle_labels_and_playback(portal):
    original = portal.fake.handle

    def multi_version(request):
        response = original(request)
        if "/Users/" in request.url.path and request.url.path.endswith("/Items/" + MOVIE):
            item = response.json()
            other = copy.deepcopy(item["MediaSources"][0])
            other["Id"] = "9" * 32
            other["MediaStreams"][-1]["Language"] = "eng"
            item["MediaSources"].append(other)
            return httpx.Response(200, json=item)
        return response

    from fastapi.testclient import TestClient

    from jellyfin_msx.app import create_app

    app = create_app(
        portal.settings, transport=httpx.MockTransport(multi_version), state=portal.state
    )
    with TestClient(app, base_url=portal.settings.public_url) as client:
        detail = client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
        titles = [item["title"] for item in detail["items"]]
        assert any("deu" in title for title in titles)
        assert not any("eng" in title for title in titles)
        response = client.get(portal.path + "/play.json", params={"item_id": MOVIE, "subtitle": 2})
        assert response.json()["response"]["status"] == 200
        assert json.loads(portal.fake.requests[-1].content)["MediaSourceId"] == SOURCE


@pytest.mark.parametrize("chunked", [False, True])
def test_public_pair_body_is_bounded(portal, chunked):
    body = (
        (chunk for chunk in [b"password=", b"x" * 5000, b"x" * 5000]) if chunked else b"x" * 10000
    )
    response = portal.client.post(
        "/pair", content=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 413
    assert not portal.fake.requests


def test_asgi_limit_stops_before_reading_remaining_chunks():
    reads = []
    output = []

    async def receive():
        reads.append(1)
        return {"type": "http.request", "body": b"x" * 5000, "more_body": True}

    async def send(message):
        output.append(message)

    async def must_not_parse(*args):
        pytest.fail("Oversized form reached parser")

    asyncio.run(
        PairBodyLimit(must_not_parse)(
            {"type": "http", "method": "POST", "path": "/pair"}, receive, send
        )
    )
    assert len(reads) == 2 and output[0]["status"] == 413


def test_blank_password_reaches_jellyfin_instead_of_validation_error(portal):
    _, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    response = portal.client.post(
        "/pair",
        headers={"Origin": portal.settings.public_url},
        data={**fields, "username": "viewer", "password": ""},
    )
    assert response.status_code == 401  # mock server rejects it, but POST reaches the server
    assert json.loads(portal.fake.requests[-1].content)["Pw"] == ""


def test_non_ascii_csrf_is_safely_denied(portal):
    portal.client.get("/pair")
    response = portal.client.post(
        "/pair",
        headers={"Origin": portal.settings.public_url},
        data={"code": "12345678", "username": "viewer", "password": "", "csrf": "ä" * 40},
    )
    assert response.status_code == 403
    assert not portal.fake.requests


def test_pending_code_unicode_rejected_without_crash(portal):
    _, device = portal.state.pair()
    page = portal.client.get("/pair")
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
    response = portal.client.post(
        "/pair",
        headers={"Origin": portal.settings.public_url},
        data={"code": "ääääääää", "username": "viewer", "password": "", "csrf": csrf},
    )
    assert response.status_code == 400 and device.token is None
    assert not portal.fake.requests


def test_all_state_routes_execute_on_event_loop(portal):
    for route in portal.client.app.routes:
        if route.path in {"/pair", "/msx/pair.json"} or "{secret}" in route.path:
            assert asyncio.iscoroutinefunction(route.endpoint), route.path


def test_mismatched_source_response_does_not_switch_versions(portal):
    original = portal.fake.handle

    def changed_source(request):
        response = original(request)
        if request.url.path.endswith("/PlaybackInfo"):
            body = response.json()
            body["MediaSources"][0]["Id"] = "9" * 32
            return httpx.Response(200, json=body)
        return response

    from fastapi.testclient import TestClient

    from jellyfin_msx.app import create_app

    app = create_app(
        portal.settings, transport=httpx.MockTransport(changed_source), state=portal.state
    )
    with TestClient(app, base_url=portal.settings.public_url) as client:
        response = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
        assert response.json()["response"]["status"] == 409
        assert TOKEN not in response.text


def test_rejected_direct_candidate_requests_fresh_forced_playbackinfo(portal):
    from fastapi.testclient import TestClient

    from jellyfin_msx.app import create_app

    original = portal.fake.handle
    portal.fake.source["MediaStreams"][0]["Codec"] = None

    def real_server_behavior(request):
        response = original(request)
        if (
            request.url.path.endswith("/PlaybackInfo")
            and json.loads(request.content)["EnableDirectPlay"]
        ):
            body = response.json()
            body["MediaSources"][0].pop("TranscodingUrl")
            return httpx.Response(200, json=body)
        return response

    app = create_app(
        portal.settings, transport=httpx.MockTransport(real_server_behavior), state=portal.state
    )
    with TestClient(app, base_url=portal.settings.public_url) as client:
        result = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
        assert result.json()["response"]["status"] == 200
        negotiations = [r for r in portal.fake.requests if r.url.path.endswith("/PlaybackInfo")]
        assert len(negotiations) == 2
        assert json.loads(negotiations[0].content)["EnableDirectPlay"] is True
        assert json.loads(negotiations[1].content)["EnableDirectPlay"] is False
        assert portal.device.diagnostics[-1]["mode"] == "TranscodeHLS"
