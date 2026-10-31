import asyncio
import copy

import pytest

from jellyfin_msx.errors import PortalError
from jellyfin_msx.lifecycle import Lifecycle


class Rig:
    def __init__(self):
        self.now = 0
        self.lifecycle = Lifecycle(clock=lambda: self.now)
        self.grant = self.issue()
        self.sent = []
        self.failing = False
        self.attempts = 0

    def issue(self, session="session"):
        return asyncio.run(
            self.lifecycle.issue(
                session,
                "item",
                "source",
                "play-session",
                30,
                300,
                send=self.send,
            )
        )

    async def send(self, kind, grant, payload):
        self.attempts += 1
        if self.failing:
            raise RuntimeError("private upstream details")
        self.sent.append((kind, copy.deepcopy(payload)))

    def body(self, *rows):
        return {"version": 1, "playback_id": self.grant.playback_id, "observations": list(rows)}

    def submit(self, *rows):
        return asyncio.run(
            self.lifecycle.submit(self.grant.secret, "session", self.body(*rows), self.send)
        )

    def expire(self, authorized=True):
        asyncio.run(self.lifecycle.expire(self.send, lambda grant: authorized))


def sample(seq, position, state=2, **data):
    return {
        "seq": seq,
        "ms": seq * 2000,
        "kind": "snapshot",
        "name": "video",
        "data": {"state": state, "position": position, "duration": 30, **data},
    }


def event(seq, name, **data):
    return {"seq": seq, "ms": seq * 2000, "kind": "event", "name": name, "data": data}


def start(rig):
    rig.submit(sample(1, 1), sample(2, 3))
    assert rig.sent[0][0] == "start"


def test_intent_never_means_started_or_progress():
    rig = Rig()
    rig.submit(event(1, "video:load"), event(2, "video:play", position=15))
    rig.submit(sample(3, 1))
    assert rig.sent == []
    rig.submit(sample(4, 3))
    assert rig.sent == [
        (
            "start",
            {
                "ItemId": "item",
                "MediaSourceId": "source",
                "PlaySessionId": "play-session",
                "PositionTicks": 30_000_000,
                "IsPaused": False,
                "CanSeek": True,
                "PlayMethod": "DirectPlay",
            },
        )
    ]


def test_pause_reconciles_sample_and_stop_uses_lastsafe_position():
    rig = Rig()
    start(rig)
    rig.submit(event(3, "video:pause", state=2, position=3), sample(4, 4))
    assert len(rig.sent) == 1
    rig.submit(sample(5, 5, state=3))
    assert rig.sent[-1][1]["IsPaused"] is True
    rig.submit(event(6, "video:stop", position=0), sample(7, 0))
    assert rig.sent[-1][0] == "stop"
    assert rig.sent[-1][1]["PositionTicks"] == 50_000_000
    rig.submit(event(8, "video:stop"), sample(9, 20))
    assert len(rig.sent) == 3


def test_seek_targets_are_intent_and_rewind_requires_sample():
    rig = Rig()
    start(rig)
    row = event(3, "video:seek", position=3)
    row["target"] = 20
    rig.submit(row, sample(4, 4))
    assert rig.grant.position == 3
    rig.submit(sample(5, 20))
    assert rig.grant.position == 20
    row = event(6, "video:seek")
    row["target"] = 5
    rig.submit(row, sample(7, 5))
    assert rig.grant.position == 5


def test_completion_requires_explicit_ended_evidence_and_duration_boundary():
    rig = Rig()
    start(rig)
    rig.submit(sample(3, 29))
    assert rig.grant.terminal is None
    rig.submit(event(4, "video:load", state=2, position=0, duration=30, ended=True))
    assert rig.grant.terminal is None
    rig.submit(event(5, "video:load", state=2, position=30, duration=30, ended=True))
    assert rig.grant.terminal is None
    rig.submit(sample(6, 30, ended=True))
    assert rig.grant.terminal == "ended"
    assert rig.sent[-1][0] == "stop"


