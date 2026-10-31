import asyncio
import base64
import hashlib
import io
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools import synthetic_https as https
from tools.lab import build_lab
from tools.synthetic_check import action, pair
from tools.synthetic_lab import MOVIE, build_synthetic_lab

ORIGIN = "https://synthetic-test.trycloudflare.com"


def test_remember_loop_factory_returns_owned_selector_loop():
    loop = https.remember_loop_factory()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows shared-listener Uvicorn restart contract")
def test_actual_windows_uvicorn_restarts_on_continuously_owned_socket(monkeypatch, tmp_path):
    from cryptography.fernet import Fernet

    monkeypatch.setattr(https, "PORT", 0)
    listener = https.reserve_listener()
    port = listener.getsockname()[1]
    control = tmp_path / "control"
    state = control / "sandbox-local"
    state.mkdir(parents=True)
    state.chmod(0o700)
    key = Fernet.generate_key().decode()
    code = (
        "import sys; from pathlib import Path; from tools import synthetic_https as h; "
        "h.CONTROL=Path(sys.argv[1]); owned=h.enter_kill_on_close_job(); "
        "h.backend_helper(20,'remember')"
    )
    children = []
    try:
        for _ in range(2):
            child = subprocess.Popen(
                [sys.executable, "-c", code, str(control)],
                cwd=https.ROOT,
                env=https.child_environment(state),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            children.append(child)
            try:
                https.share_listener(child, listener)
                observed = queue.Queue()

                def reserved(child=child, observed=observed):
                    observed.put(child.stdout.readline(32))

                threading.Thread(target=reserved, daemon=True).start()
                assert observed.get(timeout=5).strip() == b"RESERVED"
                https.configure_backend(child, ORIGIN, key)
                deadline = time.monotonic() + 6
                ready = False
                with httpx.Client(trust_env=False, follow_redirects=False, timeout=0.4) as client:
                    while time.monotonic() < deadline and child.poll() is None:
                        try:
                            result = client.get(f"http://127.0.0.1:{port}/__synthetic/ready")
                            ready = (
                                result.status_code == 200
                                and result.json().get("configured") is True
                            )
                        except (httpx.HTTPError, ValueError):
                            pass
                        if ready:
                            break
                        time.sleep(0.1)
                assert ready
            finally:
                https.stop_process(child)
            assert child.poll() == 0
            with socket.socket() as competitor:
                with pytest.raises(OSError):
                    competitor.bind(("127.0.0.1", port))
    finally:
        for child in children:
            if child.poll() is None:
                https.stop_process(child)
        listener.close()


@pytest.mark.parametrize("restart_delay,success", [(0, True), (31, False)])
def test_remember_restart_keeps_ram_key_and_original_deadline(
    monkeypatch,
    tmp_path,
    capsys,
    restart_delay,
    success,
):
    clock = [0.0]
    control = tmp_path / "control"
    monkeypatch.setattr(https, "CONTROL", control)
    monkeypatch.setattr(https, "verify_binary", lambda _: None)
    monkeypatch.setattr(https, "ready_local", lambda: True)
    calls, stopped, streams = [], [], []

    def ready_public(origin):
        if len(calls) == 3:
            clock[0] += restart_delay
        return True

    monkeypatch.setattr(https, "ready_public", ready_public)
    shared = []
    listener = SimpleNamespace(
        share=lambda pid: shared.append(pid) or b"synthetic-socket-share",
        close=lambda: shared.append("closed"),
    )
    monkeypatch.setattr(https, "reserve_listener", lambda: listener)

    def advance(delay):
        clock[0] += 10
        if clock[0] == 10:
            (control / "restart-backend").touch()
        if clock[0] == 20:
            (control / "stop").touch()

    monkeypatch.setattr(https, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=advance))

    def spawn(args, directory, **kwargs):
        calls.append(args)
        stream = io.BytesIO()
        streams.append(stream)
        return SimpleNamespace(
            pid=len(calls), stdin=stream, stdout=io.BytesIO(b"RESERVED\n"), poll=lambda: None
        )

    monkeypatch.setattr(https, "spawn", spawn)
    monkeypatch.setattr(https, "stop_process", lambda process: stopped.append(process.pid))
    monkeypatch.setattr(https, "drain_origins", lambda *args: None)
    deadlines = []

    def allocated(process, values, deadline, stop_file):
        deadlines.append(deadline)
        return ORIGIN if process.pid == 2 else "RESERVED"

    monkeypatch.setattr(https, "await_value", allocated)
    if success:
        https.activate(tmp_path / "synthetic-binary", seconds=900, scenario="remember")
    else:
        with pytest.raises(https.PreparationError, match="restart-readiness-timeout"):
            https.activate(tmp_path / "synthetic-binary", seconds=900, scenario="remember")
    assert len(calls) == 3 and calls[2][calls[2].index("--seconds") + 1] == "890"
    first = streams[0].getvalue().splitlines()
    restarted = streams[2].getvalue().splitlines()
    assert first == restarted and json.loads(first[2]).keys() == {"key"}
    assert deadlines == [180, 180, 40]
    assert set(stopped) == {1, 2, 3} and stopped[0] == 1
    assert not control.exists()
    assert shared == [1, 2, 3, "closed"]
    assert json.loads(first[2])["key"] not in capsys.readouterr().out


