import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware

from .config import Settings
from .device_profile import MODEL, PROFILE_BASIS, evidence_warnings
from .errors import PortalError
from .jellyfin import Jellyfin, identifier
from .middleware import PairBodyLimit
from .msx import button, content, text, wrapped
from .playback import PROFILE_NAME, choose_source, compatibility_reasons, resolve
from .state import State

ItemId = Annotated[str, Query(pattern=r"^[a-fA-F0-9-]{32,36}$")]
TEMPLATE = Path(__file__).with_name("templates").joinpath("pair.html").read_text()


def create_app(settings: Settings | None = None, transport=None, state: State | None = None):
    settings = settings or Settings.from_env()
    state = state or State(settings)
    jellyfin = Jellyfin(settings, transport)
    # Native playback needs bearer URLs. Never emit request URLs from HTTP client logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await jellyfin.client.aclose()

    app = FastAPI(
        title="Jellyfin MSX",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.portal = state
    app.add_middleware(PairBodyLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "OPTIONS"],
        allow_credentials=False,
    )

    def url(path, **params):
        return settings.public_url + path + ("?" + urlencode(params) if params else "")

    def device_url(secret, endpoint, **params):
        return url(f"/msx/device/{secret}/{endpoint}", **params)

    def failure(request, error):
        if request.url.path.startswith("/msx/") and "/image/" not in request.url.path:
            return JSONResponse(wrapped(status=error.status, message=error.message))
        return JSONResponse({"error": error.message}, status_code=error.status)

    @app.middleware("http")
    async def security(request: Request, call_next):
        try:
            async with asyncio.timeout(25):
                if request.method == "POST" and request.url.path == "/pair":
                    limit(request, "login", 5)
                response = await call_next(request)
        except TimeoutError:
            response = failure(request, PortalError(504, "Request timed out. Try again."))
        except PortalError as error:
            response = failure(request, error)
        response.headers.update(
            {
                "Cache-Control": "no-store, private",
                "Pragma": "no-cache",
                # Chromium sends Origin:null for native form POSTs under no-referrer.
                # Preserve same-origin CSRF validation without exposing URLs off-site.
                "Referrer-Policy": "same-origin" if request.url.path == "/pair" else "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; style-src 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; base-uri 'none'",
            }
        )
        if not settings.allow_http:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(PortalError)
    async def portal_error(request, error):
        return failure(request, error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return failure(request, PortalError(400, "Invalid request parameters."))

    def limit(request, kind, maximum):
        # Trust only the immediate peer; forwarded addresses are never used for rate limits.
        peer = request.client.host if request.client else "unknown"
        state.limit(kind + ":" + peer, maximum)
        state.limit(kind + ":global", maximum * 4)

    def form(message="", status=200):
        csrf = secrets.token_urlsafe(32)
        page = TEMPLATE.replace("{{csrf}}", csrf).replace("{{message}}", escape(message))
        page = page.replace("{{server}}", escape(settings.jellyfin_url))
        response = HTMLResponse(page, status_code=status)
        response.set_cookie(
            "pair_csrf",
            csrf,
            secure=not settings.allow_http,
            httponly=True,
            samesite="strict",
            max_age=600,
            path="/pair",
        )
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok", "version": "0.1.0", "device_verified": False}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(
            '<!doctype html><html lang="en"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>Jellyfin MSX</title>'
            "<h1>Jellyfin MSX</h1><p>Enter this server address in MSX Start Parameter."
            '</p><p><a href="/pair">Pair a TV</a></p></html>'
        )

    @app.get("/pair", response_class=HTMLResponse)
    async def pair_form(request: Request):
        limit(request, "form", 30)
        return form()

    @app.post("/pair", response_class=HTMLResponse)
    async def pair_submit(
        request: Request,
        code: Annotated[str, Form(max_length=16)],
        username: Annotated[str, Form(min_length=1, max_length=128)],
        csrf: Annotated[str, Form(max_length=128)],
        password: Annotated[str, Form(max_length=1024)] = "",
    ):
        device = None
        try:
            cookie = request.cookies.get("pair_csrf", "")
            if (
                request.headers.get("origin") != settings.public_url
                or len(cookie) < 32
                or not secrets.compare_digest(cookie.encode(), csrf.encode())
            ):
                raise PortalError(403, "Form expired. Reload this page and retry.")
            device = state.claim(code.replace(" ", "").replace("-", ""))
            user, token = await jellyfin.authenticate(device, username, password)
            try:
                state.complete(device, user, token)
            except PortalError:
                device.token = token
                try:
                    await jellyfin.logout(device)
                finally:
                    device.token = None
                raise
            return HTMLResponse(
                '<!doctype html><html lang="en"><meta name="viewport" '
                'content="width=device-width,initial-scale=1"><title>TV paired</title>'
                '<link rel="stylesheet" href="/pair.css"><main><h1>TV paired</h1>'
                '<p role="status">Sign-in succeeded. Return to Media Station X and select '
                "<strong>Continue after pairing</strong>.</p>"
                "<p>You can close this page. No further login is needed here.</p></main></html>"
            )
        except PortalError as error:
            if device:
                device.claiming = False
            return form(
                error.message
                if error.status in {400, 403, 429}
                else "Jellyfin sign-in failed. Check your credentials and server availability.",
                error.status,
            )
        finally:
            if device:
                device.claiming = False

    @app.get("/pair.css")
    def css():
        return Response(
            "body{font:18px system-ui;margin:3rem auto;padding:0 1.2rem;max-width:32rem;"
            "background:#101820;color:#f4f7fa}label{display:block;margin:1.3rem 0 .4rem}"
            "input,button{box-sizing:border-box;width:100%;font:inherit;padding:.8rem;"
            "border-radius:.4rem;border:1px solid #8a9bad}button{margin-top:1.5rem;"
            "background:#b8f16a;color:#101820;font-weight:700}p{overflow-wrap:anywhere}"
            ":focus-visible{outline:3px solid #b8f16a;outline-offset:3px}",
            media_type="text/css",
        )

    @app.get("/msx/start.json")
    def start():
        return {
            "name": "Jellyfin MSX",
            "version": "0.1.0",
            "welcome": "none",
            "parameter": "content:" + url("/msx/pair.json"),
        }

    async def authorization_input(request, field):
        limit(request, "authorization", 12)
        if request.headers.get("origin") != settings.public_url:
            raise PortalError(403, "Same-origin request required.")
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise PortalError(400, "JSON request required.")
        try:
            data = await request.json()
        except (ValueError, UnicodeError, RecursionError):
            raise PortalError(400, "Invalid authorization request.") from None
        if (
            not isinstance(data, dict)
            or set(data) != {field}
            or not isinstance(data[field], str)
            or len(data[field]) != 43
        ):
            raise PortalError(400, "Invalid authorization request.")
        return data[field]

    @app.post("/api/device-authorization/enroll")
    async def enroll_authorization(request: Request):
        secret = await authorization_input(request, "session")
        renewal, expires = state.remember(secret)
        return {"renewal": renewal, "expires": expires, "generation": 0}

    @app.post("/api/device-authorization/renew")
    async def renew_authorization(request: Request):
        renewal = await authorization_input(request, "renewal")
        secret, replacement, expires = state.restore(renewal)
        device = state.get(secret)
        try:
            # Check current upstream authorization before handing out a usable session.
            await jellyfin.json("GET", f"/Users/{device.user_id}/Views", device)
        except PortalError as error:
            # Rotation is already committed: uncertain outcomes require safe re-pairing.
            state.remove(secret)
            raise PortalError(
                error.status, "Authorization could not be restored. Pair again."
            ) from None
        # Disconnect may have occurred while the upstream request was outstanding.
        state.get(secret)
        return {
            "renewal": replacement,
            "session": secret,
            "expires": expires,
            "generation": device.authorization_generation,
        }

    @app.get("/msx/pair.json")
    async def pairing(request: Request):
        limit(request, "new_pair", 10)
        secret, device = state.pair()
        return content(
            "Pair this TV",
            [
                button(
                    f"On your phone/PC open {url('/pair')}", "info:Use your phone or PC to pair."
                ),
                button(
                    f"TV code: {device.code[:4]} {device.code[4:]} "
                    f"(valid {(settings.pairing_ttl + 59) // 60} minutes)",
                    "info:Enter this code on the pairing page.",
                ),
                button("Continue after pairing", "content:" + device_url(secret, "home.json")),
                button("Create new code", "content:" + url("/msx/pair.json")),
            ],
        )

    @app.get("/msx/device/{secret}/home.json")
    async def home(secret: str):
        device = state.get(secret, authenticated=False)
        if not device.token:
            return content(
                "Waiting for pairing",
                [
                    button("Continue after pairing", "content:" + device_url(secret, "home.json")),
                    button("Create new code", "content:" + url("/msx/pair.json")),
                ],
            )
        result = await jellyfin.json("GET", f"/Users/{device.user_id}/Views", device)
        entries = [
            button(
                item.get("Name", "Library"),
                "content:"
                + device_url(secret, "browse.json", parent_id=identifier(item.get("Id"))),
            )
            for item in result.get("Items", [])
        ]
        entries += [
            button("Diagnostics", "content:" + device_url(secret, "diagnostics.json")),
            button("Disconnect TV", "content:" + device_url(secret, "disconnect.json")),
        ]
        return content("Jellyfin libraries", entries)

    @app.get("/msx/device/{secret}/browse.json")
    async def browse(
        secret: str, parent_id: ItemId, offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0
    ):
        device = state.get(secret)
        identifier(parent_id)
        result = await jellyfin.json(
            "GET",
            f"/Users/{device.user_id}/Items",
            device,
            params={
                "ParentId": parent_id,
                "StartIndex": offset,
                "Limit": 24,
                "SortBy": "SortName",
                "SortOrder": "Ascending",
                "Recursive": "false",
                "Fields": "Overview,MediaSources",
                "EnableTotalRecordCount": "true",
            },
        )
        entries = []
        for item in result.get("Items", []):
            item_id = identifier(item.get("Id"))
            folder = item.get("IsFolder") or item.get("Type") in {"Series", "Season", "BoxSet"}
            endpoint = "browse.json" if folder else "detail.json"
            params = {"parent_id" if folder else "item_id": item_id}
            entry = button(
                item.get("Name", "Untitled"),
                "content:" + device_url(secret, endpoint, **params),
                titleFooter=text(item.get("ProductionYear", item.get("Type", ""))),
            )
            if item.get("ImageTags", {}).get("Primary"):
                entry["image"] = device_url(secret, f"image/{item_id}")
            entries.append(entry)
        total = result.get("TotalRecordCount")
        if not isinstance(total, int):
            total = offset + len(entries)
        if offset + 24 < total:
            entries.append(
                button(
                    "Next page",
                    "content:"
                    + device_url(secret, "browse.json", parent_id=parent_id, offset=offset + 24),
                )
            )
        if offset:
            entries.append(
                button(
                    "Previous page",
                    "content:"
                    + device_url(
                        secret, "browse.json", parent_id=parent_id, offset=max(0, offset - 24)
                    ),
                )
            )
        entries.append(button("Libraries", "content:" + device_url(secret, "home.json")))
        return content("Library", entries, posters=True)

    @app.get("/msx/device/{secret}/detail.json")
    async def detail(secret: str, item_id: ItemId):
        device = state.get(secret)
        identifier(item_id)
        item = await jellyfin.item(device, item_id)

        def play_button(label, force=False, subtitle=-1):
            target = device_url(
                secret,
                "play.json",
                item_id=item_id,
                media_source_id=identifier(selected.get("Id")),
                force=str(force).lower(),
                subtitle=subtitle,
            )
            return button(
                label,
                "video:resolve:" + target + "&platform={PLATFORM}&player={PLAYER}",
                playerLabel=text(item.get("Name")),
            )

        entries = []
        try:
            selected = choose_source(item, settings.max_bitrate, settings.allow_transcoding)
            entries.append(play_button("Try original (TV unverified)"))
            entries.append(
                button(
                    MODEL + ": documentation-based candidate",
                    "info:" + ". ".join(evidence_warnings(selected)),
                )
            )
        except PortalError as error:
            selected = {}
            entries.append(
                button("Outside documented candidate profile", "info:" + text(error.message))
            )
            versions = [
                {
                    "version": index + 1,
                    "reasons": compatibility_reasons(source, settings.max_bitrate),
                }
                for index, source in enumerate((item.get("MediaSources") or [])[:8])
            ]
            explanation = (
                "; ".join(
                    f"Version {version['version']}: " + ", ".join(version["reasons"])
                    for version in versions
                )
                or "No media sources returned by Jellyfin"
            )
            entries.append(button("Compatibility details", "info:" + text(explanation, 1200)))
            state.record(
                device,
                {
                    "event": "compatibility_rejection",
                    "profile": PROFILE_NAME,
                    "profile_basis": PROFILE_BASIS,
                    "versions": versions,
                    "transcoding_allowed": settings.allow_transcoding,
                    "device_playback_verified": False,
                },
            )
        if settings.allow_transcoding and selected:
            entries.append(play_button("Force HLS transcode", force=True))
        subtitles = {}
        for stream in selected.get("MediaStreams", []):
            if stream.get("Type") == "Subtitle" and isinstance(stream.get("Index"), int):
                subtitles[stream["Index"]] = text(
                    stream.get("DisplayTitle", stream.get("Language", "Subtitle")), 100
                )
        entries += [
            play_button(f"Burn subtitle: {label}", force=True, subtitle=index)
            for index, label in sorted(subtitles.items())[:8]
            if settings.allow_transcoding
        ]
        overview = text(item.get("Overview"), 1200)
        entries.append(
            button(
                overview or "No synopsis available", "info:" + (overview or "No synopsis available")
            )
        )
        entries.append(
            button(
                f"Year: {item.get('ProductionYear', 'unknown')} | "
                f"Type: {item.get('Type', 'unknown')}",
                "info:Metadata supplied by Jellyfin.",
            )
        )
        entries.append(button("Diagnostics", "content:" + device_url(secret, "diagnostics.json")))
        return content(item.get("Name", "Details"), entries)

    @app.get("/msx/device/{secret}/play.json")
    async def play(
        secret: str,
        item_id: ItemId,
        force: bool = False,
        subtitle: Annotated[int, Query(ge=-1, le=1024)] = -1,
        media_source_id: ItemId | None = None,
        platform: str = "unknown",
        player: str = "unknown",
    ):
        device = state.get(secret)
        identifier(item_id)
        limit_key = "play:" + device.device_id
        state.limit(limit_key, 12)
        try:
            stream_url, decision = await resolve(
                jellyfin, device, item_id, force, subtitle, media_source_id
            )
        except PortalError as error:
            state.record(
                device,
                {"id": secrets.token_hex(8), "event": "playback_error", "status": error.status},
            )
            raise
        decision.update(platform=text(platform, 80), player=text(player, 80))
        state.record(device, decision)
        return wrapped({"url": stream_url, "label": f"{decision['mode']} / {decision['id']}"})

    @app.get("/msx/device/{secret}/image/{item_id}")
    async def image(secret: str, item_id: str):
        device = state.get(secret)
        identifier(item_id)
        await jellyfin.item(
            device, item_id
        )  # Jellyfin image endpoints alone may not enforce library access
        upstream, raw = await jellyfin.fetch(
            "GET",
            f"/Items/{item_id}/Images/Primary",
            device,
            params={"MaxWidth": 360, "Quality": 80, "Format": "jpg"},
        )
        media_type = upstream.headers.get("content-type", "").split(";")[0]
        if media_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise PortalError(502, "Unsupported image response.")
        return Response(raw, media_type=media_type)

    @app.get("/api/device/{secret}/diagnostics")
    async def diagnostics_api(secret: str):
        device = state.get(secret)
        return {
            "version": "0.1.0",
            "profile": PROFILE_NAME,
            "device_verified": False,
            "expires_in_seconds": max(0, int(device.expires - state.clock())),
            "events": device.diagnostics,
        }

    @app.get("/msx/device/{secret}/diagnostics.json")
    async def diagnostics_tv(secret: str):
        device = state.get(secret)
        entries = [
            button(
                f"Profile: {PROFILE_NAME}", "info:Experimental profile. Physical TV tests required."
            ),
            button(
                "Playback on this device is unverified",
                "info:Diagnostics record decisions, not successful decoding.",
            ),
        ]
        entries += [
            button(json.dumps(event), "info:Record the diagnostic ID with your device test.")
            for event in reversed(device.diagnostics)
        ]
        entries.append(button("Libraries", "content:" + device_url(secret, "home.json")))
        return content("Diagnostics", entries)

    @app.get("/msx/device/{secret}/disconnect.json")
    async def disconnect(secret: str):
        state.get(secret)
        return content(
            "Disconnect this TV?",
            [
                button("Confirm disconnect", "content:" + device_url(secret, "logout.json")),
                button("Cancel", "back"),
            ],
        )

    @app.get("/msx/device/{secret}/logout.json")
    async def logout(secret: str):
        device = state.get(secret)
        state.remove(secret)
        try:
            await jellyfin.logout(device)
            message = "Disconnected"
        except PortalError:
            message = "TV disconnected. Upstream logout failed; revoke this session in Jellyfin."
        return content(message, [button("Pair again", "content:" + url("/msx/pair.json"))])

    return app
