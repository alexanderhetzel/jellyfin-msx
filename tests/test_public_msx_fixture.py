import json
from pathlib import Path

import httpx
import pytest

from tools.public_msx_fixture import export_pages, public_base
from tools.synthetic_lab import POSTER

BASE = "https://fixture.example.test/public-assets"


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_export_is_deterministic_public_and_has_no_network_fallback(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Public export attempted network access")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    pages = export_pages(BASE)
    assert pages == export_pages(BASE)
    encoded = json.dumps(pages)
    for forbidden in (
        "localhost",
        "/msx/device/",
        "ApiKey",
        "TV code:",
        "csrf",
        "synthetic-password",
        "synthetic-viewer",
        "video:resolve:",
    ):
        assert forbidden not in encoded
    rows = [row for row in walk(pages) if "action" in row]
    assert any(row["action"] == "video:" + BASE + "/synthetic.mp4" for row in rows)
    assert any(row["action"] == "video:" + BASE + "/deliberately-missing.mp4" for row in rows)
    for row in rows:
        assert row["action"] in {"back", "content:data"} or row["action"].startswith(
            ("info:", "video:" + BASE + "/")
        )
        if row["action"] == "content:data":
            assert row["data"]["headline"].startswith("PUBLIC FIXTURE / ")
        if "image" in row:
            assert row["image"] == BASE + "/poster.png"
    denied = pages["denied.json"]
    assert "1920x1080" in json.dumps(denied)
    assert not any(row.get("action", "").startswith("video:") for row in walk(denied))


@pytest.mark.parametrize(
    "value",
    [
        "http://example.test",
        "https://u:p@example.test",
        "https://example.test/?token=x",
        "https://example.test/#private",
        "https://example.test/../x",
        "https://example.test/msx/device/private",
    ],
)
def test_export_rejects_unsafe_bases(value):
    with pytest.raises(ValueError):
        public_base(value)


def test_committed_public_assets_have_explicit_provenance():
    directory = Path("tests/fixtures/msx-public")
    assert (directory / "poster.png").read_bytes() == POSTER
    # ISO BMFF header verifies this is encoded media, not the HTTP byte fixture.
    assert (directory / "synthetic.mp4").read_bytes()[4:8] == b"ftyp"
    assert "independently generated" in (directory / "README.md").read_text()


def test_committed_json_matches_current_production_derived_export():
    base = (
        "https://raw.githack.com/alexanderhetzel/jellyfin-msx/"
        "998bc0829b2df06db568443803a6fb4533e23f40/tests/fixtures/msx-public"
    )
    pages = export_pages(base)
    for name, page in pages.items():
        assert json.loads((Path("tests/fixtures/msx-public") / name).read_text()) == page
