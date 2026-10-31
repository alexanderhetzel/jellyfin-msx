"""Opt-in, supervised temporary HTTPS delivery of synthetic data ONLY.

--check never starts a service or tunnel. --activate-public-synthetic requires
separate human authorization; merely preparing this tool is not that approval.
"""

import argparse
import asyncio
import base64
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
from cryptography.fernet import Fernet
from starlette.middleware.trustedhost import TrustedHostMiddleware

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.original_file import MODE
from tools.lab import ROOT, TrafficRecorder, attach_observations
from tools.navigation_fixture import EPISODES, NavigationJellyfin
from tools.remember_observations import RememberObservations
from tools.synthetic_failures import FailureJellyfin
from tools.synthetic_lab import SyntheticJellyfin, attach_fixture_media
from tools.synthetic_lifecycle import RECOVERY_BAD_SOURCE, LifecycleJellyfin, RecoveryJellyfin
from tools.synthetic_resume import ITEMS as RESUME_ITEMS
from tools.synthetic_resume import CandidateResumeJellyfin, ResumeJellyfin
from tools.synthetic_subtitles import ITEMS as SUBTITLE_ITEMS
from tools.synthetic_subtitles import SubtitleJellyfin
from tools.windows_job import enter_kill_on_close_job

VERSION = "2026.10.7"
BINARY_SHA256 = "2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343"
MEDIA_SHA256 = "44f03da6c498584f27f5f04471935dc2ec5931769e28fbaf7c0a91fcff8fc406"
BINARY = ROOT / ".lab/tools/cloudflared/cloudflared.exe"
CLIP = ROOT / "tests/fixtures/msx-public/synthetic.mp4"
PORT = 18092
MAX_SECONDS = 900
STARTUP_SECONDS = 180
CONTROL = ROOT / ".lab/synthetic-https"
ORIGIN_PATTERN = r"https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com"


class PreparationError(Exception):
    """Messages are fixed non-sensitive outcome codes, never underlying exceptions."""


def validate_origin(origin):
    if not isinstance(origin, str) or not re.fullmatch(ORIGIN_PATTERN, origin):
        raise PreparationError("invalid-public-origin")
    return origin


def candidate_option(scenario, authenticated_file_candidate):
    if type(authenticated_file_candidate) is not bool:
        raise PreparationError("invalid-candidate-option")
    if authenticated_file_candidate and scenario != "resume":
        raise PreparationError("candidate-requires-resume")


def delivery_marker(authenticated_file_candidate):
    candidate_option("resume", authenticated_file_candidate)
    return {"original_delivery": MODE} if authenticated_file_candidate else {}


def ready_payload(authenticated_file_candidate):
    return {
        "mode": "public-synthetic",
        "configured": True,
        **delivery_marker(authenticated_file_candidate),
    }


