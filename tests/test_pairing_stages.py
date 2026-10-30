import asyncio

import httpx
import pytest
from conftest import TOKEN, code_stage, hidden_fields
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.state import State, digest


def submit(portal, fields, **extra):
    return portal.client.post(
        "/pair", data={**fields, **extra}, headers={"Origin": portal.settings.public_url}
    )


def test_code_only_stage_and_legacy_combined_post_cannot_authenticate(portal):
    _, device = portal.state.pair()
    form = portal.client.get("/pair")
    assert 'name="code"' in form.text
    assert 'name="username"' not in form.text and 'name="password"' not in form.text
    result = submit(
        portal,
        hidden_fields(form),
        code=device.code,
        username="ignored",
        password="must-not-persist",
    )
    assert result.status_code == 200 and 'name="stage"' in result.text
    assert 'name="code"' not in result.text and device.code not in result.text
    assert not portal.fake.requests and device.token is None and not device.claiming
    assert "must-not-persist" not in result.text + repr(portal.state.__dict__)


@pytest.mark.parametrize("kind", ["invalid", "expired", "used", "claiming"])
def test_unavailable_codes_never_show_credentials(portal, kind):
    _, device = portal.state.pair()
    code = device.code
    if kind == "expired":
        portal.now[0] += portal.settings.pairing_ttl
    elif kind == "used":
        portal.state.complete(device, "1" * 32, TOKEN)
    elif kind == "claiming":
        device.claiming = True
    else:
        code = "invalid"
    result = submit(portal, hidden_fields(portal.client.get("/pair")), code=code)
    assert result.status_code == 400 and "Create new code" in result.text
    assert 'name="password"' not in result.text and 'name="code"' in result.text
    assert not portal.fake.requests


def test_activation_skips_manual_code_with_independent_pending_secret(portal):
    secret, device = portal.state.pair()
    response = portal.client.get(
        "/pair", params={"activation": device.activation}, follow_redirects=False
    )
    assert response.status_code == 303 and response.headers["location"] == "/pair"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    form = portal.client.get("/pair")
    assert form.headers["referrer-policy"] == "same-origin"
    assert "SameSite=strict" in form.headers["set-cookie"]
    assert 'name="stage"' in form.text and 'name="code"' not in form.text
    assert all(s not in form.text for s in (device.activation, secret, device.code))
    assert "pair_activation" not in portal.client.cookies
    result = submit(portal, hidden_fields(form), username="viewer", password="test-password")
    assert "TV paired" in result.text and portal.state.get(secret).token == TOKEN
    for activation in (secret, device.activation, "ä" * 40):
        portal.now[0] += 61  # Each activation now has two bounded GET handoff requests.
        response = portal.client.get("/pair", params={"activation": activation})
        assert response.status_code == 400 and 'name="password"' not in response.text


def test_expired_stage_denied_before_upstream_and_cannot_be_replayed(portal):
    _, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    portal.now[0] += portal.settings.pairing_ttl
    result = submit(portal, fields, username="viewer", password="test-password")
    assert result.status_code == 400 and "expired" in result.text
    assert 'name="code"' in result.text and not portal.fake.requests
    assert not portal.state.pairing_stages


