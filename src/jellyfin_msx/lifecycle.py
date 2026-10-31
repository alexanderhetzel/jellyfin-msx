"""Bounded, RAM-only playback reconciliation; callbacks are intent, samples evidence."""

import asyncio
import hashlib
import json
import math
import secrets
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from .errors import PortalError

LEASE_SECONDS = 45
TICKS_PER_SECOND = 10_000_000
EVENTS = frozenset(
    (
        "video:load",
        "video:play",
        "video:pause",
        "video:stop",
        "video:seek",
        "video:restart",
        "video:speed",
        "app:suspend",
        "app:resume",
        "app:sleep",
        "app:awake",
        "app:connect",
        "app:disconnect",
    )
)


def invalid(status=400):
    return PortalError(status, "Playback report rejected.")


@dataclass(repr=False)
class PlaybackGrant:
    secret: str
    playback_id: str
    session_key: str
    item_id: str
    source_id: str
    play_session_id: str
    duration: float
    expires: float
    lease: float
    play_method: str = "DirectPlay"
    session_expires: float = 0
    highwater: int = 0
    digests: OrderedDict = field(default_factory=OrderedDict)
    position: float = 0
    previous_position: float | None = None
    started: bool = False
    paused: bool = False
    terminal: str | None = None
    requested: str | None = None
    intent_until: float = 0
    seek_target: float | None = None
    start_failed: bool = False
    start_delivered: bool = False
    failures: int = 0
    terminal_delivered: bool = False
    pending: deque = field(default_factory=deque)


