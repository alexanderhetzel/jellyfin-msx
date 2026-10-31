"""Export public rendering fixtures, never private auth/capability responses.

This is a static renderer/player probe, not end-to-end application authentication.
All responses originate in normal synthetic pairing; every navigable URL is
rebuilt from an explicit public allowlist before any file is written.
"""

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from jellyfin_msx.msx import button
from tools.synthetic_check import action, pair
from tools.synthetic_lab import POSTER, build_synthetic_lab


def public_base(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or "/msx/device/" in parsed.path
        or any(part in {".", ".."} for part in parsed.path.split("/"))
    ):
        raise ValueError("Supply only a public credential-free HTTPS fixture directory")
    return value.rstrip("/")


def export_pages(base):
    base = public_base(base)
    origin = "https://localhost:18091"
    app, _, _ = build_synthetic_lab(Settings(origin, origin + "/jellyfin"))
    with TestClient(app, base_url=origin) as client:
        pairing = client.get("/msx/pair.json").json()
        waiting = client.get(
            action(pairing, "Continue after pairing")
            .removeprefix("content:")
            .replace("/pairing.json", "/home.json")
        ).json()
        # Keep the historical code-free home preview. The new pairing-status
        # screen includes private QR/code data and must never be exported.
        # Waiting UI comes from the real pending-session route. Never export the
        # pairing response, code, activation link or private reload/new-code URL.
        waiting["items"] = [
            button(row["title"], "info:Public waiting preview only. No TV is being paired.")
            for row in waiting["items"]
        ]
        home_action = pair(client, origin)
        home = client.get(home_action.removeprefix("content:")).json()
        browse = client.get(action(home, "Synthetic movies").removeprefix("content:")).json()
        detail = client.get(action(browse, "Synthetic clip").removeprefix("content:")).json()
        denied = client.get(action(browse, "Oversized candidate").removeprefix("content:")).json()
        play = action(detail, "Try original").removeprefix("video:resolve:")
        resolved = client.get(play).json()["response"]
        if resolved["status"] != 200:
            raise ValueError("Synthetic production negotiation failed")
        # Do not return or export the resolved bearer URL. Playback is replaced,
        # not proof of app dispatch/source delivery, as the public notice states.
        pages = {
            "index.json": home,
            "movies.json": browse,
            "detail.json": detail,
            "denied.json": denied,
            "waiting.json": waiting,
        }
        result = {}
        for name, original in pages.items():
            page = copy.deepcopy(original)
            page["headline"] = "PUBLIC FIXTURE / " + page["headline"]
            for row in page["items"]:
                target = row["action"]
                if "image" in row:
                    row["image"] = base + "/poster.png"
                if target.startswith("video:resolve:"):
                    row["action"] = "video:" + base + "/synthetic.mp4"
                    row["playerLabel"] = "Public synthetic clip / substituted fixture URL"
                elif target.startswith("content:"):
                    parsed = urlsplit(target.removeprefix("content:"))
                    endpoint = parsed.path.rsplit("/", 1)[-1]
                    if endpoint == "browse.json":
                        filename = "movies.json"
                    elif endpoint == "detail.json":
                        filename = (
                            "detail.json" if row["title"] == "Synthetic clip" else "denied.json"
                        )
                    elif endpoint == "home.json":
                        filename = "index.json"
                    else:
                        row["action"] = (
                            "info:Dynamic authentication and diagnostics "
                            "are not covered by this public fixture."
                        )
                        continue
                    row["action"] = "content:" + base + "/" + filename
                elif target != "back" and not target.startswith("info:"):
                    raise ValueError("Unexpected production action; refuse public export")
            page["items"].append(
                button(
                    "Public fixture scope",
                    "info:Rendering and player only. Normal hosted pairing, private delivery "
                    "and dynamic recovery remain untested.",
                )
            )
            result[name] = page
        result["index.json"]["items"].append(
            button(
                "Broken public media (expected failure)",
                "video:" + base + "/deliberately-missing.mp4",
            )
        )
        result["index.json"]["items"].append(
            button(
                "Waiting for pairing (public preview)",
                "content:data",
                data=copy.deepcopy(result["waiting.json"]),
            )
        )
        # Embed pages through the documented content:data action. Only the media
        # and poster require absolute URLs, pinned to a separate asset commit.
        # This avoids circular source-commit links or mutable branch references.
        for name in ("detail.json", "denied.json", "movies.json", "index.json"):
            for row in result[name]["items"]:
                if row["action"].startswith("content:" + base + "/"):
                    filename = row["action"].rsplit("/", 1)[-1]
                    if filename == "index.json":
                        row["action"] = "back"
                    else:
                        row["action"] = "content:data"
                        row["data"] = copy.deepcopy(result[filename])
        # Fail closed if any code, local origin, secret-bearing route or resolved
        # bearer URL survived. This is a guard, not arbitrary input sanitization.
        serialized = json.dumps(result)
        if any(
            marker in serialized
            for marker in (
                origin,
                "/msx/device/",
                "ApiKey",
                "MediaSourceId=",
                "TV code:",
                "csrf",
                "synthetic-password",
                "synthetic-viewer",
                resolved["data"]["url"],
            )
        ):
            raise ValueError("Refuse to export private synthetic response data")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Public HTTPS directory for these public fixtures only")
    parser.add_argument("--output", type=Path, default=Path("tests/fixtures/msx-public"))
    args = parser.parse_args()
    pages = export_pages(args.base_url)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, page in pages.items():
        (args.output / name).write_text(json.dumps(page, indent=2) + "\n", encoding="utf-8")
    (args.output / "poster.png").write_bytes(POSTER)
    print("Public fixture pages written. Launch index.json from its reviewed HTTPS revision.")


if __name__ == "__main__":
    main()
