"""Opt-in, supervised temporary HTTPS delivery of synthetic data ONLY.

--check never starts a service or tunnel. --activate-public-synthetic requires
separate human authorization; merely preparing this tool is not that approval.
"""

import argparse
import hashlib
import json
import logging
import os
import queue
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn
from starlette.middleware.trustedhost import TrustedHostMiddleware

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from tools.lab import ROOT, TrafficRecorder, attach_observations
from tools.synthetic_lab import SyntheticJellyfin, attach_fixture_media
from tools.windows_job import enter_kill_on_close_job

VERSION = "2026.10.7"
BINARY_SHA256 = "2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343"
MEDIA_SHA256 = "44f03da6c498584f27f5f04471935dc2ec5931769e28fbaf7c0a91fcff8fc406"
BINARY = ROOT / ".lab/tools/cloudflared/cloudflared.exe"
CLIP = ROOT / "tests/fixtures/msx-public/synthetic.mp4"
PORT = 18092
MAX_SECONDS = 900
STARTUP_SECONDS = 45
CONTROL = ROOT / ".lab/synthetic-https"
ORIGIN_PATTERN = r"https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com"


class PreparationError(Exception):
    """Messages are fixed non-sensitive outcome codes, never underlying exceptions."""


def validate_origin(origin):
    if not isinstance(origin, str) or not re.fullmatch(ORIGIN_PATTERN, origin):
        raise PreparationError("invalid-public-origin")
    return origin


def build_public_synthetic_lab(origin, *, allow_public_synthetic=False):
    if allow_public_synthetic is not True:
        raise PreparationError("public-synthetic-opt-in-required")
    origin = validate_origin(origin)
    raw = CLIP.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MEDIA_SHA256:
        raise PreparationError("synthetic-clip-checksum")
    settings = Settings(origin, origin + "/jellyfin", session_ttl=900, max_states=32)
    fixture = SyntheticJellyfin(origin)
    recorder = TrafficRecorder(httpx.MockTransport(fixture.handle))
    app = create_app(settings, transport=recorder)
    app, launch = attach_observations(app, settings, recorder)
    attach_fixture_media(app, fixture, raw, None)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[urlsplit(origin).hostname, "127.0.0.1"]
    )

    @app.get("/__synthetic/ready")
    def ready():
        return {"mode": "public-synthetic", "configured": True}

    return app, launch, fixture


def verify_binary(binary):
    if hashlib.sha256(binary.read_bytes()).hexdigest() != BINARY_SHA256:
        raise PreparationError("cloudflared-checksum")


def child_environment(directory):
    # No operator MSX/Jellyfin/Cloudflare config, proxy, credentials or Python hooks.
    result = {
        key: os.environ[key]
        for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
        if key in os.environ
    }
    result.update(
        HOME=str(directory),
        USERPROFILE=str(directory),
        PYTHONPATH=str(ROOT),
        PYTHONNOUSERSITE="1",
        PYTHONUNBUFFERED="1",
    )
    return result


