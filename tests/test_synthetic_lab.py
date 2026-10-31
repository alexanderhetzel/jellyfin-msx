import json
import re
import struct
import subprocess
import sys
import zlib
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools.synthetic_check import ContractFailure, check
from tools.synthetic_lab import (
    PASSWORD,
    POSTER,
    USERNAME,
    SyntheticJellyfin,
    build_synthetic_lab,
)


def test_synthetic_poster_is_valid_rgb_png():
    assert POSTER[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    chunks = {}
    while offset < len(POSTER):
        length = struct.unpack(">I", POSTER[offset : offset + 4])[0]
        kind = POSTER[offset + 4 : offset + 8]
        data = POSTER[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", POSTER[offset + 8 + length : offset + 12 + length])[0]
        assert zlib.crc32(kind + data) == crc
        chunks[kind] = data
        offset += 12 + length
    assert offset == len(POSTER)
    assert chunks[b"IHDR"] == struct.pack(">IIBBBBB", 240, 360, 8, 2, 0, 0, 0)
    pixels = zlib.decompress(chunks[b"IDAT"])
    assert len(pixels) == 360 * (1 + 240 * 3)
    assert pixels[:4] == b"\x00\x28\xb7\x41"
    assert pixels[-3:] == bytes((219, 183, 65))
    assert chunks[b"IEND"] == b""


def test_contract_normal_pairing_playback_denial_revocation_and_recovery(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Synthetic contract attempted a real network connection")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_network)
    result = check()
    assert result["result"] == "passed"
    assert result["browser_verified"] is result["physical_device_verified"] is False
    assert result["jellyfin_requests"]["authentication"] == 2
    assert result["media_requests"] == {"original": 1, "denied": 2}
    assert result["negotiations"][0]["EnableTranscoding"] is False
    assert USERNAME not in json.dumps(result) and PASSWORD not in json.dumps(result)


@pytest.mark.parametrize(
    "fault,stage", [("json", "libraries-json"), ("playback", "playback"), ("csrf", "pairing")]
)
def test_deliberate_failures_fail_contract(fault, stage):
    with pytest.raises(ContractFailure, match=f"^{stage}$"):
        check(fault)


@pytest.mark.parametrize(
    "fault,stage", [("json", "libraries-json"), ("playback", "playback"), ("csrf", "pairing")]
)
def test_failure_command_exits_nonzero_without_sensitive_traceback(fault, stage):
    result = subprocess.run(
        [sys.executable, "-m", "tools.synthetic_check", "--fault", fault],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "result": "failed",
        "stage": stage,
        "category": "in-process-http-contract",
    }
    assert "Traceback" not in result.stderr
    assert PASSWORD not in result.stdout and "/msx/device/" not in result.stdout


def test_synthetic_rejects_real_configuration_and_unknown_fault():
    with pytest.raises(ValueError, match="lab origin"):
        build_synthetic_lab(Settings("https://localhost:18091", "https://real.invalid"))
    with pytest.raises(ValueError, match="Unknown"):
        build_synthetic_lab(
            Settings("https://localhost:18091", "https://localhost:18091/jellyfin"), fault="unknown"
        )


def test_fixture_rejects_wrong_credentials_unknown_paths_and_cross_origin():
    fixture = SyntheticJellyfin("https://localhost:18091")
    for body in ({"Username": USERNAME, "Pw": "wrong"}, {"Username": "wrong", "Pw": PASSWORD}):
        response = fixture.handle(
            httpx.Request(
                "POST", "https://localhost:18091/jellyfin/Users/AuthenticateByName", json=body
            )
        )
        assert response.status_code == 401
    assert not fixture.tokens
    with pytest.raises(RuntimeError, match="unexpected origin"):
        fixture.handle(httpx.Request("GET", "https://real.invalid/jellyfin/Users"))
    assert (
        fixture.handle(httpx.Request("GET", "https://localhost:18091/jellyfin/unknown")).status_code
        == 401
    )


def test_csrf_does_not_authenticate_and_reports_never_expose_secrets():
    origin = "https://localhost:18091"
    app, _, fixture = build_synthetic_lab(Settings(origin, origin + "/jellyfin"))
    with TestClient(app, base_url=origin) as client:
        page = client.get("/msx/pair.json").json()["pages"][0]
        target = page["items"][2]["action"].removeprefix("content:")
        secret = urlsplit(target).path.split("/")[3]
        code = re.search(r"TV code: ([A-Z0-9 ]+) \(valid", page["items"][1]["title"])[1]
        form = client.get("/pair")
        csrf = re.search(r'name="csrf" value="([^"]+)"', form.text)[1]
        fields = {"code": code, "username": USERNAME, "password": PASSWORD, "csrf": csrf}
        assert (
            client.post(
                "/pair", data=fields, headers={"Origin": "https://evil.invalid"}
            ).status_code
            == 403
        )
        assert not fixture.tokens
        assert client.get("/__lab/report").json()["jellyfin_requests"] == {}
        form = client.get("/pair")
        fields["csrf"] = re.search(r'name="csrf" value="([^"]+)"', form.text)[1]
        form = client.post("/pair", data=fields, headers={"Origin": origin})
        assert form.status_code == 200 and not fixture.tokens
        fields = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', form.text))
        assert (
            client.post(
                "/pair",
                data={**fields, "username": USERNAME, "password": PASSWORD},
                headers={"Origin": origin},
            ).status_code
            == 200
        )
        token = next(iter(fixture.tokens))
        report = client.get("/__lab/report").text + client.get("/__synthetic/report").text
        for value in (secret, code, code.replace(" ", ""), csrf, token, PASSWORD, USERNAME):
            assert value not in report
        assert client.get("/__synthetic/report").json()["browser_verified"] is False