def test_disappearance_never_extrapolates_or_completes():
    rig = Rig()
    start(rig)
    rig.now = 44
    rig.expire()
    assert len(rig.sent) == 1
    rig.now = 45
    rig.expire()
    assert rig.grant.terminal == "abandoned"
    assert rig.sent[-1][1]["PositionTicks"] == 30_000_000
    rig.submit(sample(3, 20))
    assert len(rig.sent) == 2


def test_unknown_visibility_and_invalid_sample_do_not_renew_lease():
    rig = Rig()
    start(rig)
    rig.now = 44
    rig.submit(event(3, "app:suspend"), event(4, "app:resume"))
    bad = sample(5, 0)
    bad["data"]["duration"] = 0
    rig.submit(bad)
    assert rig.grant.lease == 45
    rig.now = 45
    rig.expire()
    assert rig.grant.terminal == "abandoned"


def test_missing_start_never_creates_stop_and_no_delayed_timer_revival():
    rig = Rig()
    rig.now = 46
    rig.submit(sample(1, 1), sample(2, 3))
    assert rig.grant.terminal == "abandoned"
    assert rig.sent == []


def test_replay_idempotency_conflict_order_window_and_atomic_rejection():
    rig = Rig()
    start(rig)
    assert rig.submit(sample(2, 3)) == {"accepted": [2]}
    assert len(rig.sent) == 1
    with pytest.raises(PortalError) as error:
        rig.submit(sample(2, 4))
    assert error.value.status == 409
    with pytest.raises(PortalError):
        rig.submit(sample(4, 4), sample(3, 5))
    assert rig.grant.highwater == 2
    for seq in range(3, 70):
        rig.submit(sample(seq, 5))
    assert len(rig.grant.digests) == 64
    with pytest.raises(PortalError):
        rig.submit(sample(1, 1))


def test_previous_generation_is_rejected_and_stopped_on_sweep():
    rig = Rig()
    start(rig)
    old = rig.grant
    rig.issue()
    with pytest.raises(PortalError) as error:
        rig.submit(sample(3, 8))
    assert error.value.status == 401
    rig.expire()
    assert old.terminal == "replaced"
    assert rig.sent[-1][0] == "stop"
    assert rig.sent[-1][1]["PositionTicks"] == 30_000_000


def test_idempotent_replay_evicted_during_batch_cannot_rewind_highwater():
    rig = Rig()
    for seq in range(1, 65):
        rig.submit(sample(seq, 5))
    rig.submit(sample(65, 6), sample(1, 5))
    assert rig.grant.highwater == 65
    assert 1 not in rig.grant.digests


def test_authentication_binding_expiry_and_revocation_fail_closed():
    rig = Rig()
    for secret, session in (("bad", "session"), (rig.grant.secret, "other")):
        with pytest.raises(PortalError) as error:
            asyncio.run(rig.lifecycle.submit(secret, session, rig.body(sample(1, 1)), rig.send))
        assert error.value.status == 401
    body = rig.body(sample(1, 1))
    body["playback_id"] = "other-generation"
    with pytest.raises(PortalError):
        asyncio.run(rig.lifecycle.submit(rig.grant.secret, "session", body, rig.send))
    start(rig)
    rig.expire(authorized=False)
    assert rig.lifecycle.grants == {}
    assert len(rig.sent) == 1
    assert "session" not in repr(rig.grant)


@pytest.mark.parametrize(
    "change",
    [
        lambda row: row.update(extra="private URL"),
        lambda row: row.update(kind=[]),
        lambda row: row.update(seq=True),
        lambda row: row.update(seq=0),
        lambda row: row.update(ms=float("inf")),
        lambda row: row.update(target=-1),
        lambda row: row["data"].update(position=float("nan")),
        lambda row: row["data"].update(position="1"),
        lambda row: row["data"].update(position=True),
        lambda row: row["data"].update(position=33),
        lambda row: row["data"].update(state=2.0),
        lambda row: row["data"].update(ended=1),
        lambda row: row["data"].update(url="private URL"),
    ],
)
def test_strict_observation_allowlist(change):
    rig = Rig()
    row = sample(1, 1)
    change(row)
    with pytest.raises(PortalError):
        rig.submit(row)
    assert rig.sent == []


