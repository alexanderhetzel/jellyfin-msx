import math
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .device_profile import (
    AUDIO_CODECS,
    MAX_VIDEO_HEIGHT,
    MAX_VIDEO_WIDTH,
    MODEL,
    PHILIPS,
    PROFILE_BASIS,
    PROFILE_NAME,
    VIDEO_CODECS,
    CandidateProfile,
    evidence_warnings,
)
from .errors import PortalError
from .jellyfin import Jellyfin, identifier
from .state import Device


def lower(value):
    return value.lower() if isinstance(value, str) else ""


def choose_source(item, bitrate, allow_transcoding=False, *, candidate_profile=PHILIPS):
    sources = item.get("MediaSources") or []
    if not sources:
        raise PortalError(409, "Jellyfin returned no media source for this item.")
    candidates = [
        source
        for source in sources
        if compatible(source, bitrate, candidate_profile=candidate_profile)
    ]
    if candidates:

        def preference(source):
            video = next(s for s in source["MediaStreams"] if s.get("Type") == "Video")
            pixels = video["Width"] * video["Height"]
            width, height = candidate_profile.preferred_size
            fits_panel = video["Width"] <= width and video["Height"] <= height
            # Selection preference, not a maximum decoder resolution.
            return (
                lower(video.get("Codec")) != candidate_profile.preferred_video_codec,
                not fits_panel,
                -pixels if fits_panel else pixels,
            )

        return min(candidates, key=preference)
    if allow_transcoding:
        # Optional conversion hosts must not bypass this client's HD-only scope.
        fallback = next((source for source in sources if within_hd_policy(source)), None)
        if fallback:
            return fallback
    raise PortalError(
        409,
        "No eligible stored version for this Philips profile. "
        "Video must be at most 1920x1080; 4K playback/downscaling is not supported "
        "by this client. Use a matching 720p/1080p copy. "
        + ("Transcoding is disabled." if not allow_transcoding else "No eligible HD source."),
    )


def profile(bitrate: int | None = None, allow_transcoding=False, *, candidate_profile=PHILIPS):
    result = {
        "Name": candidate_profile.name,
        "DirectPlayProfiles": [
            {
                "Container": ",".join(candidate_profile.containers),
                "Type": "Video",
                "VideoCodec": ",".join(candidate_profile.video_codecs),
                "AudioCodec": ",".join(candidate_profile.audio_codecs),
            }
        ],
        "TranscodingProfiles": [
            {
                "Container": "ts",
                "Type": "Video",
                "VideoCodec": "h264",
                "AudioCodec": "aac",
                "Protocol": "hls",
                "Context": "Streaming",
                "MaxAudioChannels": "2",
                "MinSegments": 2,
                "BreakOnNonKeyFrames": False,
            }
        ],
        "CodecProfiles": [
            {
                "Type": "Video",
                "Codec": ",".join(candidate_profile.video_codecs),
                "Conditions": [
                    {
                        "Condition": "LessThanEqual",
                        "Property": field,
                        "Value": str(limit),
                        "IsRequired": True,
                    }
                    for field, limit in (
                        ("Width", MAX_VIDEO_WIDTH),
                        ("Height", MAX_VIDEO_HEIGHT),
                    )
                ],
            }
        ],
        "SubtitleProfiles": [
            {"Format": fmt, "Method": "Encode"}
            for fmt in ("srt", "ass", "ssa", "sub", "pgssub", "dvdsub")
        ],
    }
    if bitrate is not None:
        result.update(MaxStreamingBitrate=bitrate, MaxStaticBitrate=bitrate)
    if not allow_transcoding:
        result["TranscodingProfiles"] = []
        result["SubtitleProfiles"] = []
    return result


def compatibility_reasons(
    source: dict,
    bitrate: int | None = None,
    *,
    candidate_profile: CandidateProfile = PHILIPS,
) -> list[str]:
    """Fixed policy explanations; never reflect file names, URLs or arbitrary metadata."""
    reasons = []
    streams = source.get("MediaStreams") or []
    videos = [s for s in streams if s.get("Type") == "Video"]
    audios = [s for s in streams if s.get("Type") == "Audio"]
    if lower(source.get("Container")) not in candidate_profile.containers:
        reasons.append("Container is not covered by the documented candidate profile")
    if source.get("IsRemote") or source.get("RequiredHttpHeaders") or source.get("RequiresOpening"):
        reasons.append("Source requires an unsupported remote or opening mechanism")
    if bitrate is not None and (
        not positive_number(source.get("Bitrate")) or source["Bitrate"] > bitrate
    ):
        reasons.append("Total bitrate missing or exceeds the operator's network budget")
    if not audios:
        reasons.append("Audio stream metadata missing")
    if any(lower(a.get("Codec")) not in candidate_profile.audio_codecs for a in audios):
        reasons.append("An audio codec is not covered by the documented candidate profile")
    if any(
        not isinstance(a.get("Channels"), int)
        or isinstance(a["Channels"], bool)
        or a["Channels"] <= 0
        for a in audios
    ):
        reasons.append("Audio channel count missing or invalid")
    if len(videos) != 1:
        reasons.append("Exactly one video stream required")
        return reasons
    video = videos[0]
    if not positive_number(video.get("Width")) or not positive_number(video.get("Height")):
        reasons.append("Video dimensions missing or invalid")
    elif video["Width"] > MAX_VIDEO_WIDTH or video["Height"] > MAX_VIDEO_HEIGHT:
        reasons.append(
            "Video exceeds the 1920x1080 client limit; 4K playback/downscaling is disabled"
        )
    if lower(video.get("Codec")) not in candidate_profile.video_codecs:
        reasons.append("Video codec is not covered by the documented candidate profile")
    return reasons