def test_tunnel_eof_stops_vendor_before_releasing_shared_listener(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(https, "verify_binary", lambda _: None)
    monkeypatch.setattr(
        https.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(base64.b64encode(b"synthetic-descriptor") + b"\n")),
    )
    monkeypatch.setattr(
        https.socket,
        "fromshare",
        lambda _: SimpleNamespace(close=lambda: events.append("reservation-closed")),
        raising=False,
    )
    monkeypatch.setattr(https, "watch_parent", lambda stream, stopped: stopped.set())
    monkeypatch.setattr(https.subprocess, "Popen", lambda *a, **k: SimpleNamespace(stdout=None))
    monkeypatch.setattr(https, "drain_origins", lambda *args: None)
    monkeypatch.setattr(https, "stop_process", lambda _: events.append("vendor-stopped"))
    https.tunnel_helper(tmp_path / "synthetic-binary", tmp_path, 900, "remember")
    assert events == ["vendor-stopped", "reservation-closed"]


@pytest.mark.skipif(os.name != "nt", reason="Windows socket.share/fromshare contract")
def test_actual_windows_socket_reservation_survives_child_process_restart(monkeypatch, tmp_path):
    # An ephemeral test-only reservation, never the shared relay port or a web service.
    monkeypatch.setattr(https, "PORT", 0)
    listener = https.reserve_listener()
    port = listener.getsockname()[1]
    script = (
        "import base64,socket,sys; "
        "descriptor=base64.b64decode(sys.stdin.buffer.readline().strip(),validate=True); "
        "held=socket.fromshare(descriptor); "
        "print('HELD',flush=True); sys.stdin.buffer.read(); held.close()"
    )
    processes = []

    def assert_owned():
        with socket.socket() as other:
            with pytest.raises(OSError):
                other.bind(("127.0.0.1", port))

    try:
        assert_owned()
        for _ in range(2):
            child = subprocess.Popen(
                [sys.executable, "-c", script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=https.child_environment(tmp_path),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            processes.append(child)
            https.share_listener(child, listener)
            observed = queue.Queue()
            threading.Thread(
                target=lambda child=child, observed=observed: observed.put(
                    child.stdout.readline(16)
                ),
                daemon=True,
            ).start()
            assert observed.get(timeout=5).strip() == b"HELD"
            assert_owned()
            child.stdin.close()
            assert child.wait(timeout=5) == 0
            assert_owned()  # Includes the interval before the next exact child is created.
    finally:
        for child in processes:
            child.stdin.close()
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()
        listener.close()
    with socket.socket() as other:
        other.bind(("127.0.0.1", port))


@pytest.mark.parametrize(
    "seconds,ready_at,success", [(900, 90, True), (60, 61, False), (900, 181, False)]
)
def test_delayed_relay_readiness_keeps_original_total_budget(
    monkeypatch, tmp_path, capsys, seconds, ready_at, success
):
    assert https.STARTUP_SECONDS == 180
    clock = [0.0]
    monkeypatch.setattr(
        https,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0], sleep=lambda delay: clock.__setitem__(0, clock[0] + 10)
        ),
    )
    monkeypatch.setattr(https, "CONTROL", tmp_path / "control")
    monkeypatch.setattr(https, "verify_binary", lambda _: None)
    processes = []

    def spawn(*args, **kwargs):
        process = SimpleNamespace(
            pid=len(processes) + 1,
            stdout=io.BytesIO(b"RESERVED\n"),
            stdin=io.BytesIO(),
            poll=lambda: None,
        )
        processes.append(process)
        return process

    stopped = []
    monkeypatch.setattr(https, "spawn", spawn)
    monkeypatch.setattr(https, "stop_process", lambda process: stopped.append(process))
    monkeypatch.setattr(https, "drain_origins", lambda stream, values: None)
    allocation_deadlines = []

    def allocated(process, values, deadline, stop_file):
        allocation_deadlines.append(deadline)
        return "RESERVED" if len(allocation_deadlines) == 1 else ORIGIN

    monkeypatch.setattr(https, "await_value", allocated)
    monkeypatch.setattr(https, "ready_local", lambda: True)

    def relay_ready(origin):
        clock[0] = ready_at
        return True

    monkeypatch.setattr(https, "ready_public", relay_ready)
    if success:
        https.activate(tmp_path / "fake", seconds=seconds)
    else:
        with pytest.raises(https.PreparationError, match="relay-readiness-timeout"):
            https.activate(tmp_path / "fake", seconds=seconds)
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert any(event["status"] == "ready" for event in events) is success
    assert allocation_deadlines == [min(seconds, 180)] * 2
    if success:
        assert clock[0] == seconds  # Startup consumed the original budget; it did not renew it.
    assert stopped == list(reversed(processes))
    assert not https.CONTROL.exists()