def test_retry_and_outbox_are_bounded_without_sleep_tasks():
    rig = Rig()
    rig.failing = True
    start_rows = [sample(1, 1), sample(2, 3)]
    rig.submit(*start_rows)
    assert rig.attempts == 1
    for seq in range(3, 100):
        rig.submit(sample(seq, 5))
    assert rig.attempts == 1
    assert len(rig.grant.pending) == 2
    rig.now = 1
    rig.expire()
    assert rig.attempts == 2
    rig.now = 3
    rig.expire()
    assert rig.attempts == 3
    rig.now = 4
    rig.expire()
    assert rig.attempts == 4
    rig.now = 5
    rig.expire()
    rig.now = 7
    rig.expire()
    assert rig.attempts == 6
    assert not rig.grant.pending
    assert rig.grant.start_failed
    rig.now = 8
    rig.expire()
    assert rig.attempts == 6


def test_public_lookup_and_report_position_clamping():
    rig = Rig()
    assert rig.lifecycle.get(rig.grant.secret) is rig.grant
    with pytest.raises(PortalError):
        rig.lifecycle.get("unknown")
    start(rig)
    rig.submit(sample(3, 31))
    assert rig.sent[-1][1]["PositionTicks"] == 300_000_000
    rig.now = 300
    with pytest.raises(PortalError):
        rig.lifecycle.get(rig.grant.secret)


def test_capacity_and_session_rate_are_bounded():
    rig = Rig()
    rig.lifecycle.maximum = 1
    with pytest.raises(PortalError) as error:
        rig.issue("other")
    assert error.value.status == 503
    for seq in range(1, 121):
        rig.submit(sample(seq, 1))
    with pytest.raises(PortalError) as error:
        rig.submit(sample(121, 1))
    assert error.value.status == 429


def test_generation_replacement_waits_for_old_stop_before_new_start():
    async def scenario():
        lifecycle = Lifecycle(clock=lambda: 0)
        order = []
        stopping, release = asyncio.Event(), asyncio.Event()

        async def send(kind, grant, payload):
            if kind == "stop":
                stopping.set()
                await release.wait()
            order.append((grant.item_id, kind))

        old = await lifecycle.issue("session", "old", "source", "play", 30, 300)

        def body(grant, *rows):
            return {"version": 1, "playback_id": grant.playback_id, "observations": list(rows)}

        await lifecycle.submit(old.secret, "session", body(old, sample(1, 1), sample(2, 3)), send)
        replacing = asyncio.create_task(
            lifecycle.issue(
                "session",
                "new",
                "source",
                "play",
                30,
                300,
                send=send,
            )
        )
        await stopping.wait()
        assert lifecycle.active["session"] is old
        assert not replacing.done()
        stale = asyncio.create_task(
            lifecycle.submit(
                old.secret,
                "session",
                body(old, sample(3, 8)),
                send,
            )
        )
        release.set()
        new = await replacing
        with pytest.raises(PortalError):
            await stale
        await lifecycle.submit(new.secret, "session", body(new, sample(1, 1), sample(2, 3)), send)
        assert order == [("old", "start"), ("old", "stop"), ("new", "start")]

    asyncio.run(scenario())


def test_replacement_does_not_mutate_generation_during_inflight_report():
    async def scenario():
        lifecycle = Lifecycle(clock=lambda: 0)
        entered, release = asyncio.Event(), asyncio.Event()

        async def send(kind, grant, payload):
            if kind == "start":
                entered.set()
                await release.wait()

        old = await lifecycle.issue("session", "old", "source", "play", 30, 300)
        submitting = asyncio.create_task(
            lifecycle.submit(
                old.secret,
                "session",
                {
                    "version": 1,
                    "playback_id": old.playback_id,
                    "observations": [sample(1, 1), sample(2, 3)],
                },
                send,
            )
        )
        await entered.wait()
        replacing = asyncio.create_task(
            lifecycle.issue(
                "session",
                "new",
                "source",
                "play",
                30,
                300,
                send=send,
            )
        )
        await asyncio.sleep(0)
        assert old.terminal is None
        release.set()
        await submitting
        await replacing
        assert old.terminal_delivered

    asyncio.run(scenario())


