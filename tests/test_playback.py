import copy
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import TOKEN, media_source

from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.playback import authenticated_url, compatible


@pytest.mark.parametrize(
    "property,value",
    [
        ("Codec", "av1"),
        ("Codec", None),
        ("Width", None),
        ("Height", 0),
        ("Width", float("nan")),
        ("Width", True),
        ("Width", 10**400),
    ],
)
def test_unsupported_or_unknown_video_is_not_direct(property, value):
    source = media_source()
    source["MediaStreams"][0][property] = value
    assert not compatible(source, 4_000_000)


@pytest.mark.parametrize(
    "mutation", ["container", "audio", "channels", "bitrate", "remote", "headers", "opening"]
)
def test_other_incompatible_sources_are_not_direct(mutation):
    source = media_source()
    if mutation == "container":
        source["Container"] = "unknown"
    elif mutation == "audio":
        source["MediaStreams"][1]["Codec"] = "truehd"
    elif mutation == "channels":
        source["MediaStreams"][1]["Channels"] = None
    elif mutation == "bitrate":
        source["Bitrate"] = None
    elif mutation == "remote":
        source["IsRemote"] = True
    elif mutation == "headers":
        source["RequiredHttpHeaders"] = {"Authorization": "private"}
    else:
        source["RequiresOpening"] = True
    assert not compatible(source, 4_000_000)


def test_candidate_and_missing_streams():
    source = media_source()
    assert compatible(source, 4_000_000)
    for missing in ("Codec", "Width", "Height"):
        changed = copy.deepcopy(source)
        del changed["MediaStreams"][0][missing]
        assert not compatible(changed, 4_000_000)
    source["MediaStreams"] = []
    assert not compatible(source, 4_000_000)


@pytest.mark.parametrize(
    "path",
    [
        "/Videos/1/master.m3u8",
        "/jellyfin/Videos/1/master.m3u8",
        "Videos/1/master.m3u8",
        "https://jf.test/jellyfin/Videos/1/master.m3u8",
    ],
)
def test_playback_url_preserves_configured_base_path(path):
    result = authenticated_url("https://jf.test/jellyfin", path, TOKEN)
    assert urlsplit(result).path == "/jellyfin/Videos/1/master.m3u8"
    assert parse_qs(urlsplit(result).query)["ApiKey"] == [TOKEN]


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.test/x",
        "//evil.test/x",
        "http://jf.test/jellyfin/x",
        "https://jf.test/other/x",
        "/Videos/../admin",
        "/Videos/%2e%2e/admin",
        "https://user:pw@jf.test/jellyfin/x",
        "/Videos/x#fragment",
    ],
)
def test_playback_url_rejects_unsafe_destinations(path):
    with pytest.raises(PortalError):
        authenticated_url("https://jf.test/jellyfin", path, TOKEN)


def test_old_url_token_is_replaced():
    result = authenticated_url(
        "https://jf.test", "/Videos/x?api_key=old&ApiKey=stale&TOKEN=other&MediaSourceId=x", TOKEN
    )
    assert "old" not in result and "other" not in result and "stale" not in result
    assert parse_qs(urlsplit(result).query) == {"MediaSourceId": ["x"], "ApiKey": [TOKEN]}


@pytest.mark.parametrize(
    "url",
    [
        "http://jf.test",
        "https://user:pw@jf.test",
        "https://jf.test?token=private",
        "https://jf.test/#fragment",
        "https://jf.test/../x",
    ],
)
def test_invalid_server_configuration_is_rejected(url):
    with pytest.raises(ValueError):
        Settings("https://portal.test", url)


def test_plain_http_requires_explicit_development_flag():
    Settings("http://localhost:8090", "http://localhost:8096", allow_http=True)
