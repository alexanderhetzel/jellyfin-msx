import re


def text(value, limit=500):
    """Strip MSX inline-expression delimiters from untrusted library strings."""
    return re.sub(r"[{}\[\]|<>\x00-\x1f]", " ", str(value or ""))[:limit]


def content(headline: str, items: list[dict], posters=False):
    return {
        "type": "pages" if posters else "list",
        "headline": text(headline),
        "cache": False,
        "reuse": False,
        "preload": "none",
        "template": (
            {"type": "separate", "layout": "0,0,3,5"}
            if posters
            else {
                "type": "default",
                "layout": "0,0,12,1",
                "centration": "title",
                "truncation": "title",
                "color": "msx-glass",
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
