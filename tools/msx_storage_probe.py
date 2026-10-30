"""Print an official-MS​​X launch URL for our synthetic-only interaction probe."""

import argparse
import base64
import json
from urllib.parse import quote, urlsplit


def launch_url(plugin_url: str) -> str:
    url = urlsplit(plugin_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Use a public HTTPS URL for the synthetic probe only")
    root = {
        "headline": "MSX storage probe launcher",
        "action": "[home|interaction:load:" + plugin_url + "]",
        "data": {"operation": "startup"},
        "template": {"type": "default", "layout": "0,0,12,1"},
        "items": [
            {
                "label": "Open probe without startup action",
                "action": "content:request:interaction:init@" + plugin_url,
            }
        ],
    }
    encoded = base64.b64encode(json.dumps(root).encode()).decode()
    return (
        "https://msx.benzac.de/?start="
        + quote("content:json:" + encoded, safe="")
        + "&input=2&init=1&suspend=0&animate=0"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_url", help="HTTPS location of msx_storage_probe.html")
    args = parser.parse_args()
    print(launch_url(args.plugin_url))


if __name__ == "__main__":
    main()
