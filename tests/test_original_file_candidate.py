"""Stock static-library metadata counterexamples, not /File server observations."""

import asyncio
import copy
import json
import time

import httpx
import pytest
from conftest import media_source

from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.jellyfin import Jellyfin
from jellyfin_msx.state import Device
from tools.original_file_candidate import CandidateRejected, assess_file_snapshot

PARENT, VERSION, USER = "1" * 32, "3" * 32, "4" * 32


def snapshots():
    source = media_source()
    source.update(
        Id=VERSION,
        Protocol="File",
        Type="Default",
        VideoType="VideoFile",
        Path="/synthetic/selected-cut.mp4",
        Size=10000,
        RunTimeTicks=300000000,
        IsRemote=False,
        RequiresOpening=False,
    )
    version = {
        "Id": VERSION,
        "Type": "Movie",
        "LocationType": "FileSystem",
        "PlayAccess": "Full",
        "VideoType": "VideoFile",
        "Path": source["Path"],
        "Container": "mp4",
        "Size": source["Size"],
        "RunTimeTicks": source["RunTimeTicks"],
        "MediaSources": [copy.deepcopy(source)],
    }
    parent = copy.deepcopy(version)
    parent.update(Id=PARENT, Path="/synthetic/primary-cut.mp4")
    return parent, version, source


def run_case(mutate=None):
    parent, version, source = snapshots()
    requests = []
    counts = {"parent": 0, "version": 0}

    def handle(request):
        requests.append(request)
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["MediaSourceId"] == VERSION
            assert body["EnableTranscoding"] is False
            assert body["EnableDirectStream"] is False
            assert body["SubtitleStreamIndex"] == -1
            kind, value = "negotiation", {"MediaSources": [copy.deepcopy(source)]}
        else:
            kind = "parent" if request.url.path.endswith(PARENT) else "version"
            counts[kind] += 1
            value = copy.deepcopy(parent if kind == "parent" else version)
        if mutate:
            status = mutate(kind, counts, value)
            if status:
                return httpx.Response(status)
        return httpx.Response(200, json=value)

    async def check():
        settings = Settings(public_url="https://portal.test", jellyfin_url="https://fixture.test")
        jf = Jellyfin(settings, transport=httpx.MockTransport(handle))
        device = Device(time.monotonic() + 60, user_id=USER)
        try:
            return await assess_file_snapshot(jf, device, PARENT, VERSION)
        finally:
            await jf.client.aclose()

    result = asyncio.run(check())
    assert len(requests) == 5
    # No media, /File or /Download request and no unprotected-route fallback.
    assert all(r.url.path.endswith((PARENT, VERSION, "PlaybackInfo")) for r in requests)
    return result


def test_static_alternate_snapshot_keeps_exact_version_not_primary():
    candidate = run_case()
    assert candidate.parent_id == PARENT
    assert candidate.version_id == VERSION != PARENT
    assert candidate.container == "mp4"


@pytest.mark.parametrize(
    "field,value", [("Path", "/synthetic/wrong-cut.mp4"), ("Size", 999), ("RunTimeTicks", 999)]
)
def test_matching_guid_is_not_matching_version(field, value):
    def mutate(kind, counts, data):
        if kind == "version":
            data[field] = value

    with pytest.raises(CandidateRejected):
        run_case(mutate)


@pytest.mark.parametrize("kind", ["parent", "version"])
@pytest.mark.parametrize("access", [None, "None"])
def test_missing_or_denied_playback_access_rejects(kind, access):
    def mutate(observed, counts, data):
        if observed == kind:
            data["PlayAccess"] = access

    with pytest.raises(CandidateRejected, match="playback permission"):
        run_case(mutate)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Protocol", "Http"),
        ("Type", "Placeholder"),
        ("IsRemote", True),
        ("RequiresOpening", True),
        ("LiveStreamId", "present"),
        ("VideoType", "Dvd"),
    ],
)
def test_nonstatic_source_is_not_promoted_to_item_identity(field, value):
    def mutate(kind, counts, data):
        if kind == "parent":
            data["MediaSources"][0][field] = value

    with pytest.raises(CandidateRejected):
        run_case(mutate)


def test_membership_removed_after_negotiation_rejects():
    def mutate(kind, counts, data):
        if kind == "parent" and counts[kind] == 2:
            data["MediaSources"] = []

    with pytest.raises(CandidateRejected, match="membership"):
        run_case(mutate)


def test_playbackinfo_denial_has_no_original_route_fallback():
    def mutate(kind, counts, data):
        if kind == "negotiation":
            data["MediaSources"][0]["SupportsDirectPlay"] = False

    with pytest.raises(CandidateRejected, match="Direct Play denied"):
        run_case(mutate)


@pytest.mark.parametrize("status", [401, 403])
def test_revoked_or_denied_selected_version_cannot_yield_candidate(status):
    def mutate(kind, counts, data):
        if kind == "version" and counts[kind] == 2:
            return status

    with pytest.raises(PortalError) as denied:
        run_case(mutate)
    assert denied.value.status == 401  # Client-normalized denial, not raw status evidence.


@pytest.mark.parametrize("field", ["Size", "RunTimeTicks"])
def test_boolean_extent_is_not_version_identity(field):
    def mutate(kind, counts, data):
        if kind == "parent":
            data["MediaSources"][0][field] = 1
        if kind == "version":
            data[field] = True
            data["MediaSources"][0][field] = 1

    with pytest.raises(CandidateRejected, match="version extent"):
        run_case(mutate)


@pytest.mark.parametrize("parts", [True, 2, "1"])
def test_stacked_or_malformed_parts_rejected(parts):
    def mutate(kind, counts, data):
        if kind == "version":
            data["PartCount"] = parts

    with pytest.raises(CandidateRejected, match="parts excluded"):
        run_case(mutate)


@pytest.mark.parametrize(
    "path", ["https://remote.test/media", "//server/share", "/synthetic/../other"]
)
def test_contradictory_file_protocol_path_rejected(path):
    def mutate(kind, counts, data):
        if kind == "parent":
            data["MediaSources"][0]["Path"] = path

    with pytest.raises(CandidateRejected, match="local Linux path"):
        run_case(mutate)


def test_explicit_channel_type_rejected_even_without_channel_id():
    def mutate(kind, counts, data):
        if kind == "parent":
            data["SourceType"] = "Channel"

    with pytest.raises(CandidateRejected, match="provenance"):
        run_case(mutate)


@pytest.mark.parametrize(
    "field,value",
    [
        ("ChannelId", False),
        ("ChannelId", 0),
        ("ChannelId", []),
        ("SourceType", False),
        ("SourceType", "Library"),
    ],
)
def test_malformed_or_nonstock_provenance_is_not_permission(field, value):
    def mutate(kind, counts, data):
        if kind == "parent":
            data[field] = value

    with pytest.raises(CandidateRejected, match="provenance"):
        run_case(mutate)
