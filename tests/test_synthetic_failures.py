import sys

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools import synthetic_https as https
from tools.synthetic_check import action, pair
from tools.synthetic_failures import (
    ACCESS_DENIED,
    BROKEN_JSON,
    UNREACHABLE,
)
from tools.synthetic_lab import MOVIE, SOURCE, USER

ORIGIN = "https://synthetic-failures.trycloudflare.com"


def test_failure_scenario_remains_authenticated_strict_and_recoverable(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Operator configuration or real transport attempted")

    monkeypatch.setattr(Settings, "from_env", forbid)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "__init__", forbid)
    app, _, fixture = https.build_public_synthetic_lab(
        ORIGIN, allow_public_synthetic=True, scenario="failures"
    )
    for parent in (BROKEN_JSON, ACCESS_DENIED, UNREACHABLE):
        response = fixture.handle(
            httpx.Request("GET", ORIGIN + f"/jellyfin/Users/{USER}/Items?ParentId={parent}")
        )
        assert response.status_code == 401
    with pytest.raises(RuntimeError, match="unexpected origin"):
        fixture.handle(httpx.Request("GET", "https://operator.invalid/jellyfin/Users"))
    with TestClient(app, base_url=ORIGIN) as client:
        home_target = pair(client, ORIGIN).removeprefix("content:")
        home = client.get(home_target).json()
        for name, status, message in (
            ("Broken JSON library", 502, "malformed JSON"),
            ("Denied access library", 401, "denied access"),
            ("Unreachable upstream library", 504, "unreachable or timed out"),
        ):
            failed = client.get(action(home, name).removeprefix("content:")).json()["response"]
            assert failed["status"] == status and message in failed["message"]
            assert client.get(home_target).json()["headline"] == "Jellyfin libraries"
        browse = client.get(action(home, "Synthetic movies").removeprefix("content:")).json()
        denied = client.get(action(browse, "Rejected playback").removeprefix("content:")).json()
        failed = client.get(action(denied, "Try original").removeprefix("video:resolve:")).json()
        assert failed["response"]["status"] == 409
        assert "Jellyfin denied Direct Play" in failed["response"]["message"]
        assert fixture.media_requests["original"] == 0
        detail = client.get(action(browse, "Synthetic clip").removeprefix("content:")).json()
        played = client.get(action(detail, "Try original").removeprefix("video:resolve:")).json()
        target = played["response"]["data"]["url"]
        assert f"MediaSourceId={SOURCE}" in target and f"/Videos/{MOVIE}/" in target
        assert client.get(target, headers={"Range": "bytes=0-8"}).status_code == 206
        report = client.get("/__lab/report").json()
        assert len(report["negotiations"]) == 2
        assert all(
            row["EnableDirectPlay"] is True
            and row["EnableDirectStream"] is False
            and row["EnableTranscoding"] is False
            for row in report["negotiations"]
        )
        confirm = client.get(action(home, "Disconnect TV").removeprefix("content:")).json()
        client.get(action(confirm, "Confirm disconnect").removeprefix("content:"))
        assert client.get(target).status_code == 401 and not fixture.tokens


def test_public_requests_cannot_enable_or_mutate_failure_scenario():
    app, _, _ = https.build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True)
    with TestClient(app, base_url=ORIGIN) as client:
        home = pair(client, ORIGIN).removeprefix("content:")
        page = client.get(home + "?scenario=failures", headers={"X-Scenario": "failures"}).json()
        assert [row["title"] for row in page["items"]] == [
            "Synthetic movies",
            "Diagnostics",
            "Disconnect TV",
        ]
        assert client.post("/__synthetic/fault", json={"scenario": "failures"}).status_code == 404
    with pytest.raises(https.PreparationError, match="invalid-synthetic-scenario"):
        https.build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True, scenario="operator")
    with pytest.raises(https.PreparationError, match="invalid-synthetic-scenario"):
        https.activate(https.BINARY, scenario="operator")


@pytest.mark.skipif(https.os.name != "nt", reason="Reviewed Windows activation entry point")
def test_cli_passes_only_startup_scenario_to_supervisor(monkeypatch):
    calls = []
    monkeypatch.setattr(https, "activate", lambda *args: calls.append(args))
    monkeypatch.setattr(
        sys, "argv", ["helper", "--activate-public-synthetic", "--scenario", "failures"]
    )
    https.main()
    assert calls == [(https.BINARY.resolve(), 900, "failures")]
