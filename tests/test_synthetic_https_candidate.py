"""Source/mock containment checks; no candidate helper, listener or relay starts."""

import hashlib
import io
import json
import sys
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools import synthetic_https as https
from tools.synthetic_check import pair
from tools.synthetic_lab import MOVIE, SOURCE
from tools.synthetic_resume import CandidateResumeJellyfin, ResumeJellyfin

ORIGIN = "https://synthetic-test.trycloudflare.com"
MARKER = {"original_delivery": "authenticated-file-candidate"}
LEGACY_READY = {"mode": "public-synthetic", "configured": True}


def forbid(*args, **kwargs):
    raise AssertionError("Unexpected real transport, operator configuration or process")


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbid)
    monkeypatch.setattr(Settings, "from_env", forbid)
    monkeypatch.setattr(https.subprocess, "Popen", forbid)
    monkeypatch.setattr(https, "spawn", forbid)
    monkeypatch.setattr(https.uvicorn, "Server", forbid)


@pytest.mark.parametrize("candidate", [False, True])
def test_existing_resume_factory_constructs_only_trusted_fixture_mode(
    monkeypatch, tmp_path, candidate
):
    for key in (
        "JELLYFIN_URL",
        "MSX_ORIGINAL_DELIVERY",
        "MSX_ORIGINAL_SERVER_CONTRACT",
        "MSX_ORIGINAL_SERVER_VERSION",
        "MSX_AUTHORIZATION_KEY",
    ):
        monkeypatch.setenv(key, "operator-only")
    raw = https.CLIP.read_bytes()
    path = tmp_path / "sample.mp4"
    path.write_bytes(raw)
    monkeypatch.setattr(https, "CLIP", path)
    app, _, fixture = https.build_public_synthetic_lab(
        ORIGIN,
        allow_public_synthetic=True,
        scenario="resume",
        **({"authenticated_file_candidate": True} if candidate else {}),
    )
    assert type(fixture) is (CandidateResumeJellyfin if candidate else ResumeJellyfin)
    path.write_bytes(b"later path changes must not change the immutable snapshot")
    with TestClient(app, base_url=ORIGIN) as client:
        expected = {**LEGACY_READY, **(MARKER if candidate else {})}
        assert client.get("/__synthetic/ready").json() == expected
        secret = pair(client, ORIGIN).split("/device/", 1)[1].split("/", 1)[0]
        response = client.post(
            "/api/playback/start",
            headers={"Authorization": "Bearer " + secret},
            json={"item_id": MOVIE, "media_source_id": SOURCE, "resume": True},
        )
        assert response.status_code == 200
        result = response.json()
        expected_path = (
            f"/jellyfin/Items/{SOURCE}/File"
            if candidate
            else f"/jellyfin/Videos/{MOVIE}/stream.mp4"
        )
        assert urlsplit(result["url"]).path == expected_path
        assert result["start_position"] == 8
        assert client.get(result["url"]).content == raw
        partial = client.head(result["url"], headers={"Range": "bytes=0-99"})
        assert partial.status_code == 206 and not partial.content
        assert partial.headers["content-type"] == "video/mp4"
        assert partial.headers["content-range"] == f"bytes 0-99/{len(raw)}"
        assert client.get("/__synthetic/lifecycle").json()["start"] == 0
        report = client.get("/__lab/report").text + client.get("/__synthetic/report").text
        assert not any(value in report for value in (*fixture.tokens, secret, result["url"]))
        assert "operator-only" not in report
        assert client.get("/healthz", headers={"Host": "attacker.test"}).status_code == 400
    with pytest.raises(https.PreparationError, match="clip-checksum"):
        https.build_public_synthetic_lab(
            ORIGIN,
            allow_public_synthetic=True,
            scenario="resume",
            authenticated_file_candidate=candidate,
        )


