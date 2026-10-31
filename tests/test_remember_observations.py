import asyncio
import json

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tools.lab import build_lab
from tools.remember_observations import (
    LIMIT,
    RememberObservationMiddleware,
    RememberObservations,
)
from tools.synthetic_https import build_public_synthetic_lab

START = {"type": "http.response.start", "status": 200, "headers": [(b"x-test", b"secret")]}
FINAL = {"type": "http.response.body", "body": b"secret", "more_body": False}
SCOPE = {"type": "http", "method": "GET", "path": "/msx/remember.html"}


async def receive():
    return {"type": "http.disconnect"}


def run_app(messages, *, send_error=None, app_error=None, observations=None, scope=None):
    observations = observations or RememberObservations()
    sent = []

    async def app(actual_scope, actual_receive, send):
        assert actual_scope is (SCOPE if scope is None else scope)
        assert actual_receive is receive
        for message in messages:
            await send(message)
        if app_error is not None:
            raise app_error

    async def send(message):
        if send_error is not None and message["type"] == "http.response.body":
            raise send_error
        sent.append(message)

    asyncio.run(
        RememberObservationMiddleware(app, observations=observations)(
            SCOPE if scope is None else scope, receive, send
        )
    )
    assert all(actual is original for actual, original in zip(sent, messages, strict=True))
    return observations.snapshot(), sent


@pytest.mark.parametrize("final", [False, True])
def test_identical_headers_do_not_imply_final_body(final):
    messages = [START, FINAL] if final else [START]
    report, sent = run_app(messages)
    row = report["plugin_html"]
    assert sent == messages
    assert row["received"] == row["response_start_send_returned"]["200"] == 1
    assert row["final_body_send_returned"] == int(final)
    assert row["incomplete"] == int(not final)
    assert row["aborted"] == 0


def test_streaming_counts_only_after_final_send_returns_and_preserves_bytes():
    observations = RememberObservations()
    chunks = [START, {"type": "http.response.body", "body": b"first", "more_body": True}, FINAL]
    observed = []

    async def app(scope, receive, send):
        for message in chunks:
            await send(message)
            observed.append(observations.snapshot()["plugin_html"])

    async def send(message):
        assert observations.counts["plugin_html"]["final_body_send_returned"] == 0
        assert message is chunks[len(observed)]
        await asyncio.sleep(0)

    asyncio.run(RememberObservationMiddleware(app, observations=observations)(SCOPE, receive, send))
    assert [row["final_body_send_returned"] for row in observed] == [0, 0, 1]


@pytest.mark.parametrize("error", [RuntimeError("secret exception"), asyncio.CancelledError()])
@pytest.mark.parametrize("phase", ["start", "body", "after_final"])
def test_send_failure_and_cancellation_propagate_without_false_completion(error, phase):
    observations = RememberObservations()

    async def app(scope, receive, send):
        await send(START)
        await send(FINAL)
        raise error

    async def send(message):
        if (phase == "start" and message is START) or (phase == "body" and message is FINAL):
            raise error

    with pytest.raises(type(error)) as raised:
        asyncio.run(
            RememberObservationMiddleware(app, observations=observations)(SCOPE, receive, send)
        )
    assert raised.value is error
    row = observations.snapshot()["plugin_html"]
    assert row["response_start_send_returned"]["200"] == int(phase != "start")
    assert row["final_body_send_returned"] == int(phase == "after_final")
    assert row["incomplete"] == int(phase != "after_final")
    assert row["aborted"] == 1
    assert "secret" not in json.dumps(observations.snapshot())


def test_observed_disconnect_after_final_does_not_retract_asgi_completion():
    observations = RememberObservations()

    async def app(scope, actual_receive, send):
        await send(START)
        await send(FINAL)
        assert await actual_receive() == {"type": "http.disconnect"}

    async def send(message):
        pass

    asyncio.run(RememberObservationMiddleware(app, observations=observations)(SCOPE, receive, send))
    row = observations.snapshot()["plugin_html"]
    assert row["final_body_send_returned"] == 1
    assert row["aborted"] == row["incomplete"] == 0


def test_duplicate_messages_forwarded_once_each_but_counted_once_per_request():
    report, sent = run_app([START, START, FINAL, FINAL])
    assert len(sent) == 4
    assert report["plugin_html"]["response_start_send_returned"]["200"] == 1
    assert report["plugin_html"]["final_body_send_returned"] == 1


