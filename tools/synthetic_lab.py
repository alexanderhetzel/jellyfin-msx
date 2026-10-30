"""Isolated synthetic lab; no real Jellyfin connection or authentication bypass.

Run with python -m tools.synthetic_lab. The fixture models the consumed Jellyfin
API contract; it is not a Jellyfin server compatibility test.
"""

import argparse
import copy
import json
import secrets
import struct
import zlib
from collections import Counter
from pathlib import Path

import httpx
import uvicorn
from fastapi import Request
from fastapi.responses import FileResponse, Response

from jellyfin_msx.config import Settings
from tools.lab import ROOT, build_lab

USER, LIBRARY, MOVIE, DENIED, SOURCE = (str(n) * 32 for n in range(1, 6))
USERNAME = "synthetic-viewer"
PASSWORD = "synthetic-password"
MEDIA = ROOT / ".lab/media/synthetic.mp4"


def synthetic_poster():
    """Independent 240x360 RGB bars, large enough for a visible poster check."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    pixels = b"".join(b"\x00" + bytes((40 + y // 2, 183, 65)) * 240 for y in range(360))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 240, 360, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


POSTER = synthetic_poster()


def source():
    return {
        "Id": SOURCE,
        "Container": "mp4",
        "SupportsDirectPlay": True,
        "SupportsTranscoding": False,
        "MediaStreams": [
            {"Type": "Video", "Codec": "h264", "Width": 1280, "Height": 720, "BitDepth": 8},
            {"Type": "Audio", "Codec": "aac", "Channels": 2},
        ],
    }


class SyntheticJellyfin:
    """Strict, process-local transport with random login tokens and no network fallback."""

    def __init__(self, origin, fault=None):
        self.origin = origin
        self.fault = fault
        self.tokens = set()
        self.media_requests = Counter()

    def handle(self, request):
        if str(request.url).split("/jellyfin", 1)[0] != self.origin:
            raise RuntimeError("Synthetic transport rejected an unexpected origin")
        path = request.url.path.removeprefix("/jellyfin")
        if path == "/Users/AuthenticateByName" and request.method == "POST":
            body = json.loads(request.content)
            if body != {"Username": USERNAME, "Pw": PASSWORD}:
                return httpx.Response(401)
            token = secrets.token_urlsafe(32)
            self.tokens.add(token)
            return httpx.Response(200, json={"User": {"Id": USER}, "AccessToken": token})
        auth = request.headers.get("authorization", "")
        token = next((t for t in self.tokens if f'Token="{t}"' in auth), None)
        if not token:
            return httpx.Response(401)
        if path == "/Sessions/Logout" and request.method == "POST":
            self.tokens.remove(token)
            return httpx.Response(204)
        if request.method == "GET" and path == f"/Users/{USER}/Views":
            if self.fault == "json":
                return httpx.Response(200, text="deliberately invalid JSON")
            return httpx.Response(
                200, json={"Items": [{"Id": LIBRARY, "Name": "Synthetic movies"}]}
            )
        if request.method == "GET" and path == f"/Users/{USER}/Items":
            if request.url.params.get("ParentId") != LIBRARY:
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "Items": [
                        {
                            "Id": MOVIE,
                            "Name": "Synthetic clip",
                            "Type": "Movie",
                            "ImageTags": {"Primary": "synthetic"},
                        },
                        {"Id": DENIED, "Name": "Oversized candidate", "Type": "Movie"},
                    ],
                    "TotalRecordCount": 2,
                },
            )
        if request.method == "GET" and path in {
            f"/Users/{USER}/Items/{MOVIE}",
            f"/Users/{USER}/Items/{DENIED}",
        }:
            item_source = source()
            if path.endswith(DENIED):
                item_source["MediaStreams"][0].update(Width=3840, Height=2160)
            return httpx.Response(
                200,
                json={
                    "Id": path.rsplit("/", 1)[-1],
                    "Name": "Synthetic clip",
                    "Type": "Movie",
                    "Overview": "Generated test pattern and tone; no operator media.",
                    "MediaSources": [item_source],
                },
            )
        if request.method == "GET" and path == f"/Items/{MOVIE}/Images/Primary":
            return httpx.Response(200, content=POSTER, headers={"Content-Type": "image/png"})
        if request.method == "POST" and path == f"/Items/{MOVIE}/PlaybackInfo":
            body = json.loads(request.content)
            if (
                body.get("MediaSourceId") != SOURCE
                or not body.get("EnableDirectPlay")
                or body.get("EnableDirectStream") is not False
                or body.get("EnableTranscoding") is not False
                or body.get("SubtitleStreamIndex") != -1
            ):
                return httpx.Response(400)
            candidate = copy.deepcopy(source())
            candidate["SupportsDirectPlay"] = self.fault != "playback"
            return httpx.Response(200, json={"MediaSources": [candidate]})
        return httpx.Response(404)


def build_synthetic_lab(settings, *, media=MEDIA, fault=None):
    if settings.jellyfin_url != settings.public_url + "/jellyfin":
        raise ValueError("Synthetic Jellyfin must use the lab origin and /jellyfin")
    if fault not in {None, "json", "playback", "csrf"}:
        raise ValueError("Unknown synthetic failure")
    fixture = SyntheticJellyfin(settings.public_url, fault)
    app, launch = build_lab(settings, transport=httpx.MockTransport(fixture.handle))

    @app.api_route(f"/jellyfin/Videos/{MOVIE}/stream.mp4", methods=["GET", "HEAD"])
    async def stream(request: Request):
        # This is the fixture's original-file endpoint, not a production media proxy.
        if (
            request.query_params.get("ApiKey") not in fixture.tokens
            or request.query_params.get("MediaSourceId") != SOURCE
            or request.query_params.get("Static") != "true"
        ):
            fixture.media_requests["denied"] += 1
            return Response(status_code=401)
        if not media.is_file():
            fixture.media_requests["missing"] += 1
            return Response(status_code=503)
        fixture.media_requests["original"] += 1
        return FileResponse(media, media_type="video/mp4")

    @app.get("/__synthetic/report")
    async def report():
        return {
            "fixture": "synthetic-jellyfin-contract",
            "fault": fault,
            "media_requests": dict(fixture.media_requests),
            "browser_verified": False,
            "physical_device_verified": False,
        }

    return app, launch, fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18091)
    parser.add_argument("--cert", type=Path, help="Existing explicitly trusted loopback leaf")
    parser.add_argument("--key", type=Path)
    parser.add_argument("--http", action="store_true", help="Contract/API only, not hosted MSX")
    parser.add_argument("--fault", choices=["json", "playback"])
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    if not args.http and (not args.cert or not args.key):
        parser.error("HTTPS requires existing --cert and --key; no trust is changed")
    if args.http and (args.cert or args.key):
        parser.error("Do not combine --http with TLS options")
    if not MEDIA.is_file():
        parser.error("Generate .lab/media/synthetic.mp4 using tools/make_test_clip.py first")
    origin = f"{'http' if args.http else 'https'}://localhost:{args.port}"
    settings = Settings(origin, origin + "/jellyfin", allow_http=args.http, pairing_ttl=1800)
    app, _, _ = build_synthetic_lab(settings, fault=args.fault)
    print(f"Synthetic dashboard: {origin}/__lab/", flush=True)
    print("Use documented synthetic credentials in the normal pairing form. No operator account.")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        proxy_headers=False,
        **({} if args.http else {"ssl_certfile": str(args.cert), "ssl_keyfile": str(args.key)}),
    )


if __name__ == "__main__":
    main()
