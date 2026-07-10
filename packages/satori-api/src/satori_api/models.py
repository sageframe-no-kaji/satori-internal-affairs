"""
API response/request models for satori-api.

These are the shapes the frontend depends on. Every response must be
self-contained so the frontend can render without prior context
(DIP principle — see F-008 in future-features.md).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Inbound request bodies
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Body for POST /api/sessions."""

    case_path: str = Field(
        description="Path to the case JSON file. Relative paths are resolved from the repository root."
    )


class ExecuteActionRequest(BaseModel):
    """Body for POST /api/sessions/{id}/actions."""

    action: str = Field(description="Player action string, e.g. 'history_general' or 'order_labs:cbc'.")


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class VisibleTimerResponse(BaseModel):
    """A diegetic timer the player's character is aware of.

    Derived from pending_reveals (lab/imaging turnaround the player ordered)
    and active nodes whose timer.diegetic flag is true.
    """

    label: str
    remaining_minutes: int
    source: Literal["pending_reveal", "active_timer"]
    node_id: str


class VitalSignsResponse(BaseModel):
    """Serialised VitalSigns (all fields nullable)."""

    heart_rate: int | None = None
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    temperature: float | None = None
    respiratory_rate: int | None = None
    o2_saturation: int | None = None


class PatientContextResponse(BaseModel):
    """Patient identity and presentation data for rendering."""

    name: str
    age: int
    sex: str
    setting: str
    chief_complaint: str
    appearance: str
    backstory: str | None = None
    arriving_vitals: VitalSignsResponse
    triage_note: str | None = None


class FindingResponse(BaseModel):
    """A revealed clinical finding for the evidence board (P2-H03).

    Composed server-side from state + case data: the frontend never decides
    what counts as evidence (Truth Line). ``category`` is the node's type
    verbatim (history, medical_finding, lab_result, imaging, relational);
    display grouping is the frontend's concern.
    """

    node_id: str
    category: str
    label: str
    narrative_text: str
    structured_data: dict[str, Any] | None = None
    revealed_at_minutes: int


class GameStateResponse(BaseModel):
    """
    Serialised GameState — all frozensets become sorted lists for stable JSON.

    Includes every field a frontend needs to fully render the current turn
    without referencing previous responses.
    """

    case_id: str
    current_time_minutes: int
    flags: list[str]
    active_nodes: list[str]
    revealed_nodes: list[str]
    expired_nodes: list[str]
    pending_reveals: dict[str, int]
    timers: dict[str, int]
    timer_stages: dict[str, int]
    current_vitals: VitalSignsResponse
    available_actions: list[str]
    visible_timers: list[VisibleTimerResponse]
    emergency_active: bool = False
    emergency_timer: VisibleTimerResponse | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    case_ended: bool
    outcome_tier: str | None = None
    end_reason: str | None = None


class EventResponse(BaseModel):
    """
    Serialised event.

    The ``type`` field is an EventType string value (e.g. "node_revealed").
    Type-specific fields are stored in ``data`` to keep the shape flat and
    extensible without requiring a discriminated union on the TypeScript side.
    """

    type: str
    timestamp_minutes: int
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level response envelopes
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    """
    Response for POST /api/sessions and GET /api/sessions/{id}.

    Self-contained: includes full state + patient context + available actions
    so the frontend can render the initial screen from this alone.
    """

    session_id: str
    state: GameStateResponse
    patient: PatientContextResponse
    patient_condition: str
    available_actions: list[str]
    playable_actions: list[str]


class ActionResponse(BaseModel):
    """
    Response for POST /api/sessions/{id}/actions.

    Self-contained: includes events, narrations, and the full updated state
    so the frontend never needs to re-fetch after an action.
    """

    events: list[EventResponse]
    narrations: list[str]
    state: GameStateResponse
    patient_condition: str
    available_actions: list[str]
    playable_actions: list[str]
    case_ended: bool
    outcome_tier: str | None = None
    end_reason: str | None = None
    outcome_narrative: str | None = None


class NodeContentResponse(BaseModel):
    """Response for GET /api/sessions/{id}/nodes/{node_id}."""

    node_id: str
    narrative_text: str
    structured_data: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    detail: str | None = None