def build_public_synthetic_lab(
    origin,
    *,
    allow_public_synthetic=False,
    scenario="baseline",
    authenticated_file_candidate=False,
    authorization_key=None,
    state_directory=None,
):
    if allow_public_synthetic is not True:
        raise PreparationError("public-synthetic-opt-in-required")
    candidate_option(scenario, authenticated_file_candidate)
    origin = validate_origin(origin)
    if scenario not in {
        "baseline",
        "failures",
        "navigation",
        "subtitles",
        "lifecycle",
        "resume",
        "recovery",
        "remember",
    }:
        raise PreparationError("invalid-synthetic-scenario")
    raw = CLIP.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MEDIA_SHA256:
        raise PreparationError("synthetic-clip-checksum")
    settings = Settings(
        origin,
        origin + "/jellyfin",
        session_ttl=240 if scenario == "subtitles" else 900,
        max_states=32,
        enable_subtitle_resources=scenario == "subtitles",
        **(
            {
                "original_delivery": MODE,
                "original_server_contract": "stock-static-private-origin-v1",
                "original_server_version": "12.4.0",
            }
            if authenticated_file_candidate
            else {}
        ),
    )
    if scenario == "remember":
        from tools.synthetic_authorization import RememberedSyntheticJellyfin

        if not authorization_key or state_directory is None:
            raise PreparationError("synthetic-authorization-config-required")
        state_directory = Path(state_directory)
        if not state_directory.is_absolute() or not state_directory.is_dir():
            raise PreparationError("invalid-synthetic-state-directory")
        settings = Settings(
            origin,
            origin + "/jellyfin",
            session_ttl=900,
            max_states=32,
            authorization_db=str(state_directory / "synthetic-authorization.sqlite"),
            authorization_key=authorization_key,
            authorization_ttl=900,
            remember_devices=True,
        )
        fixture = RememberedSyntheticJellyfin(origin, state_directory / "synthetic-upstream.sqlite")
    else:
        fixture_type = {
            "baseline": SyntheticJellyfin,
            "failures": FailureJellyfin,
            "navigation": NavigationJellyfin,
            "subtitles": SubtitleJellyfin,
            "lifecycle": LifecycleJellyfin,
            "resume": ResumeJellyfin,
            "recovery": RecoveryJellyfin,
        }[scenario]
        fixture = (
            CandidateResumeJellyfin(origin, raw)
            if authenticated_file_candidate
            else fixture_type(origin)
        )
    recorder = TrafficRecorder(httpx.MockTransport(fixture.handle))
    app = create_app(settings, transport=recorder)
    app, launch = attach_observations(
        app,
        settings,
        recorder,
        remember_observations=RememberObservations() if scenario == "remember" else None,
    )
    if scenario == "navigation":
        attach_fixture_media(app, fixture, raw, None, item_ids=EPISODES)
    elif scenario == "subtitles":
        attach_fixture_media(app, fixture, raw, None, item_ids=SUBTITLE_ITEMS)
    elif scenario == "resume":
        attach_fixture_media(
            app,
            fixture,
            raw,
            None,
            item_ids=RESUME_ITEMS,
            **({"files": fixture.files} if authenticated_file_candidate else {}),
        )
    elif scenario == "recovery":
        attach_fixture_media(
            app,
            fixture,
            raw,
            None,
            item_ids=fixture.item_ids,
            source_ids=fixture.source_ids,
            unplayable_sources=(RECOVERY_BAD_SOURCE,),
        )
    else:
        attach_fixture_media(app, fixture, raw, None)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[urlsplit(origin).hostname, "127.0.0.1"]
    )

    @app.get("/__synthetic/ready")
    def ready():
        # Configuration evidence only; this cannot attest to media/native playback.
        return ready_payload(authenticated_file_candidate)

    if scenario in {"lifecycle", "resume", "recovery"}:

        @app.get("/__synthetic/lifecycle")
        def lifecycle_summary():
            # Fixed synthetic counters only; no IDs, URLs, grants or user content.
            return fixture.summary()

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


def tunnel_helper(binary, directory, seconds, scenario="baseline"):
    verify_binary(binary)
    # Keep a second reservation alive until cloudflared has stopped, including EOF
    # cleanup if the supervisor disappears before the backend exits.
    held_listener = (
        socket.fromshare(base64.b64decode(sys.stdin.buffer.readline(8192).strip(), validate=True))
        if scenario == "remember"
        else None
    )
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
        try:
            stop_process(process)
        finally:
            if held_listener is not None:
                held_listener.close()


def reserve_listener():
    listener = socket.socket()
    try:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", PORT))
        listener.listen(128)
        return listener
    except BaseException:
        listener.close()
        raise


def share_listener(backend, listener):
    if listener is not None:
        # Windows duplicates this continuously owned socket for this exact child PID.
        # The protocol descriptor travels only through the owned private stdin pipe.
        backend.stdin.write(base64.b64encode(listener.share(backend.pid)) + b"\n")
        backend.stdin.flush()


