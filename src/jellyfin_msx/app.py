import asyncio
import json
import logging
import math
import re
import secrets
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.cors import CORSMiddleware

from .config import Settings
from .device_profile import MODEL, PROFILE_BASIS, evidence_warnings
from .errors import PortalError
from .jellyfin import Jellyfin, identifier
from .lifecycle import Lifecycle
from .middleware import PairBodyLimit
from .msx import button, content, pairing_page, subtitle_playback, text, wrapped
from .pairing_qr import activation_png
from .playback import PROFILE_NAME, choose_source, compatibility_reasons, resolve
from .presentation import PAIR_CSS
from .state import State
from .subtitles import OFFICIAL_ORIGINS, SubtitleResources

ItemId = Annotated[str, Query(pattern=r"^[a-fA-F0-9-]{32,36}$")]
TEMPLATE = Path(__file__).with_name("templates").joinpath("pair.html").read_text(encoding="utf-8")
SUBTITLE_BRIDGE = (
    Path(__file__)
    .with_name("templates")
    .joinpath("subtitle-bridge.html")
    .read_text(encoding="utf-8")
)


def create_app(settings: Settings | None = None, transport=None, state: State | None = None):
    settings = settings or Settings.from_env()
    state = state or State(settings)
    jellyfin = Jellyfin(settings, transport)
    subtitles = SubtitleResources(jellyfin, state)
    lifecycle = Lifecycle(clock=state.clock, maximum=settings.max_states)
    # Native playback needs bearer URLs. Never emit request URLs from HTTP client logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(app):
        async def sweep():
            while True:
                await asyncio.sleep(2)
                await lifecycle.expire(send_report, authorize_report)

        task = asyncio.create_task(sweep())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await jellyfin.client.aclose()

    app = FastAPI(
        title="Jellyfin MSX",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.portal = state
    app.state.lifecycle = lifecycle
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
                    limit(request, "pair_post", 10)
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
                "Referrer-Policy": (
                    "same-origin"
                    if request.url.path == "/pair" and not request.query_params.get("activation")
                    else "no-referrer"
                ),
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; style-src 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; base-uri 'none'",
            }
        )
        if request.url.path in {"/subtitle-bridge.html", "/lifecycle.html"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self' https://msx.benzac.de; "
                "connect-src 'self'; frame-ancestors https://msx.benzac.de "
                "https://www.msx.benzac.de; base-uri 'none'"
            )
        if not settings.allow_http:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/device/") and "/subtitles/" in request.url.path:
            # Override the general read-only MSX CORS policy for private subtitle bytes.
            for header in ("Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"):
                if header in response.headers:
                    del response.headers[header]
            response.headers["Vary"] = "Origin"
            if request.headers.get("origin") in OFFICIAL_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
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

    def authorize_report(grant):
        try:
            state.get(grant.session_key)
            return True
        except PortalError:
            return False

    async def send_report(kind, grant, payload):
        device = state.get(grant.session_key)
        if kind == "stop":
            # Jellyfin otherwise infers watched from its near-end threshold.
            # Unknown disappearance is never evidence of natural completion.
            payload = {**payload, "Failed": grant.terminal != "ended"}
        suffix = {"start": "", "progress": "/Progress", "stop": "/Stopped"}[kind]
        await jellyfin.fetch("POST", "/Sessions/Playing" + suffix, device, json=payload)

    def bearer(request):
        value = request.headers.get("authorization", "")
        if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{43}", value):
            raise PortalError(401, "Playback authorization required.")
        return value[7:]

    async def playback_body(request):
        if request.headers.get("origin", settings.public_url) != settings.public_url:
            raise PortalError(403, "Playback origin rejected.")
        if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            raise PortalError(415, "JSON required.")

        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError
                value[key] = item
            return value

        try:
            body = json.loads(await request.body(), object_pairs_hook=unique)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise PortalError(400, "Playback report rejected.") from error
        if type(body) is not dict:
            raise PortalError(400, "Playback report rejected.")
        return body

    @app.post("/api/playback/start")
    async def playback_start(request: Request):
        secret = bearer(request)
        device = state.get(secret)
        state.limit("lifecycle-start:" + device.device_id, 12)
        limit(request, "lifecycle-start", 48)
        body = await playback_body(request)
        if (
            not {"item_id", "media_source_id"} <= set(body)
            or set(body) - {"item_id", "media_source_id", "force", "subtitle"}
            or type(body.get("force", False)) is not bool
            or type(body.get("subtitle", -1)) is not int
            or not -1 <= body.get("subtitle", -1) <= 1024
        ):
            raise PortalError(400, "Playback report rejected.")
        item_id, source_id = identifier(body["item_id"]), identifier(body["media_source_id"])
        context = {}
        stream_url, decision = await resolve(
            jellyfin,
            device,
            item_id,
            body.get("force", False),
            body.get("subtitle", -1),
            source_id,
            playback_context=context,
        )
        state.get(secret)  # Expiry/revocation during upstream negotiation fails closed.
        ticks, play_session = context["duration_ticks"], context["play_session_id"]
        if (
            type(ticks) not in (int, float)
            or not math.isfinite(ticks)
            or not 0 < ticks <= 864000 * 10_000_000
            or not isinstance(play_session, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", play_session)
        ):
            raise PortalError(409, "Playback reporting metadata unavailable. Reopen details.")
        grant = await lifecycle.issue(
            secret,
            item_id,
            context["source_id"],
            play_session,
            ticks / 10_000_000,
            device.expires,
            "DirectPlay" if context["mode"] == "DirectPlay" else "Transcode",
            send=send_report,
        )
        state.get(secret)  # The session lock/old Stop may have awaited during logout.
        state.record(device, decision)
        return {
            "grant": grant.secret,
            "playback_id": grant.playback_id,
            "url": stream_url,
            "duration": grant.duration,
            "expires_in": min(28800, device.expires - state.clock()),
        }

    @app.post("/api/playback/observations")
    async def playback_observations(request: Request):
        secret = bearer(request)
        grant = lifecycle.get(secret)
        state.get(grant.session_key)
        limit(request, "lifecycle-observations", 240)
        body = await playback_body(request)
        return await lifecycle.submit(secret, grant.session_key, body, send_report)

    def form(message="", status=200, device=None):
        csrf = secrets.token_urlsafe(32)
        page = TEMPLATE.replace("{{csrf}}", csrf).replace("{{message}}", escape(message))
        page = page.replace("{{server}}", escape(settings.jellyfin_url))
        if device:
            page = page.replace("{{heading}}", "Sign in to Jellyfin")
            page = page.replace("{{step}}", "Step 2 of 2 · Sign in")
            grant = state.stage(device, csrf)
            fields = (
                f'<input type="hidden" name="stage" value="{grant}">'
                '<label for="username">Jellyfin username</label>'
                '<input id="username" name="username" autocomplete="username" '
                'maxlength="128" required>'
                '<label for="password">Jellyfin password</label>'
                '<input id="password" name="password" type="password" '
                'autocomplete="current-password" maxlength="1024">'
                '<button type="submit">Pair this TV</button>'
            )
            instructions = "TV code verified. Sign in to pair this TV before its code expires."
            help_text = (
                "Your password is used for this sign-in and is not stored. "
                '<a href="/pair">Use a different TV code</a>.'
            )
        else:
            page = page.replace("{{heading}}", "Pair your TV")
            page = page.replace("{{step}}", "Step 1 of 2 · TV code")
            fields = (
                '<label for="code">TV code</label>'
                '<input id="code" name="code" inputmode="numeric" autocomplete="off" '
                'maxlength="16" '
                'placeholder="1234 5678" required>'
                '<button type="submit">Check TV code</button>'
            )
            instructions = "Enter the code shown in Media Station X. Next, sign in to Jellyfin."
            help_text = "Need a new code? Select Create new code in Media Station X."
        page = page.replace("{{fields}}", fields).replace("{{instructions}}", instructions)
        page = page.replace("{{help}}", help_text)
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
            '<link rel="stylesheet" href="/pair.css"><main>'
            '<p class="brand">Jellyfin MSX</p><h1>Watch with Media Station X</h1>'
            "<p>Enter this server address in MSX Start Parameter."
            '</p><p><a href="/pair">Pair your TV</a></p></main></html>'
        )

    @app.get("/pair", response_class=HTMLResponse)
    async def pair_form(request: Request, activation: Annotated[str, Query(max_length=128)] = ""):
        limit(request, "form", 30)
        link = activation or request.cookies.get("pair_activation", "")
        if not link:
            return form()
        limit(request, "activation", 5)
        try:
            device = state.pending(activation=link)
        except PortalError as error:
            if activation:
                # Never render a recovery form on a no-referrer bearer URL:
                # Chromium would submit Origin:null and fail its next code check.
                return activation_redirect("invalid", 60)
            response = form(error.message, error.status)
        else:
            if activation:
                # Clean the credential form URL before rendering under same-origin policy.
                return activation_redirect(
                    device.activation, max(1, int(device.expires - state.clock()))
                )
            response = form(device=device)
        response.delete_cookie(
            "pair_activation",
            path="/pair",
            secure=not settings.allow_http,
            httponly=True,
            samesite="lax",
        )
        return response

    def activation_redirect(value, lifetime):
        response = RedirectResponse("/pair", status_code=303)
        response.set_cookie(
            "pair_activation",
            value,
            path="/pair",
            secure=not settings.allow_http,
            httponly=True,
            # Only the pending GET handoff is Lax; credential POST CSRF remains Strict.
            samesite="lax",
            max_age=lifetime,
        )
        return response

    @app.post("/pair", response_class=HTMLResponse)
    async def pair_submit(
        request: Request,
        csrf: Annotated[str, Form(max_length=128)],
        code: Annotated[str, Form(max_length=16)] = "",
        stage: Annotated[str, Form(max_length=128)] = "",
        username: Annotated[str, Form(max_length=128)] = "",
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
            if not stage:
                limit(request, "code", 5)
                pending = state.pending(code.replace(" ", "").replace("-", ""))
                return form(device=pending)
            limit(request, "login", 5)
            device = state.claim_stage(stage, csrf)
            if not username:
                raise PortalError(400, "Enter your Jellyfin username and retry.")
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
            response = HTMLResponse(
                '<!doctype html><html lang="en"><meta name="viewport" '
                'content="width=device-width,initial-scale=1">'
                "<title>TV paired · Jellyfin MSX</title>"
                '<link rel="stylesheet" href="/pair.css"><main>'
                '<p class="brand">Jellyfin MSX</p><p class="step">Pairing complete</p>'
                "<h1>TV paired</h1>"
                '<p role="status">Sign-in succeeded. Return to Media Station X and select '
                "<strong>Continue after pairing</strong>.</p>"
                "<p>You can close this page. No further login is needed here.</p></main></html>"
            )
            response.delete_cookie(
                "pair_csrf",
                path="/pair",
                secure=not settings.allow_http,
                httponly=True,
                samesite="strict",
            )
            return response
        except PortalError as error:
            if device:
                device.claiming = False
            return form(
                error.message
                if error.status in {400, 403, 429}
                else "Jellyfin sign-in failed. Check your credentials and server availability.",
                error.status,
                device=device
                if device and device.code and device.expires > state.clock()
                else None,
            )
        finally:
            if device:
                device.claiming = False

    @app.get("/pair.css")
    def css():
        return Response(PAIR_CSS, media_type="text/css")

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
        return activation_page(secret, device)

    def activation_page(secret, device, waiting=False):
        return pairing_page(
            "Waiting for pairing" if waiting else "Pair this TV",
            url("/pair").split("://", 1)[1],
            device.code,
            url(f"/msx/pair/image/{device.activation}.png"),
            "content:" + device_url(secret, "pairing.json"),
            "content:" + url("/msx/pair.json"),
            max(1, int(device.expires - state.clock() + 59) // 60),
        )

    @app.get("/msx/device/{secret}/pairing.json")
    async def pairing_status(secret: str):
        # Expired/unknown grants may receive only public recovery, never a library or code.
        try:
            device = state.get(secret, authenticated=False)
        except PortalError as error:
            if error.status != 401:
                raise
            return content(
                "Pairing or session expired",
                [button("Create new code", "content:" + url("/msx/pair.json"))],
            )
        if not device.token:
            return activation_page(secret, device, waiting=True)
        return await home(secret)

    @app.get("/msx/pair/image/{activation}.png")
    async def pairing_image(request: Request, activation: str):
        limit(request, "pair_image", 30)
        if len(activation) != 43 or not activation.isascii():
            raise PortalError(400, "Pairing QR is unavailable. Create a new code on the TV.")
        device = state.pending(activation=activation)
        return Response(
            activation_png(url("/pair", activation=device.activation)), media_type="image/png"
        )

    @app.get("/msx/device/{secret}/home.json")
    async def home(secret: str):
        device = state.get(secret, authenticated=False)
        if not device.token:
            return content(
                "Waiting for pairing",
                [
                    button(
                        "Continue after pairing",
                        "content:" + device_url(secret, "home.json"),
                    ),
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
        if not entries:
            entries.append(button("No items available", "info:This folder has no available items."))
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
            entries.append(
                button(
                    "Play original with watch progress (TV unverified)",
                    "content:request:interaction:init@"
                    + url("/lifecycle.html")
                    + f"#{secret}/{item_id}/{identifier(selected.get('Id'))}",
                )
            )
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
        if settings.enable_subtitle_resources and selected:
            entries.append(
                button(
                    "Subtitle playback (WebVTT)",
                    "content:request:interaction:init@"
                    + url("/subtitle-bridge.html")
                    + f"#{secret}/{item_id}/{identifier(selected.get('Id'))}",
                )
            )
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

    @app.get("/msx/device/{secret}/subtitle-playback.json")
    async def subtitle_player(secret: str, item_id: ItemId, media_source_id: ItemId):
        state.get(secret)
        identifier(item_id)
        identifier(media_source_id)
        original = "video:resolve:" + device_url(
            secret, "play.json", item_id=item_id, media_source_id=media_source_id
        )
        try:
            available = await subtitles.prepare(secret, item_id, media_source_id)
        except PortalError as error:
            state.get(secret)
            if error.status in {401, 403}:
                raise
            return content(
                "Subtitles unavailable",
                [
                    button("Why subtitles are unavailable", "info:" + text(error.message)),
                    button("Play without subtitles", original),
                    button("Back to details", "back"),
                ],
            )
        state.get(secret)
        return subtitle_playback(
            available,
            original,
        )

    @app.get("/subtitle-bridge.html")
    async def subtitle_bridge():
        return HTMLResponse(SUBTITLE_BRIDGE)

    @app.get("/lifecycle.html")
    async def lifecycle_bridge():
        return HTMLResponse(
            Path(__file__)
            .with_name("templates")
            .joinpath("lifecycle.html")
            .read_text(encoding="utf-8")
        )

    @app.get("/lifecycle.js")
    async def lifecycle_script():
        return Response(
            Path(__file__)
            .with_name("templates")
            .joinpath("lifecycle.js")
            .read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @app.get("/subtitle-bridge.js")
    async def subtitle_bridge_script():
        return Response(
            Path(__file__)
            .with_name("templates")
            .joinpath("subtitle-bridge.js")
            .read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

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

    @app.get("/api/device/{secret}/subtitles/{item_id}/{source_id}")
    async def subtitle_catalogue(secret: str, item_id: str, source_id: str):
        return await subtitles.request(secret, item_id, source_id)

    @app.get("/api/device/{secret}/subtitles/{item_id}/{source_id}/{index}.vtt")
    async def subtitle_resource(secret: str, item_id: str, source_id: str, index: int):
        raw = await subtitles.request(secret, item_id, source_id, index)
        return Response(raw, media_type="text/vtt")

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
