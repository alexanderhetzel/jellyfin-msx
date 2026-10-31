"""Strict synthetic-only Jellyfin session observations, with no network fallback."""

import json
from collections import Counter

import httpx

from tools.synthetic_lab import MOVIE, SOURCE, SyntheticJellyfin


class LifecycleJellyfin(SyntheticJellyfin):
    item_ids = (MOVIE,)

    def __init__(self, origin):
        super().__init__(origin)
        self.reports = Counter()
        self.last_position = 0
        self.paused = False
        self.active = False
        self.failed_stop = False

    def handle(self, request):
        path = request.url.path.removeprefix("/jellyfin")
        if path in {"/Sessions/Playing", "/Sessions/Playing/Progress", "/Sessions/Playing/Stopped"}:
            if str(request.url).split("/jellyfin", 1)[0] != self.origin:
                raise RuntimeError("Synthetic transport rejected an unexpected origin")
            if request.method != "POST" or not any(
                f'Token="{token}"' in request.headers.get("authorization", "")
                for token in self.tokens
            ):
                return httpx.Response(401)
            body = json.loads(request.content)
            if (
                body.get("ItemId") not in self.item_ids
                or body.get("MediaSourceId") != SOURCE
                or not isinstance(body.get("PlaySessionId"), str)
                or type(body.get("PositionTicks")) is not int
                or not 0 <= body["PositionTicks"] <= 300_000_000
                or body.get("PlayMethod") != "DirectPlay"
            ):
                return httpx.Response(400)
            kind = {
                "/Sessions/Playing": "start",
                "/Sessions/Playing/Progress": "progress",
                "/Sessions/Playing/Stopped": "stop",
            }[path]
            self.reports[kind] += 1
            self.last_position = body["PositionTicks"]
            self.paused = body["IsPaused"]
            self.active = kind != "stop"
            self.failed_stop = body.get("Failed", False)
            return httpx.Response(204)
        return super().handle(request)

    def summary(self):
        return {
            "start": self.reports["start"],
            "progress": self.reports["progress"],
            "stop": self.reports["stop"],
            "position_seconds": self.last_position / 10_000_000,
            "paused": self.paused,
            "active": self.active,
            "failed_stop": self.failed_stop,
        }