def remember_loop_factory():
    # Windows Proactor associates a shared socket with one process's IOCP. A fresh
    # process cannot reuse that association. Selectors preserve the continuously
    # owned listening endpoint without any close/rebind or security-policy change.
    return asyncio.SelectorEventLoop()


def backend_helper(seconds, scenario="baseline", *, authenticated_file_candidate=False):
    candidate_option(scenario, authenticated_file_candidate)
    # In restart tests the supervisor keeps exclusive ownership continuously, even
    # while a backend process is absent. Never leave a live tunnel targeting a free port.
    listener = (
        socket.fromshare(base64.b64decode(sys.stdin.buffer.readline(8192).strip(), validate=True))
        if scenario == "remember"
        else reserve_listener()
    )
    with listener:
        print("RESERVED", flush=True)
        origin = sys.stdin.buffer.readline(256).decode("ascii").strip()
        authorization = {}
        if scenario == "remember":
            directory = Path(os.environ["HOME"])
            if directory.parent.resolve() != CONTROL.resolve() or not directory.name.startswith(
                "sandbox-"
            ):
                raise PreparationError("invalid-synthetic-state-directory")
            configuration = json.loads(sys.stdin.buffer.readline(256))
            if set(configuration) != {"key"}:
                raise PreparationError("invalid-synthetic-authorization-config")
            authorization = {
                "authorization_key": configuration["key"],
                "state_directory": directory,
            }
        app, _, _ = build_public_synthetic_lab(
            origin,
            allow_public_synthetic=True,
            scenario=scenario,
            **({"authenticated_file_candidate": True} if authenticated_file_candidate else {}),
            **authorization,
        )
        logging.getLogger("uvicorn.error").disabled = True
        logging.getLogger("uvicorn.access").disabled = True
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                access_log=False,
                proxy_headers=False,
                log_config=None,
                timeout_graceful_shutdown=2,
                loop="tools.synthetic_https:remember_loop_factory"
                if scenario == "remember"
                else "auto",
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


def reservation_queue(backend):
    reserved = queue.Queue(maxsize=1)

    def read():
        try:
            if backend.stdout.readline(32).strip() == b"RESERVED":
                reserved.put("RESERVED")
        except (OSError, ValueError):
            pass

    threading.Thread(target=read, daemon=True).start()
    return reserved


def configure_backend(backend, origin, authorization_key):
    backend.stdin.write((origin + "\n").encode("ascii"))
    if authorization_key:
        backend.stdin.write((json.dumps({"key": authorization_key}) + "\n").encode("ascii"))
    backend.stdin.flush()


def ready_local(*, authenticated_file_candidate=False):
    expected = ready_payload(authenticated_file_candidate)
    try:
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=0.5) as client:
            response = client.get(f"http://127.0.0.1:{PORT}/__synthetic/ready")
            return response.status_code == 200 and response.json() == expected
    except (httpx.HTTPError, ValueError):
        return False


def ready_public(origin, *, authenticated_file_candidate=False):
    expected = ready_payload(authenticated_file_candidate)
    origin = validate_origin(origin)
    try:
        with httpx.Client(
            trust_env=False, follow_redirects=False, verify=True, timeout=2
        ) as client:
            response = client.get(origin + "/__synthetic/ready")
            return response.status_code == 200 and response.json() == expected
    except (httpx.HTTPError, ValueError):
        return False


