"""Fixed synthetic subtitle cases behind normal auth; no public mutation control."""

import httpx

from tools.synthetic_lab import LIBRARY, MOVIE, SOURCE, USER, SyntheticJellyfin, source

MISSING, MALFORMED = "8" * 32, "9" * 32


def subtitle_source():
    result = source()
    result["MediaStreams"] += [
        {
            "Type": "Subtitle",
            "Index": index,
            "Codec": "webvtt",
            "Language": language,
            "IsExternal": True,
            "IsTextSubtitleStream": True,
            "Path": f"/synthetic/{index}.vtt",
        }
        for index, language in ((7, "deu"), (12, "eng"), (18, "deu"))
    ]
    return result


def cues(index):
    label = {7: "DE", 12: "EN", 18: "DE alternate"}[index]
    return (
        "WEBVTT\n\n00:00:00.000 --> 00:00:08.000\n"
        + label
        + " A: Grüße, ÄÖÜ äöü ß\nSecond line\n\n"
        "00:00:08.000 --> 00:00:16.000\n" + label + " B: subtitle timing\n\n"
        "00:00:16.000 --> 00:00:25.000\n" + label + " C: end test\n"
    ).encode()


class SubtitleJellyfin(SyntheticJellyfin):
    def handle(self, request):
        response = super().handle(request)
        if response.status_code == 401:
            return response
        path = request.url.path.removeprefix("/jellyfin")
        if request.method == "POST" and path in {
            f"/Items/{item}/PlaybackInfo" for item in (MISSING, MALFORMED)
        }:
            return super().handle(
                httpx.Request(
                    "POST",
                    request.url.copy_with(path=f"/jellyfin/Items/{MOVIE}/PlaybackInfo"),
                    headers=request.headers,
                    content=request.content,
                )
            )
        if (
            request.method == "GET"
            and path == f"/Users/{USER}/Items"
            and request.url.params.get("ParentId") == LIBRARY
        ):
            body = response.json()
            body["Items"] += [
                {"Id": MISSING, "Name": "Missing subtitle", "Type": "Movie"},
                {"Id": MALFORMED, "Name": "Malformed subtitle", "Type": "Movie"},
            ]
            body["TotalRecordCount"] += 2
            return httpx.Response(200, json=body)
        if request.method == "GET" and path in {
            f"/Users/{USER}/Items/{item}" for item in (MOVIE, MISSING, MALFORMED)
        }:
            return httpx.Response(
                200,
                json={
                    "Id": path.rsplit("/", 1)[-1],
                    "Type": "Movie",
                    "Name": "Synthetic subtitles",
                    "MediaSources": [subtitle_source()],
                },
            )
        for item in (MOVIE, MISSING, MALFORMED):
            for index in (7, 12, 18):
                if (
                    request.method == "GET"
                    and path == f"/Videos/{item}/{SOURCE}/Subtitles/{index}/Stream.vtt"
                ):
                    if item == MISSING:
                        return httpx.Response(404)
                    return httpx.Response(
                        200,
                        content=b"not WebVTT" if item == MALFORMED else cues(index),
                        headers={"Content-Type": "text/vtt"},
                    )
        return response


def attach_subtitle_media(app):
    """The negative subtitle cases retain the same synthetic original video."""
    route = next(r for r in app.routes if r.path == f"/jellyfin/Videos/{MOVIE}/stream.mp4")
    for item in (MISSING, MALFORMED):
        app.add_api_route(
            f"/jellyfin/Videos/{item}/stream.mp4", route.endpoint, methods=["GET", "HEAD"]
        )
