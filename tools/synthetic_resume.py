"""Isolated resume catalogue and per-login progress, never operator data."""

import json

import httpx

from tools.synthetic_lab import LIBRARY, MOVIE, USER, source
from tools.synthetic_lifecycle import LifecycleJellyfin

EPISODE, NEAR_END, WATCHED = (str(n) * 32 for n in (6, 7, 8))
ITEMS = (MOVIE, EPISODE, NEAR_END, WATCHED)
TICKS = 10_000_000


class ResumeJellyfin(LifecycleJellyfin):
    item_ids = ITEMS

    def __init__(self, origin):
        super().__init__(origin)
        self.saved = {}
        self.negotiations = 0
        self.start_position = 0

    def progress(self, token, item):
        return self.saved.setdefault(
            (token, item),
            {
                "PlaybackPositionTicks": (28 if item == NEAR_END else 8) * TICKS,
                "Played": item == WATCHED,
            },
        )

    def handle(self, request):
        if str(request.url).split("/jellyfin", 1)[0] != self.origin:
            raise RuntimeError("Synthetic transport rejected an unexpected origin")
        path = request.url.path.removeprefix("/jellyfin")
        token = next(
            (t for t in self.tokens if f'Token="{t}"' in request.headers.get("authorization", "")),
            None,
        )
        if (
            token
            and request.method == "GET"
            and path == f"/Users/{USER}/Items"
            and request.url.params.get("ParentId") == LIBRARY
        ):
            return httpx.Response(
                200,
                json={
                    "Items": [
                        {
                            "Id": item,
                            "Name": name,
                            "Type": "Episode" if item == EPISODE else "Movie",
                        }
                        for item, name in zip(
                            ITEMS,
                            ["Resume movie", "Resume episode", "Near end clip", "Watched clip"],
                            strict=True,
                        )
                    ],
                    "TotalRecordCount": 4,
                },
            )
        if (
            token
            and request.method == "GET"
            and any(path == f"/Users/{USER}/Items/{item}" for item in ITEMS)
        ):
            item = path.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "Id": item,
                    "Name": "Resume episode" if item == EPISODE else "Resume clip",
                    "Type": "Episode" if item == EPISODE else "Movie",
                    "PlayAccess": "Full",
                    "MediaSources": [source()],
                    "UserData": self.progress(token, item),
                },
            )
        if (
            token
            and request.method == "POST"
            and any(path == f"/Items/{item}/PlaybackInfo" for item in ITEMS)
        ):
            # The baseline's strict selection/DirectPlay/no-conversion validation
            # is reused unchanged, including for the extra fixed catalogue IDs.
            original = httpx.Request(
                "POST",
                self.origin + f"/jellyfin/Items/{MOVIE}/PlaybackInfo",
                headers=request.headers,
                content=request.content,
            )
            response = super().handle(original)
            if response.status_code == 200:
                self.negotiations += 1
                self.start_position = json.loads(request.content)["StartTimeTicks"] / TICKS
            return response
        response = super().handle(request)
        if token and response.status_code == 204 and path.startswith("/Sessions/Playing"):
            body = json.loads(request.content)
            progress = self.progress(token, body["ItemId"])
            progress["PlaybackPositionTicks"] = body["PositionTicks"]
            # Model watched/near-end independently of the client's resume policy.
            if path.endswith("/Stopped") and body["PositionTicks"] >= 27 * TICKS:
                progress["Played"] = True
        return response

    def summary(self):
        return {
            **super().summary(),
            "negotiations": self.negotiations,
            "requested_start_seconds": self.start_position,
        }
