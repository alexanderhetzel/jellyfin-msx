import asyncio
import json

import httpx
import pytest
from conftest import MOVIE, SOURCE, TOKEN
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app


@pytest.fixture
def reporting(portal):
    portal.fake.source["RunTimeTicks"] = 300_000_000
    portal.reports = []

    def handle(request):
        if "/Sessions/Playing" in request.url.path:
            assert f'Token="{TOKEN}"' in request.headers["authorization"]
            portal.reports.append((request.url.path, json.loads(request.content)))
            return httpx.Response(204)
        return portal.fake.handle(request)

    app = create_app(portal.settings, transport=httpx.MockTransport(handle), state=portal.state)
    with TestClient(app, base_url=portal.settings.public_url) as client:
        portal.reporting_client = client
        portal.reporting_app = app
        yield portal


def start(p, **extra):
    return p.reporting_client.post(
        "/api/playback/start",
        headers={"Authorization": "Bearer " + p.secret},
        json={"item_id": MOVIE, "media_source_id": SOURCE, **extra},
    )


def row(seq, position, state=2, kind="snapshot", name="video", **data):
    return {
        "seq": seq,
        "ms": seq * 2000,
        "kind": kind,
        "name": name,
        "data": {"state": state, "position": position, "duration": 30, **data},
    }


def submit(p, grant, *rows):
    return p.reporting_client.post(
        "/api/playback/observations",
        headers={"Authorization": "Bearer " + grant["grant"]},
        json={"version": 1, "playback_id": grant["playback_id"], "observations": list(rows)},
    )


def test_authenticated_source_pinned_reports_pause_seek_stop_and_duplicate(reporting, caplog):
    p = reporting
    grant = start(p).json()
    assert grant["expires_in"] > 0 and len(grant["grant"]) == 43
    assert not p.reports  # Negotiation is not playback.
    assert submit(p, grant, row(1, 1), row(2, 3)).status_code == 200
    assert (
        submit(p, grant, row(3, 3, kind="event", name="video:pause"), row(4, 4, 3)).status_code
        == 200
    )
    assert p.reports[-1][1]["IsPaused"] is True
    stop = row(5, 0, 1, kind="event", name="video:stop")
    assert submit(p, grant, stop).status_code == 200
    assert submit(p, grant, stop).status_code == 200
    assert [r[0] for r in p.reports] == [
        "/jellyfin/Sessions/Playing",
        "/jellyfin/Sessions/Playing/Progress",
        "/jellyfin/Sessions/Playing/Stopped",
    ]
    final = p.reports[-1][1]
    assert final["PositionTicks"] == 40_000_000 and final["Failed"] is True
    assert final["ItemId"] == MOVIE and final["MediaSourceId"] == SOURCE
    assert final["PlaySessionId"] == "test-play-session"
    assert grant["grant"] not in caplog.text and TOKEN not in caplog.text
    diagnostics = p.reporting_client.get(p.path + "/diagnostics.json").text
    assert grant["grant"] not in diagnostics and "PlaySessionId" not in diagnostics


def test_missing_callbacks_expire_at_last_safe_position_without_completion(reporting):
    p = reporting
    grant = start(p).json()
    submit(p, grant, row(1, 20), row(2, 22))
    p.now[0] += 46
    asyncio.run(
        p.reporting_app.state.lifecycle.expire(
            lambda kind, grant, payload: asyncio.sleep(0),
            lambda grant: True,
        )
    )
    state = p.reporting_app.state.lifecycle.get(grant["grant"])
    assert state.terminal == "abandoned" and state.position == 22
    assert submit(p, grant, row(3, 29)).status_code == 200
    assert state.position == 22


def test_replay_replaces_generation_and_old_grant_is_denied(reporting):
    p = reporting
    old = start(p).json()
    submit(p, old, row(1, 1), row(2, 3))
    new = start(p).json()
    assert new["playback_id"] != old["playback_id"]
    assert submit(p, old, row(3, 7)).status_code == 401
    assert p.reports[-1][0].endswith("/Stopped")
    assert submit(p, new, row(1, 1), row(2, 3)).status_code == 200
    assert p.reports[-1][0].endswith("/Playing")


def test_optional_permitted_host_transcode_uses_scoped_stop_cleanup(reporting):
    p = reporting  # Synthetic settings explicitly allow conversion; no real host.
    grant = start(p, force=True).json()
    assert ".m3u8" in grant["url"]
    assert submit(p, grant, row(1, 1), row(2, 3)).status_code == 200
    assert submit(p, grant, row(3, 0, 1, kind="event", name="video:stop")).status_code == 200
    assert p.reports[-1][0] == "/jellyfin/Sessions/Playing/Stopped"
    assert p.reports[-1][1]["PlaySessionId"] == "test-play-session"
    assert p.reports[-1][1]["PlayMethod"] == "Transcode"
    assert p.reports[-1][1]["Failed"] is True
    assert not any("Encoding" in request.url.path for request in p.fake.requests)


@pytest.mark.parametrize(
    "change",
    [
        {"media_source_id": "9" * 32},
        {"force": "false"},
        {"subtitle": True},
        {"destination": "https://untrusted.test"},
        {"item_id": "not-an-id"},
    ],
)
def test_start_rejects_untrusted_selection_or_shape(reporting, change):
    assert start(reporting, **change).status_code >= 400
    assert not reporting.reports


@pytest.mark.parametrize("missing", ["RunTimeTicks", "PlaySessionId"])
def test_missing_essential_reporting_metadata_fails_closed(reporting, missing):
    p = reporting
    if missing == "RunTimeTicks":
        p.fake.source.pop(missing)
    else:
        original = p.fake.handle

        def handle(request):
            response = original(request)
            if request.url.path.endswith("/PlaybackInfo"):
                data = response.json()
                data.pop("PlaySessionId")
                return httpx.Response(200, json=data)
            return response

        p.fake.handle = handle
    assert start(p).status_code == 409


def test_revoked_or_expired_session_cannot_report(reporting):
    p = reporting
    grant = start(p).json()
    p.state.remove(p.secret)
    assert submit(p, grant, row(1, 1)).status_code == 401
    assert start(p).status_code == 401
    assert not p.reports


def test_session_revoked_during_generation_lock_cannot_release_stream(reporting):
    p = reporting
    original = p.reporting_app.state.lifecycle.issue

    async def issue(*args, **kwargs):
        grant = await original(*args, **kwargs)
        p.state.remove(p.secret)
        return grant

    p.reporting_app.state.lifecycle.issue = issue
    response = start(p)
    assert response.status_code == 401
    assert "grant" not in response.json() and "url" not in response.json()


def test_body_limit_before_parse_content_type_origin_and_duplicate_keys(reporting):
    p = reporting
    for path in ("/api/playback/start", "/api/playback/observations"):
        response = p.reporting_client.post(path, content=b"{" + b"x" * 8192)
        assert response.status_code == 413
    headers = {"Authorization": "Bearer " + p.secret, "Content-Type": "application/json"}
    assert (
        p.reporting_client.post(
            "/api/playback/start", content='{"x":1,"x":2}', headers=headers
        ).status_code
        == 400
    )
    assert (
        p.reporting_client.post(
            "/api/playback/start", json={}, headers={**headers, "Origin": "https://untrusted.test"}
        ).status_code
        == 403
    )
    assert (
        p.reporting_client.post(
            "/api/playback/start", content="{}", headers={"Authorization": "Bearer " + p.secret}
        ).status_code
        == 415
    )
    assert p.reporting_client.post("/api/playback/start", json={}).status_code == 401
    assert not p.reports