@pytest.mark.parametrize("candidate", [None, 0, 1, "true"])
def test_nonboolean_option_rejects_before_factory_or_owned_side_effects(
    monkeypatch, tmp_path, candidate
):
    monkeypatch.setattr(https, "CLIP", SimpleNamespace(read_bytes=forbid))
    monkeypatch.setattr(https, "verify_binary", forbid)
    monkeypatch.setattr(https.socket, "socket", forbid)
    with pytest.raises(https.PreparationError, match="invalid-candidate-option"):
        https.build_public_synthetic_lab(
            ORIGIN,
            allow_public_synthetic=True,
            scenario="resume",
            authenticated_file_candidate=candidate,
        )
    with pytest.raises(https.PreparationError, match="invalid-candidate-option"):
        https.activate(tmp_path / "fake", scenario="resume", authenticated_file_candidate=candidate)
    with pytest.raises(https.PreparationError, match="invalid-candidate-option"):
        https.backend_helper(10, "resume", authenticated_file_candidate=candidate)


@pytest.mark.parametrize(
    "scenario", ["baseline", "failures", "navigation", "subtitles", "lifecycle", "recovery"]
)
def test_candidate_cannot_expand_existing_scenarios(monkeypatch, tmp_path, scenario):
    monkeypatch.setattr(https, "CLIP", SimpleNamespace(read_bytes=forbid))
    monkeypatch.setattr(https, "verify_binary", forbid)
    monkeypatch.setattr(https.socket, "socket", forbid)
    with pytest.raises(https.PreparationError, match="candidate-requires-resume"):
        https.build_public_synthetic_lab(
            ORIGIN,
            allow_public_synthetic=True,
            scenario=scenario,
            authenticated_file_candidate=True,
        )
    with pytest.raises(https.PreparationError, match="candidate-requires-resume"):
        https.activate(tmp_path / "fake", scenario=scenario, authenticated_file_candidate=True)
    with pytest.raises(https.PreparationError, match="candidate-requires-resume"):
        https.backend_helper(10, scenario, authenticated_file_candidate=True)


@pytest.mark.parametrize(
    "arguments,reason",
    [
        (["--check"], "candidate-requires-resume"),
        (["--scenario", "failures", "--check"], "candidate-requires-resume"),
        (["--scenario", "resume", "--stop"], "candidate-incompatible-mode"),
        (["--scenario", "resume", "--tunnel-helper"], "candidate-incompatible-mode"),
    ],
)
def test_cli_incompatible_mode_fails_before_reading_or_starting(
    monkeypatch, capsys, arguments, reason
):
    monkeypatch.setattr(
        sys, "argv", ["synthetic_https", *arguments, "--authenticated-file-candidate"]
    )
    monkeypatch.setattr(https, "verify_binary", forbid)
    monkeypatch.setattr(https, "backend_helper", forbid)
    monkeypatch.setattr(https, "activate", forbid)
    monkeypatch.setattr(https, "enter_kill_on_close_job", forbid)
    with pytest.raises(SystemExit) as error:
        https.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out) == {"status": "failed", "reason": reason}


def test_candidate_preflight_is_configuration_only(monkeypatch, tmp_path, capsys):
    binary = tmp_path / "fake"
    binary.write_bytes(b"fake pinned binary")
    monkeypatch.setattr(https, "BINARY_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "synthetic_https",
            "--check",
            "--scenario",
            "resume",
            "--authenticated-file-candidate",
            "--cloudflared",
            str(binary),
        ],
    )
    monkeypatch.setattr(https, "build_public_synthetic_lab", forbid)
    https.main()
    result = json.loads(capsys.readouterr().out)
    assert result["original_delivery"] == MARKER["original_delivery"]
    assert result["approval_required"] and result["tunnel_started"] is False
    assert result["maximum_seconds"] == 900 and result["scenario"] == "resume"


