"""Opt-in subtitle bytes only; no player selection, extraction or conversion."""

import asyncio
import re
from collections import Counter

import httpx

from .errors import PortalError
from .jellyfin import identifier
from .playback import compatible

MAX_BYTES = 1024 * 1024
DEADLINE = 8
MAX_ACTIVE = 4
OFFICIAL_ORIGINS = {"https://msx.benzac.de", "https://www.msx.benzac.de"}
UNSUPPORTED = (
    "Only local external plain WebVTT subtitles are supported by this resource. "
    "SRT/ASS, embedded and image subtitles are unavailable; no conversion is requested."
)
TIMING = re.compile(
    r"(?P<start>(?:\d{2}:)?[0-5]\d:[0-5]\d\.\d{3}) --> "
    r"(?P<end>(?:\d{2}:)?[0-5]\d:[0-5]\d\.\d{3})",
    re.ASCII,
)


def milliseconds(value):
    parts = value.replace(".", ":").split(":")
    if len(parts) == 3:
        parts.insert(0, "0")
    hours, minutes, seconds, millis = map(int, parts)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def plain_vtt(raw):
    """Admit a small, explicit subset, without changing the media timebase."""
    if len(raw) > MAX_BYTES:
        raise PortalError(502, "Subtitle exceeds the size limit. Select Off.")
    try:
        value = raw.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeError:
        raise PortalError(502, "Subtitle must be UTF-8 WebVTT. Select Off.") from None
    if (
        any(ord(c) < 32 and c != "\n" for c in value)
        or "<" in value
        or ">" in value.replace(" --> ", "")
    ):
        raise PortalError(502, "Subtitle contains unsupported markup or controls. Select Off.")
    blocks = value.strip("\n").split("\n\n")
    if not blocks or blocks[0] != "WEBVTT" or len(blocks) > 10001:
        raise PortalError(502, "Unsupported WebVTT header or cue count. Select Off.")
    previous = -1
    output = ["WEBVTT"]
    for block in blocks[1:]:
        lines = block.split("\n")
        # A cue identifier is data only and is omitted from the returned resource.
        if len(lines) > 1 and "-->" not in lines[0] and TIMING.fullmatch(lines[1]):
            lines = lines[1:]
        timing = TIMING.fullmatch(lines[0])
        if (
            not timing
            or len(lines) < 2
            or len(lines) > 5
            or any(not line or len(line) > 1024 or "-->" in line for line in lines[1:])
            or len(block) > 4096
        ):
            raise PortalError(502, "Unsupported WebVTT cue or layout. Select Off.")
        start, end = (milliseconds(timing[g]) for g in ("start", "end"))
        if start < previous or end <= start or end > 86400000:
            raise PortalError(502, "Invalid WebVTT timing. Select Off.")
        previous = end  # Overlapping cues are outside the initial plain-text subset.
        output.append("\n".join(lines))
    return ("\n\n".join(output) + "\n").encode("utf-8")


def eligible_track(stream):
    path = stream.get("Path")
    return (
        stream.get("Type") == "Subtitle"
        and type(stream.get("Index")) is int
        and 0 <= stream["Index"] <= 10000
        and stream.get("IsExternal") is True
        and stream.get("IsTextSubtitleStream") is True
        and isinstance(stream.get("Codec"), str)
        and stream["Codec"] in {"vtt", "webvtt"}
        and isinstance(path, str)
        and 0 < len(path) <= 4096
        and path.lower().endswith(".vtt")
        and ":" not in path
        and "\\" not in path
        and path.startswith("/")
        and not path.startswith("//")
        and not any(ord(c) < 32 for c in path)
    )


