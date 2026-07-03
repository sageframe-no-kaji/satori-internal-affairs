"""
Serialisation helpers: convert Satori domain objects → API response models.
"""

from __future__ import annotations

from satori import Event, GameState, SatoriEngine
from satori.models import CaseDefinition
from satori.patient_condition import compute_patient_condition

from satori_api.models import (
    EventResponse,
    GameStateResponse,
    PatientContextResponse,
    SessionResponse,
    VisibleTimerResponse,
    VitalSignsResponse,
)


def resolve_tier_narrative(case: CaseDefinition, outcome_tier: str | None) -> str | None:
    """Return the authored narrative text for the matched outcome tier.

    Walks case.outcome_evaluation.tiers and returns the first tier whose
    tier value matches outcome_tier.  Returns None if outcome_tier is None
    or no matching tier is found.

    Args:
        case: The loaded case definition.
        outcome_tier: The tier string from GameState (e.g. "optimal", "good").

    Returns:
        The narrative string for that tier, or None.
    """
    if outcome_tier is None:
        return None
    for tier in case.outcome_evaluation.tiers:
        if tier.tier.value == outcome_tier:
            return tier.narrative
    return None


def vitals_to_response(vitals: object) -> VitalSignsResponse:
    """Convert a VitalSigns Pydantic model to a VitalSignsResponse."""
    return VitalSignsResponse(
        heart_rate=getattr(vitals, "heart_rate", None),
        blood_pressure_systolic=getattr(vitals, "blood_pressure_systolic", None),
        blood_pressure_diastolic=getattr(vitals, "blood_pressure_diastolic", None),
        temperature=getattr(vitals, "temperature", None),
        respiratory_rate=getattr(vitals, "respiratory_rate", None),
        o2_saturation=getattr(vitals, "o2_saturation", None),
    )


def state_to_response(state: GameState) -> GameStateResponse:
    """Convert an immutable GameState to a JSON-serialisable GameStateResponse."""
    return GameStateResponse(
        case_id=str(state.case_id),
        current_time_minutes=state.current_time_minutes,
        flags=sorted(state.flags),
        active_nodes=sorted(state.active_nodes),
        revealed_nodes=sorted(state.revealed_nodes),
        expired_nodes=sorted(state.expired_nodes),
        pending_reveals=dict(state.pending_reveals),
        timers=dict(state.timers),
        timer_stages=dict(state.timer_stages),
        current_vitals=vitals_to_response(state.current_vitals),
        available_actions=sorted(state.available_actions),
        visible_timers=[
            VisibleTimerResponse(
                label=vt.label,
                remaining_minutes=vt.remaining_minutes,
                source=vt.source,
                node_id=vt.node_id,
            )
            for vt in state.visible_timers
        ],
        case_ended=state.case_ended,
        outcome_tier=state.outcome_tier,
        end_reason=state.end_reason,
    )


def patient_to_response(case: CaseDefinition) -> PatientContextResponse:
    """Convert PatientContext to a PatientContextResponse."""
    p = case.patient
    return PatientContextResponse(
        name=p.name,
        age=p.age,
        sex=p.sex.value if hasattr(p.sex, "value") else str(p.sex),
        setting=p.setting,
        chief_complaint=p.chief_complaint,
        appearance=p.appearance,
        backstory=p.backstory,
        arriving_vitals=vitals_to_response(p.arriving_vitals),
        triage_note=p.triage_note,
    )


def events_to_responses(events: list[Event]) -> list[EventResponse]:
    """Convert a list of Satori events to EventResponse models."""
    result: list[EventResponse] = []
    for event in events:
        data: dict[str, object] = {}
        # Populate type-specific fields
        for field in vars(event):
            if field not in ("type", "timestamp_minutes"):
                val = getattr(event, field)
                # Ensure all values are JSON-serialisable
                if isinstance(val, frozenset):
                    data[field] = sorted(val)
                elif hasattr(val, "model_dump"):
                    data[field] = val.model_dump()
                else:
                    data[field] = val
        result.append(
            EventResponse(
                type=event.type.value,
                timestamp_minutes=event.timestamp_minutes,
                data=data,
            )
        )
    return result


def build_session_response(session_id: str, engine: SatoriEngine) -> SessionResponse:
    """Build a full self-contained SessionResponse from a live engine."""
    state = engine.get_state()
    condition = compute_patient_condition(state, engine.case)
    return SessionResponse(
        session_id=session_id,
        state=state_to_response(state),
        patient=patient_to_response(engine.case),
        patient_condition=condition.value,
        available_actions=sorted(state.available_actions),
        playable_actions=sorted(engine.get_playable_actions()),
    )