def test_concurrent_requests_keep_independent_completion_state():
    observations = RememberObservations()

    async def app(scope, receive, send):
        await send(START)
        await asyncio.sleep(0)
        if scope["complete"]:
            await send(FINAL)

    async def send(message):
        await asyncio.sleep(0)

    async def run():
        middleware = RememberObservationMiddleware(app, observations=observations)
        await asyncio.gather(
            *(middleware({**SCOPE, "complete": n % 2}, receive, send) for n in range(20))
        )

    asyncio.run(run())
    row = observations.snapshot()["plugin_html"]
    assert row["received"] == row["response_start_send_returned"]["200"] == 20
    assert row["final_body_send_returned"] == row["incomplete"] == 10


def test_exact_categories_ignore_lookalikes_and_retain_no_secrets():
    observations = RememberObservations()
    paths = [
        ("GET", "/pair"),
        ("POST", "/pair"),
        ("GET", "/api/device-authorization/pair"),
        ("POST", "/api/device-authorization/pair"),
        ("POST", "/api/device-authorization/renew"),
        ("GET", "/msx/start.json"),
        ("GET", "/msx/remember.json"),
        ("GET", "/msx/remember.html"),
        ("GET", "/msx/remember.js"),
        ("GET", "/msx/device/secret-capability/home.json"),
        ("GET", "/evil/remember.html"),
        ("POST", "/msx/remember.html"),
        ("GET", "/msx/device//home.json"),
        ("GET", "/msx/device/secret-capability/extra/home.json"),
        ("GET", "/msx/device/secret-capability/home.json/"),
    ]
    for method, path in paths:
        run_app(
            [START, FINAL],
            observations=observations,
            scope={
                **SCOPE,
                "method": method,
                "path": path,
                "query_string": b"renewal=secret-query",
                "headers": [(b"authorization", b"secret-header")],
            },
        )
    assert all(row["received"] == 1 for row in observations.snapshot().values())
    assert "secret" not in json.dumps(vars(observations))


def test_fixed_status_buckets_saturation_and_snapshot_isolation():
    observations = RememberObservations()
    observations.counts["plugin_html"]["received"] = LIMIT
    report, _ = run_app([{**START, "status": 599}, FINAL], observations=observations)
    assert report["plugin_html"]["received"] == LIMIT
    assert report["plugin_html"]["response_start_send_returned"]["other"] == 1
    report["plugin_html"]["response_start_send_returned"]["other"] = 99
    assert observations.snapshot()["plugin_html"]["response_start_send_returned"]["other"] == 1


def test_non_http_scope_passes_through_unchanged():
    report, sent = run_app([{"type": "lifespan.startup.complete"}], scope={"type": "lifespan"})
    assert sent == [{"type": "lifespan.startup.complete"}]
    assert all(row["received"] == 0 for row in report.values())


def test_outer_generated_500_is_not_counted_as_observed_response():
    observations = RememberObservations()
    app = FastAPI()
    app.add_middleware(RememberObservationMiddleware, observations=observations)

    @app.get("/msx/remember.html")
    async def fail():
        raise RuntimeError("secret")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/msx/remember.html").status_code == 500
    row = observations.snapshot()["plugin_html"]
    assert row["received"] == row["aborted"] == row["incomplete"] == 1
    assert sum(row["response_start_send_returned"].values()) == 0


def test_only_remember_synthetic_report_has_counters_and_http200_is_not_auth(tmp_path):
    app, _, _ = build_public_synthetic_lab(
        "https://synthetic-test.trycloudflare.com",
        allow_public_synthetic=True,
        scenario="remember",
        authorization_key=Fernet.generate_key().decode(),
        state_directory=tmp_path,
    )
    with TestClient(app, base_url="https://synthetic-test.trycloudflare.com") as client:
        assert client.get("/msx/remember.html", headers={"host": "wrong.test"}).status_code == 400
        before = client.get("/__lab/report").json()["remember_asgi"]
        assert all(row["received"] == 0 for row in before.values())
        for path in ("start.json", "remember.json", "remember.html", "remember.js"):
            assert client.get("/msx/" + path).status_code == 200
        denied = client.get("/msx/device/secret-capability/home.json")
        assert denied.status_code == 200 and denied.json()["response"]["status"] == 401
        report = client.get("/__lab/report").json()
        row = report["remember_asgi"]["private_home"]
        assert row["response_start_send_returned"]["200"] == row["final_body_send_returned"] == 1
        assert report["paired_sessions"] == 0
        assert "secret-capability" not in json.dumps(report)
    baseline, _, _ = build_public_synthetic_lab(
        "https://synthetic-test.trycloudflare.com", allow_public_synthetic=True
    )
    with TestClient(baseline, base_url="https://synthetic-test.trycloudflare.com") as client:
        assert "remember_asgi" not in client.get("/__lab/report").json()
    from jellyfin_msx.config import Settings

    real_lab, _ = build_lab(Settings("https://localhost:18091", "https://jellyfin.test"))
    with TestClient(real_lab) as client:
        assert "remember_asgi" not in client.get("/__lab/report").json()
