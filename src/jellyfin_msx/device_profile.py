"""Documented candidates for one model; no physical MSX pass is implied.

Evidence, scope and unresolved limits: docs/philips-32phs6605-12.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateProfile:
    """Trusted source-defined candidates, never a client-supplied permission set.

    Application admission limits and operator bitrate budgets live outside this
    description. A profile is not proof of any physical playback combination.
    Production remains fixed to PHILIPS; synthetic instances are test seams only.
    """

    name: str
    model: str
    basis: str
    evidence_document: str
    containers: tuple[str, ...]
    video_codecs: tuple[str, ...]
    audio_codecs: tuple[str, ...]
    conditional_audio: frozenset[str]
    warnings: tuple[str, ...]
    preferred_size: tuple[int, int]
    preferred_video_codec: str = "h264"


MODEL = "Philips 32PHS6605/12"
PROFILE_NAME = "philips-32phs6605-12-hd-policy-v2"
PROFILE_BASIS = "model_documentation_hd_admission_policy_msx_unverified"

# Client admission policy: documentation gives no basis to admit UHD. These are
# deliberately NOT presented as proven silicon/MSX decoder maxima.
MAX_VIDEO_WIDTH = 1920
MAX_VIDEO_HEIGHT = 1080

# Model multimedia list plus qualified STA streaming containers. These sets do
# not certify every possible mux/codec combination in the installed MSX player.
CONTAINERS = ("mp4", "mkv", "avi", "ts", "mpegts")
VIDEO_CODECS = ("h264", "hevc", "vp9", "mpeg1video", "mpeg2video", "mpeg4", "vc1", "wmv3")
AUDIO_CODECS = (
    "aac",
    "mp3",
    "wmav2",
    "wmapro",
    "ac3",
    "eac3",
    "dts",
)
CONDITIONAL_AUDIO = frozenset({"ac3", "eac3", "dts"})

PHILIPS = CandidateProfile(
    name=PROFILE_NAME,
    model=MODEL,
    basis=PROFILE_BASIS,
    evidence_document="docs/philips-32phs6605-12.md",
    containers=CONTAINERS,
    video_codecs=VIDEO_CODECS,
    audio_codecs=AUDIO_CODECS,
    conditional_audio=CONDITIONAL_AUDIO,
    warnings=(
        "MSX playback on this Philips model is not yet verified",
        "Client policy permits up to 1920x1080; 4K playback/downscaling is not supported",
        "Exact container/codec combinations and decoder limits remain unverified",
    ),
    preferred_size=(1366, 768),
)


def evidence_warnings(source, *, candidate_profile: CandidateProfile = PHILIPS):
    warnings = list(candidate_profile.warnings)
    if any(
        stream.get("Type") == "Audio"
        and stream.get("Codec", "").lower() in candidate_profile.conditional_audio
        for stream in source.get("MediaStreams", [])
        if isinstance(stream.get("Codec"), str)
    ):
        warnings.append(
            "Dolby/DTS documentation is conditional; verify the actual audio output path"
        )
    return warnings
