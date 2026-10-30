import json
from pathlib import Path
from urllib.parse import unquote

from tools.public_subtitle_fixture import MEDIA, PLUGIN, fixture


def test_public_subtitle_matrix_uses_official_plugin_without_online_proxy():
    base = "https://fixture.example.test/public-subtitles"
    page = fixture(base)
    assert page["headline"].startswith("PUBLIC SYNTHETIC")
    assert len(page["items"]) == 6
    for item in page["items"]:
        assert item["properties"]["html5x:cors"] == "true"
        action = unquote(item["action"])
        assert action.startswith(("video:plugin:" + PLUGIN, "video:" + base))
        assert action.endswith((MEDIA, base + "/embedded.mp4"))
    text = json.dumps(page)
    for forbidden in ("ApiKey", "/msx/device/", "csrf", "video:resolve:", "password"):
        assert forbidden not in text


def test_subtitle_cues_are_utf8_and_embedded_fixture_has_expected_hash():
    import hashlib

    directory = Path("tests/fixtures/msx-subtitles")
    for filename in ("de.vtt", "de.srt", "de.ass"):
        text = (directory / filename).read_text(encoding="utf-8")
        assert "Grüße, ÄÖÜ äöü ß" in text
        assert "Rückwärts suchen" in text
    assert (directory / "en.vtt").read_text().startswith("WEBVTT")
    assert not (directory / "missing.vtt").exists()
    assert hashlib.sha256((directory / "embedded.mp4").read_bytes()).hexdigest() == (
        "5d01d1499ad049ea72cc2ef98a068a2059442a91aed7a27646f6bf8bee76b5ca"
    )
