"""Restricted operator-opted-in original-file policy, not a general media gateway."""

from dataclasses import dataclass, field

from .errors import PortalError
from .jellyfin import identifier

SOURCE_SECONDS = 10
OPERATION_SECONDS = 15
MODE = "authenticated-file-candidate"


def enabled(settings):
    return settings.original_delivery == MODE


def unsupported():
    return PortalError(
        409, "This playback mode requires reported original MP4 playback with subtitles Off."
    )


def require(condition):
    if not condition:
        raise PortalError(
            409, "Authenticated original source evidence is unavailable or changed. Reopen details."
        )


@dataclass(frozen=True)
class Identity:
    source_id: str
    path: str = field(repr=False)
    container: str
    size: int
    duration: int


def item_access(item, expected):
    require(type(item) is dict)
    require(item.get("Id") == expected and item.get("Type") in ("Movie", "Episode"))
    if item.get("PlayAccess") == "None":
        raise PortalError(403, "Jellyfin does not allow playback of this item.")
    if item.get("PlayAccess") != "Full":
        raise PortalError(502, "Jellyfin playback permission is unavailable. Reopen details.")
    require(item.get("LocationType") == "FileSystem")
    require(item.get("SourceType") is None and item.get("ChannelId") is None)
    count = item.get("PartCount")
    require(count is None or type(count) is int and count == 1)


def source_identity(source, bitrate):
    # Import on use to keep transport, selection and delivery policy separate.
    from .playback import compatible

    require(type(source) is dict)
    source_id = identifier(source.get("Id"))
    require(source.get("Protocol") == "File" and source.get("Type") in ("Default", "Grouping"))
    require(source.get("VideoType") == "VideoFile")
    require(source.get("IsRemote") is False and source.get("RequiresOpening") is False)
    require(source.get("OpenToken") is None and source.get("LiveStreamId") is None)
    headers = source.get("RequiredHttpHeaders")
    require(headers is None or type(headers) is dict and not headers)
    streams = source.get("MediaStreams")
    require(type(streams) is list and all(type(stream) is dict for stream in streams))
    require(source.get("Container") == "mp4" and compatible(source, bitrate))
    for stream in streams:
        require(stream.get("Type") in ("Video", "Audio"))
        require(stream.get("Codec") == ("h264" if stream["Type"] == "Video" else "aac"))
    path = source.get("Path")
    require(
        isinstance(path, str)
        and 0 < len(path) <= 4096
        and path.startswith("/")
        and not path.startswith("//")
        and "\\" not in path
        and not any(part in {".", ".."} for part in path.split("/"))
        and not any(ord(c) < 32 for c in path)
    )
    size, duration = source.get("Size"), source.get("RunTimeTicks")
    require(type(size) is int and size > 0)
    require(type(duration) is int and 0 < duration <= 864000 * 10_000_000)
    return Identity(source_id, path, "mp4", size, duration)


def member(item, source_id):
    require(type(item) is dict)
    values = item.get("MediaSources")
    require(type(values) is list and all(type(source) is dict for source in values))
    sources = [s for s in values if s.get("Id") == source_id]
    require(len(sources) == 1)
    return sources[0]


def admitted(source, bitrate):
    try:
        source_identity(source, bitrate)
        return True
    except PortalError:
        return False


def version_identity(item, expected, bitrate):
    item_access(item, expected)
    require(item.get("VideoType") == "VideoFile")
    for name in ("Size", "RunTimeTicks"):
        require(type(item.get(name)) is int and item[name] > 0)
    own = source_identity(member(item, expected), bitrate)
    require(
        (item.get("Path"), item.get("Container"), item["Size"], item["RunTimeTicks"])
        == (own.path, own.container, own.size, own.duration)
    )
    return own


async def prepare(jellyfin, device, parent_id, parent, source):
    item_access(parent, parent_id)
    proof = source_identity(source, jellyfin.settings.max_bitrate)
    require(
        source_identity(member(parent, proof.source_id), jellyfin.settings.max_bitrate) == proof
    )
    identity = await jellyfin.json("GET", "/System/Info/Public", device)
    require(identity.get("Version") == jellyfin.settings.original_server_version)
    # The public version can restrict the operator's declaration, never grant it.
    version = await jellyfin.item(device, proof.source_id)
    require(version_identity(version, proof.source_id, jellyfin.settings.max_bitrate) == proof)
    return proof


async def revalidate(jellyfin, device, parent_id, proof, negotiated):
    require(negotiated.get("SupportsDirectPlay") is True)
    require(source_identity(negotiated, jellyfin.settings.max_bitrate) == proof)
    parent = await jellyfin.item(device, parent_id)
    item_access(parent, parent_id)
    require(
        source_identity(member(parent, proof.source_id), jellyfin.settings.max_bitrate) == proof
    )
    version = await jellyfin.item(device, proof.source_id)
    require(version_identity(version, proof.source_id, jellyfin.settings.max_bitrate) == proof)
    return f"/Items/{proof.source_id}/File"