def test_unacknowledged_old_stop_blocks_new_generation_even_after_retry_exhaustion():
    rig = Rig()
    start(rig)
    rig.failing = True
    for now in (0, 1, 3, 5):
        rig.now = now
        with pytest.raises(PortalError) as error:
            rig.issue()
        assert error.value.status == 503
        assert rig.lifecycle.active["session"] is rig.grant
    assert len(rig.lifecycle.grants) == 1
    assert rig.grant.terminal == "replaced"
    assert not rig.grant.terminal_delivered
    assert rig.attempts == 4  # One successful Start, three failed Stop attempts.


def test_sweep_marks_all_leases_before_stalled_delivery_and_bounds_concurrency():
    async def scenario():
        now = [0]
        lifecycle = Lifecycle(clock=lambda: now[0])
        release, entered = asyncio.Event(), asyncio.Event()
        current = maximum = 0
        completed = []

        async def send(kind, grant, payload):
            nonlocal current, maximum
            current += 1
            maximum = max(maximum, current)
            try:
                if kind == "stop" and grant.item_id == "0":
                    entered.set()
                    await release.wait()
                completed.append((grant.item_id, kind))
            finally:
                current -= 1

        grants = []
        for index in range(12):
            grant = await lifecycle.issue(str(index), str(index), "source", "play", 30, 300)
            grants.append(grant)
            await lifecycle.submit(
                grant.secret,
                str(index),
                {
                    "version": 1,
                    "playback_id": grant.playback_id,
                    "observations": [sample(1, 1), sample(2, 3)],
                },
                send,
            )
        now[0] = 45
        sweeping = asyncio.create_task(lifecycle.expire(send, lambda grant: True))
        await entered.wait()
        assert all(grant.terminal == "abandoned" for grant in grants)
        assert ("1", "stop") in completed
        release.set()
        await sweeping
        await lifecycle.expire(send, lambda grant: True)
        assert all(grant.terminal_delivered for grant in grants)
        assert maximum <= 8

    asyncio.run(scenario())


def test_exhausted_stop_fence_survives_terminal_replay_retention():
    rig = Rig()
    rig.grant.expires = rig.grant.session_expires = 3600
    start(rig)
    rig.failing = True
    for now in (0, 1, 3):
        rig.now = now
        with pytest.raises(PortalError):
            rig.issue()
    rig.now = 301
    rig.expire()
    assert not rig.lifecycle.grants
    with pytest.raises(PortalError) as error:
        asyncio.run(
            rig.lifecycle.issue(
                "session",
                "item",
                "source",
                "play",
                30,
                3600,
                send=rig.send,
            )
        )
    assert error.value.status == 503


def test_sweep_retains_session_lock_for_woken_waiter():
    async def scenario():
        lifecycle = Lifecycle(clock=lambda: 0)
        entered, release = asyncio.Event(), asyncio.Event()

        async def borrower():
            async with lifecycle._locked("session"):
                entered.set()
                await release.wait()

        async with lifecycle._locked("session"):
            original = lifecycle.locks["session"]
            waiting = asyncio.create_task(borrower())
            await asyncio.sleep(0)
            assert lifecycle.lock_users["session"] == 2
        # The waiter has been woken but has not reacquired the unlocked lock.
        await lifecycle.expire(lambda *args: None, lambda grant: True)
        assert lifecycle.locks["session"] is original
        await entered.wait()
        release.set()
        await waiting
        await lifecycle.expire(lambda *args: None, lambda grant: True)
        assert "session" not in lifecycle.locks

    asyncio.run(scenario())


