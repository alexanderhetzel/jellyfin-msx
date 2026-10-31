"""Deterministic in-process HTTP contract smoke. This does not run a browser."""

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools.synthetic_lab import PASSWORD, POSTER, USERNAME, build_synthetic_lab


class ContractFailure(Exception):
    pass


def require(condition, stage):
    if not condition:
        raise ContractFailure(stage)


def action(page, title):
    rows = page.get("items", []) + [
        item for child in page.get("pages", []) for item in child.get("items", [])
    ]
    matches = [
        row["action"] for row in rows if "action" in row and row.get("title", "").startswith(title)
    ]
    require(len(matches) == 1, "render-contract")
    return matches[0]


def content(client, target):
    require(target.startswith("content:"), "content-action")
    return client.get(target.removeprefix("content:")).json()


def pair(client, origin, fault=None):
    page = client.get("/msx/pair.json").json()
    code = re.search(r"TV code: ([A-Z0-9 ]+) \(valid", page["pages"][0]["items"][1]["title"])
    require(code is not None, "pairing-contract")
    home_action = action(page, "Continue after pairing")
    require(content(client, home_action).get("headline") == "Waiting for pairing", "pending")
    form = client.get("/pair")
    csrf = re.search(r'name="csrf" value="([^"]+)"', form.text).group(1)
    fields = {"code": code[1], "username": USERNAME, "password": PASSWORD, "csrf": csrf}
    # A real denial must happen before authentication and still permit a fresh retry.
    denied = client.post("/pair", data={**fields, "csrf": "wrong"}, headers={"Origin": origin})
    require(denied.status_code == 403, "csrf-denial")
    form = client.get("/pair")
    fields["csrf"] = re.search(r'name="csrf" value="([^"]+)"', form.text).group(1)
    if fault == "csrf":
        fields["csrf"] = "deliberately-broken"
    result = client.post("/pair", data=fields, headers={"Origin": origin})
    require(result.status_code == 200 and 'name="stage"' in result.text, "pairing")
    stage_fields = dict(
        re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', result.text)
    )
    result = client.post(
        "/pair",
        data={**stage_fields, "username": USERNAME, "password": PASSWORD},
        headers={"Origin": origin},
    )
    require(result.status_code == 200 and "Sign-in succeeded" in result.text, "pairing")
    return home_action


def check(fault=None):
    origin = "https://localhost:18091"
    settings = Settings(origin, origin + "/jellyfin")
    with TemporaryDirectory() as directory:
        # Byte/range delivery contract ONLY: these bytes are deliberately not video.
        media = Path(directory) / "contract-bytes.mp4"
        media.write_bytes(b"synthetic-byte-delivery-contract")
        app, _, fixture = build_synthetic_lab(settings, media=media, fault=fault)
        with TestClient(app, base_url=origin) as client:
            home_action = pair(client, origin, fault)
            home = content(client, home_action)
            require(home.get("headline") == "Jellyfin libraries", "libraries-json")
            browse = content(client, action(home, "Synthetic movies"))
            movie = next(row for row in browse["items"] if row["title"] == "Synthetic clip")
            poster = client.get(movie["image"])
            require(poster.status_code == 200 and poster.content == POSTER, "poster")
            detail = content(client, movie["action"])
            play_action = action(detail, "Try original")
            require(play_action.startswith("video:resolve:"), "play-action")
            resolved = client.get(play_action.removeprefix("video:resolve:")).json()["response"]
            require(resolved["status"] == 200, "playback")
            media_url = resolved["data"]["url"]
            partial = client.get(media_url, headers={"Range": "bytes=0-8"})
            require(partial.status_code == 206 and partial.content == b"synthetic", "media-range")
            require(client.get(media_url.split("?", 1)[0]).status_code == 401, "media-auth")
            before = client.get("/__lab/report").json()["jellyfin_requests"]["playback_info"]
            oversized = content(client, action(browse, "Oversized candidate"))
            require(
                not any(r["action"].startswith("video:") for r in oversized["items"]), "hd-denial"
            )
            report = client.get("/__lab/report").json()
            require(report["jellyfin_requests"]["playback_info"] == before, "hd-no-negotiation")
            require(
                report["negotiations"]
                == [
                    {
                        "EnableDirectPlay": True,
                        "EnableDirectStream": False,
                        "EnableTranscoding": False,
                        "SubtitleStreamIndex": -1,
                    }
                ],
                "conversion-policy",
            )
            confirm = content(client, action(home, "Disconnect TV"))
            content(client, action(confirm, "Confirm disconnect"))
            revoked = client.get(home_action.removeprefix("content:")).json()
            require(revoked["response"]["status"] == 401, "revoked-private")
            require(client.get(movie["image"]).status_code == 401, "revoked-poster")
            require(
                client.get(media_url).status_code == 401 and not fixture.tokens, "revoked-media"
            )
            recovered = pair(client, origin)
            require(content(client, recovered).get("headline") == "Jellyfin libraries", "recovery")
            report = client.get("/__lab/report").json()
            # Return only the allowlisted aggregate report; no actions, codes or URLs.
            return {
                "result": "passed",
                "category": "in-process-http-contract",
                "browser_verified": False,
                "physical_device_verified": False,
                "portal_requests": report["portal_requests"],
                "jellyfin_requests": report["jellyfin_requests"],
                "negotiations": report["negotiations"],
                "media_requests": dict(fixture.media_requests),
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault", choices=["json", "playback", "csrf"])
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.fault), indent=2))
    except ContractFailure as error:
        print(
            json.dumps(
                {"result": "failed", "stage": str(error), "category": "in-process-http-contract"}
            )
        )
        raise SystemExit(1) from None
    except Exception:
        # HTTP exceptions can contain capability/media URLs; never print tracebacks.
        print(
            json.dumps(
                {
                    "result": "failed",
                    "stage": "unexpected-contract-error",
                    "category": "in-process-http-contract",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
