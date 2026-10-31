"""In-process authored File model; never real Jellyfin/native acceptance."""

from dataclasses import replace
from urllib.parse import parse_qs, urlsplit, urlunsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools.lab import ROOT, build_lab
from tools.synthetic_check import pair
from tools.synthetic_lab import MOVIE, SOURCE, attach_fixture_media, build_synthetic_lab
from tools.synthetic_resume import EPISODE, CandidateResumeJellyfin

ORIGIN = "https://localhost:18091"
MEDIA = (ROOT / "tests/fixtures/msx-public/synthetic.mp4").read_bytes()


@pytest.fixture(autouse=True)
def no_real_transport(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Synthetic File contract attempted real HTTP transport")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid)


def settings():
    return Settings(
        ORIGIN,
        ORIGIN + "/jellyfin",
        original_delivery="authenticated-file-candidate",
        original_server_contract="stock-static-private-origin-v1",
        original_server_version="12.4.0",
    )


def paired(client):
    return pair(client, ORIGIN).split("/device/", 1)[1].split("/", 1)[0]


def start(client, secret, item=MOVIE):
    response = client.post(
        "/api/playback/start",
        headers={"Authorization": "Bearer " + secret},
        json={"item_id": item, "media_source_id": SOURCE, "resume": True},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("item", [MOVIE, EPISODE])
def test_paired_candidate_exact_selected_file_bytes_resume_and_observed_lifecycle(item):
    app, _, fixture = build_synthetic_lab(settings(), media=MEDIA)
    with TestClient(app, base_url=ORIGIN) as client:
        secret = paired(client)
        result = start(client, secret, item)
        target = urlsplit(result["url"])
        assert target.path == f"/jellyfin/Items/{SOURCE}/File"
        assert list(parse_qs(target.query)) == ["ApiKey"]
        assert result["start_position"] == fixture.start_position == 8
        full = client.get(result["url"])
        assert full.status_code == 200 and full.content == MEDIA
        assert full.headers["content-type"] == "video/mp4"
        assert int(full.headers["content-length"]) == len(MEDIA)
        assert full.headers["accept-ranges"] == "bytes"
        wrong = client.get(result["url"].replace(SOURCE, MOVIE))
        assert wrong.status_code == 200 and wrong.content != MEDIA
        assert wrong.content == fixture.files[MOVIE]
        assert not fixture.reports  # URL issuance and byte GETs are not observed Start.

        grant = app.state.lifecycle.get(result["grant"])
        assert grant.item_id == item and grant.source_id == SOURCE and grant.play_session_id
        observations = [
            {
                "seq": n,
                "ms": n * 2000,
                "kind": "snapshot",
                "name": "video",
                "data": {"state": 2, "position": position, "duration": 30},
            }
            for n, position in ((1, 8), (2, 10))
        ]
        response = client.post(
            "/api/playback/observations",
            headers={"Authorization": "Bearer " + result["grant"]},
            json={
                "version": 1,
                "playback_id": result["playback_id"],
                "observations": observations,
            },
        )
        assert response.status_code == 200
        assert fixture.summary()["start"] == 1 and fixture.summary()["position_seconds"] == 10
        token = next(iter(fixture.tokens))
        assert fixture.progress(token, item)["PlaybackPositionTicks"] == 100_000_000
        assert (token, SOURCE) not in fixture.saved
        response = client.post(
            "/api/playback/observations",
            headers={"Authorization": "Bearer " + result["grant"]},
            json={
                "version": 1,
                "playback_id": result["playback_id"],
                "observations": [
                    {
                        "seq": n,
                        "ms": n * 2000,
                        "kind": kind,
                        "name": name,
                        "data": data,
                    }
                    for n, kind, name, data in (
                        (3, "event", "video:pause", {"position": 10, "state": 2}),
                        (4, "snapshot", "video", {"position": 10, "state": 3, "duration": 30}),
                        (5, "event", "video:stop", {"position": 0}),
                        (6, "snapshot", "video", {"position": 0, "state": 0, "duration": 30}),
                    )
                ],
            },
        )
        assert response.status_code == 200
        assert fixture.summary()["progress"] == fixture.summary()["stop"] == 1
        assert fixture.summary()["position_seconds"] == 10 and not fixture.active
        again = start(client, secret, item)
        assert again["start_position"] == fixture.start_position == 10
        assert fixture.summary()["start"] == 1  # Resume intent does not manufacture Start.
        report = client.get("/__lab/report").text + client.get("/__synthetic/report").text
        assert not any(value in report for value in (secret, token, result["grant"], result["url"]))


@pytest.mark.parametrize(
    "selection,start_byte,end_byte",
    [
        ("bytes=0-99", 0, 99),
        ("bytes=100-", 100, len(MEDIA) - 1),
        ("bytes=-5", len(MEDIA) - 5, len(MEDIA) - 1),
    ],
)
def test_file_range_and_head_preserve_selected_snapshot(selection, start_byte, end_byte):
    app, _, fixture = build_synthetic_lab(settings(), media=MEDIA)
    with TestClient(app, base_url=ORIGIN) as client:
        result = start(client, paired(client))
        for method in ("GET", "HEAD"):
            response = client.request(method, result["url"], headers={"Range": selection})
            assert response.status_code == 206
            expected_range = f"bytes {start_byte}-{end_byte}/{len(MEDIA)}"
            assert response.headers["content-range"] == expected_range
            assert int(response.headers["content-length"]) == end_byte - start_byte + 1
            expected = MEDIA[start_byte : end_byte + 1] if method == "GET" else b""
            assert response.content == expected
        head = client.head(result["url"])
        assert head.status_code == 200 and head.content == b""
        assert int(head.headers["content-length"]) == len(MEDIA)
        assert not fixture.reports


@pytest.mark.parametrize(
    "selection", ["bytes=999999999999-", "bytes=4-2", "bytes=", "bytes=0-1,4-5"]
)
def test_invalid_range_denies_without_media_or_lifecycle(selection):
    app, _, fixture = build_synthetic_lab(settings(), media=MEDIA)
    with TestClient(app, base_url=ORIGIN) as client:
        result = start(client, paired(client))
        response = client.get(result["url"], headers={"Range": selection})
        assert response.status_code == 416 and response.content == b""
        assert response.headers["content-range"] == f"bytes */{len(MEDIA)}"
        assert not fixture.media_requests and not fixture.reports


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_authored_token_denial_and_independent_login_are_not_jellyfin_revocation_proof(method):
    app, _, fixture = build_synthetic_lab(settings(), media=MEDIA)
    with TestClient(app, base_url=ORIGIN) as client:
        first_secret = paired(client)
        first = start(client, first_secret)
        second_secret = paired(client)
        second = start(client, second_secret)
        target = urlsplit(first["url"])
        api_key = parse_qs(target.query)["ApiKey"][0]
        for query in (
            "",
            "ApiKey=invalid-synthetic-token",
            f"ApiKey={api_key}&ApiKey={api_key}",
            f"api_key={api_key}",
            f"ApiKey={api_key}&MediaSourceId={SOURCE}",
        ):
            rejected = urlunsplit(target._replace(query=query))
            response = client.request(method, rejected, headers={"Range": "bytes=0-99"})
            assert response.status_code == 401 and response.content == b""
        assert client.get(f"/msx/device/{first_secret}/logout.json").status_code == 200
        response = client.request(method, first["url"], headers={"Range": "bytes=0-99"})
        assert response.status_code == 401 and response.content == b""
        assert client.get(second["url"]).content == MEDIA
        assert len(fixture.tokens) == 1
        assert client.get(first["url"].replace(SOURCE, "f" * 32)).status_code == 404
        legacy = first["url"].split("/Items/", 1)[0] + f"/Videos/{MOVIE}/stream.mp4"
        assert client.get(legacy).status_code == 404


@pytest.mark.parametrize("media", [None, b"", bytearray(b"mutable"), b"x" * (32 * 1024 * 1024 + 1)])
def test_candidate_builder_requires_explicit_bounded_immutable_bytes(media):
    with pytest.raises(ValueError, match="immutable bytes"):
        build_synthetic_lab(settings(), media=media)


def test_builder_rejects_implicit_path_and_legacy_faults_and_does_not_echo_release():
    with pytest.raises(ValueError, match="immutable bytes"):
        build_synthetic_lab(settings())
    with pytest.raises(ValueError, match="immutable bytes"):
        build_synthetic_lab(settings(), media=ROOT / "tests/fixtures/msx-public/synthetic.mp4")
    with pytest.raises(ValueError, match="legacy faults"):
        build_synthetic_lab(settings(), media=MEDIA, fault="json")
    app, _, fixture = build_synthetic_lab(
        replace(settings(), original_server_version="12.3.0"), media=MEDIA
    )
    with TestClient(app, base_url=ORIGIN) as client:
        secret = paired(client)
        response = client.post(
            "/api/playback/start",
            headers={"Authorization": "Bearer " + secret},
            json={"item_id": MOVIE, "media_source_id": SOURCE},
        )
        assert response.status_code == 409 and "url" not in response.json()
        assert not fixture.media_requests and not app.state.lifecycle.grants


def test_file_attachment_freezes_known_ids_bytes_and_metadata():
    fixture = CandidateResumeJellyfin(ORIGIN, MEDIA)
    source = fixture.file_source()
    source["Size"] = 1
    assert fixture.file_source()["Size"] == len(MEDIA)
    app, _ = build_lab(settings(), transport=httpx.MockTransport(fixture.handle))
    payloads = dict(fixture.files)
    attach_fixture_media(app, fixture, MEDIA, None, files=payloads)
    payloads[SOURCE] = b"changed caller mapping"
    payloads["f" * 32] = b"unadvertised"
    with TestClient(app, base_url=ORIGIN) as client:
        result = start(client, paired(client))
        assert client.get(result["url"]).content == MEDIA
        assert client.get(f"/jellyfin/Items/{'f' * 32}/File").status_code == 404
    with pytest.raises(TypeError):
        fixture.files[SOURCE] = b"mutation"
