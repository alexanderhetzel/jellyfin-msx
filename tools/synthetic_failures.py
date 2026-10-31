"""Startup-selected synthetic failures; no real transport or public fault controls."""

import httpx

from tools.synthetic_lab import LIBRARY, MOVIE, USER, SyntheticJellyfin, source

BROKEN_JSON, ACCESS_DENIED, UNREACHABLE, REJECTED_PLAYBACK = (letter * 32 for letter in "abcd")


class FailureJellyfin(SyntheticJellyfin):
    def handle(self, request):
        # Preserve the baseline's strict origin, login and token checks FIRST.
        response = super().handle(request)
        if response.status_code == 401:
            return response
        path = request.url.path.removeprefix("/jellyfin")
        if request.method == "GET" and path == f"/Users/{USER}/Views":
            body = response.json()
            body["Items"] += [
                {"Id": BROKEN_JSON, "Name": "Broken JSON library"},
                {"Id": ACCESS_DENIED, "Name": "Denied access library"},
                {"Id": UNREACHABLE, "Name": "Unreachable upstream library"},
            ]
            return httpx.Response(200, json=body)
        if request.method == "GET" and path == f"/Users/{USER}/Items":
            parent = request.url.params.get("ParentId")
            if parent == BROKEN_JSON:
                return httpx.Response(200, text="deliberately invalid JSON")
            if parent == ACCESS_DENIED:
                return httpx.Response(403)
            if parent == UNREACHABLE:
                raise httpx.ConnectError("Synthetic upstream unavailable", request=request)
            if parent == LIBRARY:
                body = response.json()
                body["Items"].append(
                    {"Id": REJECTED_PLAYBACK, "Name": "Rejected playback", "Type": "Movie"}
                )
                body["TotalRecordCount"] += 1
                return httpx.Response(200, json=body)
        if request.method == "GET" and path == f"/Users/{USER}/Items/{REJECTED_PLAYBACK}":
            return httpx.Response(
                200,
                json={
                    "Id": REJECTED_PLAYBACK,
                    "Name": "Rejected playback",
                    "Type": "Movie",
                    "PlayAccess": "Full",
                    "Overview": "Synthetic PlaybackInfo rejection; healthy clip remains available.",
                    "MediaSources": [source()],
                },
            )
        if request.method == "POST" and path == f"/Items/{REJECTED_PLAYBACK}/PlaybackInfo":
            # Reuse every baseline selected-source/no-conversion request assertion.
            healthy = httpx.Request(
                "POST",
                request.url.copy_with(path=f"/jellyfin/Items/{MOVIE}/PlaybackInfo"),
                headers=request.headers,
                content=request.content,
            )
            response = super().handle(healthy)
            if response.status_code == 200:
                body = response.json()
                body["MediaSources"][0]["SupportsDirectPlay"] = False
                return httpx.Response(200, json=body)
        return response
