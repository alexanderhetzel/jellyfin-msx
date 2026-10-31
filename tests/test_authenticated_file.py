"""Candidate tests use only MockTransport; no /File server bytes are fetched."""

import asyncio
import copy
import json
from dataclasses import replace
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from conftest import MOVIE, SOURCE, TOKEN, USER, media_source

from jellyfin_msx import original_file
from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.state import State


def candidate_settings(**overrides):
    return Settings(
        "https://portal.test",
        "https://fixture.test/jellyfin",
        original_delivery="authenticated-file-candidate",
        original_server_contract="stock-static-private-origin-v1",
        original_server_version="12.4.0",
        **overrides,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"original_server_contract": None},
        {"original_server_contract": "trusted"},
        {"original_server_version": "12.5.0"},
        {"original_server_version": None},
        {"allow_transcoding": True},
        {"public_url": "http://portal.test", "allow_http": True},
        {"public_url": "https://raw.githack.com"},
        {"public_url": "https://raw.githack.com."},
        {"original_delivery": "auto"},
    ],
)
def test_candidate_requires_explicit_operator_contract_and_known_configuration(change):
    with pytest.raises(ValueError):
        replace(candidate_settings(), **change)


def test_candidate_is_default_off_and_environment_does_not_infer_contract(monkeypatch):
    for key in (
        "MSX_ORIGINAL_DELIVERY",
        "MSX_ORIGINAL_SERVER_CONTRACT",
        "MSX_ORIGINAL_SERVER_VERSION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MSX_PUBLIC_URL", "https://portal.test")
    monkeypatch.setenv("JELLYFIN_URL", "https://fixture.test/jellyfin")
    assert Settings.from_env().original_delivery == "legacy"
    monkeypatch.setenv("MSX_ORIGINAL_DELIVERY", "authenticated-file-candidate")
    with pytest.raises(ValueError):
        Settings.from_env()


def fixture(hook=None, **settings_changes):
    settings = candidate_settings(**settings_changes)
    now = [1000.0]
    state = State(settings, clock=lambda: now[0])
    secret, device = state.pair()
    state.complete(device, USER, TOKEN)
    source = media_source()
    source.update(
        Id=SOURCE,
        Path="/synthetic/selected-cut.mp4",
        Protocol="File",
        Type="Default",
        VideoType="VideoFile",
        Size=10000,
        RunTimeTicks=300000000,
        IsRemote=False,
        RequiresOpening=False,
    )
    source["MediaStreams"] = [s for s in source["MediaStreams"] if s["Type"] in {"Video", "Audio"}]
    version = {
        "Id": SOURCE,
        "Type": "Movie",
        "PlayAccess": "Full",
        "LocationType": "FileSystem",
        "VideoType": "VideoFile",
        "Path": source["Path"],
        "Container": "mp4",
        "Size": 10000,
        "RunTimeTicks": 300000000,
        "MediaSources": [copy.deepcopy(source)],
    }
    parent = copy.deepcopy(version)
    parent.update(
        Id=MOVIE, Path="/synthetic/primary-cut.mp4", UserData={"PlaybackPositionTicks": 80000000}
    )
    p = SimpleNamespace(
        settings=settings,
        state=state,
        secret=secret,
        device=device,
        now=now,
        requests=[],
        counts={},
    )

    async def upstream(request):
        path = request.url.path.removeprefix("/jellyfin")
        p.requests.append(request)
        if path == "/System/Info/Public":
            kind, data = "version-info", {"Version": "12.4.0"}
        elif path == f"/Users/{USER}/Items/{MOVIE}":
            kind, data = "parent", copy.deepcopy(parent)
        elif path == f"/Users/{USER}/Items/{SOURCE}":
            kind, data = "version", copy.deepcopy(version)
        elif path == f"/Items/{MOVIE}/PlaybackInfo":
            body = json.loads(request.content)
            assert body["MediaSourceId"] == SOURCE
            assert body["EnableTranscoding"] is False and body["EnableDirectStream"] is False
            assert body["SubtitleStreamIndex"] == -1
            kind, data = (
                "negotiation",
                {"MediaSources": [copy.deepcopy(source)], "PlaySessionId": "fixture-session"},
            )
        elif path.startswith("/Sessions/Playing"):
            kind, data = "report", {}
        elif path == "/Sessions/Logout":
            return httpx.Response(204)
        else:
            raise AssertionError("Unexpected upstream endpoint; media must not be fetched")
        p.counts[kind] = p.counts.get(kind, 0) + 1
        if hook:
            status = await hook(p, kind, data)
            if status:
                return httpx.Response(status)
        return httpx.Response(
            204 if kind == "report" else 200, json=None if kind == "report" else data
        )

    p.app = create_app(settings, state=state, transport=httpx.MockTransport(upstream))
    return p


