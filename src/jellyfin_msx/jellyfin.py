import asyncio
import re

import httpx

from .config import Settings
from .errors import PortalError
from .state import Device

ID = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$")


def identifier(value) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise PortalError(502, "Jellyfin returned an invalid identifier.")
    return value


def normalize_contract(value, depth=0):
    """Treat nullable collections as empty; reject invalid upstream shapes."""
    if depth > 20:
        raise PortalError(502, "Jellyfin returned excessively nested metadata.")
    if isinstance(value, dict):
        for key in ("Items", "MediaSources", "MediaStreams"):
            if key in value:
                value[key] = value[key] if value[key] is not None else []
                if not isinstance(value[key], list) or any(
                    not isinstance(x, dict) for x in value[key]
                ):
                    raise PortalError(502, "Jellyfin returned invalid metadata collections.")
        for key in ("ImageTags", "User"):
            if key in value:
                value[key] = value[key] if value[key] is not None else {}
                if not isinstance(value[key], dict):
                    raise PortalError(502, "Jellyfin returned invalid metadata objects.")
        for child in value.values():
            normalize_contract(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            normalize_contract(child, depth + 1)
    return value


class Jellyfin:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.client = httpx.AsyncClient(
            transport=transport, timeout=10, follow_redirects=False, trust_env=False
        )

    def headers(self, device: Device):
        auth = (
            'MediaBrowser Client="Jellyfin MSX", Device="Media Station X", '
            f'DeviceId="{device.device_id}", Version="0.1.0"'
        )
        if device.token:
            auth += f', Token="{device.token}"'
        return {"Authorization": auth, "Accept": "application/json"}

    async def fetch(self, method: str, path: str, device: Device, **kwargs):
        try:
            async with asyncio.timeout(12):
                async with self.client.stream(
                    method,
                    self.settings.jellyfin_url + path,
                    headers=self.headers(device),
                    **kwargs,
                ) as response:
                    if response.status_code in (401, 403):
                        raise PortalError(
                            401, "Jellyfin denied access. Check permissions or pair again."
                        )
                    if response.status_code == 404:
                        raise PortalError(404, "Item or image is unavailable.")
                    if not 200 <= response.status_code < 300:
                        raise PortalError(502, "Jellyfin request failed. Check server diagnostics.")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 2_000_000:
                            raise PortalError(502, "Jellyfin response exceeds the size limit.")
                    return response, bytes(data)
        except (httpx.TimeoutException, TimeoutError) as from_error:
            raise PortalError(
                504, "Jellyfin is unreachable or timed out.", category="upstream_timeout"
            ) from from_error
        except httpx.NetworkError as from_error:
            raise PortalError(
                504, "Jellyfin is unreachable or timed out.", category="upstream_connectivity"
            ) from from_error
        except httpx.RequestError as from_error:
            raise PortalError(502, "Jellyfin request failed.") from from_error

    async def json(self, method: str, path: str, device: Device, **kwargs) -> dict:
        import json

        _, raw = await self.fetch(method, path, device, **kwargs)
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise PortalError(502, "Jellyfin returned malformed JSON.") from error
        if not isinstance(result, dict):
            raise PortalError(502, "Jellyfin returned an invalid object.")
        return normalize_contract(result)

    async def authenticate(self, device: Device, username: str, password: str):
        result = await self.json(
            "POST", "/Users/AuthenticateByName", device, json={"Username": username, "Pw": password}
        )
        user = identifier(result.get("User", {}).get("Id"))
        token = result.get("AccessToken")
        if not isinstance(token, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{16,512}", token):
            raise PortalError(502, "Jellyfin returned invalid authentication data.")
        return user, token

    async def item(self, device: Device, item_id: str):
        return await self.json("GET", f"/Users/{device.user_id}/Items/{item_id}", device)

    async def logout(self, device: Device):
        await self.fetch("POST", "/Sessions/Logout", device)
