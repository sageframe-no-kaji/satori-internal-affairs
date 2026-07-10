"""
In-memory session store.

A dict mapping session_id (str UUID) to a _Session record holding the live
SatoriEngine, its per-session lock, and its last-access time. Sessions are
lost on process restart and reaped after SESSION_TTL_SECONDS idle (P2-H13,
audit C-8).

Concurrency (audit C-8): FastAPI runs the sync handlers on a threadpool, so
two requests can touch one session at once. The per-session lock serializes
writes (the action endpoint); read-only endpoints stay lock-free because
engine state is replaced by a single atomic assignment — readers see a
complete before-or-after snapshot, never a partial one.

Time note: time.monotonic() here is server operations, not gameplay — the
engine's no-wall-clock determinism rule applies to satori, not this layer.

Design note: this module is intentionally thin and isolated. Nothing in
main.py or models.py reaches into session state directly — they only call
the functions below. When a later phase introduces persistent or serialised
sessions, only this module changes (see F-008 in future-features.md).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from satori import SatoriEngine
from satori.models import validate_case

# Idle sessions are reaped after an hour. Tests override the module global.
SESSION_TTL_SECONDS: float = 3600.0

# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------


@dataclass
class _Session:
    engine: SatoriEngine
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_access: float = field(default_factory=time.monotonic)


_sessions: dict[str, _Session] = {}


def _sweep_expired() -> None:
    """Drop sessions idle past the TTL. list() snapshot: other threads may
    mutate the dict while we iterate."""
    now = time.monotonic()
    for session_id, session in list(_sessions.items()):
        if now - session.last_access > SESSION_TTL_SECONDS:
            _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def create_session(case_path: str) -> tuple[str, SatoriEngine]:
    """
    Load a case and create a new engine session.

    ``case_path`` may be absolute or relative to the current working directory.
    The caller is expected to run the server from the repository root so that
    relative paths like ``"cases/example-neurocysticercosis.json"`` resolve
    correctly.

    Returns ``(session_id, engine)``.

    Raises:
        FileNotFoundError: case file does not exist.
        pydantic.ValidationError: case JSON is invalid.
        CaseValidationError: case has structural issues.
    """
    _sweep_expired()
    resolved = Path(case_path)
    case = validate_case(resolved)
    engine = SatoriEngine(case)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = _Session(engine=engine)
    return session_id, engine


def get_engine(session_id: str) -> SatoriEngine | None:
    """Return the engine for ``session_id``, or ``None`` if not found.
    Refreshes the session's idle clock."""
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.last_access = time.monotonic()
    return session.engine


def lock_for(session_id: str) -> threading.Lock | None:
    """Return the per-session write lock, or ``None`` if the session does
    not exist. The action endpoint holds this across execute + narrate +
    serialize so concurrent actions on one session serialize instead of
    losing updates (audit C-8). Refreshes the session's idle clock."""
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.last_access = time.monotonic()
    return session.lock


def delete_session(session_id: str) -> None:
    """Remove a session. No-op if it does not exist."""
    _sessions.pop(session_id, None)


def session_count() -> int:
    """Return the number of active sessions. Used by health checks and
    tests; sweeping here makes the health probe the reaper heartbeat."""
    _sweep_expired()
    return len(_sessions)
