"""
FastAPI application — Satori API bridge.

Endpoints:
  POST   /api/sessions                        Create session, get initial state
  GET    /api/sessions/{id}                   Get current session state
  POST   /api/sessions/{id}/actions          Execute action, get events + new state
  GET    /api/sessions/{id}/nodes/{node_id}  Get revealed node content
  GET    /health                              Health check
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from satori import InvalidActionError
from satori.patient_condition import compute_patient_condition

from satori_api import session_manager
from satori_api.models import (
    ActionResponse,
    CreateSessionRequest,
    ErrorResponse,
    ExecuteActionRequest,
    NodeContentResponse,
    SessionResponse,
)
from satori_api.narrator_bridge import narrate_events
from satori_api.serialisation import (
    build_session_response,
    events_to_responses,
    resolve_tier_narrative,
    state_to_response,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Satori API",
    description="HTTP bridge exposing the Satori deterministic game engine.",
    version="0.1.0",
)

# Accept requests from the SvelteKit dev server and any localhost port.
# In production this should be locked to the actual origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "active_sessions": session_manager.session_count(),
    }


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/sessions",
    response_model=SessionResponse,
    status_code=201,
    tags=["sessions"],
    summary="Create a new game session",
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_session(body: CreateSessionRequest) -> SessionResponse:
    """
    Load the specified case file, initialise a SatoriEngine, and return the
    initial game state together with the patient presentation.

    The response is **self-contained**: the frontend can render the full
    opening screen from this single response without any prior state.
    """
    try:
        session_id, engine = session_manager.create_session(body.case_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Case file not found: {exc}") from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid case definition: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_session_response(session_id, engine)


@app.get(
    "/api/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["sessions"],
    summary="Get current session state",
    responses={404: {"model": ErrorResponse}},
)
def get_session(session_id: str) -> SessionResponse:
    """Return the current full state for a session without advancing the simulation."""
    engine = session_manager.get_engine(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return build_session_response(session_id, engine)


@app.delete(
    "/api/sessions/{session_id}",
    status_code=204,
    tags=["sessions"],
    summary="Delete a session",
)
def delete_session(session_id: str) -> None:
    """Remove a session from the in-memory store. Idempotent."""
    session_manager.delete_session(session_id)


# ---------------------------------------------------------------------------
# Action endpoint
# ---------------------------------------------------------------------------


@app.post(
    "/api/sessions/{session_id}/actions",
    response_model=ActionResponse,
    tags=["gameplay"],
    summary="Execute a player action",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def execute_action(session_id: str, body: ExecuteActionRequest) -> ActionResponse:
    """
    Execute a player action and return the resulting events with narration,
    plus the complete updated state.

    The response is **self-contained**: ``state`` and ``available_actions``
    are always present so the frontend can fully re-render without a
    separate GET.
    """
    engine = session_manager.get_engine(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    try:
        events = engine.execute_action(body.action)
    except InvalidActionError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    narrations = narrate_events(events, engine)
    state = engine.get_state()
    condition = compute_patient_condition(state, engine.case)

    return ActionResponse(
        events=events_to_responses(events),
        narrations=narrations,
        state=state_to_response(state),
        patient_condition=condition.value,
        available_actions=sorted(state.available_actions),
        playable_actions=sorted(engine.get_playable_actions()),
        case_ended=state.case_ended,
        outcome_tier=state.outcome_tier,
        end_reason=state.end_reason,
        # Prefer the narrative of the tier that actually matched (tier levels
        # are not unique — two tiers can share the "failure" register); fall
        # back to the level-keyed lookup for cases ended purely by an
        # end_case effect, where no tier evaluation runs.
        outcome_narrative=state.outcome_narrative or resolve_tier_narrative(engine.case, state.outcome_tier),
    )


# ---------------------------------------------------------------------------
# Node content endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/sessions/{session_id}/nodes/{node_id}",
    response_model=NodeContentResponse,
    tags=["gameplay"],
    summary="Get revealed node content",
    responses={
        404: {"model": ErrorResponse},
    },
)
def get_node_content(session_id: str, node_id: str) -> NodeContentResponse:
    """
    Return the narrative text and structured data for a revealed node.

    Returns 404 if the session does not exist, the node does not exist,
    or the node has not yet been revealed to the player.
    """
    engine = session_manager.get_engine(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    content = engine.get_node_content(node_id)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' is not revealed or does not exist",
        )

    return NodeContentResponse(
        node_id=node_id,
        narrative_text=content.narrative_text,
        structured_data=content.structured_data,
    )
