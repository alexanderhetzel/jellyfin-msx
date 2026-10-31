"""Desired resolver-time permission boundary; mocked transport only."""

import asyncio

import httpx
import pytest
from conftest import MOVIE

from jellyfin_msx.errors import PortalError
from jellyfin_msx.jellyfin import Jellyfin
from jellyfin_msx.playback import resolve


@pytest.mark.parametrize(
    "access,status",
    [
        ("None", 403),
        ("NavigationOnly", 502),
        ("absent", 502),
        (None, 502),
        (True, 502),
        (0, 502),
        ([], 502),
        ({}, 502),
        ("full", 502),
    ],
)
def test_denied_or_unknown_playback_access_prevents_negotiation(portal, access, status):
    requests = []

    def upstream(request):
        requests.append(request)
        response = portal.fake.handle(request)
        if request.url.path.endswith("/Items/" + MOVIE):
            data = response.json()
            if access == "absent":
                data.pop("PlayAccess", None)
            else:
                data["PlayAccess"] = access
            return httpx.Response(200, json=data)
        return response

    async def check():
        jf = Jellyfin(portal.settings, transport=httpx.MockTransport(upstream))
        try:
            with pytest.raises(PortalError) as denied:
                await resolve(jf, portal.device, MOVIE, False, -1)
            assert denied.value.status == status
        finally:
            await jf.client.aclose()

    asyncio.run(check())
    assert len(requests) == 1


def test_full_permission_retains_existing_original_delivery(portal):
    result = portal.client.get(portal.path + "/play.json", params={"item_id": MOVIE})
    assert result.json()["response"]["status"] == 200
    assert portal.device.diagnostics[-1]["mode"] == "DirectPlay"
    assert [r.method for r in portal.fake.requests] == ["GET", "POST"]
