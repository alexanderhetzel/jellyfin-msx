"""Fixed synthetic subtitle cases behind normal auth; no public mutation control."""

import httpx

from tools.synthetic_lab import LIBRARY, MOVIE, SOURCE, USER, SyntheticJellyfin, source

MISSING, MALFORMED = "8" * 32, "9" * 32
LAYOUT, LONG = "a" * 32, "b" * 32
ITEMS = (MOVIE, MISSING, MALFORMED, LAYOUT, LONG)
BOUNDARY_TEXT = "W" * 32 + "\n" + "漢" * 16
FAILED_FOUR_LINE_TEXT = (
    "DE alternate A: four-line wrap\n"
    "Wrapped subtitle text demonstrates a readable multi-line cue across a paused "
    "language switch and seek.\nThird line with umlauts: ÄÖÜ äöü ß\nFourth line"
)


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
    first_text = label + " A: Grüße, ÄÖÜ äöü ß\nSecond line"
    if index == 18:
        first_text = BOUNDARY_TEXT
    return (
        "WEBVTT\n\n00:00:00.000 --> 00:00:08.000\n" + first_text + "\n\n"
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
            f"/Items/{item}/PlaybackInfo" for item in ITEMS[1:]
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
                {"Id": LAYOUT, "Name": "Unsupported four-line layout", "Type": "Movie"},
                {"Id": LONG, "Name": "Unsupported long line", "Type": "Movie"},
            ]
            body["TotalRecordCount"] += 4
            return httpx.Response(200, json=body)
        if request.method == "GET" and path in {f"/Users/{USER}/Items/{item}" for item in ITEMS}:
            return httpx.Response(
                200,
                json={
                    "Id": path.rsplit("/", 1)[-1],
                    "Type": "Movie",
                    "Name": "Synthetic subtitles",
                    "PlayAccess": "Full",
                    "MediaSources": [subtitle_source()],
                },
            )
        for item in ITEMS:
            for index in (7, 12, 18):
                if (
                    request.method == "GET"
                    and path == f"/Videos/{item}/{SOURCE}/Subtitles/{index}/Stream.vtt"
                ):
                    if item == MISSING:
                        return httpx.Response(404)
                    content = cues(index)
                    if item == LAYOUT:
                        content = cues(18).replace(
                            BOUNDARY_TEXT.encode(), FAILED_FOUR_LINE_TEXT.encode()
                        )
                    elif item == LONG:
                        content = b"WEBVTT\n\n00:00:00.000 --> 00:00:08.000\n" + b"W" * 33 + b"\n"
                    return httpx.Response(
                        200,
                        content=b"not WebVTT" if item == MALFORMED else content,
                        headers={"Content-Type": "text/vtt"},
                    )
        return response
