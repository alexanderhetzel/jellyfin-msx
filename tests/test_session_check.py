import json
import subprocess
import sys

import httpx
import pytest

from jellyfin_msx.config import Settings
from tools import session_check
from tools.synthetic_check import ContractFailure


def test_two_session_contract_has_no_operator_or_real_transport_fallback(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Operator configuration or real network transport attempted")

    monkeypatch.setattr(Settings, "from_env", forbid)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "__init__", forbid)
    report = session_check.check()
    assert set(report) == {
        "result",
        "category",
        "checks",
        "browser_verified",
        "physical_device_verified",
        "native_media_revoked_by_portal_expiry",
    }
    assert report["result"] == "passed"
    assert report["browser_verified"] is report["physical_device_verified"] is False
    assert report["native_media_revoked_by_portal_expiry"] is False
    assert {
        "a-home-revoked",
        "a-browse-revoked",
        "a-detail-revoked",
        "a-resolver-revoked",
        "a-poster-revoked",
        "a-media-revoked",
        "b-survives-a-logout",
        "a-repair-recovery",
        "portal-absolute-expiry",
        "native-token-expiry-boundary",
    } <= set(report["checks"])
    assert not any(
        value in json.dumps(report) for value in ("https://", "ApiKey", "synthetic-password")
    )


def test_ignored_upstream_logout_fails_the_original_media_revocation_assertion():
    with pytest.raises(ContractFailure, match="^a-media-revoked$"):
        session_check.check("logout-ignored")


def test_fault_cli_fails_with_only_fixed_sanitized_fields():
    result = subprocess.run(
        [sys.executable, "-m", "tools.session_check", "--fault", "logout-ignored"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout) == {
        "result": "failed",
        "stage": "a-media-revoked",
        "category": "in-process-session-contract",
    }


def test_invalid_fault_stops_before_constructing_any_app(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Invalid option constructed an app")

    monkeypatch.setattr(session_check, "SessionFixture", forbid)
    with pytest.raises(ContractFailure, match="^invalid-fault$"):
        session_check.check("operator")
