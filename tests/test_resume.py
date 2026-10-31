import copy
import json
from dataclasses import replace
from urllib.parse import urlsplit

import httpx
import pytest
from conftest import EPISODE, MOVIE, SOURCE
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.playback import position_label, resume_ticks

TICKS = 10_000_000


@pytest.mark.parametrize(
    "position,played,duration,expected",
    [
        (5 * TICKS, False, 30 * TICKS, 5 * TICKS),
        (20 * TICKS, False, 30 * TICKS, 20 * TICKS),
        (None, False, 30 * TICKS, 0),
        (True, False, 30 * TICKS, 0),
        ("80000000", False, 30 * TICKS, 0),
        (float("inf"), False, 30 * TICKS, 0),
        (-TICKS, False, 30 * TICKS, 0),
        (5 * TICKS - 1, False, 30 * TICKS, 0),
        (25 * TICKS, False, 30 * TICKS, 0),
        (27 * TICKS, False, 30 * TICKS, 0),
        (90 * TICKS, False, 100 * TICKS, 0),
        (30 * TICKS, False, 30 * TICKS, 0),
        (10**100, False, 30 * TICKS, 0),
        (8 * TICKS, True, 30 * TICKS, 0),
        (8 * TICKS, False, None, 0),
        (8 * TICKS, False, True, 0),
        (8 * TICKS, False, 10**100, 0),
    ],
)
def test_bounded_progress_policy(position, played, duration, expected):
    item = {"UserData": {"PlaybackPositionTicks": position, "Played": played}}
    assert resume_ticks(item, {"RunTimeTicks": duration}) == expected


def test_duration_and_malformed_userdata_boundaries():
    item = {"RunTimeTicks": 100 * TICKS, "UserData": {"PlaybackPositionTicks": 20 * TICKS}}
    assert resume_ticks(item, {}) == 20 * TICKS
    assert resume_ticks(item, {"RunTimeTicks": 10 * TICKS}) == 0
    assert resume_ticks(item, {"RunTimeTicks": None}) == 0
    for value in [None, [], "invalid", True]:
        assert resume_ticks({**item, "UserData": value}, {}) == 0
    assert position_label(3661 * TICKS) == "01:01:01"


@pytest.fixture
def saved(portal):
    p = portal
    p.fake.source["RunTimeTicks"] = 100 * TICKS
    p.progress = {"PlaybackPositionTicks": 20 * TICKS, "Played": False}
    p.sources = [p.fake.source]
    p.returned = None
    p.reports = []
    original = p.fake.handle

    def handle(request):
        if "/Sessions/Playing" in request.url.path:
            p.reports.append(json.loads(request.content))
            return httpx.Response(204)
        response = original(request)
        if response.status_code != 200:
            return response
        if any(request.url.path.endswith("/Items/" + key) for key in (MOVIE, EPISODE)):
            item = response.json()
            item.update(
                Type="Episode" if request.url.path.endswith(EPISODE) else "Movie",
                MediaSources=copy.deepcopy(p.sources),
                UserData=copy.deepcopy(p.progress),
            )
            return httpx.Response(200, json=item)
        if request.url.path.endswith("/PlaybackInfo"):
            data = response.json()
            data["MediaSources"] = copy.deepcopy(p.sources if p.returned is None else p.returned)
            return httpx.Response(200, json=data)
        return response

    settings = replace(p.settings, allow_transcoding=False)
    app = create_app(settings, transport=httpx.MockTransport(handle), state=p.state)
    with TestClient(app, base_url=settings.public_url) as client:
        p.saved_client = client
        p.saved_app = app
        yield p


def start(p, item=MOVIE, **extra):
    return p.saved_client.post(
        "/api/playback/start",
        headers={"Authorization": "Bearer " + p.secret},
        json={"item_id": item, "media_source_id": SOURCE, "resume": True, **extra},
    )


def negotiations(p):
    return [json.loads(r.content) for r in p.fake.requests if r.url.path.endswith("/PlaybackInfo")]


@pytest.mark.parametrize("item", [MOVIE, EPISODE])
def test_detail_choices_fresh_resume_and_explicit_start_over(saved, item):
    p = saved
    page = p.saved_client.get(p.path + "/detail.json", params={"item_id": item}).json()
    choices = page["items"][:2]
    assert [row["title"] for row in choices] == ["Resume from 00:00:20", "Start over"]
    for row, mode in zip(choices, ["resume", "start"], strict=True):
        assert urlsplit(row["action"].split("init@", 1)[1]).fragment == (
            f"{p.secret}/{item}/{SOURCE}/0/-1/{mode}"
        )
    p.progress["PlaybackPositionTicks"] = 22 * TICKS  # Fresh, not the old detail label.
    response = start(p, item).json()
    assert response["start_position"] == 22
    assert negotiations(p)[0]["StartTimeTicks"] == 22 * TICKS
    assert negotiations(p)[0]["MediaSourceId"] == SOURCE
    assert negotiations(p)[0]["EnableTranscoding"] is False
    assert negotiations(p)[0]["EnableDirectStream"] is False
    assert negotiations(p)[0]["DeviceProfile"]["TranscodingProfiles"] == []
    assert start(p, item, resume=False).json()["start_position"] == 0
    assert negotiations(p)[-1]["StartTimeTicks"] == 0
    assert p.progress["PlaybackPositionTicks"] == 22 * TICKS
    assert not p.reports  # Neither choice/negotiation fabricates progress or clears history.