@pytest.mark.parametrize(
    "origin",
    [
        "http://synthetic-test.trycloudflare.com",
        "https://example.test",
        "https://sub.test.trycloudflare.com",
        ORIGIN + "/",
        ORIGIN + "/msx/device/private",
        ORIGIN + "?token=private",
        ORIGIN + "#private",
        ORIGIN + ":443",
        "https://user:pw@synthetic-test.trycloudflare.com",
        ORIGIN + ".evil.test",
    ],
)
def test_public_factory_rejects_unapproved_origins(origin):
    with pytest.raises(https.PreparationError, match="invalid-public-origin"):
        https.build_public_synthetic_lab(origin, allow_public_synthetic=True)


def test_opt_in_does_not_relax_real_or_existing_synthetic_loopback_guards():
    with pytest.raises(https.PreparationError, match="opt-in"):
        https.build_public_synthetic_lab(ORIGIN)
    settings = Settings(ORIGIN, ORIGIN + "/jellyfin")
    with pytest.raises(ValueError, match="loopback"):
        build_lab(settings)
    with pytest.raises(ValueError, match="loopback"):
        build_synthetic_lab(settings)


def test_normal_public_synthetic_auth_media_privacy_and_revocation(monkeypatch, tmp_path):
    def forbid(*args, **kwargs):
        raise AssertionError("Operator configuration or real network fallback attempted")

    monkeypatch.setattr(Settings, "from_env", forbid)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "__init__", forbid)
    monkeypatch.setenv("JELLYFIN_URL", "https://operator.invalid")
    monkeypatch.setenv("MSX_AUTHORIZATION_DB", str(tmp_path / "operator.sqlite"))
    original = https.CLIP.read_bytes()
    media = tmp_path / "clip.mp4"
    media.write_bytes(original)
    monkeypatch.setattr(https, "CLIP", media)
    app, _, fixture = https.build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True)
    media.write_bytes(b"changed local file must never be exposed")
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get(f"/jellyfin/Videos/{MOVIE}/stream.mp4").status_code == 401
        assert client.get("/msx/device/unknown/home.json").json()["response"]["status"] == 401
        page = client.get("/pair")
        assert "Secure" in page.headers["set-cookie"]
        assert client.get("/healthz").headers["strict-transport-security"]
        home_target = pair(client, ORIGIN)
        home = client.get(home_target.removeprefix("content:")).json()
        browse = client.get(action(home, "Synthetic movies").removeprefix("content:")).json()
        movie = next(row for row in browse["items"] if row["title"] == "Synthetic clip")
        assert client.get(movie["image"]).status_code == 200
        detail = client.get(movie["action"].removeprefix("content:")).json()
        play = action(detail, "Try original").removeprefix("video:resolve:")
        target = client.get(play).json()["response"]["data"]["url"]
        for selection, expected in (
            ("bytes=0-8", original[:9]),
            ("bytes=-9", original[-9:]),
            ("bytes=100-", original[100:]),
        ):
            response = client.get(target, headers={"Range": selection})
            assert response.status_code == 206 and response.content == expected
        for selection in (
            "bytes=-0",
            "bytes=9-2",
            "bytes=99999999-",
            "bytes=0-1,3-5",
            "bytes=" + "9" * 5000 + "-",
        ):
            assert client.get(target, headers={"Range": selection}).status_code == 416
        head = client.head(target)
        assert head.status_code == 200 and not head.content
        assert int(head.headers["content-length"]) == len(original)
        report = client.get("/__lab/report").json()
        assert report["paired_sessions"] == 1
        assert report["negotiations"][0]["EnableTranscoding"] is False
        for sensitive in (*fixture.tokens, home_target, target, "operator.invalid"):
            assert sensitive not in json.dumps(report)
        confirm = client.get(action(home, "Disconnect TV").removeprefix("content:")).json()
        client.get(action(confirm, "Confirm disconnect").removeprefix("content:"))
        assert client.get(target).status_code == 401
        assert client.get(movie["image"]).status_code == 401
        assert client.get(play).json()["response"]["status"] == 401
        assert not fixture.tokens and not (tmp_path / "operator.sqlite").exists()
    with pytest.raises(https.PreparationError, match="clip-checksum"):
        https.build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True)