def test_fresh_samples_cannot_reset_failed_progress_retry_budget():
    rig = Rig()
    start(rig)
    rig.failing = True
    rig.submit(sample(3, 5))
    for seq in range(4, 10):
        rig.submit(sample(seq, 6))
    assert rig.attempts == 2
    rig.now = 1
    rig.submit(sample(10, 7))
    assert rig.attempts == 3
    rig.now = 2
    rig.submit(sample(11, 8))
    assert rig.attempts == 3
    rig.now = 3
    rig.submit(sample(12, 9))
    assert rig.attempts == 4
    assert rig.grant.terminal == "reporting_lost"
    lease = rig.grant.lease
    rig.now = 4
    rig.failing = False
    rig.submit(sample(13, 20))
    assert rig.grant.lease == lease
    assert rig.grant.position == 9
    assert rig.sent[-1][0] == "stop"
    assert rig.sent[-1][1]["PositionTicks"] == 90_000_000
    assert rig.grant.terminal_delivered


@pytest.mark.parametrize("failures", [1, 2])
def test_successful_delivery_resets_consecutive_failure_circuit(failures):
    rig = Rig()
    start(rig)
    rig.failing = True
    rig.submit(sample(3, 5))
    if failures == 2:
        rig.now = 1
        rig.expire()
    rig.failing = False
    rig.now = 3
    rig.expire()
    assert rig.grant.failures == 0
    assert rig.grant.terminal is None
    rig.failing = True
    rig.submit(sample(4, 6))
    assert rig.grant.failures == 1
    assert rig.grant.terminal is None


def test_lost_start_ack_still_gets_bounded_cleanup_stop_before_replacement():
    async def scenario():
        now = [0]
        lifecycle = Lifecycle(clock=lambda: now[0])
        active = [None]
        attempts = []

        async def send(kind, grant, payload):
            attempts.append(kind)
            if kind == "start":
                active[0] = grant.item_id  # Upstream applied it; response was lost.
                raise RuntimeError("response lost")
            if kind == "stop":
                assert grant.terminal == "reporting_lost"
                active[0] = None

        grant = await lifecycle.issue("session", "old", "source", "play", 30, 300)
        await lifecycle.submit(
            grant.secret,
            "session",
            {
                "version": 1,
                "playback_id": grant.playback_id,
                "observations": [sample(1, 1), sample(2, 3)],
            },
            send,
        )
        for instant in (1, 3):
            now[0] = instant
            await lifecycle.expire(send, lambda grant: True)
        assert active[0] == "old"
        with pytest.raises(PortalError):
            await lifecycle.issue("session", "new", "source", "play", 30, 300, send=send)
        now[0] = 4
        await lifecycle.expire(send, lambda grant: True)
        assert active[0] is None
        assert attempts == ["start", "start", "start", "stop"]
        await lifecycle.issue("session", "new", "source", "play", 30, 300, send=send)

    asyncio.run(scenario())


def test_cancelled_inflight_start_remains_pending_before_progress():
    async def scenario():
        now = [0]
        lifecycle = Lifecycle(clock=lambda: now[0])
        entered = asyncio.Event()
        acknowledged = []
        calls = [0]

        async def send(kind, grant, payload):
            calls[0] += 1
            if calls[0] == 1:
                entered.set()
                await asyncio.Future()
            acknowledged.append(kind)

        grant = await lifecycle.issue("session", "old", "source", "play", 30, 300)
        task = asyncio.create_task(
            lifecycle.submit(
                grant.secret,
                "session",
                {
                    "version": 1,
                    "playback_id": grant.playback_id,
                    "observations": [sample(1, 1), sample(2, 3)],
                },
                send,
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert grant.pending[0][0] == "start"
        assert grant.pending[0][2] == 1
        now[0] = 1
        await lifecycle.submit(
            grant.secret,
            "session",
            {
                "version": 1,
                "playback_id": grant.playback_id,
                "observations": [sample(3, 5)],
            },
            send,
        )
        assert acknowledged == ["start", "progress"]

    asyncio.run(scenario())