async def selected_source(jellyfin, device, item_id, source_id):
    identifier(item_id)
    identifier(source_id)
    item = await jellyfin.item(device, item_id)
    sources = [s for s in item.get("MediaSources", []) if s.get("Id") == source_id]
    if (
        item.get("Id") != item_id
        or item.get("Type") not in ("Movie", "Episode", "Video")
        or len(sources) != 1
        or not compatible(sources[0], jellyfin.settings.max_bitrate)
    ):
        raise PortalError(409, "Selected version is no longer eligible. Reopen item details.")
    return sources[0]


def tracks(source):
    streams = source.get("MediaStreams", [])
    indices = Counter(s.get("Index") for s in streams if isinstance(s.get("Index"), int))
    result = []
    for stream in streams:
        if eligible_track(stream) and indices[stream["Index"]] == 1:
            language = stream.get("Language", "")
            if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2,3}", language):
                language = "und"
            result.append({"index": stream["Index"], "language": language})
    return result


class SubtitleResources:
    def __init__(self, jellyfin, state):
        self.jellyfin = jellyfin
        self.state = state
        self.active = 0

    async def prepare(self, secret, item_id, source_id):
        """Bound startup validation; never substitute another source or track."""
        self.state.get(secret)
        try:
            async with asyncio.timeout(12):
                catalogue = await self.request(secret, item_id, source_id)
                available = catalogue["tracks"][:8]
                if not available:
                    raise PortalError(409, UNSUPPORTED)
                for track in available:
                    await self.request(secret, item_id, source_id, track["index"])
                self.state.get(secret)
                return available
        except TimeoutError:
            raise PortalError(
                504, "Subtitle preparation timed out. Play without subtitles."
            ) from None

    async def request(self, secret, item_id, source_id, index=None):
        device = self.state.get(secret)
        if not self.jellyfin.settings.enable_subtitle_resources:
            raise PortalError(409, "Subtitle resources are disabled. Subtitles remain Off.")
        self.state.limit("subtitles:" + device.device_id, 30)
        if self.active >= MAX_ACTIVE:
            raise PortalError(429, "Subtitle service busy. Retry or select Off.")
        self.active += 1
        try:
            async with asyncio.timeout(DEADLINE):
                source = await selected_source(self.jellyfin, device, item_id, source_id)
                self.state.get(secret)
                available = tracks(source)
                if index is None:
                    return {"default": "off", "tracks": available, "unsupported": UNSUPPORTED}
                if type(index) is not int or not any(t["index"] == index for t in available):
                    raise PortalError(409, UNSUPPORTED)
                headers = self.jellyfin.headers(device) | {
                    "Accept": "text/vtt",
                    "Accept-Encoding": "identity",
                }
                path = f"/Videos/{item_id}/{source_id}/Subtitles/{index}/Stream.vtt"
                async with self.jellyfin.client.stream(
                    "GET",
                    self.jellyfin.settings.jellyfin_url + path,
                    headers=headers,
                    params={
                        "CopyTimestamps": "true",
                        "StartPositionTicks": 0,
                        "AddVttTimeMap": "false",
                    },
                ) as response:
                    if response.status_code in {401, 403, 404}:
                        raise PortalError(response.status_code, "Subtitle unavailable. Select Off.")
                    if response.status_code != 200:
                        raise PortalError(502, "Subtitle request failed. Select Off.")
                    if (
                        response.headers.get("content-type", "").split(";")[0].lower() != "text/vtt"
                        or response.headers.get("content-encoding", "identity") != "identity"
                    ):
                        raise PortalError(502, "Unsupported subtitle response. Select Off.")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(raw) + len(chunk) > MAX_BYTES:
                            raise PortalError(502, "Subtitle exceeds the size limit. Select Off.")
                        raw.extend(chunk)
                # Never release buffered private data after logout, expiry or generation revocation.
                self.state.get(secret)
                if device.token.encode() in raw:
                    raise PortalError(502, "Invalid subtitle content. Select Off.")
                return plain_vtt(bytes(raw))
        except (httpx.RequestError, TimeoutError):
            raise PortalError(504, "Subtitle request timed out. Retry or select Off.") from None
        finally:
            self.active -= 1