def positive_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False  # Malformed numeric metadata, not a hardware decoder ceiling.


def compatible(
    source: dict, bitrate: int | None = None, *, candidate_profile: CandidateProfile = PHILIPS
) -> bool:
    """Matches documentation-based candidates, not a physical-device pass."""
    return not compatibility_reasons(source, bitrate, candidate_profile=candidate_profile)


def within_hd_policy(source: dict) -> bool:
    videos = [s for s in (source.get("MediaStreams") or []) if s.get("Type") == "Video"]
    return (
        len(videos) == 1
        and positive_number(videos[0].get("Width"))
        and positive_number(videos[0].get("Height"))
        and videos[0]["Width"] <= MAX_VIDEO_WIDTH
        and videos[0]["Height"] <= MAX_VIDEO_HEIGHT
    )


def authenticated_url(base: str, returned: str, token: str) -> str:
    """Accept only the configured Jellyfin origin/base path, including subpath installs."""
    original = urlsplit(base)
    if not isinstance(returned, str) or len(returned) > 16000 or returned.startswith("//"):
        raise PortalError(502, "Jellyfin returned an invalid playback URL.")
    if returned.startswith("/") and not returned.startswith("//"):
        if original.path and not returned.startswith(original.path + "/"):
            returned = original.path + returned
        returned = urlunsplit((original.scheme, original.netloc, "", "", "")) + returned
    elif not urlsplit(returned).scheme:
        returned = base + "/" + returned
    candidate = urlsplit(returned)
    if (
        candidate.scheme != original.scheme
        or candidate.netloc != original.netloc
        or candidate.username
        or candidate.password
        or candidate.fragment
        or not candidate.path.startswith(original.path + "/")
        or any(p in {".", ".."} for p in candidate.path.split("/"))
        or any(c in returned for c in ("\\", "\r", "\n"))
        or "%2e" in candidate.path.lower()
        or "%2f" in candidate.path.lower()
    ):
        raise PortalError(502, "Jellyfin returned a playback URL outside the configured server.")
    query = {
        k: v
        for k, v in parse_qsl(candidate.query)
        if k.lower() not in {"api_key", "apikey", "token"}
    }
    query["ApiKey"] = token
    return urlunsplit((candidate.scheme, candidate.netloc, candidate.path, urlencode(query), ""))


