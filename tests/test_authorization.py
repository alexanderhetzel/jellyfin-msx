import asyncio
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from conftest import TOKEN, USER, FakeJellyfin
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from jellyfin_msx.app import create_app
from jellyfin_msx.authorization import AuthorizationStore, verifier
from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.middleware import PairBodyLimit
from jellyfin_msx.state import State


@pytest.fixture
def durable(tmp_path):
    tmp_path.chmod(0o700)
    return Settings(
        "https://portal.test",
        "https://jellyfin.test/jellyfin",
        authorization_db=str(tmp_path / "authority.sqlite"),
        authorization_key=Fernet.generate_key().decode(),
        authorization_ttl=100,
        session_ttl=20,
    )


def paired(state):
    secret, device = state.pair()
    state.complete(device, USER, TOKEN)
    return secret, device


def test_restart_rotation_expiry_and_generation(durable):
    wall = [1000.0]
    first = State(durable, wall_clock=lambda: wall[0])
    old, device = paired(first)
    renewal, expiry = first.remember(old)
    assert expiry == 1100
    second = State(durable, wall_clock=lambda: wall[0])
    with pytest.raises(PortalError):
        second.get(old)
    fresh, replacement, new_expiry = second.restore(renewal)
    assert new_expiry == expiry
    assert second.get(fresh).device_id == device.device_id
    assert second.get(fresh).authorization_generation == 1
    for state, secret in [(first, old), (second, old)]:
        with pytest.raises(PortalError):
            state.get(secret)
    with pytest.raises(PortalError):
        first.restore(renewal)
    third = State(durable, wall_clock=lambda: wall[0])
    wall[0] = expiry
    with pytest.raises(PortalError):
        third.restore(replacement)
    with pytest.raises(PortalError):
        second.get(fresh)


def test_session_expiry_does_not_delete_renewal(durable):
    monotonic = [100.0]
    state = State(durable, clock=lambda: monotonic[0])
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    monotonic[0] += durable.session_ttl
    with pytest.raises(PortalError):
        state.get(secret)
    fresh, _, _ = state.restore(renewal)
    assert state.get(fresh).token == TOKEN


def test_concurrent_independent_stores_have_one_rotation_winner(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    stores = [AuthorizationStore(durable) for _ in range(8)]

    def rotate(store):
        try:
            return store.rotate(renewal)
        except PortalError as error:
            assert error.status == 401
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(rotate, stores))
    assert sum(result is not None for result in results) == 1


def test_revocation_denies_all_sessions_and_survives_restart(durable):
    first = State(durable)
    secret, device = paired(first)
    renewal, _ = first.remember(secret)
    second = State(durable)
    fresh, replacement, _ = second.restore(renewal)
    second.remove(fresh)
    assert device.authorization_generation == 0
    with pytest.raises(PortalError):
        first.get(secret)
    with pytest.raises(PortalError):
        State(durable).restore(replacement)


def test_ciphertext_contains_no_plaintext_secrets_and_key_not_in_repr(durable):
    state = State(durable)
    secret, device = paired(state)
    renewal, _ = state.remember(secret)
    state.restore(renewal)
    raw = Path(durable.authorization_db).read_bytes()
    for value in [TOKEN, USER, secret, renewal, "test-password"]:
        assert value.encode() not in raw
    assert durable.authorization_key not in repr(durable)
    assert TOKEN not in repr(device)


