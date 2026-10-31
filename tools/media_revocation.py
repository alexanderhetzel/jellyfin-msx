"""Strict original-media denial observer; no CLI, server runner or product policy."""

import asyncio
import json
import logging

import httpx


class RevocationFailure(Exception):
    """Fixed assertion failure; never includes a request target or response body."""


def require(condition, message):
    if not condition:
        raise RevocationFailure(message)


async def verify_revoked_original(url, original_prefix, *, transport=None):
    """Require denial on a fresh request without the fixture prefix in its body.

    The injectable transport supports mocked contract checks only. A successful
    mocked check says nothing about server or physical-player compatibility.
    """
    # Unlike the former runner, this helper does not rely on create_app to
    # suppress library logs of request targets. No credential-bearing URL output.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        async with (
            asyncio.timeout(12),
            httpx.AsyncClient(
                transport=transport, timeout=12, follow_redirects=False, trust_env=False
            ) as fresh,
        ):
            async with fresh.stream(
                "GET", url, headers={"Range": "bytes=0-1023", "Cache-Control": "no-cache"}
            ) as media:
                received = bytearray()
                async for chunk in media.aiter_bytes():
                    require(len(received) + len(chunk) <= 2048, "revoked range body exceeds bound")
                    received.extend(chunk)
                matches_original = original_prefix in received
                print(
                    json.dumps(
                        {
                            "logout_media_status": media.status_code,
                            "matches_original_prefix": matches_original,
                        }
                    ),
                    flush=True,
                )
                require(
                    media.status_code in (401, 403),
                    f"fresh logged-out media HTTP {media.status_code}",
                )
                require(not matches_original, "revoked denial body contains original media bytes")
    except (httpx.RequestError, httpx.InvalidURL, TimeoutError):
        raise RevocationFailure("revoked request transport failed; details withheld") from None
