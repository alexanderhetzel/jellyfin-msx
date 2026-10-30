import hashlib
import io
import json
import os
import queue
import socket
import subprocess
import sys
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from jellyfin_msx.config import Settings
from tools import synthetic_https as https
from tools.lab import build_lab
from tools.synthetic_check import action, pair
from tools.synthetic_lab import MOVIE, build_synthetic_lab

ORIGIN = "https://synthetic-test.trycloudflare.com"


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
            https.activate(binary, seconds=4)
    elif failure in {"timeout", "helper-exit"}:
        with pytest.raises(https.PreparationError):
            https.activate(binary, seconds=4)
    else:
        https.activate(binary, seconds=1 if failure == "lifetime" else 4)
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


def test_actual_backend_reserves_local_only_and_exits_on_parent_eof(tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    code = f"from tools import synthetic_https as h; h.PORT={port}; h.backend_helper(15)"
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
