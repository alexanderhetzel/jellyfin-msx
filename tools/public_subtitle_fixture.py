"""Generate public-only subtitle research JSON; never supply private media URLs."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote

from tools.public_msx_fixture import public_base

MEDIA = (
    "https://raw.githack.com/alexanderhetzel/jellyfin-msx/"
    "d0c6fe2ab74f643756f9d7ea8119298b238d8f2f/tests/fixtures/msx-public/synthetic.mp4"
)
PLUGIN = "https://msx.benzac.de/plugins/html5x.html?url="


def fixture(base: str) -> dict:
    """Return a fixed synthetic matrix. No runtime/backend authentication occurs."""
    base = public_base(base)

    def item(title, media=MEDIA, tracks=None, preselect="de", plugin=True):
        properties = {
            "button:content:icon": "subtitles",
            "button:content:action": "panel:request:player:subtitle",
            "html5x:cors": "true",
            "html5x:subtitle": preselect,
            "control:timeout": "30",
        }
        for language, label, name in tracks or []:
            properties[f"html5x:subtitle:{language}:{label}"] = f"{base}/{name}"
        return {
            "title": title,
            "playerLabel": "PUBLIC SYNTHETIC / " + title,
            "action": "video:" + ("plugin:" + PLUGIN + quote(media, safe="") if plugin else media),
            "properties": properties,
        }

    return {
        "type": "list",
        "headline": "PUBLIC SYNTHETIC / subtitle research",
        "cache": False,
        "reuse": False,
        "preload": "none",
        "template": {
            "type": "default",
            "layout": "0,0,12,1",
            "color": "msx-glass",
        },
        "items": [
            item(
                "WebVTT DE and EN",
                tracks=[("de", "Deutsch", "de.vtt"), ("en", "English", "en.vtt")],
            ),
            item("Raw SRT negative", tracks=[("de", "Raw SRT", "de.srt")]),
            item("Raw ASS negative", tracks=[("de", "Raw ASS", "de.ass")]),
            item("Embedded mov_text native", media=base + "/embedded.mp4", plugin=False),
            item("Embedded mov_text HTML5X", media=base + "/embedded.mp4"),
            item("Missing WebVTT negative", tracks=[("de", "Missing", "missing.vtt")]),
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_asset_base", help="Known public synthetic HTTPS asset directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(fixture(args.public_asset_base), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
