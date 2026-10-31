import json

from fastapi.testclient import TestClient

from tools.synthetic_check import action, pair
from tools.synthetic_https import build_public_synthetic_lab
from tools.synthetic_lab import MOVIE, SOURCE
from tools.synthetic_subtitles import MALFORMED, MISSING, cues


def test_subtitle_scenario_normal_private_routes_and_recovery():
    origin = "https://synthetic-subtitle.trycloudflare.com"
    app, _, fixture = build_public_synthetic_lab(
        origin, allow_public_synthetic=True, scenario="subtitles"
    )
    with TestClient(app, base_url=origin) as client:
        private = pair(client, origin).removeprefix("content:").rsplit("/", 1)[0]
        page = client.get(
            private + "/subtitle-playback.json",
            params={"item_id": MOVIE, "media_source_id": SOURCE},
        ).json()
        assert (
            len([k for k in page["items"][0]["properties"] if k.startswith("html5x:subtitle:")])
            == 3
        )
        resource = (
            private.replace("/msx/device/", "/api/device/") + f"/subtitles/{MOVIE}/{SOURCE}/7.vtt"
        )
        assert app.state.portal.settings.session_ttl == 240
        response = client.get(resource, headers={"Origin": "https://msx.benzac.de"})
        assert response.status_code == 200 and "Grüße" in response.text
        assert len(cues(18).decode().split("\n\n")[1].splitlines()[1:]) == 4
        assert "Wrapped subtitle text" in cues(18).decode()
        assert not any(token in response.text + json.dumps(page) for token in fixture.tokens)
        for item in (MISSING, MALFORMED):
            bad = client.get(
                private + "/subtitle-playback.json",
                params={"item_id": item, "media_source_id": SOURCE},
            ).json()
            assert bad["headline"] == "Subtitles unavailable"
            assert action(bad, "Play without subtitles").startswith("video:resolve:")
            resolved = client.get(
                action(bad, "Play without subtitles").removeprefix("video:resolve:")
            ).json()
            assert resolved["response"]["status"] == 200
            media = client.get(resolved["response"]["data"]["url"], headers={"Range": "bytes=0-31"})
            assert media.status_code == 206 and len(media.content) == 32
            outside = resolved["response"]["data"]["url"].replace(item, "f" * 32)
            assert client.get(outside).status_code == 404
        client.get(private + "/logout.json")
        assert client.get(resource).status_code == 401