@pytest.mark.parametrize("activation", ["invalid", "ä" * 40, "\U0001f512" * 8])
def test_invalid_activation_cleans_url_before_rendering_usable_code_recovery(portal, activation):
    response = portal.client.get("/pair", params={"activation": activation}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/pair"
    assert response.headers["referrer-policy"] == "no-referrer" and "<form" not in response.text
    assert "pair_activation=invalid" in response.headers["set-cookie"]
    recovery = portal.client.get("/pair")
    assert recovery.status_code == 400 and recovery.headers["referrer-policy"] == "same-origin"
    assert "Create new code" in recovery.text and 'name="password"' not in recovery.text
    assert "pair_activation" not in portal.client.cookies
    _, device = portal.state.pair()
    result = submit(portal, hidden_fields(recovery), code=device.code)
    assert result.status_code == 200 and 'name="stage"' in result.text
    assert not portal.fake.requests


def test_stage_cannot_change_device_and_replay_after_success_is_denied(portal):
    _, first = portal.state.pair()
    _, second = portal.state.pair()
    fields = code_stage(portal.client, first.code)
    result = submit(portal, fields, code=second.code, username="viewer", password="test-password")
    assert "TV paired" in result.text and first.token == TOKEN and second.token is None
    assert "pair_csrf" not in portal.client.cookies
    portal.client.cookies.set("pair_csrf", fields["csrf"], domain="portal.test", path="/pair")
    result = submit(portal, fields, username="viewer", password="test-password")
    assert result.status_code == 400 and len(portal.fake.requests) == 1


def test_new_tab_cookie_and_cross_browser_stage_swap_fail_closed(portal):
    _, first = portal.state.pair()
    _, second = portal.state.pair()
    old = code_stage(portal.client, first.code)
    new = code_stage(portal.client, second.code)
    assert submit(portal, old, username="viewer", password="test-password").status_code == 403
    # Even with the current CSRF token, a different form's grant is not transferable.
    current = hidden_fields(portal.client.get("/pair"))
    result = submit(
        portal, {**current, "stage": new["stage"]}, username="viewer", password="test-password"
    )
    assert result.status_code == 400 and not portal.fake.requests
    assert first.token is None and second.token is None


@pytest.mark.parametrize(
    "origin,csrf",
    [("https://evil.test", None), ("null", None), (None, None), ("https://portal.test", "ä" * 40)],
)
def test_credential_stage_csrf_denial(portal, origin, csrf):
    _, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    if csrf:
        fields["csrf"] = csrf
    result = portal.client.post(
        "/pair",
        data={**fields, "username": "viewer", "password": "secret"},
        headers={"Origin": origin} if origin else {},
    )
    assert result.status_code == 403 and not portal.fake.requests and not device.claiming


def test_bad_password_has_fresh_bound_retry_and_restart_link(portal):
    _, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    result = submit(portal, fields, username="viewer", password="wrong-password")
    assert result.status_code == 401 and 'href="/pair">Use a different TV code' in result.text
    retry = hidden_fields(result)
    assert retry["stage"] != fields["stage"] and not device.claiming
    assert "wrong-password" not in result.text + repr(portal.state.__dict__)
    assert "TV paired" in submit(portal, retry, username="viewer", password="test-password").text


def test_expiry_during_auth_revokes_upstream_token_and_cannot_pair(portal):
    _, device = portal.state.pair()
    original = portal.fake.handle

    def expire(request):
        response = original(request)
        if request.url.path.endswith("/AuthenticateByName"):
            portal.now[0] += portal.settings.pairing_ttl
        return response

    app = create_app(portal.settings, transport=httpx.MockTransport(expire), state=portal.state)
    with TestClient(app, base_url=portal.settings.public_url) as client:
        fields = code_stage(client, device.code)
        result = client.post(
            "/pair",
            data={**fields, "username": "viewer", "password": "test-password"},
            headers={"Origin": portal.settings.public_url},
        )
    assert result.status_code == 400 and "expired" in result.text
    assert device.token is None and not device.claiming
    assert portal.fake.requests[-1].url.path.endswith("/Sessions/Logout")


def test_bounded_stage_storage_and_absolute_pending_expiry():
    now = [0]
    state = State(
        Settings("https://portal.test", "https://jellyfin.test", max_states=1), clock=lambda: now[0]
    )
    _, device = state.pair()
    grant = state.stage(device, "browser-one")
    assert grant not in state.pairing_stages and digest(grant) in state.pairing_stages
    with pytest.raises(PortalError, match="capacity"):
        state.stage(device, "browser-two")
    replacement = state.stage(device, "browser-one")
    assert digest(grant) not in state.pairing_stages
    now[0] = device.expires
    with pytest.raises(PortalError):
        state.claim_stage(replacement, "browser-one")
    assert not state.pairing_stages


def test_code_guessing_stays_five_per_peer(portal):
    for _ in range(5):
        form = portal.client.get("/pair")
        assert submit(portal, hidden_fields(form), code="invalid").status_code == 400
    form = portal.client.get("/pair")
    assert submit(portal, hidden_fields(form), code="invalid").status_code == 429
    assert not portal.fake.requests


def test_credential_attempts_stay_bounded_and_activation_is_pending_only(portal):
    _, device = portal.state.pair()
    fields = code_stage(portal.client, device.code)
    for _ in range(5):
        result = submit(portal, fields, username="viewer", password="wrong-password")
        assert result.status_code == 401
        fields = hidden_fields(result)
    assert submit(portal, fields, username="viewer", password="test-password").status_code == 429
    assert len(portal.fake.requests) == 5 and device.token is None
    portal.now[0] += portal.settings.pairing_ttl
    result = portal.client.get("/pair", params={"activation": device.activation})
    assert result.status_code == 400 and 'name="password"' not in result.text


def test_concurrent_credential_submissions_make_only_one_upstream_request(portal):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def upstream(request):
            entered.set()
            await release.wait()
            return portal.fake.handle(request)

        app = create_app(
            portal.settings, transport=httpx.MockTransport(upstream), state=portal.state
        )
        _, device = portal.state.pair()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url=portal.settings.public_url
        ) as client:
            page = await client.get("/pair")
            headers = {"Origin": portal.settings.public_url}
            page = await client.post(
                "/pair", data={**hidden_fields(page), "code": device.code}, headers=headers
            )
            data = {**hidden_fields(page), "username": "viewer", "password": "test-password"}
            winner = asyncio.create_task(client.post("/pair", data=data, headers=headers))
            await asyncio.wait_for(entered.wait(), 2)
            loser = await client.post("/pair", data=data, headers=headers)
            assert loser.status_code == 400 and device.claiming
            release.set()
            assert "TV paired" in (await winner).text
            assert len(portal.fake.requests) == 1

    asyncio.run(scenario())