def test_request_headers_never_reconfigure_origin():
    app, _, _ = https.build_public_synthetic_lab(ORIGIN, allow_public_synthetic=True)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/healthz", headers={"Host": "attacker.test"}).status_code == 400
        start = client.get(
            "/msx/start.json",
            headers={"X-Forwarded-Host": "attacker.test", "X-Forwarded-Proto": "http"},
        ).json()
        assert start["parameter"] == "content:" + ORIGIN + "/msx/pair.json"


@pytest.mark.parametrize(
    "line,expected",
    [
        ("| " + ORIGIN + " |", ORIGIN),
        (ORIGIN, ORIGIN),
        (ORIGIN + "/msx/device/secret/home.json", None),
        (ORIGIN + "?ApiKey=secret", None),
        (ORIGIN + ".evil.test", None),
        ("private " * 1000 + ORIGIN, None),
    ],
)
def test_only_bounded_origin_not_request_urls_can_escape_log_drain(line, expected):
    assert https.origin_from_line(line) == expected


def test_preflight_has_no_subprocess_or_network_side_effect(monkeypatch, tmp_path, capsys):
    binary = tmp_path / "fake-binary"
    binary.write_bytes(b"synthetic helper")
    monkeypatch.setattr(https, "BINARY_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    monkeypatch.setattr(sys, "argv", ["synthetic_https", "--check", "--cloudflared", str(binary)])

    def forbid(*args, **kwargs):
        raise AssertionError("Preflight must never spawn a helper")

    monkeypatch.setattr(subprocess, "Popen", forbid)
    https.main()
    result = json.loads(capsys.readouterr().out)
    assert result["approval_required"] is True and result["tunnel_started"] is False
    binary.write_bytes(b"modified")
    with pytest.raises(https.PreparationError, match="cloudflared-checksum"):
        https.verify_binary(binary)


def test_child_environment_and_arguments_exclude_operator_settings(monkeypatch, tmp_path):
    for name in (
        "JELLYFIN_URL",
        "MSX_AUTHORIZATION_KEY",
        "TUNNEL_TOKEN",
        "HTTPS_PROXY",
        "PYTHONSTARTUP",
        "CF_API_TOKEN",
        "CLOUDFLARED_CONFIG",
    ):
        monkeypatch.setenv(name, "operator-only")
    environment = https.child_environment(tmp_path)
    assert "operator-only" not in environment.values()
    assert environment["USERPROFILE"] == str(tmp_path)
    args = https.tunnel_args(tmp_path / "cloudflared.exe", tmp_path)
    assert args[args.index("--url") + 1] == "http://127.0.0.1:18092"
    assert args[args.index("--config") + 1] == str(tmp_path / "empty.yml")
    assert "--no-autoupdate" in args and "--management-diagnostics=false" in args
    assert not any(flag in args for flag in ("--no-tls-verify", "--logfile", "--token"))


@pytest.mark.parametrize("failure", ["lifetime", "timeout", "interrupt", "helper-exit", "stop"])
def test_owned_helpers_cleanup_on_all_supervisor_exit_paths(monkeypatch, tmp_path, capsys, failure):
    binary = tmp_path / "fake-binary"
    binary.write_bytes(b"fake")
    monkeypatch.setattr(https, "BINARY_SHA256", hashlib.sha256(b"fake").hexdigest())
    monkeypatch.setattr(https, "CONTROL", tmp_path / "control")
    monkeypatch.setattr(https, "STARTUP_SECONDS", 0.8 if failure == "timeout" else 3)
    real_spawn = https.spawn
    processes = []

    def spawn_fake(args, directory, *, output=False):
        # These local owned Python helpers never start cloudflared or any listener.
        if "--backend-helper" in args:
            assert args[args.index("--scenario") + 1] == "failures"
            code = (
                "import sys; print('RESERVED',flush=True); sys.stdin.readline(); sys.stdin.read()"
            )
        else:
            code = (
                "import sys,time; print('private request URL must be discarded',flush=True); "
                f"print('{ORIGIN}',flush=True); "
            )
            code += "time.sleep(.2)" if failure == "helper-exit" else "sys.stdin.read()"
        process = real_spawn([sys.executable, "-u", "-c", code], directory, output=output)
        processes.append(process)
        return process

    monkeypatch.setattr(https, "spawn", spawn_fake)

    def ready():
        if failure == "interrupt":
            raise KeyboardInterrupt
        if failure == "stop":
            (https.CONTROL / "stop").touch()
        return failure != "timeout"

    monkeypatch.setattr(https, "ready_local", ready)
    monkeypatch.setattr(https, "ready_public", lambda origin: True)
    if failure == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            https.activate(binary, seconds=4, scenario="failures")
    elif failure in {"timeout", "helper-exit"}:
        with pytest.raises(https.PreparationError):
            https.activate(binary, seconds=4, scenario="failures")
    else:
        https.activate(binary, seconds=1 if failure == "lifetime" else 4, scenario="failures")
    assert len(processes) == 2 and all(p.poll() is not None for p in processes)
    assert not https.CONTROL.exists()
    assert "private request URL" not in capsys.readouterr().out


def test_tunnel_wrapper_parent_eof_stops_owned_fake_tunnel(monkeypatch, tmp_path):
    binary = tmp_path / "fake"
    binary.write_bytes(b"fake")
    monkeypatch.setattr(https, "BINARY_SHA256", hashlib.sha256(b"fake").hexdigest())
    monkeypatch.setattr(https.sys, "stdin", type("Input", (), {"buffer": io.BytesIO()})())
    monkeypatch.setattr(
        https, "tunnel_args", lambda *_: [sys.executable, "-c", "import time; time.sleep(30)"]
    )
    real_popen = subprocess.Popen
    children = []

    def owned(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", owned)
    https.tunnel_helper(binary, tmp_path, 4)
    assert len(children) == 1 and children[0].poll() is not None


def test_public_readiness_uses_verified_tls_and_never_redirects(monkeypatch):
    options = []

    class Client:
        def __init__(self, **kwargs):
            options.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            assert url == ORIGIN + "/__synthetic/ready"
            return httpx.Response(200, json={"mode": "public-synthetic", "configured": True})

    monkeypatch.setattr(httpx, "Client", Client)
    assert https.ready_public(ORIGIN)
    assert options == [
        {"trust_env": False, "follow_redirects": False, "verify": True, "timeout": 2}
    ]
    with pytest.raises(https.PreparationError):
        https.ready_public("https://operator.invalid")


def test_occupied_listener_aborts_before_any_tunnel_helper(monkeypatch, tmp_path):
    binary = tmp_path / "fake-binary"
    binary.write_bytes(b"fake")
    monkeypatch.setattr(https, "BINARY_SHA256", hashlib.sha256(b"fake").hexdigest())
    monkeypatch.setattr(https, "CONTROL", tmp_path / "control")
    real_spawn = https.spawn
    children = []
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        port = occupied.getsockname()[1]

        def only_backend(args, directory, *, output=False):
            assert "--backend-helper" in args, "Must not expose an occupied listener"
            code = (
                "from tools import synthetic_https as h; import sys; "
                f"h.PORT={port}; sys.argv=['helper','--backend-helper','--seconds','2']; "
                "h.main()"
            )
            child = real_spawn([sys.executable, "-u", "-c", code], directory, output=output)
            children.append(child)
            return child

        monkeypatch.setattr(https, "spawn", only_backend)
        with pytest.raises(https.PreparationError, match="owned-helper-exited"):
            https.activate(binary, seconds=3)
        assert occupied.getsockname()[1] == port
    assert len(children) == 1 and children[0].poll() is not None
    assert not https.CONTROL.exists()


@pytest.mark.parametrize("scenario", ["baseline", "failures", "navigation"])
def test_actual_backend_reserves_local_only_and_exits_on_parent_eof(tmp_path, scenario):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    code = (
        f"from tools import synthetic_https as h; h.PORT={port}; h.backend_helper(15, {scenario!r})"
    )
    process = https.spawn([sys.executable, "-u", "-c", code], tmp_path, output=True)
    try:
        lines = queue.Queue()
        import threading

        threading.Thread(target=lambda: lines.put(process.stdout.readline(32)), daemon=True).start()
        assert lines.get(timeout=5).strip() == b"RESERVED"
        process.stdin.write((ORIGIN + "\n").encode())
        process.stdin.flush()
        deadline = time.monotonic() + 5
        with httpx.Client(trust_env=False, timeout=0.3) as client:
            while True:
                try:
                    response = client.get(f"http://127.0.0.1:{port}/__synthetic/ready")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline
                time.sleep(0.05)
        assert response.json() == {"mode": "public-synthetic", "configured": True}
    finally:
        https.stop_process(process)
    assert process.returncode == 0
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))