async def start(client, p, **changes):
    return await client.post(
        "/api/playback/start",
        headers={"Authorization": "Bearer " + p.secret},
        json={"item_id": MOVIE, "media_source_id": SOURCE, **changes},
    )


def run(hook=None, **changes):
    async def case():
        p = fixture(hook)
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            return p, await start(client, p, **changes)

    return asyncio.run(case())


@pytest.mark.parametrize("resume,position", [(False, 0), (True, 8)])
def test_exact_selected_version_file_url_preserves_report_resume_identity(resume, position):
    p, response = run(resume=resume)
    assert response.status_code == 200
    result = response.json()
    target = urlsplit(result["url"])
    assert target.scheme == "https" and target.netloc == "fixture.test"
    assert target.path == f"/jellyfin/Items/{SOURCE}/File"
    assert list(parse_qs(target.query)) == ["ApiKey"]
    assert result["start_position"] == position
    grant = next(iter(p.app.state.lifecycle.grants.values()))
    assert grant.item_id == MOVIE and grant.source_id == SOURCE
    assert grant.play_session_id == "fixture-session"
    assert p.counts == {"parent": 2, "version-info": 1, "version": 2, "negotiation": 1}


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-cut",
        "changed-version",
        "permission",
        "unknown-version",
        "remote",
        "oversized",
        "subtitle",
        "missing-membership",
    ],
)
def test_candidate_rejects_changed_or_unsupported_evidence_without_fallback(fault):
    async def hook(p, kind, data):
        if fault == "wrong-cut" and kind == "version":
            data["Path"] = "/synthetic/wrong-cut.mp4"
        if fault == "changed-version" and kind == "version" and p.counts[kind] == 2:
            data["Size"] = 1
        if fault == "permission" and kind == "parent":
            data["PlayAccess"] = "None"
        if fault == "unknown-version" and kind == "version-info":
            data["Version"] = "12.5.0"
        if kind == "parent":
            source = data["MediaSources"][0]
            if fault == "remote":
                source["Protocol"] = "Http"
            if fault == "oversized":
                source["MediaStreams"][0]["Width"] = 3840
            if fault == "subtitle":
                source["MediaStreams"].append({"Type": "Subtitle", "Codec": "mov_text"})
            if fault == "missing-membership" and p.counts[kind] == 2:
                data["MediaSources"] = []

    p, response = run(hook)
    assert response.status_code in (401, 403, 409, 502)
    assert "url" not in response.json()
    assert not p.app.state.lifecycle.grants


@pytest.mark.parametrize("changes", [{"force": True}, {"subtitle": 2}])
def test_candidate_never_falls_back_to_conversion(changes):
    p, response = run(**changes)
    assert response.status_code == 409
    assert not p.requests


@pytest.mark.parametrize("field", ["OpenToken", "LiveStreamId", "RequiredHttpHeaders"])
@pytest.mark.parametrize("value", [0, False, [], ""])
def test_malformed_falsy_source_requirements_are_rejected(field, value):
    async def hook(p, kind, data):
        if kind == "parent":
            data["MediaSources"][0][field] = value

    p, response = run(hook)
    assert response.status_code == 409
    assert not p.app.state.lifecycle.grants
    assert "negotiation" not in p.counts