def spawn(args, directory, *, output=False):
    return subprocess.Popen(
        args,
        cwd=ROOT,
        env=child_environment(directory),
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE if output else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def stop_process(process):
    if process.stdin:
        try:
            process.stdin.close()  # Helpers also clean up if the parent dies.
        except (BrokenPipeError, OSError):
            pass
    elif process.poll() is None:
        process.terminate()  # cloudflared has no stdin watchdog of its own.
    try:
        process.wait(timeout=8 if process.stdin else 3)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    if process.stdout:
        process.stdout.close()


def watch_parent(stream, stopped):
    def read():
        try:
            while stream.read(1):
                pass
        except (OSError, ValueError):
            pass
        finally:
            stopped.set()

    threading.Thread(target=read, daemon=True).start()


def origin_from_line(line):
    if len(line) > 4096:
        return None
    match = re.search(r"(?:^|\s|\|)(" + ORIGIN_PATTERN + r")(?=\s|\||$)", line)
    return validate_origin(match[1]) if match else None


def drain_origins(stream, origins):
    """Discard raw helper logs; bound buffers and retain only one validated origin."""

    def read():
        buffer = b""
        try:
            while chunk := stream.read(1):
                if chunk == b"\n":
                    origin = origin_from_line(buffer.decode("utf-8", errors="replace"))
                    if origin and origins.empty():
                        origins.put_nowait(origin)
                    buffer = b""
                elif len(buffer) <= 4096:
                    buffer += chunk
        except (OSError, ValueError):
            pass

    threading.Thread(target=read, daemon=True).start()


def tunnel_args(binary, directory):
    return [
        str(binary),
        "tunnel",
        "--config",
        str(directory / "empty.yml"),
        "--no-autoupdate",
        "--url",
        f"http://127.0.0.1:{PORT}",
        "--metrics",
        "127.0.0.1:0",
        "--loglevel",
        "info",
        "--management-diagnostics=false",
    ]


def tunnel_helper(binary, directory, seconds):
    verify_binary(binary)
    stopped = threading.Event()
    watch_parent(sys.stdin.buffer, stopped)
    deadline = time.monotonic() + seconds
    origins = queue.Queue(maxsize=1)
    process = subprocess.Popen(
        tunnel_args(binary, directory),
        cwd=directory,
        env=child_environment(directory),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    sent = False
    try:
        drain_origins(process.stdout, origins)
        while not stopped.wait(0.1) and time.monotonic() < deadline:
            if process.poll() is not None:
                raise PreparationError("tunnel-helper-exited")
            if not sent and not origins.empty():
                print(origins.get_nowait(), flush=True)
                sent = True
    finally:
        stop_process(process)


def backend_helper(seconds):
    # Reserve our exclusive listener BEFORE the tunnel can start: never expose an
    # unrelated existing listener. Keep ownership while waiting for fixed IPC config.
    with socket.socket() as listener:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", PORT))
        listener.listen(128)
        print("RESERVED", flush=True)
        origin = sys.stdin.buffer.readline(256).decode("ascii").strip()
        app, _, _ = build_public_synthetic_lab(origin, allow_public_synthetic=True)
        logging.getLogger("uvicorn.error").disabled = True
        logging.getLogger("uvicorn.access").disabled = True
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                access_log=False,
                proxy_headers=False,
                log_config=None,
                timeout_graceful_shutdown=2,
            )
        )
        stopped = threading.Event()
        watch_parent(sys.stdin.buffer, stopped)

        def shutdown():
            stopped.wait(seconds)
            server.should_exit = True

        threading.Thread(target=shutdown, daemon=True).start()
        server.run(sockets=[listener])


def await_value(process, values, deadline, stop_file):
    while time.monotonic() < deadline:
        if stop_file.exists():
            raise PreparationError("stop-requested")
        if process.poll() is not None:
            raise PreparationError("owned-helper-exited")
        try:
            return values.get(timeout=0.1)
        except queue.Empty:
            pass
    raise PreparationError("startup-timeout")


def ready_local():
    try:
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=0.5) as client:
            response = client.get(f"http://127.0.0.1:{PORT}/__synthetic/ready")
            return response.status_code == 200 and response.json() == {
                "mode": "public-synthetic",
                "configured": True,
            }
    except (httpx.HTTPError, ValueError):
        return False


def ready_public(origin):
    origin = validate_origin(origin)
    try:
        with httpx.Client(
            trust_env=False, follow_redirects=False, verify=True, timeout=2
        ) as client:
            response = client.get(origin + "/__synthetic/ready")
            return response.status_code == 200 and response.json() == {
                "mode": "public-synthetic",
                "configured": True,
            }
    except (httpx.HTTPError, ValueError):
        return False


