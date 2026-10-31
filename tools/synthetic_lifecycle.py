"""Strict synthetic-only Jellyfin session observations, with no network fallback."""

import json
from collections import Counter

import httpx

from tools.synthetic_lab import LIBRARY, MOVIE, SOURCE, USER, SyntheticJellyfin, source

RECOVERY_NATIVE, RECOVERY_DENIED, RECOVERY_TIMEOUT, RECOVERY_CONNECT = (
    letter * 32 for letter in "6789"
)
RECOVERY_ALTERNATE, RECOVERY_BAD_SOURCE = (letter * 32 for letter in "ab")


class LifecycleJellyfin(SyntheticJellyfin):
    item_ids = frozenset((MOVIE,))
    source_ids = frozenset((SOURCE,))

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
                or body.get("MediaSourceId") not in self.source_ids
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


class RecoveryJellyfin(LifecycleJellyfin):
    """Fixed startup-only faults and stored copies; never real transport or fault controls."""

    item_ids = frozenset(
        (MOVIE, RECOVERY_NATIVE, RECOVERY_DENIED, RECOVERY_TIMEOUT, RECOVERY_CONNECT)
    )
    source_ids = frozenset((SOURCE, RECOVERY_ALTERNATE, RECOVERY_BAD_SOURCE))
    names = {
        RECOVERY_NATIVE: "Native failure with stored alternative",
        RECOVERY_DENIED: "Negotiation denied",
        RECOVERY_TIMEOUT: "Negotiation timeout",
        RECOVERY_CONNECT: "Negotiation connectivity failure",
    }

    def __init__(self, origin):
        super().__init__(origin)
        self.negotiations = Counter()

    def handle(self, request):
        # Baseline validates origin and normal authentication before custom cases.
        response = super().handle(request)
        if response.status_code == 401:
            return response
        path = request.url.path.removeprefix("/jellyfin")
        if (
            request.method == "GET"
            and path == f"/Users/{USER}/Items"
            and request.url.params.get("ParentId") == LIBRARY
        ):
            body = response.json()
            body["Items"] += [
                {"Id": key, "Name": name, "Type": "Movie"} for key, name in self.names.items()
            ]
            body["TotalRecordCount"] += len(self.names)
            return httpx.Response(200, json=body)
        for item_id in self.names:
            if request.method == "GET" and path == f"/Users/{USER}/Items/{item_id}":
                sources = [source()]
                if item_id == RECOVERY_NATIVE:
                    sources[0]["Id"] = RECOVERY_BAD_SOURCE
                    alternate = source()
                    alternate["Id"] = RECOVERY_ALTERNATE
                    sources.append(alternate)
                return httpx.Response(
                    200,
                    json={
                        "Id": item_id,
                        "Name": self.names[item_id],
                        "Type": "Movie",
                        "PlayAccess": "Full",
                        "MediaSources": sources,
                    },
                )
            if request.method == "POST" and path == f"/Items/{item_id}/PlaybackInfo":
                body = json.loads(request.content)
                allowed = (
                    {RECOVERY_BAD_SOURCE, RECOVERY_ALTERNATE}
                    if item_id == RECOVERY_NATIVE
                    else {SOURCE}
                )
                if (
                    body.get("MediaSourceId") not in allowed
                    or body.get("EnableDirectPlay") is not True
                    or body.get("EnableDirectStream") is not False
                    or body.get("EnableTranscoding") is not False
                    or body.get("SubtitleStreamIndex") != -1
                ):
                    return httpx.Response(400)
                self.negotiations[item_id] += 1
                if item_id == RECOVERY_TIMEOUT:
                    raise httpx.ReadTimeout("Synthetic request timeout", request=request)
                if item_id == RECOVERY_CONNECT:
                    raise httpx.ConnectError("Synthetic connection failure", request=request)
                candidate = source()
                candidate["Id"] = body["MediaSourceId"]
                candidate["SupportsDirectPlay"] = item_id != RECOVERY_DENIED
                return httpx.Response(
                    200,
                    json={
                        "MediaSources": [candidate],
                        "PlaySessionId": "synthetic-recovery-session",
                    },
                )
        return response

    def summary(self):
        return {**super().summary(), "negotiations": sum(self.negotiations.values())}