def test_initial_ambiguous_membership_cannot_be_repaired_by_later_response():
    async def hook(p, kind, data):
        if kind == "parent" and p.counts[kind] == 1:
            data["MediaSources"].append(copy.deepcopy(data["MediaSources"][0]))

    p, response = run(hook)
    assert response.status_code == 409
    assert "version-info" not in p.counts
    assert not p.app.state.lifecycle.grants


def test_ambiguous_negotiated_membership_denies_instead_of_choosing_first():
    async def hook(p, kind, data):
        if kind == "negotiation":
            other = copy.deepcopy(data["MediaSources"][0])
            other["Path"] = "/synthetic/contradictory-cut.mp4"
            data["MediaSources"].append(other)

    p, response = run(hook)
    assert response.status_code == 409
    assert not p.app.state.lifecycle.grants


@pytest.mark.parametrize("value", [[], {}])
def test_malformed_item_type_denies_with_fixed_client_error(value):
    async def hook(p, kind, data):
        if kind == "parent":
            data["Type"] = value

    p, response = run(hook)
    assert response.status_code == 400
    assert not p.app.state.lifecycle.grants


@pytest.mark.parametrize("source", [None, [], {"Id": SOURCE, "MediaStreams": None}])
def test_recovery_admission_fails_closed_on_malformed_source(source):
    assert original_file.admitted(source, 20_000_000) is False


def test_enabled_mode_blocks_legacy_and_subtitle_bypasses_and_hides_their_actions():
    async def case():
        p = fixture(enable_subtitle_resources=True)
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            root = f"/msx/device/{p.secret}"
            response = await client.get(
                root + "/play.json", params={"item_id": MOVIE, "media_source_id": SOURCE}
            )
            assert response.json()["response"]["status"] == 409
            assert not p.requests
            for path in (
                "/subtitle-bridge.html",
                "/subtitle-bridge.js",
                f"/api/device/{p.secret}/subtitles/{MOVIE}/{SOURCE}",
                f"/api/device/{p.secret}/subtitles/{MOVIE}/{SOURCE}/7.vtt",
            ):
                assert (await client.get(path)).status_code == 409
            detail = (await client.get(root + "/detail.json", params={"item_id": MOVIE})).json()
            actions = [entry["action"] for entry in detail["items"]]
            assert not any(
                "play.json" in action or "subtitle-bridge" in action for action in actions
            )

    asyncio.run(case())


@pytest.mark.parametrize("change", ["logout", "expiry", "token", "generation"])
def test_authority_loss_during_source_await_never_issues_media_or_generation(change):
    async def case():
        entered, release = asyncio.Event(), asyncio.Event()

        async def hook(p, kind, data):
            if kind == "version" and p.counts[kind] == 2:
                entered.set()
                await release.wait()

        p = fixture(hook)
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            task = asyncio.create_task(start(client, p))
            await asyncio.wait_for(entered.wait(), 1)
            if change == "logout":
                assert (await client.get(f"/msx/device/{p.secret}/logout.json")).status_code == 200
            elif change == "expiry":
                p.now[0] = p.device.expires + 1
            elif change == "token":
                p.device.token = "changed-in-memory"
            else:
                p.state.authorizations = SimpleNamespace(validate=lambda _: None)
                p.device.authorization_generation = 1
            release.set()
            response = await task
            assert response.status_code == 401
            assert "url" not in response.json()
            assert not p.app.state.lifecycle.grants

    asyncio.run(case())