def activate(
    binary, seconds=MAX_SECONDS, scenario="baseline", *, authenticated_file_candidate=False
):
    candidate_option(scenario, authenticated_file_candidate)
    if not 1 <= seconds <= MAX_SECONDS:
        raise PreparationError("invalid-lifetime")
    if scenario not in {
        "baseline",
        "failures",
        "navigation",
        "subtitles",
        "lifecycle",
        "resume",
        "recovery",
        "remember",
    }:
        raise PreparationError("invalid-synthetic-scenario")
    verify_binary(binary)
    CONTROL.parent.mkdir(parents=True, exist_ok=True)
    CONTROL.mkdir()  # Exclusive; never overwrite another run's containment state.
    processes = []
    owned_listener = None
    stop_file = CONTROL / "stop"
    deadline = time.monotonic() + seconds
    startup = min(deadline, time.monotonic() + STARTUP_SECONDS)
    try:
        (CONTROL / "owner.json").write_text(json.dumps({"supervisor_pid": os.getpid()}))
        with tempfile.TemporaryDirectory(prefix="sandbox-", dir=CONTROL) as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            # Generated ONLY for this synthetic lifetime; kept in RAM/owned stdin pipes.
            authorization_key = Fernet.generate_key().decode() if scenario == "remember" else None
            if scenario == "remember":
                owned_listener = reserve_listener()
            (directory / "empty.yml").write_text("{}\n")
            try:
                base = [sys.executable, "-m", "tools.synthetic_https", "--seconds", str(seconds)]
                backend = spawn(
                    [
                        *base,
                        "--backend-helper",
                        "--scenario",
                        scenario,
                        *(
                            ["--authenticated-file-candidate"]
                            if authenticated_file_candidate
                            else []
                        ),
                    ],
                    directory,
                    output=True,
                )
                processes.append(backend)
                share_listener(backend, owned_listener)
                reserved = reservation_queue(backend)
                await_value(backend, reserved, startup, stop_file)
                print('{"status":"starting","stage":"listener-reserved"}', flush=True)
                tunnel = spawn(
                    [
                        *base,
                        "--tunnel-helper",
                        "--scenario",
                        scenario,
                        "--cloudflared",
                        str(binary),
                        "--directory",
                        str(directory),
                    ],
                    directory,
                    output=True,
                )
                processes.append(tunnel)
                share_listener(tunnel, owned_listener)
                origins = queue.Queue(maxsize=1)
                drain_origins(tunnel.stdout, origins)
                origin = await_value(tunnel, origins, startup, stop_file)
                print(
                    json.dumps(
                        {"status": "starting", "stage": "origin-assigned", "public_origin": origin}
                    ),
                    flush=True,
                )
                configure_backend(backend, origin, authorization_key)
                while True:
                    if time.monotonic() >= startup:
                        raise PreparationError("relay-readiness-timeout")
                    if any(p.poll() is not None for p in processes) or stop_file.exists():
                        raise PreparationError("startup-stopped")
                    readiness_options = (
                        {"authenticated_file_candidate": True}
                        if authenticated_file_candidate
                        else {}
                    )
                    if ready_local(**readiness_options) and ready_public(
                        origin, **readiness_options
                    ):
                        if time.monotonic() >= startup:
                            raise PreparationError("relay-readiness-timeout")
                        break
                    time.sleep(0.1)
                (CONTROL / "owner.json").write_text(
                    json.dumps(
                        {
                            "supervisor_pid": os.getpid(),
                            "backend_pid": backend.pid,
                            "tunnel_helper_pid": tunnel.pid,
                            "scenario": scenario,
                        }
                    )
                )
                print(
                    json.dumps(
                        {
                            "status": "ready",
                            "public_origin": origin,
                            "maximum_seconds": seconds,
                            "scenario": scenario,
                            **delivery_marker(authenticated_file_candidate),
                        }
                    ),
                    flush=True,
                )
                while time.monotonic() < deadline and not stop_file.exists():
                    if any(p.poll() is not None for p in processes):
                        raise PreparationError("owned-helper-exited")
                    restart = CONTROL / "restart-backend"
                    if scenario == "remember" and restart.exists():
                        restart.unlink()
                        stop_process(backend)
                        processes.remove(backend)
                        remaining = max(1, int(deadline - time.monotonic()))
                        backend = spawn(
                            [
                                sys.executable,
                                "-m",
                                "tools.synthetic_https",
                                "--seconds",
                                str(remaining),
                                "--backend-helper",
                                "--scenario",
                                scenario,
                            ],
                            directory,
                            output=True,
                        )
                        processes.append(backend)
                        share_listener(backend, owned_listener)
                        restart_deadline = min(deadline, time.monotonic() + 30)
                        await_value(
                            backend, reservation_queue(backend), restart_deadline, stop_file
                        )
                        configure_backend(backend, origin, authorization_key)
                        while not (ready_local() and ready_public(origin)):
                            if (
                                time.monotonic() >= restart_deadline
                                or stop_file.exists()
                                or backend.poll() is not None
                            ):
                                raise PreparationError("synthetic-restart-readiness-timeout")
                            time.sleep(0.1)
                        if time.monotonic() >= restart_deadline:
                            raise PreparationError("synthetic-restart-readiness-timeout")
                        (CONTROL / "owner.json").write_text(
                            json.dumps(
                                {
                                    "supervisor_pid": os.getpid(),
                                    "backend_pid": backend.pid,
                                    "tunnel_helper_pid": tunnel.pid,
                                    "scenario": scenario,
                                }
                            )
                        )
                        print('{"status":"backend-restarted"}', flush=True)
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
        # All owned backend/tunnel helpers have been stopped before releasing the port.
        if owned_listener is not None:
            owned_listener.close()
        for name in ("owner.json", "stop", "restart-backend"):
            (CONTROL / name).unlink(missing_ok=True)
        CONTROL.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--activate-public-synthetic", action="store_true")
    modes.add_argument("--stop", action="store_true")
    modes.add_argument("--restart-backend", action="store_true")
    modes.add_argument("--backend-helper", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--tunnel-helper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--cloudflared", type=Path, default=BINARY)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS)
    parser.add_argument(
        "--scenario",
        choices=[
            "baseline",
            "failures",
            "navigation",
            "subtitles",
            "lifecycle",
            "resume",
            "recovery",
            "remember",
        ],
        default="baseline",
    )
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--authenticated-file-candidate",
        action="store_true",
        help="Default-off synthetic File model, only with --scenario resume; "
        "not activation approval",
    )
    args = parser.parse_args()
    try:
        candidate_option(args.scenario, args.authenticated_file_candidate)
        if args.authenticated_file_candidate and (args.stop or args.tunnel_helper):
            raise PreparationError("candidate-incompatible-mode")
        candidate_options = (
            {"authenticated_file_candidate": True} if args.authenticated_file_candidate else {}
        )
        if not 1 <= args.seconds <= MAX_SECONDS:
            raise PreparationError("invalid-lifetime")
        if args.backend_helper:
            if args.scenario == "remember":
                _owned_backend_job = enter_kill_on_close_job()
            backend_helper(args.seconds, args.scenario, **candidate_options)
        elif args.tunnel_helper:
            _owned_job = enter_kill_on_close_job()
            tunnel_helper(args.cloudflared.resolve(), args.directory, args.seconds, args.scenario)
        elif args.restart_backend:
            owner = json.loads((CONTROL / "owner.json").read_text())
            if owner.get("scenario") != "remember":
                raise PreparationError("no-owned-remember-run")
            (CONTROL / "restart-backend").touch()
            print('{"status":"backend-restart-requested"}')
        elif args.stop:
            if not (CONTROL / "owner.json").is_file():
                raise PreparationError("no-owned-run")
            (CONTROL / "stop").touch()
            print('{"status":"stop-requested"}')
        elif args.activate_public_synthetic:
            if os.name != "nt":
                raise PreparationError("activation-requires-reviewed-windows-supervision")
            activate(args.cloudflared.resolve(), args.seconds, args.scenario, **candidate_options)
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
                        "scenario": args.scenario,
                        **delivery_marker(args.authenticated_file_candidate),
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
