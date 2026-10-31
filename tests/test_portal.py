import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import EPISODE, LIBRARY, MOVIE, TOKEN, USER, code_stage

from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.state import State, digest


def error(response, status):
    assert response.status_code == 200
    result = response.json()["response"]
    assert result["status"] == status
    assert result["data"] is None
    assert TOKEN not in response.text
    return result


def play(portal, **params):
    return portal.client.get(portal.path + "/play.json", params={"item_id": MOVIE, **params})


def test_public_start_and_pairing_do_not_disclose_library(portal):
    start = portal.client.get("/msx/start.json?v=0.1.167&t=123")
    assert start.json()["parameter"] == "content:https://portal.test/msx/pair.json"
    page = portal.client.get("/msx/pair.json").json()["pages"][0]
    assert "TV code:" == page["items"][1]["titleHeader"]
    assert "Test Movie" not in json.dumps(page)
    assert TOKEN not in json.dumps(page)
    target = page["items"][2]["action"].removeprefix("content:")
    pending = portal.client.get(target).json()
    assert pending["headline"] == "Waiting for pairing"
    assert not portal.fake.requests


def test_browser_pair_to_tv_home_and_one_time_code(portal):
    secret, device = portal.state.pair()
    code = device.code
    fields = code_stage(portal.client, code)
    assert not portal.fake.requests
    data = {**fields, "username": "viewer", "password": "test-password"}
    response = portal.client.post("/pair", data=data, headers={"Origin": "https://portal.test"})
    assert response.status_code == 200
    assert "TV paired" in response.text
    assert "Sign-in succeeded" in response.text and "<form" not in response.text
    assert response.headers["referrer-policy"] == "same-origin"
    assert "test-password" not in response.text and TOKEN not in response.text
    auth_request = portal.fake.requests[0]
    assert auth_request.method == "POST" and not auth_request.url.query
    assert device.token == TOKEN and device.code is None
    home = portal.client.get(f"/msx/device/{secret}/home.json")
    assert home.headers["referrer-policy"] == "no-referrer"
    assert home.json()["items"][0]["title"] == "Movies & TV"
    with pytest.raises(PortalError):
        portal.state.claim(code)


@pytest.mark.parametrize(
    "origin,csrf", [("https://evil.test", "valid"), ("", "valid"), ("https://portal.test", "wrong")]
)
def test_pair_csrf_denies_without_upstream_request(portal, origin, csrf):
    page = portal.client.get("/pair")
    valid = re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
    response = portal.client.post(
        "/pair",
        headers={"Origin": origin},
        data={
            "code": "12345678",
            "username": "viewer",
            "password": "test-password",
            "csrf": valid if csrf == "valid" else csrf,
        },
    )
    assert response.status_code == 403
    assert not portal.fake.requests


