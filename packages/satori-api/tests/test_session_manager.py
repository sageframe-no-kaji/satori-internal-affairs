"""Session store lock + TTL tests (P2-H13, audit C-8).

The store gained two behaviors: a per-session write lock (concurrent actions
on one session serialize instead of losing updates) and an idle TTL swept on
session creation and health checks. These tests pin both, plus the
access-refreshes-idle-clock contract the TTL depends on.
"""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from satori_api import session_manager
from satori_api.main import app

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    session_manager._sessions.clear()
    yield
    session_manager._sessions.clear()


# ---------------------------------------------------------------------------
# Locks
# ---------------------------------------------------------------------------


def test_lock_for_unknown_session_is_none():
    assert session_manager.lock_for("no-such-session") is None


def test_lock_is_stable_per_session():
    sid, _ = session_manager.create_session(EXAMPLE_CASE)
    assert session_manager.lock_for(sid) is session_manager.lock_for(sid)


def test_concurrent_actions_serialize_no_lost_update():
    """Two threads each wait 15 minutes on the same session. Serialized, the
    clock lands at 30; the pre-C-8 race could lose one write and land at 15."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    sid = resp.json()["session_id"]

    barrier = threading.Barrier(2)
    results: list[int] = []

    def act() -> None:
        barrier.wait()
        r = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait:15"})
        results.append(r.status_code)

    threads = [threading.Thread(target=act) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == [200, 200]
    state = client.get(f"/api/sessions/{sid}").json()["state"]
    assert state["current_time_minutes"] == 30


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------


def _age_session(sid: str, seconds: float) -> None:
    session_manager._sessions[sid].last_access -= seconds


def test_idle_session_reaped_on_next_create():
    old_sid, _ = session_manager.create_session(EXAMPLE_CASE)
    _age_session(old_sid, session_manager.SESSION_TTL_SECONDS + 1)
    new_sid, _ = session_manager.create_session(EXAMPLE_CASE)
    assert session_manager.get_engine(old_sid) is None
    assert session_manager.get_engine(new_sid) is not None


def test_fresh_session_survives_the_sweep():
    sid, _ = session_manager.create_session(EXAMPLE_CASE)
    session_manager.create_session(EXAMPLE_CASE)
    assert session_manager.get_engine(sid) is not None


def test_session_count_sweeps():
    sid, _ = session_manager.create_session(EXAMPLE_CASE)
    _age_session(sid, session_manager.SESSION_TTL_SECONDS + 1)
    assert session_manager.session_count() == 0


def test_access_refreshes_the_idle_clock():
    """An almost-expired session that gets used stays alive."""
    sid, _ = session_manager.create_session(EXAMPLE_CASE)
    _age_session(sid, session_manager.SESSION_TTL_SECONDS - 1)
    assert session_manager.get_engine(sid) is not None  # touch
    session_manager.create_session(EXAMPLE_CASE)  # sweep
    assert session_manager.get_engine(sid) is not None
