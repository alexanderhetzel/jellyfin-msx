import copy
import json
import re
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.state import State

USER = "1" * 32
MOVIE = "2" * 32
SOURCE = "3" * 32
LIBRARY = "4" * 32
SERIES = "5" * 32
SEASON = "6" * 32
EPISODE = "7" * 32
TOKEN = "test-token-not-a-real-secret-123456"


def hidden_fields(response):
    return dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', response.text))


def code_stage(client, code):
    fields = hidden_fields(client.get("/pair"))
    response = client.post(
        "/pair", data={**fields, "code": code}, headers={"Origin": str(client.base_url).rstrip("/")}
    )
    assert response.status_code == 200 and 'name="stage"' in response.text
    return hidden_fields(response)


def media_source():
    return {
        "Id": SOURCE,
        "Container": "mp4",
        "Bitrate": 2_000_000,
        "SupportsDirectPlay": True,
        "SupportsTranscoding": True,
        "TranscodingUrl": f"/Videos/{MOVIE}/master.m3u8?VideoCodec=h264&AudioCodec=aac",
        "TranscodingSubProtocol": "hls",
        "MediaStreams": [
            {
                "Type": "Video",
                "Codec": "h264",
                "Width": 1280,
                "Height": 720,
                "BitDepth": 8,
                "Level": 31,
                "Profile": "High",
                "VideoRange": "SDR",
                "AverageFrameRate": 24,
            },
            {"Type": "Audio", "Codec": "aac", "Channels": 2},
            {"Type": "Subtitle", "Codec": "srt", "Index": 2, "Language": "deu"},
        ],
    }


class FakeJellyfin:
    def __init__(self):
        self.requests = []
        self.source = media_source()
        self.error = None
        self.error_code = None
        self.timeout = False
        self.deny_item = False
        self.logout_error = False
        self.image_type = "image/jpeg"
        self.image_bytes = b"fake-jpeg"
        self.empty = False
        self.malformed = False
        self.children = {
            LIBRARY: [
                {
                    "Id": MOVIE,
                    "Name": "Test Movie",
                    "Type": "Movie",
                    "ProductionYear": 2020,
                    "ImageTags": {"Primary": "tag"},
                },
                {"Id": SERIES, "Name": "Test Series", "Type": "Series", "IsFolder": True},
            ],
            SERIES: [{"Id": SEASON, "Name": "Season 1", "Type": "Season", "IsFolder": True}],
            SEASON: [{"Id": EPISODE, "Name": "Episode 1", "Type": "Episode"}],
        }

    def handle(self, request):
        self.requests.append(request)
        path = request.url.path.removeprefix("/jellyfin")
        if self.timeout:
            raise httpx.ReadTimeout("private URL must not be reflected", request=request)
        if self.error:
            return httpx.Response(self.error, text="private upstream details")
        if self.malformed:
            return httpx.Response(200, text="not-json")
        if path == "/Users/AuthenticateByName":
            credentials = json.loads(request.content)
            if credentials["Pw"] != "test-password":
                return httpx.Response(401)
            return httpx.Response(200, json={"User": {"Id": USER}, "AccessToken": TOKEN})
        if f'Token="{TOKEN}"' not in request.headers.get("authorization", ""):
            return httpx.Response(401)
        if path == "/Sessions/Logout":
            return httpx.Response(503 if self.logout_error else 204)
        if self.deny_item:
            return httpx.Response(403)
        if path == f"/Users/{USER}/Views":
            return httpx.Response(200, json={"Items": [{"Id": LIBRARY, "Name": "Movies & TV"}]})
        if path == f"/Users/{USER}/Items":
            children = self.children.get(request.url.params.get("ParentId"), [])
            offset = int(request.url.params.get("StartIndex", 0))
            return httpx.Response(
                200,
                json={"Items": children[offset : offset + 24], "TotalRecordCount": len(children)},
            )
        if path.startswith(f"/Users/{USER}/Items/"):
            return httpx.Response(
                200,
                json={
                    "Id": path.rsplit("/", 1)[-1],
                    "Name": "A movie",
                    "Type": "Movie",
                    "Overview": "A synopsis",
                    "MediaSources": [copy.deepcopy(self.source)],
                },
            )
        if path.endswith("/PlaybackInfo"):
            return httpx.Response(
                200,
                json={
                    "MediaSources": [] if self.empty else [self.source],
                    "PlaySessionId": "test-play-session",
                    "ErrorCode": self.error_code,
                },
            )
        if "/Images/" in path:
            return httpx.Response(
                200, content=self.image_bytes, headers={"Content-Type": self.image_type}
            )
        raise AssertionError(f"Unexpected mock path {path}")


@pytest.fixture
def portal():
    now = [1000.0]
    settings = Settings(
        "https://portal.test", "https://jellyfin.test/jellyfin", allow_transcoding=True
    )
    state = State(settings, clock=lambda: now[0])
    fake = FakeJellyfin()
    app = create_app(settings, transport=httpx.MockTransport(fake.handle), state=state)
    with TestClient(app, base_url=settings.public_url) as client:
        secret, device = state.pair()
        state.complete(device, USER, TOKEN)
        yield SimpleNamespace(
            client=client,
            state=state,
            fake=fake,
            device=device,
            secret=secret,
            now=now,
            settings=settings,
            path=f"/msx/device/{secret}",
        )