@pytest.mark.parametrize(
    "progress",
    [
        None,
        {},
        {"Played": True, "PlaybackPositionTicks": 20 * TICKS},
        {"PlaybackPositionTicks": 99 * TICKS},
        {"PlaybackPositionTicks": -1},
    ],
)
def test_invalid_watched_near_end_and_missing_only_offer_beginning(saved, progress):
    p = saved
    p.progress = progress
    page = p.saved_client.get(p.path + "/detail.json", params={"item_id": MOVIE}).json()
    assert not any(row["title"].startswith("Resume") for row in page["items"])
    assert start(p).json()["start_position"] == 0
    assert negotiations(p)[-1]["StartTimeTicks"] == 0


def test_source_reorder_pin_and_different_cut_clamping(saved):
    p = saved
    other = copy.deepcopy(p.fake.source)
    other.update(Id="8" * 32, RunTimeTicks=10 * TICKS)
    p.sources.insert(0, other)
    assert start(p).json()["start_position"] == 20
    assert negotiations(p)[-1]["MediaSourceId"] == SOURCE
    assert start(p, media_source_id=other["Id"]).json()["start_position"] == 0
    p.sources.pop()
    before = len(negotiations(p))
    assert start(p).status_code == 409
    assert len(negotiations(p)) == before


def test_returned_shorter_cut_fails_closed_and_does_not_report(saved):
    p = saved
    p.returned = [copy.deepcopy(p.fake.source)]
    p.returned[0]["RunTimeTicks"] = 21 * TICKS
    assert start(p).status_code == 409
    assert not p.reports


def test_saved_resume_never_falls_back_to_hls_on_conversion_enabled_host(portal):
    p = portal
    p.fake.source["RunTimeTicks"] = 100 * TICKS
    p.fake.source["SupportsDirectPlay"] = False
    response = p.client.post(
        "/api/playback/start",
        headers={"Authorization": "Bearer " + p.secret},
        json={"item_id": MOVIE, "media_source_id": SOURCE, "resume": True},
    )
    assert response.status_code == 409
    assert negotiations(p)[0]["EnableTranscoding"] is False
    assert negotiations(p)[0]["DeviceProfile"]["TranscodingProfiles"] == []


@pytest.mark.parametrize(
    "extra",
    [
        {"resume": 1},
        {"resume": "true"},
        {"resume": None},
        {"position": 12},
        {"force": True},
        {"subtitle": 2},
    ],
)
def test_client_cannot_supply_arbitrary_position_or_conversion(saved, extra):
    assert start(saved, **extra).status_code == 400
    assert negotiations(saved) == []


def test_resume_access_revocation_and_no_legacy_position_promise(saved):
    p = saved
    p.fake.deny_item = True
    assert start(p).status_code == 401
    assert negotiations(p) == []
    p.state.remove(p.secret)
    assert start(p).status_code == 401


def test_observed_resume_seek_and_stop_retains_position_instead_of_requested_target(saved):
    p = saved
    grant = start(p).json()
    assert grant["start_position"] == 20 and not p.reports

    def submit(seq, position, state=2, kind="snapshot", name="video", **extra):
        row = {
            "seq": seq,
            "ms": seq * 2000,
            "kind": kind,
            "name": name,
            "data": {"position": position, "duration": 100, "state": state},
            **extra,
        }
        result = p.saved_client.post(
            "/api/playback/observations",
            headers={"Authorization": "Bearer " + grant["grant"]},
            json={"version": 1, "playback_id": grant["playback_id"], "observations": [row]},
        )
        assert result.status_code == 200

    submit(1, 21)
    assert not p.reports
    submit(2, 23)
    assert p.reports[-1]["PositionTicks"] == 23 * TICKS
    submit(3, 23, kind="event", name="video:seek", target=70)
    assert p.reports[-1]["PositionTicks"] == 23 * TICKS
    submit(4, 70, 3)
    assert p.reports[-1]["PositionTicks"] == 70 * TICKS
    submit(5, 0, 1, kind="event", name="video:stop")
    assert p.reports[-1]["PositionTicks"] == 70 * TICKS
    assert p.reports[-1]["Failed"] is True
