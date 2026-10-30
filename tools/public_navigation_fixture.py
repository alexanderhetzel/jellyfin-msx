"""Export production-derived series pages via public synthetic request IDs only."""

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from tools.navigation_fixture import EPISODES, NavigationJellyfin
from tools.public_msx_fixture import public_base
from tools.synthetic_check import pair

ASSETS = (
    "https://raw.githack.com/alexanderhetzel/jellyfin-msx/"
    "998bc0829b2df06db568443803a6fb4533e23f40/tests/fixtures/msx-public"
)


def export_pages(assets=ASSETS):
    assets = public_base(assets)
    origin = "https://localhost:18091"
    fixture = NavigationJellyfin(origin)
    app = create_app(
        Settings(origin, origin + "/jellyfin"), transport=httpx.MockTransport(fixture.handle)
    )
    with TestClient(app, base_url=origin) as client:
        root = pair(client, origin).removeprefix("content:")
        targets = {root: "init"}
        queue = [root]
        pages = {}
        while queue:
            target = queue.pop(0)
            response = client.get(target)
            page = copy.deepcopy(response.json())
            if "headline" in page:
                page["headline"] = "PUBLIC NAVIGATION / " + page["headline"]
            for row in page.get("items", []):
                if "image" in row:
                    poster = client.get(row["image"])
                    if poster.status_code != 200:
                        raise ValueError("Synthetic poster failed")
                    row["image"] = assets + "/poster.png"
                action = row["action"]
                if action.startswith("content:"):
                    url = action.removeprefix("content:")
                    endpoint = urlsplit(url).path.rsplit("/", 1)[-1]
                    if endpoint in {"home.json", "browse.json", "detail.json"}:
                        if url not in targets:
                            targets[url] = f"page{len(targets)}"
                            queue.append(url)
                        row["action"] = "content:request:interaction:" + targets[url]
                    else:
                        row["action"] = (
                            "info:Public renderer only; private authentication "
                            "and diagnostics are not exercised."
                        )
                elif action.startswith("video:resolve:"):
                    resolver = action.removeprefix("video:resolve:")
                    item_id = parse_qs(urlsplit(resolver).query)["item_id"][0]
                    # Six boundary samples respect the real resolver rate budget.
                    # Every detail is fetched; this is not fifty playback passes.
                    if item_id in {EPISODES[i] for i in (0, 23, 24, 47, 48, 49)}:
                        result = client.get(resolver).json()["response"]
                        if result["status"] != 200:
                            raise ValueError("Synthetic episode negotiation failed")
                    row["action"] = "video:" + assets + "/synthetic.mp4"
                    row["playerLabel"] = "Public synthetic episode / substituted video"
                elif action != "back" and not action.startswith("info:"):
                    raise ValueError("Unexpected action; refuse export")
            pages[targets[target]] = page
        encoded = json.dumps(pages)
        if any(
            marker in encoded
            for marker in (
                origin,
                "/msx/device/",
                "ApiKey",
                "MediaSourceId=",
                "TV code:",
                "csrf",
                "synthetic-password",
                "synthetic-viewer",
                "video:resolve:",
            )
        ):
            raise ValueError("Private data survived export")
        return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("tests/fixtures/msx-navigation"))
    args = parser.parse_args()
    pages = export_pages()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "pages.json").write_text(json.dumps(pages, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(pages)} public pages; no browser verification inferred.")


if __name__ == "__main__":
    main()
