"""Mocked private delivery evidence; this is not an MSX playback test."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from conftest import MOVIE, SOURCE, TOKEN
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.errors import PortalError
from jellyfin_msx.subtitles import CUE_LAYOUT, MAX_BYTES, plain_vtt

VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nGrüße, ÄÖÜ äöü ß\nSecond line\n".encode()


@pytest.fixture
def subtitle_portal(portal):
    portal.fake.source["MediaStreams"][2] = {
        "Type": "Subtitle",
        "Index": 7,
        "Codec": "webvtt",
        "Language": "deu",
        "IsExternal": True,
        "IsTextSubtitleStream": True,
        "Path": "/media/subtitle.vtt",
        "DeliveryUrl": "https://untrusted.test/never-fetch?ApiKey=synthetic-marker",
    }
    portal.subtitle_response = lambda: httpx.Response(
        200, content=VTT, headers={"Content-Type": "text/vtt"}
    )
    portal.subtitle_requests = []
    portal.before_resource = lambda: None

    async def handle(request):
        if "/Subtitles/" in request.url.path:
            portal.subtitle_requests.append(request)
            portal.before_resource()
            return portal.subtitle_response()
        return portal.fake.handle(request)

    settings = replace(portal.settings, enable_subtitle_resources=True, allow_transcoding=False)
    app = create_app(settings, transport=httpx.MockTransport(handle), state=portal.state)
    with TestClient(app, base_url=settings.public_url) as client:
        portal.subtitle_client = client
        portal.subtitle_path = f"/api/device/{portal.secret}/subtitles/{MOVIE}/{SOURCE}"
        yield portal


def test_off_default_and_configuration(portal, monkeypatch):
    response = portal.client.get(f"/api/device/{portal.secret}/subtitles/{MOVIE}/{SOURCE}")
    assert response.status_code == 409
    assert not portal.fake.requests
    with pytest.raises(ValueError, match="HTTPS"):
        replace(
            portal.settings,
            public_url="http://portal.test",
            allow_http=True,
            enable_subtitle_resources=True,
        )
    monkeypatch.setenv("MSX_PUBLIC_URL", "https://portal.test")
    monkeypatch.setenv("JELLYFIN_URL", "https://jellyfin.test")
    monkeypatch.setenv("MSX_ENABLE_SUBTITLE_RESOURCES", "true")
    assert portal.settings.from_env().enable_subtitle_resources


def test_catalogue_absolute_indices_duplicate_language_and_delivery(subtitle_portal, caplog):
    p = subtitle_portal
    second = p.fake.source["MediaStreams"][2] | {"Index": 12}
    p.fake.source["MediaStreams"].insert(0, second)
    catalogue = p.subtitle_client.get(p.subtitle_path)
    assert catalogue.json()["tracks"] == [
        {"index": 12, "language": "deu"},
        {"index": 7, "language": "deu"},
    ]
    assert catalogue.json()["default"] == "off"
    response = p.subtitle_client.get(
        p.subtitle_path + "/7.vtt", headers={"Origin": "https://msx.benzac.de"}
    )
    assert response.status_code == 200 and response.content == plain_vtt(VTT, position=True)
    assert response.headers["content-type"] == "text/vtt; charset=utf-8"
    assert response.headers["access-control-allow-origin"] == "https://msx.benzac.de"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in response.headers["cache-control"]
    request = p.subtitle_requests[0]
    assert request.url.path == f"/jellyfin/Videos/{MOVIE}/{SOURCE}/Subtitles/7/Stream.vtt"
    assert dict(request.url.params) == {
        "CopyTimestamps": "true",
        "StartPositionTicks": "0",
        "AddVttTimeMap": "false",
    }
    assert request.url.host == "jellyfin.test" and TOKEN not in str(request.url)
    assert f'Token="{TOKEN}"' in request.headers["authorization"]
    assert request.headers["accept-encoding"] == "identity"
    for marker in (TOKEN, "untrusted.test", "synthetic-marker", "/media/"):
        assert marker not in response.text + catalogue.text + caplog.text


@pytest.mark.parametrize(
    "change",
    [
        {"Index": True},
        {"Index": -1},
        {"Index": None},
        {"Type": "Audio"},
        {"Codec": "srt"},
        {"Codec": "ass"},
        {"Codec": "pgssub"},
        {"Codec": []},
        {"IsExternal": False},
        {"IsExternal": None},
        {"IsTextSubtitleStream": False},
        {"Path": None},
        {"Path": "/media/subtitle.mks"},
        {"Path": "/media/subtitle.srt"},
        {"Path": "https://untrusted.test/a.vtt"},
        {"Path": "//host/a.vtt"},
        {"Path": "C:\\media\\a.vtt"},
    ],
)
def test_unsupported_never_fetches(subtitle_portal, change):
    p = subtitle_portal
    p.fake.source["MediaStreams"][2].update(change)
    catalogue = p.subtitle_client.get(p.subtitle_path)
    assert catalogue.status_code == 409 or catalogue.json()["tracks"] == []
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == 409
    assert "no conversion" in response.text or "no longer eligible" in response.text
    assert not p.subtitle_requests


@pytest.mark.parametrize(
    "change", ["duplicate-index", "wrong-source", "hd", "denied", "expired", "logout", "unpaired"]
)
def test_authorization_source_and_index_isolation(subtitle_portal, change):
    p = subtitle_portal
    if change == "duplicate-index":
        p.fake.source["MediaStreams"].append(p.fake.source["MediaStreams"][2].copy())
    elif change == "wrong-source":
        p.fake.source["Id"] = "f" * 32
    elif change == "hd":
        p.fake.source["MediaStreams"][0]["Width"] = 3840
    elif change == "denied":
        p.fake.deny_item = True
    elif change == "expired":
        p.now[0] = p.device.expires + 1
    elif change == "logout":
        p.state.remove(p.secret)
    else:
        p.device.token = None
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code in {401, 409}
    assert not p.subtitle_requests
    assert TOKEN not in response.text


@pytest.mark.parametrize("suffix", ["/0.vtt", "/-1.vtt", "/true.vtt", "/10001.vtt"])
def test_never_interprets_ordinal_as_absolute_index(subtitle_portal, suffix):
    p = subtitle_portal
    assert p.subtitle_client.get(p.subtitle_path + suffix).status_code in {400, 409}
    assert not p.subtitle_requests


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 401, 403, 404, 500, 206])
def test_upstream_failures_no_redirect_or_body_leak(subtitle_portal, status, caplog):
    p = subtitle_portal
    p.subtitle_response = lambda: httpx.Response(
        status, text=TOKEN, headers={"Location": "https://untrusted.test/" + TOKEN}
    )
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == (status if status in {401, 403, 404} else 502)
    assert len(p.subtitle_requests) == 1
    assert "location" not in response.headers
    assert TOKEN not in response.text + caplog.text


@pytest.mark.parametrize(
    "content,headers",
    [
        (b"<html>not vtt</html>", {"Content-Type": "text/html"}),
        (VTT, {"Content-Type": "text/vtt", "Content-Encoding": "br"}),
        (b"x" * (MAX_BYTES + 1), {"Content-Type": "text/vtt"}),
        (b"WEBVTT\n\n" + TOKEN.encode(), {"Content-Type": "text/vtt"}),
    ],
)
def test_hostile_responses(subtitle_portal, content, headers):
    p = subtitle_portal
    p.subtitle_response = lambda: httpx.Response(200, content=content, headers=headers)
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == 502 and TOKEN not in response.text


def test_revoke_during_request_withholds_buffer(subtitle_portal):
    p = subtitle_portal
    p.before_resource = lambda: p.state.remove(p.secret)
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == 401 and "Grüße" not in response.text


@pytest.mark.parametrize(
    "origin", ["https://untrusted.test", "null", "https://msx.benzac.de.untrusted.test"]
)
def test_cors_never_wildcard_even_errors_and_preflight(subtitle_portal, origin):
    p = subtitle_portal
    for response in (
        p.subtitle_client.get(p.subtitle_path + "/7.vtt", headers={"Origin": origin}),
        p.subtitle_client.options(
            p.subtitle_path + "/7.vtt",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        ),
        p.subtitle_client.get(
            p.subtitle_path.replace(p.secret, "unknown"), headers={"Origin": origin}
        ),
    ):
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "raw",
    [
        b"WEBVTT\nX-TIMESTAMP-MAP=MPEGTS:900000\n",
        b"WEBVTT\n\nSTYLE\n::cue { color:red }",
        b"WEBVTT\n\nREGION\nid:region",
        b"WEBVTT\n\nNOTE comment",
        VTT.replace(b"Gr", b"<b>Gr"),
        VTT.replace(b"Gr", b"\xffGr"),
        VTT.replace(b"00:00:04.000", b"00:00:00.000"),
        VTT.replace(b"00:00:04.000", b"25:00:00.000"),
        VTT.replace(b" --> ", b" -->  line:0 "),
        VTT + VTT.split(b"\n\n")[1],
        VTT.replace(b"Second line", b"x" * 1025),
        VTT.replace(b"Second line", b"a\x00b"),
        "WEBVTT\n\n٠٠:0٠:0١.٠٠٠ --> ٠٠:0٠:0٤.٠٠٠\nhello\n".encode(),
        VTT.replace(b"Gr", b"00:00:02.000 --> 00:00:03.000\nGr"),
    ],
)
def test_plain_subset_rejects_unsupported_layout_encoding_and_timing(raw):
    with pytest.raises(PortalError):
        plain_vtt(raw)


def test_plain_subset_preserves_cue_times_and_unicode():
    assert plain_vtt(b"\xef\xbb\xbf" + VTT.replace(b"\n", b"\r\n")) == VTT
    assert plain_vtt(VTT.replace(b"\n\n", b"\n\nidentifier\n")) == VTT
    positioned = plain_vtt(VTT, position=True)
    assert positioned == VTT.replace(
        b"00:00:04.000\n", b"00:00:04.000 " + CUE_LAYOUT.encode() + b"\n"
    )
    with pytest.raises(PortalError):
        plain_vtt(positioned, position=True)  # Upstream settings remain outside admission.


def test_rate_budget_and_unknown_capability_do_not_fetch(subtitle_portal):
    p = subtitle_portal
    response = p.subtitle_client.get(p.subtitle_path.replace(p.secret, "unknown") + "/7.vtt")
    assert response.status_code == 401 and not p.fake.requests
    for _ in range(30):
        assert p.subtitle_client.get(p.subtitle_path).status_code == 200
    assert p.subtitle_client.get(p.subtitle_path + "/7.vtt").status_code == 429
    assert not p.subtitle_requests


def test_allowed_origin_preflight_and_no_origin_response(subtitle_portal):
    p = subtitle_portal
    response = p.subtitle_client.options(
        p.subtitle_path + "/7.vtt",
        headers={"Origin": "https://msx.benzac.de", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://msx.benzac.de"
    assert "access-control-allow-credentials" not in response.headers
    assert "access-control-allow-origin" not in p.subtitle_client.get(p.subtitle_path).headers


def test_chunked_fetch_is_bounded_and_transport_failure_is_sanitized(subtitle_portal):
    p = subtitle_portal

    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * MAX_BYTES
            yield b"x"
            raise AssertionError("Must stop reading at the bound")

    p.subtitle_response = lambda: httpx.Response(
        200, stream=Chunks(), headers={"Content-Type": "text/vtt"}
    )
    assert p.subtitle_client.get(p.subtitle_path + "/7.vtt").status_code == 502

    def failure():
        raise httpx.ReadTimeout("synthetic-private-detail")

    p.subtitle_response = failure
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == 504 and "synthetic-private-detail" not in response.text


def test_parser_cue_count_and_size_bounds():
    with pytest.raises(PortalError):
        plain_vtt(b"x" * (MAX_BYTES + 1))
    with pytest.raises(PortalError, match="cue count"):
        plain_vtt(b"WEBVTT\n\n" + b"x\n\n" * 10001)

    def timestamp(seconds):
        return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}.000"

    raw = (
        "WEBVTT\n\n"
        + "\n\n".join(f"{timestamp(i)} --> {timestamp(i + 1)}\n" + "x" * 32 for i in range(9000))
        + "\n"
    ).encode()
    assert len(raw) < MAX_BYTES and len(plain_vtt(raw)) <= MAX_BYTES
    with pytest.raises(PortalError, match="size limit"):
        plain_vtt(raw, position=True)


def test_simple_cue_boundary_preserves_text_and_timestamps():
    raw = (
        "WEBVTT\n\n00:00:00.000 --> 00:00:08.000\n"
        + "W" * 32
        + "\n"
        + "漢" * 16
        + "\n\n00:00:08.000 --> 00:00:16.000\nGrüße, ÄÖÜ äöü ß\nSecond line\n"
    ).encode()
    assert plain_vtt(raw) == raw
    assert plain_vtt(raw, position=True).replace((" " + CUE_LAYOUT).encode(), b"") == raw


@pytest.mark.parametrize(
    "cue",
    ["W" * 33, "漢" * 17, "First\nSecond\nThird", "e\u0301", "a\u200db", "a\u2028b", "a\u0085b"],
)
def test_unsupported_layout_rejects_the_whole_track_and_explains_recovery(subtitle_portal, cue):
    p = subtitle_portal
    raw = VTT + ("\n00:00:10.000 --> 00:00:12.000\n" + cue + "\n").encode()
    with pytest.raises(PortalError, match="Subtitle layout is unsupported"):
        plain_vtt(raw)
    p.subtitle_response = lambda: httpx.Response(
        200, content=raw, headers={"Content-Type": "text/vtt"}
    )
    response = p.subtitle_client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == 502 and cue not in response.text
    page = p.subtitle_client.get(
        p.path + "/subtitle-playback.json", params={"item_id": MOVIE, "media_source_id": SOURCE}
    ).json()
    assert page["headline"] == "Subtitles unavailable"
    assert "at most two short lines" in json.dumps(page)
    assert any(i["title"] == "Play without subtitles" for i in page["items"])


@pytest.mark.parametrize(
    "mutation", ["list-type", "dict-type", "duplicate-source", "wrong-item", "revoke"]
)
def test_malformed_or_revoked_metadata_fails_closed(subtitle_portal, mutation):
    p = subtitle_portal

    def handle(request):
        response = p.fake.handle(request)
        data = response.json()
        if mutation == "list-type":
            data["Type"] = []
        elif mutation == "dict-type":
            data["Type"] = {}
        elif mutation == "duplicate-source":
            data["MediaSources"] *= 2
        elif mutation == "wrong-item":
            data["Id"] = "f" * 32
        else:
            p.state.remove(p.secret)
        return httpx.Response(200, json=data)

    app = create_app(
        replace(p.settings, enable_subtitle_resources=True),
        transport=httpx.MockTransport(handle),
        state=p.state,
    )
    with TestClient(app, base_url=p.settings.public_url) as client:
        response = client.get(p.subtitle_path + "/7.vtt")
    assert response.status_code == (401 if mutation == "revoke" else 409)
    assert len(p.fake.requests) == 1
    assert TOKEN not in response.text


def test_deadline_and_concurrency_bound(subtitle_portal, monkeypatch):
    from jellyfin_msx import subtitles
    from jellyfin_msx.jellyfin import Jellyfin

    p = subtitle_portal

    async def run():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def slow(request):
            entered.set()
            await release.wait()
            return p.fake.handle(request)

        jellyfin = Jellyfin(
            replace(p.settings, enable_subtitle_resources=True), httpx.MockTransport(slow)
        )
        service = subtitles.SubtitleResources(jellyfin, p.state)
        pending = [asyncio.create_task(service.request(p.secret, MOVIE, SOURCE)) for _ in range(4)]
        await entered.wait()
        with pytest.raises(PortalError) as busy:
            await service.request(p.secret, MOVIE, SOURCE)
        assert busy.value.status == 429
        release.set()
        await asyncio.gather(*pending)
        assert service.active == 0
        release.clear()
        monkeypatch.setattr(subtitles, "DEADLINE", 0.01)
        with pytest.raises(PortalError) as timeout:
            await service.request(p.secret, MOVIE, SOURCE)
        assert timeout.value.status == 504 and service.active == 0
        await jellyfin.client.aclose()

    asyncio.run(run())


def test_subtitle_menu_uses_private_source_pinned_bridge_and_unique_labels(subtitle_portal):
    p = subtitle_portal
    p.fake.source["MediaStreams"].append(p.fake.source["MediaStreams"][2] | {"Index": 12})
    detail = p.subtitle_client.get(p.path + "/detail.json", params={"item_id": MOVIE}).json()
    target = next(
        i["action"] for i in detail["items"] if i["title"].startswith("Subtitle playback")
    )
    assert target.startswith(
        "content:request:interaction:init@https://portal.test/subtitle-bridge.html#"
    )
    assert target.endswith(f"/{MOVIE}/{SOURCE}") and TOKEN not in target
    page = p.subtitle_client.get(
        p.path + "/subtitle-playback.json", params={"item_id": MOVIE, "media_source_id": SOURCE}
    ).json()
    playback = page["items"][0]
    assert (
        playback["action"]
        == "video:plugin:https://msx.benzac.de/plugins/html5x.html?id=portal-video"
    )
    assert TOKEN not in json.dumps(page) and "ApiKey" not in json.dumps(page)
    props = playback["properties"]
    assert props["html5x:subtitle"] == "default" and props["html5x:cors"] == "true"
    assert props["trigger:complete"] == "player:stop"
    assert props["button:next:enable"] == props["button:prev:enable"] == "false"
    assert props["html5x:subtitle:deu-x-7:Deutsch (track 7)"] == "portal-subtitle-7"
    assert props["html5x:subtitle:deu-x-12:Deutsch (track 12)"] == "portal-subtitle-12"
    assert "/api/device/" not in json.dumps(page)
    assert len(p.subtitle_requests) == 2
    assert not any(r.url.path.endswith("PlaybackInfo") for r in p.fake.requests)


@pytest.mark.parametrize("status,content", [(404, VTT), (200, b"bad VTT")])
def test_bad_subtitle_preparation_offers_clear_original_recovery(subtitle_portal, status, content):
    p = subtitle_portal
    p.subtitle_response = lambda: httpx.Response(
        status, content=content, headers={"Content-Type": "text/vtt"}
    )
    page = p.subtitle_client.get(
        p.path + "/subtitle-playback.json", params={"item_id": MOVIE, "media_source_id": SOURCE}
    ).json()
    assert page["headline"] == "Subtitles unavailable"
    assert page["items"][1]["title"] == "Play without subtitles"
    assert page["items"][1]["action"].startswith("video:resolve:")
    assert not any(i["action"].startswith("video:plugin:") for i in page["items"])
    assert TOKEN not in json.dumps(page)


def test_bridge_public_code_is_secret_free_and_only_html_frame_policy_changes(portal):
    html = portal.client.get("/subtitle-bridge.html")
    js = portal.client.get("/subtitle-bridge.js")
    assert html.status_code == js.status_code == 200
    assert "https://msx.benzac.de/js/tvx-plugin.min.js" in html.text
    assert "script-src 'self' https://msx.benzac.de" in html.headers["content-security-policy"]
    assert (
        "frame-ancestors https://msx.benzac.de https://www.msx.benzac.de"
        in html.headers["content-security-policy"]
    )
    assert "connect-src 'self'" in html.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in portal.client.get("/pair").headers["content-security-policy"]
    assert "application/javascript" in js.headers["content-type"]
    assert "no-store" in js.headers["cache-control"]
    assert "no-referrer" == html.headers["referrer-policy"]
    assert TOKEN not in html.text + js.text and portal.secret not in html.text + js.text


def test_subtitle_ui_absent_by_default_and_private_preparation_denied(portal):
    detail = portal.client.get(portal.path + "/detail.json", params={"item_id": MOVIE}).json()
    assert not any(i["title"].startswith("Subtitle playback") for i in detail["items"])
    response = portal.client.get(
        "/msx/device/unknown/subtitle-playback.json",
        params={"item_id": MOVIE, "media_source_id": SOURCE},
    )
    assert response.json()["response"]["status"] == 401
