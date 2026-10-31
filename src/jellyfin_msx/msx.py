import re

from .presentation import ACCENT, PRODUCT, SURFACE


def text(value, limit=500):
    """Strip MSX inline-expression delimiters from untrusted library strings."""
    return re.sub(r"[{}\[\]|<>\x00-\x1f]", " ", str(value or ""))[:limit]


def content(headline: str, items: list[dict], posters=False):
    return {
        "type": "pages" if posters else "list",
        "headline": text(headline),
        "extension": f"{{txt:{ACCENT}:{PRODUCT}}}",
        "cache": False,
        "reuse": False,
        "preload": "none",
        "template": (
            {"type": "separate", "layout": "0,0,3,5", "color": SURFACE}
            if posters
            else {
                "type": "default",
                "layout": "0,0,12,1",
                "centration": "title",
                "truncation": "title",
                "color": SURFACE,
            }
        ),
        "items": items or [{"title": "No items available", "action": "back"}],
    }


def wrapped(data=None, status=200, message=None):
    return {
        "response": {
            "status": status,
            "text": "OK" if status == 200 else "Error",
            "message": message,
            "data": data,
        }
    }


def button(title: str, action: str, **kwargs):
    return {"title": text(title), "action": action, **kwargs}


def subtitle_playback(available, resource, original):
    """Public HTML5X properties; unique keys retain duplicate-language indices."""
    names = {"deu": "Deutsch", "ger": "Deutsch", "eng": "English"}
    properties = {
        "button:content:icon": "subtitles",
        "button:content:action": "panel:request:player:subtitle",
        "html5x:cors": "true",
        "html5x:subtitle": "default",
    }
    for track in available:
        index, language = track["index"], track["language"]
        label = f"{names.get(language, language)} (track {index})"
        properties[f"html5x:subtitle:{language}-x-{index}:{label}"] = resource(index)
    return content(
        "Subtitles",
        [
            button(
                "Play with subtitle controls (Off initially)",
                "video:plugin:https://msx.benzac.de/plugins/html5x.html?id=portal-video",
                playerLabel="Subtitles: use the subtitle button to choose a track or Off",
                properties=properties,
            ),
            button("Play without subtitles", original),
            button(
                "Subtitle help",
                "info:Use the subtitle button during playback for language or Off. "
                "Selection keeps the playback position. If a track stops loading, "
                "select Off or Stop and reopen details. Only external plain WebVTT is supported; "
                "SRT/ASS, embedded and image subtitles need a compatible stored sidecar. "
                "No conversion or burn-in is requested. Up to eight tracks are offered.",
            ),
            button("Back to details", "back"),
        ],
    )


def pairing_page(headline, companion, code, image, proceed, retry, minutes):
    """Native activation layout; only the two recovery/proceed controls take focus."""
    page = content(headline, [])
    page["type"] = "pages"
    del page["template"]
    del page["items"]
    page["pages"] = [
        {
            "items": [
                {"type": "space", "layout": "5,1,7,1", "title": text(companion), "color": SURFACE},
                {
                    "type": "space",
                    "layout": "5,2,7,2",
                    "titleHeader": "TV code:",
                    "title": text(f"{code[:4]} {code[4:]}"),
                    "titleFooter": f"Valid {minutes} minutes",
                    "color": SURFACE,
                },
                button(
                    "Continue after pairing", proceed, layout="0,5,8,1", color=SURFACE, focus=True
                ),
                button("Create new code", retry, layout="8,5,4,1", color=SURFACE),
                {
                    "type": "space",
                    "layout": "0,4,4,1",
                    "title": "Scan only from your own TV",
                    "color": SURFACE,
                },
                {
                    "type": "space",
                    "layout": "0,0,4,4",
                    "image": image,
                    "imageFiller": "fit",
                    "imageOverlay": 0,
                    "color": "white",
                },
                {
                    "type": "space",
                    "layout": "5,0,7,1",
                    "title": "or open on your phone / PC",
                    "color": SURFACE,
                },
                {
                    "type": "space",
                    "layout": "5,4,7,1",
                    "title": "Enter the code, then sign in to Jellyfin.",
                    "color": SURFACE,
                },
            ]
        }
    ]
    return page