def test_key_server_corruption_schema_and_deleted_database_fail_closed(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    for changed in [
        replace(durable, authorization_key=Fernet.generate_key().decode()),
        replace(durable, jellyfin_url="https://other.test"),
    ]:
        with pytest.raises(ValueError, match="validation failed"):
            State(changed)
    with closing(sqlite3.connect(durable.authorization_db)) as db, db:
        db.execute("UPDATE authorizations SET payload=?", (b"corrupt",))
    with pytest.raises(PortalError) as caught:
        state.restore(renewal)
    assert caught.value.status == 401
    with closing(sqlite3.connect(durable.authorization_db)) as db, db:
        db.execute("ALTER TABLE authorizations RENAME TO unrelated")
        db.execute("CREATE TABLE authorizations (unexpected TEXT)")
    with pytest.raises(ValueError):
        State(durable)
    Path(durable.authorization_db).unlink()
    with pytest.raises(PortalError) as caught:
        state.get(secret)
    assert caught.value.status == 503
    assert not Path(durable.authorization_db).exists()


@pytest.mark.parametrize(
    "column,value",
    [
        ("id", "f" * 32),
        ("generation", 9),
        ("expires", 99999999999),
        ("verifier", verifier("attacker-chosen")),
    ],
)
def test_plaintext_row_tampering_is_authenticated(durable, column, value):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    with closing(sqlite3.connect(durable.authorization_db)) as db, db:
        db.execute(f"UPDATE authorizations SET {column}=?", (value,))
    with pytest.raises(PortalError):
        state.get(secret)
    with pytest.raises(PortalError):
        state.restore(renewal)


def test_capacity_repeat_enrollment_and_device_isolation(durable):
    state = State(replace(durable, max_states=2))
    first, _ = paired(state)
    second, other = paired(state)
    renewal, _ = state.remember(first)
    with pytest.raises(PortalError) as caught:
        state.remember(first)
    assert caught.value.status == 409
    assert state.get(second) is other
    assert other.authorization_generation is None
    with pytest.raises(PortalError):
        state.restore(renewal)  # Capacity denial must not consume the renewal secret.
    state.remove(second)
    assert state.restore(renewal)
    # The store has its own bound, independent of the RAM session count.
    third, _ = paired(state)
    state.remember(third)
    state.devices.clear()
    fourth, _ = paired(state)
    with pytest.raises(PortalError) as caught:
        state.remember(fourth)
    assert caught.value.status == 503


def test_configuration_requires_external_key_and_https(durable):
    assert State(Settings("https://portal.test", "https://jellyfin.test")).authorizations is None
    for changes in [
        {"authorization_key": None},
        {"authorization_db": None},
        {"authorization_key": "invalid"},
        {"authorization_db": "relative.sqlite"},
        {"public_url": "http://portal.test", "allow_http": True},
        {"authorization_ttl": 0},
        {"authorization_ttl": 91 * 86400},
    ]:
        with pytest.raises(ValueError):
            State(replace(durable, **changes))


def test_api_requires_origin_json_capability_and_rejects_identity(durable, caplog):
    fake = FakeJellyfin()
    state = State(durable)
    secret, device = paired(state)
    other, _ = state.pair()
    app = create_app(durable, transport=httpx.MockTransport(fake.handle), state=state)
    path = "/api/device-authorization/"
    with TestClient(app, base_url=durable.public_url) as client:
        headers = {"Origin": durable.public_url}
        for origin in [None, "null", "https://attacker.test"]:
            assert (
                client.post(
                    path + "enroll",
                    json={"session": secret},
                    headers={"Origin": origin} if origin else {},
                ).status_code
                == 403
            )
        assert (
            client.post(path + "enroll", data={"session": secret}, headers=headers).status_code
            == 400
        )
        assert (
            client.post(
                path + "enroll",
                content="{",
                headers={**headers, "Content-Type": "application/json"},
            ).status_code
            == 400
        )
        assert (
            client.post(path + "enroll", json={"session": other}, headers=headers).status_code
            == 401
        )
        assert (
            client.post(
                path + "enroll", json={"session": device.device_id}, headers=headers
            ).status_code
            == 400
        )
        result = client.post(path + "enroll", json={"session": secret}, headers=headers)
        renewal = result.json()["renewal"]
        assert result.headers["Cache-Control"] == "no-store, private"
        assert result.headers["Referrer-Policy"] == "no-referrer"
        response = client.post(path + "renew", json={"renewal": renewal}, headers=headers)
        assert response.status_code == 200
        fresh = response.json()["session"]
        assert (
            client.get(f"/msx/device/{fresh}/home.json").json()["headline"] == "Jellyfin libraries"
        )
        assert (
            client.post(path + "renew", json={"renewal": renewal}, headers=headers).status_code
            == 401
        )
        assert client.get(path + "renew").status_code == 405
        assert client.get(f"/api/device/{secret}/diagnostics").status_code == 401
        for value in [secret, renewal, TOKEN, response.json()["renewal"]]:
            assert value not in caplog.text
    assert all("authorization" not in r.url.path.lower() for r in fake.requests)


def test_upstream_restore_failure_revokes_consumed_authorization(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    fake = FakeJellyfin()
    fake.error = 401
    app = create_app(durable, transport=httpx.MockTransport(fake.handle), state=state)
    with TestClient(app, base_url=durable.public_url) as client:
        response = client.post(
            "/api/device-authorization/renew",
            json={"renewal": renewal},
            headers={"Origin": durable.public_url},
        )
        assert response.status_code == 401
    assert not state.devices
    with closing(sqlite3.connect(durable.authorization_db)) as db, db:
        assert db.execute("SELECT count(*) FROM authorizations").fetchone()[0] == 0


def test_logout_revokes_before_failed_upstream_logout(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    fake = FakeJellyfin()
    fake.logout_error = True
    app = create_app(durable, transport=httpx.MockTransport(fake.handle), state=state)
    with TestClient(app, base_url=durable.public_url) as client:
        response = client.get(f"/msx/device/{secret}/logout.json")
        assert "Upstream logout failed" in response.json()["headline"]
    with pytest.raises(PortalError):
        State(durable).restore(renewal)


def test_rotation_response_loss_is_strict_repair_not_replay(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    state.restore(renewal)  # Discard response, as if the client failed to persist it.
    with pytest.raises(PortalError):
        State(durable).restore(renewal)


@pytest.mark.parametrize("path", ["enroll", "renew"])
def test_oversized_chunked_authorization_rejected_before_application(path):
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    messages = iter(
        [
            {"type": "http.request", "body": b"a" * 5000, "more_body": True},
            {"type": "http.request", "body": b"a" * 5000, "more_body": False},
        ]
    )
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    asyncio.run(
        PairBodyLimit(app)(
            {"type": "http", "method": "POST", "path": f"/api/device-authorization/{path}"},
            receive,
            send,
        )
    )
    assert sent[0]["status"] == 413
    assert not called


def test_expired_records_are_pruned_before_capacity_check(durable):
    wall = [1000.0]
    state = State(replace(durable, max_states=1), wall_clock=lambda: wall[0])
    secret, _ = paired(state)
    state.remember(secret)
    wall[0] += durable.authorization_ttl
    state.devices.clear()
    fresh, _ = paired(state)
    assert state.remember(fresh)


def test_normal_csrf_pairing_then_body_only_restore_after_restart(durable):
    fake = FakeJellyfin()
    state = State(durable)
    app = create_app(durable, transport=httpx.MockTransport(fake.handle), state=state)
    headers = {"Origin": durable.public_url}
    with TestClient(app, base_url=durable.public_url) as client:
        secret, device = state.pair()
        code = device.code
        from conftest import code_stage

        fields = code_stage(client, code)
        result = client.post(
            "/pair",
            headers=headers,
            data={**fields, "username": "viewer", "password": "test-password"},
        )
        assert result.status_code == 200 and "TV paired" in result.text
        with pytest.raises(PortalError):
            state.claim(code)
        renewal = client.post(
            "/api/device-authorization/enroll", json={"session": secret}, headers=headers
        ).json()["renewal"]
    restored = State(durable)
    app = create_app(durable, transport=httpx.MockTransport(fake.handle), state=restored)
    with TestClient(app, base_url=durable.public_url) as client:
        result = client.post(
            "/api/device-authorization/renew", json={"renewal": renewal}, headers=headers
        )
        assert result.status_code == 200
        assert restored.get(result.json()["session"]).token == TOKEN
    assert b"test-password" not in Path(durable.authorization_db).read_bytes()


def test_database_busy_and_failed_commit_do_not_fallback_or_consume(durable):
    state = State(durable)
    secret, _ = paired(state)
    renewal, _ = state.remember(secret)
    with closing(sqlite3.connect(durable.authorization_db)) as db:
        db.execute("BEGIN EXCLUSIVE")
        with pytest.raises(PortalError) as caught:
            state.restore(renewal)
        assert caught.value.status == 503
        db.rollback()
        db.execute(
            "CREATE TRIGGER fail_rotation BEFORE UPDATE ON authorizations "
            "BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END"
        )
        db.commit()
        with pytest.raises(PortalError) as caught:
            state.restore(renewal)
        assert caught.value.status == 503
        assert state.get(secret).token == TOKEN
        db.execute("DROP TRIGGER fail_rotation")
        db.commit()
    assert state.restore(renewal)


def test_wal_and_sqlite_backup_do_not_contain_plaintext_credentials(durable, tmp_path):
    state = State(durable)
    secret, _ = paired(state)
    backup = tmp_path / "backup.sqlite"
    with closing(sqlite3.connect(durable.authorization_db)) as db:
        assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        renewal, _ = state.remember(secret)
        _, replacement, _ = state.restore(renewal)
        with closing(sqlite3.connect(backup)) as target:
            db.backup(target)
        files = [Path(durable.authorization_db), Path(durable.authorization_db + "-wal"), backup]
        assert files[1].exists()
        for path in files:
            raw = path.read_bytes()
            for value in [TOKEN, USER, secret, renewal, replacement, "test-password"]:
                assert value.encode() not in raw


@pytest.mark.skipif(os.name == "nt", reason="Windows ACLs are an operator requirement")
def test_posix_database_directory_and_file_permissions(durable):
    path = Path(durable.authorization_db)
    path.parent.chmod(0o755)
    with pytest.raises(ValueError):
        State(durable)
    path.parent.chmod(0o700)
    State(durable)
    assert path.stat().st_mode & 0o077 == 0
    path.chmod(0o644)
    with pytest.raises(ValueError):
        State(durable)


def test_nested_json_is_fixed_error_and_disabled_routes_grant_nothing():
    settings = Settings("https://portal.test", "https://jellyfin.test")
    fake = FakeJellyfin()
    state = State(settings)
    secret, _ = paired(state)
    app = create_app(settings, transport=httpx.MockTransport(fake.handle), state=state)
    with TestClient(app, base_url=settings.public_url) as client:
        headers = {"Origin": settings.public_url, "Content-Type": "application/json"}
        result = client.post(
            "/api/device-authorization/renew",
            content='{"renewal":' + "[" * 1200 + "0" + "]" * 1200 + "}",
            headers=headers,
        )
        assert result.status_code == 400
        result = client.post(
            "/api/device-authorization/enroll", json={"session": secret}, headers=headers
        )
        assert result.status_code == 404
    assert not fake.requests
