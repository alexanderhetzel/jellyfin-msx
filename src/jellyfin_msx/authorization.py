"""Optional durable renewal authority; no session capability or password is persisted."""

import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .errors import PortalError


def verifier(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


class AuthorizationStore:
    def __init__(self, settings, clock=time.time):
        self.settings, self.clock = settings, clock
        self.path = Path(settings.authorization_db)
        try:
            self.cipher = Fernet(settings.authorization_key.encode())
            # The operator must protect the containing directory/Windows ACL and backups.
            if self.path.is_symlink() or not self.path.parent.is_dir():
                raise ValueError
            if os.name != "nt" and self.path.parent.stat().st_mode & 0o077:
                raise ValueError
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            if os.name != "nt" and self.path.stat().st_mode & 0o077:
                raise ValueError("Authorization database permissions are not private") from None
        except (OSError, ValueError, TypeError):
            raise ValueError("Invalid authorization key or protected database location") from None
        try:
            with self.transaction() as db:
                db.execute("CREATE TABLE IF NOT EXISTS metadata (value BLOB NOT NULL)")
                marker = db.execute("SELECT value FROM metadata").fetchall()
                expected = ("jellyfin-msx.authorization.v1:" + settings.jellyfin_url).encode()
                if not marker:
                    # A pre-existing device table without metadata must not be adopted.
                    if db.execute(
                        "SELECT 1 FROM sqlite_master WHERE name='authorizations'"
                    ).fetchone():
                        raise ValueError
                    db.execute("INSERT INTO metadata VALUES (?)", (self.cipher.encrypt(expected),))
                elif len(marker) != 1 or self.cipher.decrypt(marker[0][0]) != expected:
                    raise ValueError
                db.execute(
                    "CREATE TABLE IF NOT EXISTS authorizations ("
                    "id TEXT PRIMARY KEY, verifier TEXT UNIQUE NOT NULL, "
                    "generation INTEGER NOT NULL, expires REAL NOT NULL, payload BLOB NOT NULL)"
                )
                if [r[1] for r in db.execute("PRAGMA table_info(authorizations)")] != [
                    "id",
                    "verifier",
                    "generation",
                    "expires",
                    "payload",
                ]:
                    raise ValueError
        except (PortalError, InvalidToken, ValueError):
            raise ValueError("Authorization database/key/schema validation failed") from None

    @contextmanager
    def transaction(self):
        db = None
        try:
            # Refuse to silently recreate a removed database while the process is running.
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=2)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except (sqlite3.Error, OSError):
            raise PortalError(503, "Authorization storage unavailable. Try again later.") from None
        finally:
            if db is not None:
                db.close()

    def _payload(self, row):
        try:
            data = json.loads(self.cipher.decrypt(row[4]))
            if (
                set(data)
                != {"schema", "id", "server", "user", "token", "expires", "verifier", "generation"}
                or data["schema"] != 1
                or data["id"] != row[0]
                or data["expires"] != row[3]
                or data["verifier"] != row[1]
                or data["generation"] != row[2]
                or data["server"] != self.settings.jellyfin_url
                or not isinstance(data["user"], str)
                or not data["user"]
                or not isinstance(data["token"], str)
                or not data["token"]
            ):
                raise ValueError
            return data
        except (InvalidToken, ValueError, TypeError):
            raise PortalError(401, "Authorization unavailable. Pair this device again.") from None

    def enroll(self, device):
        renewal = secrets.token_urlsafe(32)
        expires = self.clock() + self.settings.authorization_ttl
        data = {
            "schema": 1,
            "id": device.device_id,
            "server": self.settings.jellyfin_url,
            "user": device.user_id,
            "token": device.token,
            "expires": expires,
            "verifier": verifier(renewal),
            "generation": 0,
        }
        payload = self.cipher.encrypt(json.dumps(data).encode())
        with self.transaction() as db:
            db.execute("DELETE FROM authorizations WHERE expires <= ?", (self.clock(),))
            if db.execute(
                "SELECT 1 FROM authorizations WHERE id=?", (device.device_id,)
            ).fetchone():
                raise PortalError(
                    409, "Device already enrolled. Pair again if its secret was lost."
                )
            if (
                db.execute("SELECT count(*) FROM authorizations").fetchone()[0]
                >= self.settings.max_states
            ):
                raise PortalError(503, "Authorization capacity reached. Retry later.")
            db.execute(
                "INSERT INTO authorizations VALUES (?, ?, 0, ?, ?)",
                (device.device_id, verifier(renewal), expires, payload),
            )
        return renewal, expires

    def rotate(self, renewal):
        if not isinstance(renewal, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", renewal):
            raise PortalError(401, "Authorization missing or expired. Pair this device again.")
        replacement = secrets.token_urlsafe(32)
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM authorizations WHERE verifier=? AND expires>?",
                (verifier(renewal), self.clock()),
            ).fetchone()
            if row is None:
                raise PortalError(401, "Authorization missing or expired. Pair this device again.")
            data = self._payload(row)
            generation = row[2] + 1
            data.update(verifier=verifier(replacement), generation=generation)
            db.execute(
                "UPDATE authorizations SET verifier=?, generation=?, payload=? WHERE id=?",
                (
                    verifier(replacement),
                    generation,
                    self.cipher.encrypt(json.dumps(data).encode()),
                    row[0],
                ),
            )
        return data, generation, replacement

    def validate(self, device):
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM authorizations WHERE id=? AND generation=? AND expires>?",
                (device.device_id, device.authorization_generation, self.clock()),
            ).fetchone()
            if row is None:
                raise PortalError(401, "Authorization missing or expired. Pair this device again.")
            data = self._payload(row)
            if data["user"] != device.user_id or data["token"] != device.token:
                raise PortalError(401, "Authorization unavailable. Pair this device again.")

    def revoke(self, device_id):
        with self.transaction() as db:
            db.execute("DELETE FROM authorizations WHERE id=?", (device_id,))
