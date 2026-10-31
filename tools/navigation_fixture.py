"""Synthetic series catalogue behind normal authentication; never a real server."""

import httpx

from tools.synthetic_lab import POSTER, USER, SyntheticJellyfin, source

LIBRARY, SERIES, SEASON, EMPTY, DENIED = (f"{n:032x}" for n in range(100, 105))
EPISODES = [f"{n:032x}" for n in range(200, 250)]


def folder(item_id, name, kind):
    return {"Id": item_id, "Name": name, "Type": kind, "ImageTags": {"Primary": "synthetic"}}


class NavigationJellyfin(SyntheticJellyfin):
    def __init__(self, origin):
        super().__init__(origin)
        self.children = {
            LIBRARY: [folder(SERIES, "Synthetic series", "Series")],
            SERIES: [
                folder(SEASON, "Season 1 - fifty episodes", "Season"),
                folder(EMPTY, "Season 2 - empty", "Season"),
                folder(DENIED, "Restricted season", "Season"),
            ],
            SEASON: [
                {
                    "Id": item_id,
                    "Name": f"Episode {i:02d}",
                    "Type": "Episode",
                    "ProductionYear": 2026,
                    "ImageTags": {"Primary": "synthetic"},
                }
                for i, item_id in enumerate(EPISODES, 1)
            ],
            EMPTY: [],
        }

    def handle(self, request):
        # Let the existing strict transport validate the origin and authentication
        # before serving catalogue responses. No route or state auth bypass.
        fallback = super().handle(request)
        if fallback.status_code == 401 or request.method not in {"GET", "POST"}:
            return fallback
        path = request.url.path.removeprefix("/jellyfin")
        if path == f"/Users/{USER}/Views":
            return httpx.Response(
                200, json={"Items": [{"Id": LIBRARY, "Name": "Synthetic television"}]}
            )
        if path == f"/Users/{USER}/Items":
            parent = request.url.params.get("ParentId")
            if parent == DENIED:
                return httpx.Response(403)
            if parent not in self.children:
                return httpx.Response(404)
            rows = self.children[parent]
            start = int(request.url.params.get("StartIndex", "0"))
            limit = int(request.url.params.get("Limit", "24"))
            return httpx.Response(
                200, json={"Items": rows[start : start + limit], "TotalRecordCount": len(rows)}
            )
        item_id = path.split("/")[-1]
        if path.startswith(f"/Users/{USER}/Items/") and item_id not in EPISODES:
            for rows in self.children.values():
                for row in rows:
                    if row["Id"] == item_id:
                        return httpx.Response(200, json=row)
        if path.startswith(f"/Users/{USER}/Items/") and item_id in EPISODES:
            return httpx.Response(
                200,
                json={
                    "Id": item_id,
                    "Name": f"Episode {EPISODES.index(item_id) + 1:02d}",
                    "Type": "Episode",
                    "PlayAccess": "Full",
                    "ProductionYear": 2026,
                    "Overview": (
                        "Independent synthetic episode; public clip substituted in renderer probe."
                    ),
                    "MediaSources": [source()],
                },
            )
        parts = path.split("/")
        if len(parts) > 2 and parts[2] in EPISODES:
            if path.endswith("/PlaybackInfo"):
                # Reuse the strict existing negotiation contract for each episode.
                from tools.synthetic_lab import MOVIE

                clone = httpx.Request(
                    request.method,
                    str(request.url).replace(parts[2], MOVIE),
                    headers=request.headers,
                    content=request.content,
                )
                return super().handle(clone)
        if path.endswith("/Images/Primary") and parts[2] in {
            *EPISODES,
            LIBRARY,
            SERIES,
            SEASON,
            EMPTY,
            DENIED,
        }:
            return httpx.Response(200, content=POSTER, headers={"Content-Type": "image/png"})
        return fallback