class Lifecycle:
    def __init__(self, clock=time.monotonic, maximum=256):
        self.clock = clock
        self.maximum = maximum
        self.grants = {}
        self.active = {}
        self.rates = {}
        self.locks = {}
        self.lock_users = {}
        self.sweep_cursor = 0
        self.blocked_sessions = {}

    async def issue(
        self,
        session_key,
        item_id,
        source_id,
        play_session_id,
        duration,
        expires,
        play_method="DirectPlay",
        *,
        send=None,
    ):
        if not _number(duration, 864000) or duration <= 0 or expires <= self.clock():
            raise invalid()
        self.blocked_sessions = {
            key: expiry for key, expiry in self.blocked_sessions.items() if expiry > self.clock()
        }
        if session_key in self.blocked_sessions or len(self.blocked_sessions) >= self.maximum:
            raise invalid(503)
        if len(self.grants) >= self.maximum:
            raise invalid(503)
        async with self._locked(session_key):
            if session_key in self.blocked_sessions:
                raise invalid(503)
            previous = self.active.get(session_key)
            if previous:
                self._stop(previous, "replaced")
                if previous.started and not previous.terminal_delivered:
                    if send is not None:
                        await self._flush(previous, send)
                    # Jellyfin Stop can clear a newer item in the same session.
                    # Never publish the replacement until the old Stop is ACKed.
                    if not previous.terminal_delivered:
                        raise invalid(503)
            if len(self.grants) >= self.maximum or expires <= self.clock():
                raise invalid(503)
            grant = PlaybackGrant(
                secrets.token_urlsafe(32),
                secrets.token_hex(16),
                session_key,
                item_id,
                source_id,
                play_session_id,
                duration,
                expires,
                self.clock() + LEASE_SECONDS,
                play_method,
                session_expires=expires,
            )
            self.grants[_digest(grant.secret)] = grant
            self.active[session_key] = grant
            return grant

    @asynccontextmanager
    async def _locked(self, session_key):
        lock = self.locks.setdefault(session_key, asyncio.Lock())
        # Count waiting borrowers too: Lock.locked() can be false between
        # waking a waiter and that waiter actually acquiring the same lock.
        self.lock_users[session_key] = self.lock_users.get(session_key, 0) + 1
        try:
            async with lock:
                yield
        finally:
            self.lock_users[session_key] -= 1
            if not self.lock_users[session_key]:
                self.lock_users.pop(session_key)

    def _limit(self, session):
        now = self.clock()
        self.rates = {key: value for key, value in self.rates.items() if value[0] > now}
        for key, maximum in (("global", 1024), (session, 120)):
            until, count = self.rates.get(key, (now + 60, 0))
            if count >= maximum:
                raise invalid(429)
            self.rates[key] = (until, count + 1)

    def get(self, secret):
        grant = self.grants.get(_digest(secret))
        if (
            grant is None
            or grant.expires <= self.clock()
            or self.active.get(grant.session_key) is not grant
        ):
            raise invalid(401)
        return grant

    async def submit(self, secret, session_key, body, send):
        grant = self.get(secret)
        if grant.session_key != session_key:
            raise invalid(401)
        self._limit(session_key)
        rows = _validate(body, grant)
        async with self._locked(session_key):
            # Recheck after another in-flight report or generation replacement.
            if self.active.get(session_key) is not grant or grant.expires <= self.clock():
                raise invalid(401)
            if self.clock() >= grant.lease and not grant.terminal:
                self._stop(grant, "abandoned")
            # Validate the entire batch before applying any part of it.
            highwater = grant.highwater
            remembered = dict(grant.digests)
            for row, digest in rows:
                seq = row["seq"]
                if seq in remembered:
                    if remembered[seq] != digest:
                        raise invalid(409)
                elif seq <= highwater:
                    raise invalid(409)
                else:
                    highwater = seq
                    remembered[seq] = digest
            accepted = []
            for row, digest in rows:
                seq = row["seq"]
                if seq > grant.highwater:
                    self._observe(grant, row)
                    grant.highwater = seq
                    grant.digests[seq] = digest
                    while len(grant.digests) > 64:
                        grant.digests.popitem(last=False)
                accepted.append(seq)
            await self._flush(grant, send)
            return {"accepted": accepted}

    def _enqueue(self, grant, kind):
        if grant.start_failed and kind != "stop":
            return
        payload = {
            "ItemId": grant.item_id,
            "MediaSourceId": grant.source_id,
            "PlaySessionId": grant.play_session_id,
            "PositionTicks": round(min(grant.position, grant.duration) * TICKS_PER_SECOND),
            "IsPaused": grant.paused,
            "CanSeek": True,
            "PlayMethod": grant.play_method,
        }
        # Keep controls/start/terminal; one newest pending ordinary progress.
        attempts, due = 0, self.clock()
        if kind == "progress":
            previous = next((entry for entry in grant.pending if entry[0] == "progress"), None)
            if previous:
                attempts, due = previous[2], previous[3]
            grant.pending = deque(entry for entry in grant.pending if entry[0] != "progress")
        if len(grant.pending) >= 16:
            # At capacity discard superseded progress first; never grow the queue.
            grant.pending = deque(entry for entry in grant.pending if entry[0] == "start")
        grant.pending.append((kind, payload, attempts, due))

    def _stop(self, grant, reason):
        if grant.terminal:
            return
        grant.terminal = reason
        # Keep a finite terminal replay window rather than every item for an
        # entire eight-hour TV authorization. Pending retries remain bounded.
        grant.expires = min(grant.expires, self.clock() + 300)
        if grant.started:
            self._enqueue(grant, "stop")

    def _observe(self, grant, row):
        if grant.terminal:
            return
        data = row["data"]
        if row["kind"] == "event":
            name = row["name"]
            grant.requested = name
            if name == "video:stop":
                self._stop(grant, "stopped")
            elif name in ("video:seek", "video:restart"):
                # A requested target cannot advance or rewind observed progress.
                grant.previous_position = None
                grant.seek_target = row.get("target")
                grant.intent_until = self.clock() + 5
            elif name in ("video:pause", "video:play"):
                grant.intent_until = self.clock() + 5
            return
        if not _valid_sample(data, grant):
            return
        position, state = data["position"], data["state"]
        if data.get("ended") is True and grant.started and position >= grant.duration - 2:
            grant.position = position
            self._stop(grant, "ended")
            return
        if state not in (2, 3):
            return
        if self.clock() < grant.intent_until:
            if grant.requested == "video:pause" and state != 3:
                return
            if grant.requested == "video:play" and state != 2:
                return
            if grant.seek_target is not None and abs(position - grant.seek_target) > 5:
                return
        grant.seek_target = None
        grant.intent_until = 0
        grant.lease = min(grant.expires, self.clock() + LEASE_SECONDS)
        if not grant.started:
            if (
                state == 2
                and grant.previous_position is not None
                and position > grant.previous_position
            ):
                grant.position, grant.started = position, True
                self._enqueue(grant, "start")
            grant.previous_position = position
            return
        grant.position = position
        grant.paused = state == 3
        self._enqueue(grant, "progress")

    async def _flush(self, grant, send):
        # One lock / in-flight upload, finite attempts, no per-report tasks or sleeps.
        deadline = asyncio.get_running_loop().time() + 5
        for _ in range(16):
            if not grant.pending or grant.pending[0][3] > self.clock():
                return
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return
            kind, payload, attempts, _ = grant.pending.popleft()
            try:
                await asyncio.wait_for(send(kind, grant, payload), timeout=remaining)
                grant.failures = 0
                if kind == "start":
                    grant.start_delivered = True
                if kind == "stop":
                    grant.terminal_delivered = True
                    self.blocked_sessions.pop(grant.session_key, None)
            except (Exception, asyncio.CancelledError) as error:
                cancelled = isinstance(error, asyncio.CancelledError)
                grant.failures += 1
                if kind != "stop" and grant.failures >= 3:
                    grant.start_failed = kind == "start"
                    grant.pending.clear()
                    grant.terminal = "reporting_lost"
                    grant.expires = min(grant.expires, self.clock() + 300)
                    self._enqueue(grant, "stop")
                    # A start may have reached Jellyfin despite a lost response.
                    # The cleanup Stop has a separate finite retry budget.
                    self.blocked_sessions[grant.session_key] = grant.session_expires
                    if cancelled:
                        raise
                    return
                if attempts < 2:
                    grant.pending.appendleft(
                        (kind, payload, attempts + 1, self.clock() + 2**attempts)
                    )
                elif kind == "stop":
                    self.blocked_sessions[grant.session_key] = grant.session_expires
                if cancelled:
                    raise
                return

    async def expire(self, send, authorize):
        """Call from one supervised periodic task; authorize rechecks session revocation."""
        # Reconcile every lease before any network await. A stalled first host
        # must not keep an unrelated vanished player's state active indefinitely.
        for grant in tuple(self.grants.values()):
            authorized = authorize(grant)
            if not authorized:
                grant.pending.clear()
                grant.terminal = grant.terminal or "unauthorized"
            elif self.clock() >= min(grant.lease, grant.expires):
                self._stop(grant, "abandoned")
            if not authorized or (grant.expires <= self.clock() and not grant.pending):
                self.grants.pop(_digest(grant.secret), None)
                if self.active.get(grant.session_key) is grant:
                    self.active.pop(grant.session_key, None)

        pending = [grant for grant in self.grants.values() if grant.pending]
        selected = []
        if pending:
            offset = self.sweep_cursor % len(pending)
            selected = (pending[offset:] + pending[:offset])[:8]
            self.sweep_cursor += len(selected)

        async def deliver(grant):
            async with self._locked(grant.session_key):
                if authorize(grant):
                    await self._flush(grant, send)

        # At most eight delivery tasks per sweep, each with a five-second total
        # budget. Rotation bounds work without starving the tail of the registry.
        await asyncio.gather(*(deliver(grant) for grant in selected))
        retained_sessions = {grant.session_key for grant in self.grants.values()}
        self.locks = {
            key: lock
            for key, lock in self.locks.items()
            if key in retained_sessions or self.lock_users.get(key, 0)
        }


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _number(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def _valid_sample(data, grant):
    return (
        all(key in data for key in ("state", "position", "duration"))
        and data["duration"] > 0
        and abs(data["duration"] - grant.duration) <= 2
        and data["position"] <= grant.duration + 2
    )


def _validate(body, grant):
    if (
        type(body) is not dict
        or set(body) != {"version", "playback_id", "observations"}
        or type(body["version"]) is not int
        or body["version"] != 1
        or body["playback_id"] != grant.playback_id
        or type(body["observations"]) is not list
        or not 1 <= len(body["observations"]) <= 16
    ):
        raise invalid()
    result = []
    for row in body["observations"]:
        if (
            type(row) is not dict
            or not {"seq", "ms", "kind", "name", "data"} <= set(row)
            or set(row) - {"seq", "ms", "kind", "name", "data", "target"}
            or type(row["seq"]) is not int
            or not 1 <= row["seq"] <= 2**31 - 1
            or not _number(row["ms"], 864000000)
            or type(row["data"]) is not dict
            or type(row["kind"]) is not str
            or type(row["name"]) is not str
            or set(row["data"]) - {"state", "position", "duration", "speed", "ended"}
            or (row["kind"], row["name"])
            not in {("snapshot", "video"), *[("event", name) for name in EVENTS]}
        ):
            raise invalid()
        for key, value in row["data"].items():
            maximum = 4 if key == "state" else 16 if key == "speed" else grant.duration + 2
            if key == "ended":
                if type(value) is not bool:
                    raise invalid()
            elif not _number(value, maximum):
                raise invalid()
            elif key == "state" and (type(value) is not int or value not in (0, 1, 2, 3, 4)):
                raise invalid()
        if "target" in row and not _number(row["target"], grant.duration + 2):
            raise invalid()
        digest = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        result.append((row, digest))
    return result
