"""Loopback-only MSX integration lab. Uses a real operator-selected Jellyfin server.

No credentials are accepted by this launcher. Sign in through the normal pairing form.
"""

import argparse
import base64
import json
import os
import subprocess
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx
import uvicorn
from fastapi.responses import HTMLResponse

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.msx import button, content

ROOT = Path(__file__).resolve().parents[1]
TLS = ROOT / ".lab" / "tls"


def smoke_url():
    """Pure runtime fixture; does not claim Jellyfin integration coverage."""
    page = content(
        "Jellyfin MSX - runtime smoke",
        [
            button("Movies navigation", "info:Movies navigation works"),
            button("Series navigation", "info:Series navigation works"),
            button(
                "Play official MSX sample",
                "video:https://msx.benzac.de/media/video1.mp4",
                playerLabel="Official MSX sample",
            ),
            button("Diagnostics", "info:Official web runtime. SAPHI remains unverified."),
        ],
    )
    data = base64.b64encode(json.dumps(page).encode()).decode()
    return (
        "https://msx.benzac.de/?start="
        + quote("content:json:" + data, safe="")
        + "&input=1&layout=auto&animate=0&init=1&suspend=0"
    )


class TrafficRecorder(httpx.AsyncBaseTransport):
    """Pass through real HTTP; retain only policy flags and counts, never URLs/tokens."""

    def __init__(self, transport=None):
        self.transport = transport if transport is not None else httpx.AsyncHTTPTransport()
        self.counts = Counter()
        self.responses = {}
        self.negotiations = []

    async def handle_async_request(self, request):
        path = request.url.path
        category = (
            "playback_info"
            if path.endswith("/PlaybackInfo")
            else "authentication"
            if path.endswith("/AuthenticateByName")
            else "poster"
            if "/Images/" in path
            else "logout"
            if path.endswith("/Sessions/Logout")
            else "library"
        )
        self.counts[category] += 1
        if category == "playback_info":
            body = json.loads(request.content)
            self.negotiations.append(
                {
                    key: body.get(key)
                    for key in (
                        "EnableDirectPlay",
                        "EnableDirectStream",
                        "EnableTranscoding",
                        "SubtitleStreamIndex",
                    )
                }
            )
            del self.negotiations[:-30]
        response = await self.transport.handle_async_request(request)
        statuses = self.responses.setdefault(category, Counter())
        statuses[str(response.status_code)] += 1
        return response

    async def aclose(self):
        await self.transport.aclose()


def build_lab(settings, *, transport=None):
    if urlsplit(settings.public_url).hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("The integration lab must stay on loopback")
    if settings.allow_transcoding:
        raise ValueError("The integration lab never enables transcoding")
    recorder = TrafficRecorder(transport)
    app = create_app(settings, transport=recorder)
    counts = Counter()
    pairing_results = []
    launch = (
        "https://msx.benzac.de/?start="
        + quote("content:" + settings.public_url + "/msx/pair.json", safe="")
        + "&input=2&layout=auto&animate=0&init=1&suspend=0"
    )

    @app.middleware("http")
    async def observe(request, call_next):
        # Record only public endpoint names, never path parameters or query strings.
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if endpoint in {
            "pair",
            "pair.json",
            "home.json",
            "browse.json",
            "detail.json",
            "play.json",
            "diagnostics.json",
            "disconnect.json",
            "logout.json",
        }:
            counts[endpoint] += 1
        response = await call_next(request)
        if request.method == "POST" and request.url.path == "/pair":
            pairing_results.append(
                {
                    "status": response.status_code,
                    # A successful code-check response is not an authenticated session.
                    "outcome": "http-accepted" if response.status_code == 200 else "error",
                }
            )
            del pairing_results[:-20]
        return response

    @app.get("/__lab/", response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(
            '<!doctype html><html lang="en"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>MSX integration lab</title>'
            '<link rel="stylesheet" href="/pair.css"><main><h1>MSX integration lab</h1>'
            "<p>Real MSX web runtime. Direct Play only. "
            "Physical SAPHI playback remains unverified.</p>"
            f'<p><a href="{escape(launch, quote=True)}" target="_blank" rel="noreferrer">'
            "Open Media Station X</a></p>"
            '<p><a href="/pair" target="_blank">Open pairing form</a></p>'
            '<p><a href="/__lab/report">Redacted integration observations</a></p>'
            "<p>Click visible entries, or use arrows and Enter in MSX. "
            "Enter credentials only in the pairing form.</p></main></html>"
        )

    @app.get("/__lab/report")
    async def report():
        events = [
            event for device in app.state.portal.devices.values() for event in device.diagnostics
        ]
        return {
            "target": "official-msx-web",
            "physical_device_verified": False,
            "transcoding_allowed": False,
            "portal_requests": dict(counts),
            "jellyfin_requests": dict(recorder.counts),
            "jellyfin_responses": {key: dict(value) for key, value in recorder.responses.items()},
            "negotiations": recorder.negotiations,
            "pairing_results": pairing_results,
            "playback_decisions": events[-30:],
            "paired_sessions": sum(bool(d.token) for d in app.state.portal.devices.values()),
            "interpretation": "Network observations do not prove successful video decoding. "
            "Verify playback using the visible MSX player and video element.",
        }

    return app, launch


def certificate():
    TLS.mkdir(parents=True, exist_ok=True)
    key, cert = TLS / "key.pem", TLS / "cert.pem"
    if cert.exists() and key.exists():
        valid = (
            subprocess.run(
                ["openssl", "x509", "-in", str(cert), "-noout", "-checkend", "60"],
                capture_output=True,
            ).returncode
            == 0
        )
        if not valid:
            raise ValueError(
                "Local test certificate expired. Remove its old trust entry and "
                ".lab/tls certificate/key, then restart and explicitly trust the new certificate."
            )
    if not key.exists() or not cert.exists():
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-sha256",
                "-days",
                "1",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost,IP:127.0.0.1",
                "-addext",
                "basicConstraints=critical,CA:FALSE",
                "-addext",
                "extendedKeyUsage=serverAuth",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        key.chmod(0o600)
    return key, cert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jellyfin-url", default=os.getenv("JELLYFIN_URL"), required=False)
    parser.add_argument("--port", type=int, default=18091)
    parser.add_argument(
        "--http", action="store_true", help="API development only; hosted MSX needs HTTPS"
    )
    parser.add_argument(
        "--smoke-url", action="store_true", help="Print standalone MSX renderer/player smoke URL"
    )
    args = parser.parse_args()
    if args.smoke_url:
        print(smoke_url())
        return
    if not args.jellyfin_url:
        parser.error("Set JELLYFIN_URL or supply --jellyfin-url. Never supply credentials.")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    public = f"{'http' if args.http else 'https'}://localhost:{args.port}"
    settings = Settings(
        public, args.jellyfin_url, allow_http=args.http, allow_transcoding=False, pairing_ttl=1800
    )
    app, launch = build_lab(settings)
    print(f"Lab dashboard: {public}/__lab/", flush=True)
    print(f"MSX runtime: {launch}", flush=True)
    tls_options = {}
    if not args.http:
        key, cert = certificate()
        print(
            "HTTPS requires explicit local certificate trust; "
            "no trust settings are changed automatically.",
            flush=True,
        )
        tls_options = {"ssl_keyfile": str(key), "ssl_certfile": str(cert)}
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        workers=1,
        access_log=False,
        proxy_headers=False,
        **tls_options,
    )


if __name__ == "__main__":
    main()
