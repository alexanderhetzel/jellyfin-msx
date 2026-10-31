import hashlib
import json
import re
import sqlite3
from contextlib import closing
from dataclasses import replace

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from tools.synthetic_check import action
from tools.synthetic_https import PreparationError, build_public_synthetic_lab
from tools.synthetic_lab import PASSWORD, USERNAME

ORIGIN = "https://synthetic-remember.trycloudflare.com"


def sign_in(client, code):
    form = client.get("/pair")
    csrf = re.search(r'name="csrf" value="([^"]+)"', form.text)[1]
    step = client.post("/pair", headers={"Origin": ORIGIN}, data={"code": code, "csrf": csrf})
    fields = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', step.text))
    result = client.post(
        "/pair",
        headers={"Origin": ORIGIN},
        data={
            **fields,
            "username": USERNAME,
            "password": PASSWORD,
        },
    )
    assert result.status_code == 200 and "Sign-in succeeded" in result.text


def test_disabled_plugin_is_unavailable_and_does_not_change_start():
    settings = Settings("https://portal.test", "https://jellyfin.test")
    app = create_app(settings, transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with TestClient(app, base_url=settings.public_url) as client:
        assert client.get("/msx/start.json").json()["parameter"].endswith("/msx/pair.json")
        for path in ["remember.html", "remember.js", "remember.json"]:
            assert client.get("/msx/" + path).json()["response"]["status"] == 404
        for endpoint in ["pair", "status"]:
            assert client.post("/api/device-authorization/" + endpoint, json={}).status_code == 404
    with pytest.raises(ValueError, match="durable"):
        replace(settings, remember_devices=True)


def test_opt_in_client_routes_csp_and_normal_pairing_restart_isolation(tmp_path):
    tmp_path.chmod(0o700)
    key = Fernet.generate_key().decode()

    def build():
        return build_public_synthetic_lab(
            ORIGIN,
            allow_public_synthetic=True,
            scenario="remember",
            authorization_key=key,
            state_directory=tmp_path,
        )[0]

    app = build()
    with TestClient(app, base_url=ORIGIN) as client:
        headers = {"Origin": ORIGIN}
        assert client.get("/msx/start.json").json()["parameter"].endswith("/msx/remember.json")
        start = client.get("/msx/remember.json").json()
        assert "reference" not in start and "ready" not in start
        assert start["action"] == (
            "[home|content:request:interaction:init@" + ORIGIN + "/msx/remember.html]"
        )
        assert start["restore"] is False
        assert start["items"][0]["action"] == (
            "content:request:interaction:init@" + ORIGIN + "/msx/remember.html"
        )
        assert start["items"][1]["action"] == "content:" + ORIGIN + "/msx/pair.json"
        plugin = client.get("/msx/remember.html")
        assert 'data-jellyfin-msx-lifecycle="1"' in plugin.text
        body = re.search(r"<body([^>]*)>(.*?)</body>", plugin.text, re.S)
        assert body and not body[1].strip() and not body[2].strip()
        assert re.findall(r'<script src="([^"]+)"', plugin.text) == [
            "https://msx.benzac.de/js/tvx-plugin.min.js",
            "/msx/remember.js",
        ]
        csp = plugin.headers["Content-Security-Policy"]
        assert "script-src 'self' https://msx.benzac.de/js/tvx-plugin.min.js;" in csp
        assert "frame-ancestors https://msx.benzac.de https://www.msx.benzac.de" in csp
        assert "connect-src 'self'" in csp and "unsafe-" not in csp
        assert "frame-ancestors 'none'" in client.get("/pair").headers["Content-Security-Policy"]
        script = client.get("/msx/remember.js")
        assert script.headers["content-type"].startswith("application/javascript")
        assert "no-store" in script.headers["Cache-Control"]
        assert "localStorage" not in script.text and "TVXServices.storage" in script.text
        path = "/api/device-authorization/"
        assert client.post(path + "pair", json={}).status_code == 403
        assert client.post(path + "pair", json={"untrusted": 1}, headers=headers).status_code == 400
        created = client.post(path + "pair", json={}, headers=headers).json()
        assert not {"action", "ready", "reference"}.intersection(created["page"])
        pending = created["session"]
        assert (
            client.post(path + "status", json={"session": pending}, headers=headers).json()[
                "paired"
            ]
            is False
        )
        other = client.post(path + "pair", json={}, headers=headers).json()["session"]
        device = app.state.portal.get(pending, authenticated=False)
        sign_in(client, device.code)
        assert client.post(path + "status", json={"session": pending}, headers=headers).json() == {
            "paired": True,
            "page": None,
        }
        assert (
            client.post(path + "enroll", json={"session": other}, headers=headers).status_code
            == 401
        )
        remembered = client.post(path + "enroll", json={"session": pending}, headers=headers).json()
        raw = (tmp_path / "synthetic-authorization.sqlite").read_bytes()
        assert remembered["renewal"].encode() not in raw and device.token.encode() not in raw
        with closing(sqlite3.connect(tmp_path / "synthetic-upstream.sqlite")) as db:
            assert (
                db.execute("SELECT verifier FROM synthetic_tokens").fetchone()[0]
                == hashlib.sha256(device.token.encode()).hexdigest()
            )
    # Fresh app, RAM sessions AND upstream fixture instance: only encrypted state/verifiers survive.
    restarted = build()
    with TestClient(restarted, base_url=ORIGIN) as client:
        result = client.post(
            path + "renew", json={"renewal": remembered["renewal"]}, headers=headers
        )
        assert result.status_code == 200
        fresh = result.json()["session"]
        assert result.json()["generation"] == 1
        assert client.get(f"/msx/device/{pending}/home.json").json()["response"]["status"] == 401
        assert (
            client.post(path + "status", json={"session": other}, headers=headers).status_code
            == 401
        )
        home = client.get(f"/msx/device/{fresh}/home.json").json()
        assert home["headline"] == "Jellyfin libraries"
        assert not {"action", "ready", "reference"}.intersection(home)
        confirm = client.get(action(home, "Disconnect TV").removeprefix("content:")).json()
        assert not {"action", "ready", "reference"}.intersection(confirm)
        client.get(action(confirm, "Confirm disconnect").removeprefix("content:"))
        assert (
            client.post(
                path + "renew", json={"renewal": result.json()["renewal"]}, headers=headers
            ).status_code
            == 401
        )
        assert all(
            marker not in json.dumps(client.get("/__lab/report").json())
            for marker in [fresh, device.token, key]
        )


def test_synthetic_persistence_requires_explicit_isolated_configuration(tmp_path):
    with pytest.raises(PreparationError, match="config-required"):
        build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True, scenario="remember")
    with pytest.raises(PreparationError, match="state-directory"):
        build_public_synthetic_lab(
            ORIGIN,
            allow_public_synthetic=True,
            scenario="remember",
            authorization_key=Fernet.generate_key().decode(),
            state_directory="relative",
        )