@pytest.mark.parametrize("stage", ["source", "lock"])
def test_candidate_has_bounded_source_and_whole_operation_deadlines(monkeypatch, stage):
    async def hook(p, kind, data):
        if stage == "source" and kind == "version-info":
            await asyncio.Event().wait()

    async def case():
        p = fixture(hook)
        if stage == "source":
            monkeypatch.setattr(original_file, "SOURCE_SECONDS", 0.02)
        else:
            monkeypatch.setattr(original_file, "OPERATION_SECONDS", 0.02)
            lock = asyncio.Lock()
            await lock.acquire()
            p.app.state.lifecycle.locks[p.secret] = lock
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            response = await start(client, p)
            assert response.status_code == 504
            assert not p.app.state.lifecycle.grants

    asyncio.run(case())


async def observe_start(client, p, result):
    response = await client.post(
        "/api/playback/observations",
        headers={"Authorization": "Bearer " + result["grant"]},
        json={
            "version": 1,
            "playback_id": result["playback_id"],
            "observations": [
                {
                    "seq": i,
                    "ms": i * 2000,
                    "kind": "snapshot",
                    "name": "video",
                    "data": {"state": 2, "position": pos, "duration": 30},
                }
                for i, pos in ((1, 1), (2, 3))
            ],
        },
    )
    assert response.status_code == 200


@pytest.mark.parametrize("change", ["logout", "expiry", "token", "generation"])
def test_authority_is_rechecked_after_awaited_old_stop(change):
    async def case():
        entered, release = asyncio.Event(), asyncio.Event()

        async def hook(p, kind, data):
            if kind == "report" and p.requests[-1].url.path.endswith("/Stopped"):
                entered.set()
                await release.wait()

        p = fixture(hook)
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            first = (await start(client, p)).json()
            await observe_start(client, p, first)
            task = asyncio.create_task(start(client, p))
            await asyncio.wait_for(entered.wait(), 1)
            if change == "logout":
                await client.get(f"/msx/device/{p.secret}/logout.json")
            elif change == "expiry":
                p.now[0] = p.device.expires + 1
            elif change == "token":
                p.device.token = "changed-in-memory"
            else:
                p.state.authorizations = SimpleNamespace(validate=lambda _: None)
                p.device.authorization_generation = 1
            release.set()
            response = await task
            assert response.status_code == 401
            assert "url" not in response.json()
            assert len(p.app.state.lifecycle.grants) == 1

    asyncio.run(case())


def test_old_stop_timeout_preserves_ack_fence_and_bounded_retry(monkeypatch):
    async def case():
        block = [True]

        async def hook(p, kind, data):
            if kind == "report" and p.requests[-1].url.path.endswith("/Stopped") and block[0]:
                await asyncio.Event().wait()

        p = fixture(hook)
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            first = (await start(client, p)).json()
            await observe_start(client, p, first)
            old = p.app.state.lifecycle.get(first["grant"])
            assert old.started and old.start_delivered
            monkeypatch.setattr(original_file, "OPERATION_SECONDS", 0.05)
            response = await start(client, p)
            assert response.status_code == 504
            assert not old.terminal_delivered and old.pending
            assert len(p.app.state.lifecycle.grants) == 1
            block[0] = False
            p.now[0] += 4
            monkeypatch.setattr(original_file, "OPERATION_SECONDS", 15)
            assert (await start(client, p)).status_code == 200
            assert old.terminal_delivered

    asyncio.run(case())


def test_unpublished_generation_is_removed_if_authority_changes_on_return():
    async def case():
        p = fixture()
        original = p.app.state.lifecycle.issue

        async def issue(*args, **kwargs):
            grant = await original(*args, **kwargs)
            p.device.token = "changed-in-memory"
            return grant

        p.app.state.lifecycle.issue = issue
        async with (
            p.app.router.lifespan_context(p.app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(p.app), base_url=p.settings.public_url
            ) as client,
        ):
            response = await start(client, p)
            assert response.status_code == 401
            assert not p.app.state.lifecycle.grants and not p.app.state.lifecycle.active

    asyncio.run(case())