@pytest.mark.skipif(os.name != "nt", reason="Windows job-object termination contract")
def test_abrupt_owned_wrapper_termination_kills_descendant(tmp_path):
    import ctypes
    from ctypes import wintypes

    code = (
        "from tools.windows_job import enter_kill_on_close_job; import subprocess,sys; "
        "job=enter_kill_on_close_job(); "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
        "creationflags=subprocess.CREATE_NO_WINDOW); "
        "print(child.pid,flush=True); sys.stdin.read(); child.wait()"
    )
    wrapper = https.spawn([sys.executable, "-u", "-c", code], tmp_path, output=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = None
    try:
        values = queue.Queue()
        import threading

        threading.Thread(
            target=lambda: values.put(wrapper.stdout.readline(32)), daemon=True
        ).start()
        child_pid = int(values.get(timeout=5))
        handle = kernel.OpenProcess(
            0x100001, False, child_pid
        )  # Owned child: synchronize/terminate.
        assert handle and kernel.WaitForSingleObject(handle, 0) == 258
        wrapper.kill()
        wrapper.wait(timeout=5)
        assert kernel.WaitForSingleObject(handle, 5000) == 0
    finally:
        https.stop_process(wrapper)
        if handle:
            if kernel.WaitForSingleObject(handle, 0) == 258:
                kernel.TerminateProcess(handle, 1)  # Containment only for this test-owned child.
            kernel.CloseHandle(handle)
