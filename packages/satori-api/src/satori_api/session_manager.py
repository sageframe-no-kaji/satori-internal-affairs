"""
In-memory session store.

Phase 1 implementation: a plain dict mapping session_id (str UUID) to a
live SatoriEngine instance. Sessions are lost on process restart.

Design note: this module is intentionally thin and isolated. Nothing in
main.py or models.py reaches into session state directly — they only call
the functions below. When Phase 2 introduces persistent or serialised sessions,
only this module changes (see F-008 in future-features.md).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from satori import SatoriEngine
from satori.models import validate_case

# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

_sessions: dict[str, SatoriEngine] = {}


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
    resolved = Path(case_path)
    case = validate_case(resolved)
    engine = SatoriEngine(case)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = engine
    return session_id, engine


def get_engine(session_id: str) -> SatoriEngine | None:
    """Return the engine for ``session_id``, or ``None`` if not found."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    """Remove a session. No-op if it does not exist."""
    _sessions.pop(session_id, None)


def session_count() -> int:
    """Return the number of active sessions. Used by health checks and tests."""
    return len(_sessions)