@pytest.mark.parametrize(
    "expected,actual", [(False, False), (True, True), (True, False), (False, True)]
)
def test_candidate_and_legacy_readiness_never_substitute(monkeypatch, expected, actual):
    options = []

    class Client:
        def __init__(self, **kwargs):
            options.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            assert url in (
                ORIGIN + "/__synthetic/ready",
                "http://127.0.0.1:18092/__synthetic/ready",
            )
            return httpx.Response(200, json={**LEGACY_READY, **(MARKER if actual else {})})

    monkeypatch.setattr(httpx, "Client", Client)
    assert https.ready_local(authenticated_file_candidate=expected) is (expected == actual)
    assert https.ready_public(ORIGIN, authenticated_file_candidate=expected) is (expected == actual)
    assert options == [
        {"trust_env": False, "follow_redirects": False, "timeout": 0.5},
        {"trust_env": False, "follow_redirects": False, "verify": True, "timeout": 2},
    ]


@pytest.mark.parametrize("propagated", [False, True])
def test_fake_supervisor_propagates_backend_only_and_lost_flag_cannot_publish_ready(
    monkeypatch, tmp_path, capsys, propagated
):
    assert https.MAX_SECONDS == 900 and https.STARTUP_SECONDS == 180
    monkeypatch.setattr(
        https.threading, "Thread", lambda **kwargs: SimpleNamespace(start=lambda: None)
    )
    clock = [0]
    monkeypatch.setattr(
        https,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0], sleep=lambda _: clock.__setitem__(0, clock[0] + 10)
        ),
    )
    monkeypatch.setattr(https, "CONTROL", tmp_path / "control")
    monkeypatch.setattr(https, "verify_binary", lambda _: None)
    processes, arguments, stopped = [], [], []

    def spawn(args, directory, *, output=False):
        arguments.append(args)
        process = SimpleNamespace(
            pid=len(processes) + 1,
            stdout=io.BytesIO(b"RESERVED\n"),
            stdin=io.BytesIO(),
            poll=lambda: None,
        )
        processes.append(process)
        return process

    monkeypatch.setattr(https, "spawn", spawn)
    monkeypatch.setattr(https, "stop_process", lambda process: stopped.append(process))
    monkeypatch.setattr(https, "drain_origins", lambda *_: None)
    allocations = []

    def allocated(process, values, deadline, stop_file):
        allocations.append(deadline)
        return "RESERVED" if len(allocations) == 1 else ORIGIN

    monkeypatch.setattr(https, "await_value", allocated)
    monkeypatch.setattr(
        https,
        "ready_local",
        lambda **kwargs: kwargs == {"authenticated_file_candidate": True} and propagated,
    )
    monkeypatch.setattr(
        https,
        "ready_public",
        lambda origin, **kwargs: (
            origin == ORIGIN and kwargs == {"authenticated_file_candidate": True} and propagated
        ),
    )
    if propagated:
        https.activate(
            tmp_path / "fake", seconds=60, scenario="resume", authenticated_file_candidate=True
        )
    else:
        with pytest.raises(https.PreparationError, match="relay-readiness-timeout"):
            https.activate(
                tmp_path / "fake", seconds=60, scenario="resume", authenticated_file_candidate=True
            )
    assert "--authenticated-file-candidate" in arguments[0]
    assert "--backend-helper" in arguments[0] and "resume" in arguments[0]
    assert "--authenticated-file-candidate" not in arguments[1]
    assert processes[0].stdin.getvalue() == (ORIGIN + "\n").encode("ascii")
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    ready = [event for event in events if event["status"] == "ready"]
    assert bool(ready) is propagated
    if propagated:
        assert ready[0]["original_delivery"] == MARKER["original_delivery"]
    assert clock[0] == 60 and allocations == [60, 60]
    assert stopped == list(reversed(processes)) and not https.CONTROL.exists()


