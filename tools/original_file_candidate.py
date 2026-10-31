"""Mock-only prototype for /File snapshot admission, never a production resolver.

No CLI or media request. The returned candidate is not a URL, byte-identity proof,
per-request playback-policy guarantee or real-server compatibility observation.
"""

import asyncio
from dataclasses import dataclass

from jellyfin_msx.jellyfin import identifier
from jellyfin_msx.playback import compatible, profile


class CandidateRejected(Exception):
    """Fixed reason only; never reflect metadata, paths, URLs or credentials."""


@dataclass(frozen=True)
class FileSnapshotCandidate:
    parent_id: str
    version_id: str
    container: str


def require(value, reason):
    if not value:
        raise CandidateRejected(reason)


def identity(item, expected_id):
    require(item.get("Id") == expected_id, "item identity changed")
    require(item.get("Type") in {"Movie", "Episode"}, "unsupported item type")
    require(item.get("LocationType") == "FileSystem", "filesystem provenance unavailable")
    # Pinned DtoService leaves PartCount null for a single file; it populates
    # the count only for AdditionalParts. This is a stock all-field DTO contract.
    parts = item.get("PartCount")
    require(parts is None or type(parts) is int and parts == 1, "stacked or invalid parts excluded")
    require(item.get("ChannelId") is None, "channel provenance unavailable or excluded")
    # Stock DtoService emits SourceType for Channel and leaves it null for Library.
    require(item.get("SourceType") is None, "non-library provenance unavailable or excluded")
    require(item.get("PlayAccess") == "Full", "playback permission unavailable or denied")


def proof(source, bitrate):
    require(source.get("Protocol") == "File", "non-file source excluded")
    require(source.get("Type") in {"Default", "Grouping"}, "provider provenance excluded")
    require(source.get("VideoType") == "VideoFile", "disc or unknown video type excluded")
    for field in ("IsRemote", "RequiresOpening"):
        require(source.get(field) is False, "opening or remote state unavailable")
    require(
        not any(source.get(key) for key in ("LiveStreamId", "OpenToken", "RequiredHttpHeaders")),
        "live or header-dependent source excluded",
    )
    require(compatible(source, bitrate), "selected source violates playback admission")
    path = source.get("Path")
    require(
        isinstance(path, str)
        and path.startswith("/")
        and not path.startswith("//")
        and "\\" not in path
        and not any(part in {".", ".."} for part in path.split("/")),
        "unsubstituted local Linux path unavailable",
    )
    for field in ("Size", "RunTimeTicks"):
        require(type(source.get(field)) is int and source[field] > 0, "source extent unavailable")
    return source["Path"], source["Container"], source["Size"], source["RunTimeTicks"]


def member(item, source_id):
    matches = [s for s in item.get("MediaSources", []) if s.get("Id") == source_id]
    require(len(matches) == 1, "source membership missing or ambiguous")
    return matches[0]


def version_proof(item, source_id, bitrate):
    identity(item, source_id)
    require(item.get("VideoType") == "VideoFile", "version video type unavailable")
    own = proof(member(item, source_id), bitrate)
    for field in ("Size", "RunTimeTicks"):
        require(type(item.get(field)) is int and item[field] > 0, "version extent unavailable")
    require(
        own
        == (item.get("Path"), item.get("Container"), item.get("Size"), item.get("RunTimeTicks")),
        "self-source and version path or extent differ",
    )
    return own


async def assess_file_snapshot(jellyfin, device, parent_id, source_id):
    """Reject incomplete stock-library evidence; do not select a delivery route.

    Preconditions: caller knows these are ordinary static library items on the
    pinned stock-server contract, not plugin-supplied metadata. JSON field shape
    cannot itself prove that provenance. No fallback or permission upgrade.
    """
    identifier(parent_id)
    identifier(source_id)
    require(not jellyfin.settings.allow_transcoding, "conversion-enabled host excluded")
    bitrate = jellyfin.settings.max_bitrate
    async with asyncio.timeout(20):
        parent = await jellyfin.item(device, parent_id)
        identity(parent, parent_id)
        selected = member(parent, source_id)
        expected = proof(selected, bitrate)
        version = await jellyfin.item(device, source_id)
        require(version_proof(version, source_id, bitrate) == expected, "wrong version snapshot")
        info = await jellyfin.json(
            "POST",
            f"/Items/{parent_id}/PlaybackInfo",
            device,
            json={
                "UserId": device.user_id,
                "MediaSourceId": source_id,
                "DeviceProfile": profile(bitrate, False),
                "EnableDirectPlay": True,
                "EnableDirectStream": False,
                "EnableTranscoding": False,
                "AllowVideoStreamCopy": False,
                "AllowAudioStreamCopy": False,
                "SubtitleStreamIndex": -1,
                "StartTimeTicks": 0,
            },
        )
        require(not info.get("ErrorCode"), "negotiation denied")
        negotiated = member(info, source_id)
        require(negotiated.get("SupportsDirectPlay") is True, "Direct Play denied")
        require(proof(negotiated, bitrate) == expected, "negotiated source changed")
        # Recheck both visibility/permission snapshots and membership after awaits.
        parent = await jellyfin.item(device, parent_id)
        identity(parent, parent_id)
        require(proof(member(parent, source_id), bitrate) == expected, "membership changed")
        version = await jellyfin.item(device, source_id)
        require(version_proof(version, source_id, bitrate) == expected, "version changed")
        return FileSnapshotCandidate(parent_id, source_id, expected[1])