def activate(binary, seconds=MAX_SECONDS):
    if not 1 <= seconds <= MAX_SECONDS:
        raise PreparationError("invalid-lifetime")
    verify_binary(binary)
    CONTROL.parent.mkdir(parents=True, exist_ok=True)
    CONTROL.mkdir()  # Exclusive; never overwrite another run's containment state.
    processes = []
    stop_file = CONTROL / "stop"
    deadline = time.monotonic() + seconds
    startup = min(deadline, time.monotonic() + STARTUP_SECONDS)
    try:
        (CONTROL / "owner.json").write_text(json.dumps({"supervisor_pid": os.getpid()}))
        with tempfile.TemporaryDirectory(prefix="sandbox-", dir=CONTROL) as temporary:
            directory = Path(temporary)
            (directory / "empty.yml").write_text("{}\n")
            try:
                base = [sys.executable, "-m", "tools.synthetic_https", "--seconds", str(seconds)]
                backend = spawn([*base, "--backend-helper"], directory, output=True)
                processes.append(backend)
                reserved = queue.Queue(maxsize=1)

                def read_reserved():
                    try:
                        if backend.stdout.readline(32).strip() == b"RESERVED":
                            reserved.put("RESERVED")
                    except (OSError, ValueError):
                        pass

                threading.Thread(target=read_reserved, daemon=True).start()
                await_value(backend, reserved, startup, stop_file)
                tunnel = spawn(
                    [
                        *base,
                        "--tunnel-helper",
                        "--cloudflared",
                        str(binary),
                        "--directory",
                        str(directory),
                    ],
                    directory,
                    output=True,
                )
                processes.append(tunnel)
                origins = queue.Queue(maxsize=1)
                drain_origins(tunnel.stdout, origins)
                origin = await_value(tunnel, origins, startup, stop_file)
                backend.stdin.write((origin + "\n").encode("ascii"))
                backend.stdin.flush()
                while True:
                    if time.monotonic() >= startup:
                        raise PreparationError("startup-timeout")
                    if any(p.poll() is not None for p in processes) or stop_file.exists():
                        raise PreparationError("startup-stopped")
                    if ready_local() and ready_public(origin):
                        if time.monotonic() >= startup:
                            raise PreparationError("startup-timeout")
                        break
                    time.sleep(0.1)
                (CONTROL / "owner.json").write_text(
                    json.dumps(
                        {
                            "supervisor_pid": os.getpid(),
                            "backend_pid": backend.pid,
                            "tunnel_helper_pid": tunnel.pid,
                        }
                    )
                )
                print(
                    json.dumps(
                        {"status": "ready", "public_origin": origin, "maximum_seconds": seconds}
                    ),
                    flush=True,
                )
                while time.monotonic() < deadline and not stop_file.exists():
                    if any(p.poll() is not None for p in processes):
                        raise PreparationError("owned-helper-exited")
                    time.sleep(0.1)
            finally:
                # Stop all owned helpers BEFORE removing their isolated cwd/config.
                failed = False
                for process in reversed(processes):
                    try:
                        stop_process(process)
                    except Exception:
                        failed = True
                if failed:
                    raise PreparationError("owned-helper-cleanup-failed")
    finally:
        for name in ("owner.json", "stop"):
            (CONTROL / name).unlink(missing_ok=True)
        CONTROL.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--activate-public-synthetic", action="store_true")
    modes.add_argument("--stop", action="store_true")
    modes.add_argument("--backend-helper", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--tunnel-helper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--cloudflared", type=Path, default=BINARY)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS)
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if not 1 <= args.seconds <= MAX_SECONDS:
            raise PreparationError("invalid-lifetime")
        if args.backend_helper:
            backend_helper(args.seconds)
        elif args.tunnel_helper:
            _owned_job = enter_kill_on_close_job()
            tunnel_helper(args.cloudflared.resolve(), args.directory, args.seconds)
        elif args.stop:
            if not (CONTROL / "owner.json").is_file():
                raise PreparationError("no-owned-run")
            (CONTROL / "stop").touch()
            print('{"status":"stop-requested"}')
        elif args.activate_public_synthetic:
            if os.name != "nt":
                raise PreparationError("activation-requires-reviewed-windows-supervision")
            activate(args.cloudflared.resolve(), args.seconds)
            print('{"status":"stopped"}')
        else:
            verify_binary(args.cloudflared)
            if hashlib.sha256(CLIP.read_bytes()).hexdigest() != MEDIA_SHA256:
                raise PreparationError("synthetic-clip-checksum")
            print(
                json.dumps(
                    {
                        "status": "prepared",
                        "version": VERSION,
                        "sha256": BINARY_SHA256,
                        "port": PORT,
                        "maximum_seconds": MAX_SECONDS,
                        "approval_required": True,
                        "tunnel_started": False,
                    }
                )
            )
    except KeyboardInterrupt:
        print('{"status":"stopped","reason":"interrupted"}')
        raise SystemExit(130) from None
    except PreparationError as error:
        print(json.dumps({"status": "failed", "reason": str(error)}))
        raise SystemExit(1) from None
    except Exception:
        # Never surface third-party logs, request URLs or raw exception strings.
        print('{"status":"failed","reason":"local-preparation-error"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