@pytest.mark.parametrize("candidate", [False, True])
@pytest.mark.parametrize("mode", ["--backend-helper", "--activate-public-synthetic"])
def test_cli_forwards_explicit_option_without_inference(monkeypatch, capsys, candidate, mode):
    arguments = ["synthetic_https", mode, "--scenario", "resume"]
    if candidate:
        arguments.append("--authenticated-file-candidate")
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(https, "os", SimpleNamespace(name="nt"))
    calls = []
    monkeypatch.setattr(https, "backend_helper", lambda *args, **kw: calls.append((args, kw)))
    monkeypatch.setattr(https, "activate", lambda *args, **kw: calls.append((args, kw)))
    https.main()
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[-2:] == (900, "resume")
    assert kwargs == ({"authenticated_file_candidate": True} if candidate else {})
    output = capsys.readouterr().out
    assert output == ('{"status":"stopped"}\n' if mode == "--activate-public-synthetic" else "")


@pytest.mark.parametrize("candidate", [False, True])
def test_backend_option_reaches_factory_with_only_fake_socket_server_and_threads(
    monkeypatch, capsys, candidate
):
    calls = []
    monkeypatch.setattr(
        https, "logging", SimpleNamespace(getLogger=lambda _: SimpleNamespace(disabled=False))
    )

    class Listener:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def setsockopt(self, *args):
            calls.append("exclusive-socket-option")

        def bind(self, address):
            assert address == ("127.0.0.1", 18092)
            calls.append("bind")

        def listen(self, backlog):
            assert backlog == 128

    listener = Listener()
    monkeypatch.setattr(https.socket, "socket", lambda: listener)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO((ORIGIN + "\n").encode())))

    def factory(origin, **kwargs):
        assert calls[-1] == "bind" and origin == ORIGIN
        assert kwargs == {
            "allow_public_synthetic": True,
            "scenario": "resume",
            **({"authenticated_file_candidate": True} if candidate else {}),
        }
        calls.append("factory")
        return "fixed-synthetic-app", None, None

    monkeypatch.setattr(https, "build_public_synthetic_lab", factory)

    def config(app, **kwargs):
        assert app == "fixed-synthetic-app"
        assert kwargs == {
            "access_log": False,
            "proxy_headers": False,
            "log_config": None,
            "timeout_graceful_shutdown": 2,
        }
        return "fixed-config"

    monkeypatch.setattr(https.uvicorn, "Config", config)

    def server(config):
        assert config == "fixed-config"
        return SimpleNamespace(run=lambda sockets: calls.append(("run", sockets)))

    monkeypatch.setattr(https.uvicorn, "Server", server)
    monkeypatch.setattr(https, "watch_parent", lambda *_: None)
    monkeypatch.setattr(
        https.threading, "Thread", lambda **kwargs: SimpleNamespace(start=lambda: None)
    )
    https.backend_helper(900, "resume", authenticated_file_candidate=candidate)
    assert calls[-2:] == ["factory", ("run", [listener])]
    assert capsys.readouterr().out == "RESERVED\n"


def test_candidate_does_not_relax_opt_in_or_allow_real_origin(monkeypatch):
    monkeypatch.setattr(https, "CLIP", SimpleNamespace(read_bytes=forbid))
    with pytest.raises(https.PreparationError, match="opt-in-required"):
        https.build_public_synthetic_lab(
            ORIGIN, scenario="resume", authenticated_file_candidate=True
        )
    with pytest.raises(https.PreparationError, match="invalid-public-origin"):
        https.build_public_synthetic_lab(
            "https://operator.invalid",
            allow_public_synthetic=True,
            scenario="resume",
            authenticated_file_candidate=True,
        )


@pytest.mark.parametrize("marker", [{}, {"original_delivery": "legacy"}, {**MARKER, "extra": True}])
def test_candidate_readiness_rejects_missing_wrong_or_extra_marker(monkeypatch, marker):
    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            return httpx.Response(200, json={**LEGACY_READY, **marker})

    monkeypatch.setattr(httpx, "Client", Client)
    assert not https.ready_local(authenticated_file_candidate=True)
    assert not https.ready_public(ORIGIN, authenticated_file_candidate=True)