def test_bad_password_leaves_pair_retryable_and_does_not_store_password(portal):
    secret, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    response = portal.client.post(
        "/pair",
        headers={"Origin": "https://portal.test"},
        data={
            **fields,
            "username": "viewer",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401 and not device.claiming and device.token is None
    assert "wrong-password" not in repr(device)
    assert "wrong-password" not in response.text
    assert digest(secret) in portal.state.devices


def test_expired_pair_code_explains_recovery_without_attempting_sign_in(portal):
    _, device = portal.state.pair()
    code = device.code
    page = portal.client.get("/pair")
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
    portal.now[0] += portal.settings.pairing_ttl + 1
    response = portal.client.post(
        "/pair",
        headers={"Origin": "https://portal.test"},
        data={"code": code, "username": "viewer", "password": "test-password", "csrf": csrf},
    )
    assert response.status_code == 400
    assert response.headers["referrer-policy"] == "same-origin"
    assert "TV code is invalid, expired or already used" in response.text
    assert "Create new code" in response.text and "<form" in response.text
    assert "test-password" not in response.text and code not in response.text
    assert not portal.fake.requests


@pytest.mark.parametrize(
    "endpoint",
    [
        "home.json",
        f"browse.json?parent_id={LIBRARY}",
        f"detail.json?item_id={MOVIE}",
        f"play.json?item_id={MOVIE}",
        "diagnostics.json",
        "logout.json",
    ],
)
def test_unknown_capability_denies_all_private_json(portal, endpoint):
    error(portal.client.get("/msx/device/unknown/" + endpoint), 401)
    assert not portal.fake.requests


def test_expiry_and_unknown_images_deny_without_upstream(portal):
    portal.now[0] += portal.settings.session_ttl + 1
    error(portal.client.get(portal.path + "/home.json"), 401)
    assert portal.client.get(portal.path + f"/image/{MOVIE}").status_code == 401
    assert not portal.fake.requests


def test_browsing_movie_series_season_episode_actions(portal):
    home = portal.client.get(portal.path + "/home.json").json()
    library = portal.client.get(home["items"][0]["action"].removeprefix("content:")).json()
    movie = library["items"][0]
    assert "/detail.json?item_id=" + MOVIE in movie["action"]
    assert "/image/" + MOVIE in movie["image"] and TOKEN not in movie["image"]
    series = portal.client.get(library["items"][1]["action"].removeprefix("content:")).json()
    season = portal.client.get(series["items"][0]["action"].removeprefix("content:")).json()
    assert EPISODE in season["items"][0]["action"]
    for request in portal.fake.requests:
        assert f"/Users/{USER}/" in request.url.path
        assert f'Token="{TOKEN}"' in request.headers["authorization"]
        assert "x-emby-token" not in request.headers


def test_pagination_reaches_items_after_first_page(portal):
    portal.fake.children[LIBRARY] = [
        {"Id": MOVIE, "Name": f"Movie {i}", "Type": "Movie"} for i in range(30)
    ]
    first = portal.client.get(portal.path + "/browse.json", params={"parent_id": LIBRARY}).json()
    next_action = next(x["action"] for x in first["items"] if x["title"] == "Next page")
    second = portal.client.get(next_action.removeprefix("content:")).json()
    assert second["items"][0]["title"] == "Movie 24"
    assert any(x["title"] == "Previous page" for x in second["items"])
    assert not any(x["title"] == "Next page" for x in second["items"])


def test_playbackinfo_direct_candidate_and_redacted_diagnostics(portal):
    response = play(portal, platform="saphi", player="html5")
    data = response.json()["response"]["data"]
    parsed = urlsplit(data["url"])
    assert parsed.path == f"/jellyfin/Videos/{MOVIE}/stream.mp4"
    assert parse_qs(parsed.query)["ApiKey"] == [TOKEN]
    assert parse_qs(parsed.query)["Static"] == ["true"]
    negotiation = portal.fake.requests[-1]
    assert negotiation.method == "POST" and negotiation.url.path.endswith("/PlaybackInfo")
    body = json.loads(negotiation.content)
    assert body["UserId"] == USER and not body["EnableDirectStream"]
    assert "h264" in body["DeviceProfile"]["DirectPlayProfiles"][0]["VideoCodec"].split(",")
    diagnostic = portal.client.get(f"/api/device/{portal.secret}/diagnostics")
    assert TOKEN not in diagnostic.text and MOVIE not in diagnostic.text
    assert "A movie" not in diagnostic.text and portal.secret not in diagnostic.text
    event = diagnostic.json()["events"][-1]
    assert event["mode"] == "DirectPlay" and event["platform"] == "saphi"
    assert event["device_playback_verified"] is False


def test_force_hls_and_subtitle_burn_in(portal):
    response = play(portal, force=True, subtitle=2)
    assert "master.m3u8" in response.json()["response"]["data"]["url"]
    body = json.loads(portal.fake.requests[-1].content)
    assert not body["EnableDirectPlay"] and not body["AllowVideoStreamCopy"]
    assert not body["AllowAudioStreamCopy"] and body["SubtitleStreamIndex"] == 2
    assert body["AlwaysBurnInSubtitleWhenTranscoding"] is True
    assert portal.device.diagnostics[-1]["subtitle_burn_in"] is True


def test_unknown_subtitle_denies_before_playbackinfo(portal):
    error(play(portal, subtitle=99), 400)
    assert not any(r.url.path.endswith("/PlaybackInfo") for r in portal.fake.requests)


def test_unlisted_codec_negotiates_opted_in_transcoding(portal):
    portal.fake.source["MediaStreams"][0]["Codec"] = "unlisted"
    response = play(portal)
    assert "master.m3u8" in response.json()["response"]["data"]["url"]
    assert portal.device.diagnostics[-1]["mode"] == "TranscodeHLS"


@pytest.mark.parametrize("mutation", ["empty", "disabled", "off_origin", "error_code"])
def test_no_compatible_stream_has_visible_msx_error(portal, mutation):
    expected = 409
    if mutation == "empty":
        portal.fake.empty = True
    elif mutation == "disabled":
        portal.fake.source["SupportsDirectPlay"] = False
        portal.fake.source["SupportsTranscoding"] = False
    elif mutation == "off_origin":
        portal.fake.source["SupportsDirectPlay"] = False
        portal.fake.source["TranscodingUrl"] = "https://evil.test/steal"
        expected = 502
    else:
        portal.fake.error_code = "NotAllowed"
    error(play(portal), expected)
    assert portal.device.diagnostics[-1]["event"] == "playback_error"


@pytest.mark.parametrize("status", [401, 403, 404, 500, 302])
def test_upstream_errors_are_not_reflected(portal, status):
    portal.fake.error = status
    response = portal.client.get(portal.path + "/home.json")
    error(response, 401 if status in (401, 403) else 404 if status == 404 else 502)
    assert "private upstream" not in response.text


def test_timeout_and_malformed_json(portal):
    portal.fake.timeout = True
    error(portal.client.get(portal.path + "/home.json"), 504)
    portal.fake.timeout = False
    portal.fake.malformed = True
    error(portal.client.get(portal.path + "/home.json"), 502)


def test_authorized_images_enforce_item_access_and_types(portal):
    response = portal.client.get(portal.path + f"/image/{MOVIE}")
    assert response.content == b"fake-jpeg" and response.headers["content-type"] == "image/jpeg"
    assert "/Users/" in portal.fake.requests[-2].url.path
    portal.fake.deny_item = True
    before = len(portal.fake.requests)
    assert portal.client.get(portal.path + f"/image/{MOVIE}").status_code == 401
    assert len(portal.fake.requests) == before + 1
    portal.fake.deny_item = False
    portal.fake.image_type = "image/svg+xml"
    assert portal.client.get(portal.path + f"/image/{MOVIE}").status_code == 502


def test_image_size_limit(portal):
    portal.fake.image_bytes = b"x" * 2_000_001
    assert portal.client.get(portal.path + f"/image/{MOVIE}").status_code == 502


@pytest.mark.parametrize("fail", [False, True])
def test_logout_invalidates_even_when_upstream_is_down(portal, fail):
    portal.fake.logout_error = fail
    result = portal.client.get(portal.path + "/logout.json")
    assert result.status_code == 200
    assert ("Upstream logout failed" in result.text) == fail
    error(portal.client.get(portal.path + "/home.json"), 401)


def test_private_responses_no_store_and_msx_cors_without_cookies(portal):
    response = portal.client.get(
        portal.path + "/home.json", headers={"Origin": "https://msx.benzac.de"}
    )
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["strict-transport-security"]


def test_malformed_identifier_is_not_forwarded(portal):
    error(portal.client.get(portal.path + "/detail.json?item_id=../../admin"), 400)
    assert not portal.fake.requests


def test_expired_pairing_capacity_and_login_rate_limit(portal):
    secret, pending = portal.state.pair()
    portal.now[0] += portal.settings.pairing_ttl + 1
    with pytest.raises(PortalError):
        portal.state.claim(pending.code)
    assert digest(secret) not in portal.state.devices
    small = State(Settings("https://portal.test", "https://jellyfin.test", max_states=1))
    small.pair()
    with pytest.raises(PortalError, match="capacity"):
        small.pair()
    for _ in range(5):
        portal.state.limit("login:test", 5)
    with pytest.raises(PortalError) as caught:
        portal.state.limit("login:test", 5)
    assert caught.value.status == 429


def test_pair_claim_cannot_be_taken_twice(portal):
    _, pending = portal.state.pair()
    portal.state.claim(pending.code)
    with pytest.raises(PortalError):
        portal.state.claim(pending.code)


def test_isolated_sessions_and_no_tokens_in_device_repr(portal):
    secret, pending = portal.state.pair()
    assert secret != portal.secret and pending.device_id != portal.device.device_id
    assert TOKEN not in repr(portal.device)
    error(portal.client.get(f"/msx/device/{secret}/browse.json?parent_id={LIBRARY}"), 401)


def test_detail_has_remote_actions_and_sanitizes_metadata(portal):
    portal.fake.children[LIBRARY][0]["Name"] = "{txt:red:Injected} [bad]|<tag>"
    result = portal.client.get(portal.path + "/browse.json", params={"parent_id": LIBRARY}).json()
    assert all(c not in result["items"][0]["title"] for c in "{}[]|<>")
    detail = portal.client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    assert detail["items"][0]["action"].startswith("video:resolve:https://portal.test/")
    assert any("Burn subtitle" in item["title"] for item in detail["items"])
    assert TOKEN not in json.dumps(detail)
