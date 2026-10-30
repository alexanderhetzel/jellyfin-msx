"""Synthetic evidence for the resolver boundary, not a native-player assertion."""

import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from conftest import MOVIE, SOURCE, TOKEN, USER
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app


@pytest.mark.parametrize("force", [False, True])
def test_media_credentials_are_delivered_only_in_resolver_not_diagnostics(portal, caplog, force):
    response = portal.client.get(
        portal.path + "/play.json", params={"item_id": MOVIE, "force": force}
    )
    assert response.json()["response"]["status"] == 200
    media = urlsplit(response.json()["response"]["data"]["url"])
    assert media.scheme == "https" and media.netloc == "jellyfin.test"
    assert media.path.startswith("/jellyfin/Videos/")
    assert media.path.endswith(".m3u8" if force else ".mp4")
    assert parse_qs(media.query)["ApiKey"] == [TOKEN]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "no-store" in response.headers["cache-control"]
    # The backend negotiates only: it does not fetch the file or HLS descendants.
    assert [r.url.path for r in portal.fake.requests] == [
        f"/jellyfin/Users/{USER}/Items/{MOVIE}",
        f"/jellyfin/Items/{MOVIE}/PlaybackInfo",
    ]
    assert all(TOKEN not in str(r.url) for r in portal.fake.requests)
    assert all(f'Token="{TOKEN}"' in r.headers["authorization"] for r in portal.fake.requests)
    diagnostic = portal.client.get("/api/device/" + portal.secret + "/diagnostics")
    observed = diagnostic.text + json.dumps(portal.device.diagnostics) + caplog.text
    for marker in (TOKEN, portal.secret, MOVIE, SOURCE, "test-play-session", "ApiKey"):
        assert marker not in observed


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_backend_never_follows_upstream_redirect_or_reflects_location(portal, caplog, status):
    requests = []
    location = "https://other.test/private?ApiKey=synthetic-redirect-marker"

    def redirect(request):
        requests.append(request)
        return httpx.Response(status, headers={"Location": location}, text=location)

    app = create_app(portal.settings, transport=httpx.MockTransport(redirect), state=portal.state)
    with TestClient(app, base_url=portal.settings.public_url) as client:
        response = client.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert len(requests) == 1
    assert requests[0].url.host == "jellyfin.test"
    assert response.json()["response"]["status"] == 502
    assert "location" not in response.headers
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "no-store" in response.headers["cache-control"]
    observed = response.text + json.dumps(portal.device.diagnostics) + caplog.text
    for marker in (TOKEN, portal.secret, location, "synthetic-redirect-marker"):
        assert marker not in observed


@pytest.mark.parametrize(
    "url",
    [
        "https://other.test/jellyfin/master.m3u8?ApiKey=synthetic-old-marker",
        "http://jellyfin.test/jellyfin/master.m3u8?ApiKey=synthetic-old-marker",
        "https://jellyfin.test/outside/master.m3u8?ApiKey=synthetic-old-marker",
        "//other.test/master.m3u8?ApiKey=synthetic-old-marker",
    ],
)
def test_hls_initial_destination_denied_without_reflecting_upstream_url(portal, caplog, url):
    portal.fake.source["TranscodingUrl"] = url
    response = portal.client.get(
        portal.path + "/play.json", params={"item_id": MOVIE, "force": True}
    )
    assert response.json()["response"]["status"] == 502
    observed = response.text + json.dumps(portal.device.diagnostics) + caplog.text
    for marker in (TOKEN, url, "synthetic-old-marker"):
        assert marker not in observed
    assert all(request.url.host == "jellyfin.test" for request in portal.fake.requests)