async def resolve(
    jellyfin: Jellyfin,
    device: Device,
    item_id: str,
    force: bool,
    subtitle: int,
    media_source_id: str | None = None,
    playback_context: dict | None = None,
):
    allow_transcoding = jellyfin.settings.allow_transcoding
    if not allow_transcoding and (force or subtitle >= 0):
        raise PortalError(409, "Transcoding and subtitle burn-in are disabled for this server.")
    item = await jellyfin.item(device, item_id)  # enforce user access before negotiation
    if item.get("Type") not in {"Movie", "Episode", "Video"}:
        raise PortalError(400, "Select a movie or episode to play.")
    if media_source_id is None:
        selected = choose_source(item, jellyfin.settings.max_bitrate, allow_transcoding)
    else:
        identifier(media_source_id)
        selected = next(
            (s for s in item.get("MediaSources", []) if s.get("Id") == media_source_id), None
        )
        if (
            not selected
            or not within_hd_policy(selected)
            or (not allow_transcoding and not compatible(selected, jellyfin.settings.max_bitrate))
        ):
            raise PortalError(
                409, "Selected version is no longer eligible. Reopen the item details."
            )
    source_id = identifier(selected.get("Id"))
    body = {
        "UserId": device.user_id,
        "DeviceProfile": profile(jellyfin.settings.max_bitrate, allow_transcoding),
        "EnableDirectPlay": not force and subtitle < 0,
        "EnableDirectStream": False,
        "EnableTranscoding": allow_transcoding,
        "AllowVideoStreamCopy": False,
        "AllowAudioStreamCopy": False,
        "SubtitleStreamIndex": subtitle,
        "StartTimeTicks": 0,
        "MediaSourceId": source_id,
    }
    if jellyfin.settings.max_bitrate is not None:
        body["MaxStreamingBitrate"] = jellyfin.settings.max_bitrate
    if subtitle >= 0:
        if not any(
            t.get("Type") == "Subtitle" and t.get("Index") == subtitle
            for t in selected.get("MediaStreams", [])
        ):
            raise PortalError(400, "Subtitle track is unavailable.")
        body["AlwaysBurnInSubtitleWhenTranscoding"] = True
    info = await jellyfin.json("POST", f"/Items/{item_id}/PlaybackInfo", device, json=body)
    if info.get("ErrorCode"):
        raise PortalError(
            409, "Jellyfin cannot play this item. Check permissions and encoder support."
        )
    sources = [
        s for s in info.get("MediaSources", []) if s.get("Id") == source_id and within_hd_policy(s)
    ]
    if not sources:
        raise PortalError(409, "Jellyfin returned no playable HD media source (1920x1080 limit).")
    direct = next(
        (
            s
            for s in sources
            if body["EnableDirectPlay"]
            and s.get("SupportsDirectPlay")
            and compatible(s, jellyfin.settings.max_bitrate)
        ),
        None,
    )
    if direct:
        source = direct
        query = urlencode(
            {
                "Static": "true",
                "MediaSourceId": identifier(source.get("Id")),
                "DeviceId": device.device_id,
                "PlaySessionId": info.get("PlaySessionId", ""),
            }
        )
        url = authenticated_url(
            jellyfin.settings.jellyfin_url,
            f"/Videos/{item_id}/stream.{lower(source['Container'])}?{query}",
            device.token,
        )
        mode = "DirectPlay"
    else:
        if not allow_transcoding:
            raise PortalError(
                409,
                "Jellyfin denied Direct Play. Transcoding is disabled; "
                "check the selected version and user permissions.",
            )
        source = next(
            (s for s in sources if s.get("SupportsTranscoding") and s.get("TranscodingUrl")), None
        )
        if not source and body["EnableDirectPlay"]:
            body["EnableDirectPlay"] = False
            info = await jellyfin.json("POST", f"/Items/{item_id}/PlaybackInfo", device, json=body)
            source = next(
                (
                    s
                    for s in info.get("MediaSources", [])
                    if s.get("Id") == source_id
                    and within_hd_policy(s)
                    and s.get("SupportsTranscoding")
                    and s.get("TranscodingUrl")
                ),
                None,
            )
        if not source or lower(source.get("TranscodingSubProtocol")) != "hls":
            raise PortalError(
                409, "No compatible stream. Enable video/audio transcoding for this user."
            )
        url = authenticated_url(
            jellyfin.settings.jellyfin_url, source["TranscodingUrl"], device.token
        )
        if not urlsplit(url).path.lower().endswith(".m3u8"):
            raise PortalError(502, "Jellyfin did not return an HLS manifest.")
        mode = "TranscodeHLS"
    if playback_context is not None:
        # Transport correlation is private state, never a diagnostic field.
        playback_context.update(
            source_id=source_id,
            play_session_id=info.get("PlaySessionId"),
            duration_ticks=source.get("RunTimeTicks", item.get("RunTimeTicks")),
            mode=mode,
        )
    diagnostic = {
        "id": secrets.token_hex(8),
        "event": "playback_decision",
        "mode": mode,
        "profile": PROFILE_NAME,
        "device_model": MODEL,
        "profile_basis": PROFILE_BASIS,
        "warnings": evidence_warnings(selected),
        "forced": force,
        "subtitle_burn_in": subtitle >= 0,
        "device_playback_verified": False,
        "transcoding_allowed": allow_transcoding,
        "selected_video_height": next(
            (s.get("Height") for s in selected.get("MediaStreams", []) if s.get("Type") == "Video"),
            None,
        ),
        "streams": stream_summary(source),
    }
    return url, diagnostic


def stream_summary(source):
    summaries = []
    for stream in source.get("MediaStreams", []):
        kind = stream.get("Type")
        if kind not in {"Video", "Audio"}:
            continue
        codec = lower(stream.get("Codec"))
        allowed = VIDEO_CODECS if kind == "Video" else AUDIO_CODECS
        summary = {"Type": kind, "Codec": codec if codec in allowed else "unlisted"}
        fields = ("Width", "Height", "BitDepth") if kind == "Video" else ("Channels",)
        for field in fields:
            if positive_number(stream.get(field)):
                summary[field] = stream[field]
        summaries.append(summary)
    return summaries
