"""Mock-only security expectations, never evidence of real-server compatibility."""

import asyncio
import json
import logging
import traceback

import httpx
import pytest

from tools.media_revocation import RevocationFailure, verify_revoked_original


@pytest.mark.parametrize("status", [401, 403])
def test_revoked_original_requires_denial_without_media(status, capsys):
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx.Response(status, content=b"denied")

    asyncio.run(
        verify_revoked_original(
            "https://fixture.test/media",
            b"independent-media-prefix",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].headers["range"] == "bytes=0-1023"
    assert requests[0].headers["cache-control"] == "no-cache"
    assert "authorization" not in requests[0].headers
    assert json.loads(capsys.readouterr().out) == {
        "logout_media_status": status,
        "matches_original_prefix": False,
    }


@pytest.mark.parametrize("status", [200, 206, 302])
def test_successful_media_and_redirect_cannot_pass_revocation(status, capsys):
    requests = []
    prefix = b"synthetic-original-prefix"

    def upstream(request):
        requests.append(request)
        return httpx.Response(status, content=prefix, headers={"Location": "https://other.test/"})

    with pytest.raises(RevocationFailure, match=f"fresh logged-out media HTTP {status}"):
        asyncio.run(
            verify_revoked_original(
                "https://fixture.test/media",
                prefix,
                transport=httpx.MockTransport(upstream),
            )
        )
    assert len(requests) == 1  # The redirect destination is never requested.
    output = json.loads(capsys.readouterr().out)
    assert output == {"logout_media_status": status, "matches_original_prefix": True}


@pytest.mark.parametrize("status", [401, 403])
def test_denial_status_cannot_hide_original_bytes(status, capsys):
    prefix = b"synthetic-original-prefix"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, content=b"wrapper" + prefix + b"suffix")
    )
    with pytest.raises(RevocationFailure, match="denial body contains original media bytes"):
        asyncio.run(
            verify_revoked_original("https://fixture.test/media", prefix, transport=transport)
        )
    assert json.loads(capsys.readouterr().out)["matches_original_prefix"] is True


def test_revoked_response_bound_and_output_do_not_reflect_body(capsys):
    body = b"synthetic-private-response-" * 100
    transport = httpx.MockTransport(lambda request: httpx.Response(401, content=body))
    with pytest.raises(RevocationFailure, match="revoked range body exceeds bound"):
        asyncio.run(
            verify_revoked_original(
                "https://fixture.test/media", b"synthetic-original-prefix", transport=transport
            )
        )
    assert capsys.readouterr().out == ""


def test_standalone_observer_suppresses_request_target_logs(caplog):
    caplog.set_level(logging.INFO, logger="httpx")
    caplog.set_level(logging.DEBUG, logger="httpcore")
    transport = httpx.MockTransport(lambda request: httpx.Response(401, content=b"denied"))
    asyncio.run(
        verify_revoked_original(
            "https://fixture.test/media?ApiKey=synthetic-redaction-marker",
            b"synthetic-original-prefix",
            transport=transport,
        )
    )
    assert "synthetic-redaction-marker" not in caplog.text
    assert "fixture.test" not in caplog.text


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.InvalidURL, TimeoutError])
def test_standalone_transport_failures_do_not_expose_request_target(failure, caplog, capsys):
    caplog.set_level(logging.INFO, logger="httpx")
    target = "https://fixture.test/media?ApiKey=synthetic-redaction-marker"

    def upstream(request):
        raise failure(target)

    with pytest.raises(RevocationFailure, match="revoked request transport failed") as caught:
        asyncio.run(
            verify_revoked_original(
                target, b"synthetic-original-prefix", transport=httpx.MockTransport(upstream)
            )
        )
    evidence = (
        "".join(traceback.format_exception(caught.value)) + caplog.text + capsys.readouterr().out
    )
    assert "synthetic-redaction-marker" not in evidence
    assert "fixture.test" not in evidence
