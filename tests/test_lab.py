import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings

spec = importlib.util.spec_from_file_location("msx_lab", Path(__file__).parents[1] / "tools/lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def test_lab_requires_loopback_and_direct_only():
    with pytest.raises(ValueError, match="loopback"):
        lab.build_lab(Settings("https://public.example", "https://jellyfin.test"))
    with pytest.raises(ValueError, match="never enables"):
        lab.build_lab(
            Settings("https://localhost:18091", "https://jellyfin.test", allow_transcoding=True)
        )


def test_dashboard_and_report_are_redacted_and_do_not_create_auth_bypass():
    settings = Settings("https://localhost:18091", "https://private-jellyfin.test")
    app, launch = lab.build_lab(settings)
    secret, device = app.state.portal.pair()
    app.state.portal.complete(device, "1" * 32, "private-test-token")
    with TestClient(app, base_url=settings.public_url) as client:
        dashboard = client.get("/__lab/")
        assert dashboard.status_code == 200 and "Open Media Station X" in dashboard.text
        assert "content%3Ahttps%3A%2F%2Flocalhost" in launch
        assert "input=2" in launch and "init=1" in launch and "suspend=0" in launch
        result = client.get("/__lab/report")
        assert result.json()["paired_sessions"] == 1
        assert result.json()["transcoding_allowed"] is False
        for sensitive in (secret, "private-test-token", "private-jellyfin.test"):
            assert sensitive not in result.text and sensitive not in dashboard.text
        denied = client.get("/msx/device/unknown/home.json")
        assert denied.json()["response"]["status"] == 401
        assert client.get("/__lab/report").json()["portal_requests"]["home.json"] == 1


def test_recorder_keeps_policy_only_not_credentials_or_source_ids():
    import asyncio

    async def run():
        recorder = lab.TrafficRecorder()
        await recorder.transport.aclose()
        recorder.transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        request = httpx.Request(
            "POST",
            "https://jf.test/Items/private-id/PlaybackInfo?api_key=secret",
            json={
                "EnableTranscoding": False,
                "MediaSourceId": "private-id",
                "SubtitleStreamIndex": -1,
                "Token": "secret",
            },
        )
        await recorder.handle_async_request(request)
        observed = json.dumps(recorder.negotiations)
        assert "private-id" not in observed and "secret" not in observed
        assert recorder.negotiations[-1]["EnableTranscoding"] is False
        assert recorder.responses == {"playback_info": {"200": 1}}
        recorder.transport = httpx.MockTransport(lambda request: httpx.Response(401))
        await recorder.handle_async_request(httpx.Request("GET", "https://jf.test/UserViews"))
        assert recorder.responses["library"] == {"401": 1}
        await recorder.aclose()

    asyncio.run(run())


def test_expired_certificate_requires_explicit_retrust(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "TLS", tmp_path)
    (tmp_path / "key.pem").write_text("test key")
    (tmp_path / "cert.pem").write_text("test cert")
    monkeypatch.setattr(
        lab.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1)
    )
    with pytest.raises(ValueError, match="expired"):
        lab.certificate()


def test_valid_certificate_is_reused_without_changing_trust(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "TLS", tmp_path)
    (tmp_path / "key.pem").write_text("test key")
    (tmp_path / "cert.pem").write_text("test cert")
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(lab.subprocess, "run", run)
    key, cert = lab.certificate()
    assert key.name == "key.pem" and cert.name == "cert.pem"
    assert len(calls) == 1 and "-checkend" in calls[0]
    assert all("security" not in arg for call in calls for arg in call)


def test_private_lab_artifacts_are_excluded_from_docker_context():
    assert ".lab" in Path(".dockerignore").read_text().splitlines()
