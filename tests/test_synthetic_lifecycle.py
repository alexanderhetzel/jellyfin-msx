import httpx
from fastapi.testclient import TestClient

from tools.synthetic_check import pair
from tools.synthetic_https import build_public_synthetic_lab
from tools.synthetic_lab import MOVIE, SOURCE
from tools.synthetic_lifecycle import (
    RECOVERY_ALTERNATE,
    RECOVERY_BAD_SOURCE,
    RECOVERY_CONNECT,
    RECOVERY_DENIED,
    RECOVERY_NATIVE,
    RECOVERY_TIMEOUT,
)


def test_recovery_scenario_is_authenticated_source_pinned_and_has_no_network_fallback(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Unexpected real network or configuration")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    origin = "https://synthetic-test.trycloudflare.com"
    app, _, fixture = build_public_synthetic_lab(
        origin, allow_public_synthetic=True, scenario="recovery"
    )
    with TestClient(app, base_url=origin) as client:
        assert (
            client.get(origin + f"/jellyfin/Videos/{RECOVERY_NATIVE}/stream.mp4").status_code == 401
        )
        secret = pair(client, origin).split("/device/", 1)[1].split("/", 1)[0]
        headers = {"Authorization": "Bearer " + secret}
        for item_id, expected in [
            (RECOVERY_DENIED, "negotiation_denied"),
            (RECOVERY_TIMEOUT, "upstream_timeout"),
            (RECOVERY_CONNECT, "upstream_connectivity"),
        ]:
            response = client.post(
                "/api/playback/start",
                headers=headers,
                json={"item_id": item_id, "media_source_id": SOURCE},
            )
            assert response.json()["category"] == expected
        response = client.post(
            "/api/playback/options",
            headers=headers,
            json={"item_id": RECOVERY_NATIVE, "media_source_id": RECOVERY_BAD_SOURCE},
        )
        assert response.json() == {"alternatives": [RECOVERY_ALTERNATE]}
        for source_id, expected in [
            (RECOVERY_BAD_SOURCE, b"synthetic non-media fixture"),
            (RECOVERY_ALTERNATE, b"\x00\x00\x00"),
        ]:
            response = client.post(
                "/api/playback/start",
                headers=headers,
                json={"item_id": RECOVERY_NATIVE, "media_source_id": source_id},
            )
            assert response.status_code == 200
            response = client.get(response.json()["url"])
            assert response.status_code == 200 and response.content.startswith(expected)
        assert fixture.media_requests["unplayable"] == 1
        assert fixture.media_requests["original"] == 1
        assert fixture.summary()["negotiations"] == 5


def test_lifecycle_scenario_normal_auth_reports_and_no_network_fallback(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Unexpected real network")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    origin = "https://synthetic-test.trycloudflare.com"
    app, _, fixture = build_public_synthetic_lab(
        origin, allow_public_synthetic=True, scenario="lifecycle"
    )
    with TestClient(app, base_url=origin) as client:
        home_action = pair(client, origin)
        secret = home_action.split("/device/", 1)[1].split("/", 1)[0]
        response = client.post(
            "/api/playback/start",
            headers={"Authorization": "Bearer " + secret},
            json={"item_id": MOVIE, "media_source_id": SOURCE},
        )
        assert response.status_code == 200
        grant = response.json()
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
        response = client.post(
            "/api/playback/observations",
            headers={"Authorization": "Bearer " + grant["grant"]},
            json={"version": 1, "playback_id": grant["playback_id"], "observations": observations},
        )
        assert response.status_code == 200
        summary = client.get("/__synthetic/lifecycle").json()
        assert summary == fixture.summary()
        assert summary["start"] == 1 and summary["active"] is True
        assert summary["position_seconds"] == 4
        assert not any(value in str(summary) for value in (grant["grant"], grant["url"], secret))
