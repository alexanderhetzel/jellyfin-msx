"""Isolated synthetic upstream session verifiers for remembered-device restart tests."""

import hashlib
import re
import sqlite3
from contextlib import closing

import httpx

from tools.synthetic_lab import SyntheticJellyfin


class RememberedSyntheticJellyfin(SyntheticJellyfin):
    """Normal synthetic login only; no network fallback or real account configuration."""

    def __init__(self, origin, path):
        super().__init__(origin)
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS synthetic_tokens (verifier TEXT PRIMARY KEY)")

    def handle(self, request):
        if str(request.url).split("/jellyfin", 1)[0] != self.origin:
            raise RuntimeError("Synthetic transport rejected an unexpected origin")
        path = request.url.path.removeprefix("/jellyfin")
        auth = re.search(r'Token="([A-Za-z0-9_-]{43})"', request.headers.get("authorization", ""))
        token = auth[1] if auth else ""
        digest = hashlib.sha256(token.encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            self.tokens.discard(token)
            if (
                token
                and db.execute(
                    "SELECT 1 FROM synthetic_tokens WHERE verifier=?", (digest,)
                ).fetchone()
            ):
                self.tokens.add(token)
            if (
                path == "/Users/AuthenticateByName"
                and db.execute("SELECT count(*) FROM synthetic_tokens").fetchone()[0] >= 32
            ):
                return httpx.Response(503)
            response = super().handle(request)
            if path == "/Users/AuthenticateByName" and response.status_code == 200:
                issued = response.json()["AccessToken"]
                db.execute(
                    "INSERT INTO synthetic_tokens VALUES (?)",
                    (hashlib.sha256(issued.encode()).hexdigest(),),
                )
            if path == "/Sessions/Logout" and response.status_code == 204:
                db.execute("DELETE FROM synthetic_tokens WHERE verifier=?", (digest,))
        return response
