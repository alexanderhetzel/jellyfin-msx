import httpx
from fastapi.testclient import TestClient

from tools.synthetic_check import pair
from tools.synthetic_https import build_public_synthetic_lab
from tools.synthetic_lab import MOVIE, SOURCE
from tools.synthetic_resume import EPISODE, ITEMS, NEAR_END, WATCHED


def test_resume_scenario_isolated_auth_catalog_progress_and_original_media(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Unexpected real network")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    origin = "https://synthetic-test.trycloudflare.com"
    app, _, fixture = build_public_synthetic_lab(
        origin, allow_public_synthetic=True, scenario="resume"
    )
    with TestClient(app, base_url=origin) as client:
        action = pair(client, origin)
        secret = action.split("/device/", 1)[1].split("/", 1)[0]
        headers = {"Authorization": "Bearer " + secret}
        for item in ITEMS:
            detail = client.get(
                f"/msx/device/{secret}/detail.json", params={"item_id": item}
            ).json()
            assert any(row["title"].startswith("Resume from") for row in detail["items"]) == (
                item in {MOVIE, EPISODE}
            )
            response = client.post(
                "/api/playback/start",
                headers=headers,
                json={"item_id": item, "media_source_id": SOURCE, "resume": True},
            )
            assert response.status_code == 200
            grant = response.json()
            assert grant["start_position"] == (8 if item in {MOVIE, EPISODE} else 0)
            media = client.get(grant["url"], headers={"Range": "bytes=0-99"})
            assert media.status_code == 206 and len(media.content) == 100
            assert client.get(grant["url"].replace(item, "9" * 32)).status_code == 404
        assert fixture.negotiations == 4
        observations = [
            {
                "seq": n,
                "ms": n * 2000,
                "kind": "snapshot",
                "name": "video",
                "data": {"state": 2, "position": n * 2, "duration": 30},
            }
            for n in (1, 2)
        ]
        assert (
            client.post(
                "/api/playback/observations",
                headers={"Authorization": "Bearer " + grant["grant"]},
                json={
                    "version": 1,
                    "playback_id": grant["playback_id"],
                    "observations": observations,
                },
            ).status_code
            == 200
        )
        token = next(iter(fixture.tokens))
        assert fixture.progress(token, WATCHED)["PlaybackPositionTicks"] == 40_000_000
        assert fixture.progress(token, NEAR_END)["PlaybackPositionTicks"] == 280_000_000
        assert fixture.progress("another-login", WATCHED)["PlaybackPositionTicks"] == 80_000_000
        assert (
            client.post(
                "/api/playback/start",
                headers=headers,
                json={"item_id": MOVIE, "media_source_id": SOURCE, "force": True},
            ).status_code
            == 409
        )
        summary = client.get("/__synthetic/lifecycle").json()
        assert not any(value in str(summary) for value in (grant["grant"], grant["url"], secret))
        assert summary["requested_start_seconds"] == 0
        app.state.portal.remove(secret)
        assert (
            client.post(
                "/api/playback/start",
                headers=headers,
                json={"item_id": MOVIE, "media_source_id": SOURCE, "resume": True},
            ).status_code
            == 401
        )
