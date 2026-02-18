"""
Server-side narration bridge.

Converts Satori events into narrated text using the MockNarrator (Phase 1).
Narration runs on the API server (Boundary 3 — the narration line). The
frontend receives pre-narrated strings, never raw events for text generation.
"""

from __future__ import annotations

from satori import (
    ActionLockedEvent,
    ActionUnlockedEvent,
    CaseEndedEvent,
    Event,
    FlagClearedEvent,
    FlagSetEvent,
    NodeActivatedEvent,
    NodeExpiredEvent,
    NodeRevealedEvent,
    PendingRevealStartedEvent,
    SatoriEngine,
    TimeAdvancedEvent,
    TimerStageEvent,
    VitalsChangedEvent,
)
from llm_client import (
    ModelConfig,
    NarrationContext,
    NarrationEvent,
    Narrator,
    Provider,
    create_narrator,
)

# ---------------------------------------------------------------------------
# Module-level narrator (singleton)
# ---------------------------------------------------------------------------

_narrator: Narrator = create_narrator(ModelConfig(provider=Provider.MOCK, model="mock"))


# ---------------------------------------------------------------------------
# Event → description helpers
# ---------------------------------------------------------------------------


def _describe_event(event: Event) -> tuple[str, dict | None]:  # type: ignore[type-arg]
    """
    Return a human-readable description and optional structured_data for
    any event type. Used to populate NarrationEvent.
    """
    if isinstance(event, TimeAdvancedEvent):
        return (
            f"Time advanced from {event.old_time} to {event.new_time} minutes ({event.cause})",
            {"old_time": event.old_time, "new_time": event.new_time, "cause": event.cause},
        )
    if isinstance(event, NodeRevealedEvent):
        return (
            event.content_text,
            event.structured_data,
        )
    if isinstance(event, NodeActivatedEvent):
        return (
            f"A new situation is developing ({event.node_type})",
            {"node_id": event.node_id, "node_type": event.node_type},
        )
    if isinstance(event, NodeExpiredEvent):
        return (
            f"The window for {event.node_id} has passed",
            {"node_id": event.node_id},
        )
    if isinstance(event, TimerStageEvent):
        vitals_note = " Vitals have changed." if event.vital_signs_changed else ""
        return (
            f"Patient condition is progressing (stage {event.stage_index}).{vitals_note}",
            {"node_id": event.node_id, "stage_index": event.stage_index},
        )
    if isinstance(event, FlagSetEvent):
        return (
            f"Clinical marker recorded: {event.flag}",
            {"flag": event.flag},
        )
    if isinstance(event, FlagClearedEvent):
        return (
            f"Clinical marker cleared: {event.flag}",
            {"flag": event.flag},
        )
    if isinstance(event, VitalsChangedEvent):
        return (
            "Vital signs have changed",
            {"old_vitals": event.old_vitals, "new_vitals": event.new_vitals},
        )
    if isinstance(event, ActionUnlockedEvent):
        return (
            f"New action available: {event.action}",
            {"action": event.action},
        )
    if isinstance(event, ActionLockedEvent):
        return (
            f"Action no longer available: {event.action}",
            {"action": event.action},
        )
    if isinstance(event, PendingRevealStartedEvent):
        return (
            f"Results pending in {event.delay_minutes} minutes ({event.node_id})",
            {"node_id": event.node_id, "delay_minutes": event.delay_minutes},
        )
    if isinstance(event, CaseEndedEvent):
        return (
            f"Case concluded: {event.end_reason} (Outcome: {event.outcome_tier})",
            {"outcome_tier": event.outcome_tier, "end_reason": event.end_reason},
        )
    # Fallback for any future event types
    return (str(event.type), None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def narrate_events(events: list[Event], engine: SatoriEngine) -> list[str]:
    """
    Narrate a list of events in the context of the current engine state.

    Returns a list of narration strings parallel to ``events``.
    Events that are not player-facing (e.g. internal flags) still receive
    a narration string — the frontend can choose to filter by event type.
    """
    state = engine.get_state()
    case = engine.case
    patient = case.patient

    context = NarrationContext(
        patient_name=patient.name,
        patient_age=patient.age,
        patient_sex=patient.sex.value if hasattr(patient.sex, "value") else str(patient.sex),
        setting=patient.setting,
        current_vitals={
            k: v
            for k, v in {
                "heart_rate": state.current_vitals.heart_rate,
                "blood_pressure_systolic": state.current_vitals.blood_pressure_systolic,
                "blood_pressure_diastolic": state.current_vitals.blood_pressure_diastolic,
                "temperature": state.current_vitals.temperature,
                "respiratory_rate": state.current_vitals.respiratory_rate,
                "o2_saturation": state.current_vitals.o2_saturation,
            }.items()
            if v is not None
        },
        elapsed_minutes=state.current_time_minutes,
    )

    narrations: list[str] = []
    for event in events:
        description, structured_data = _describe_event(event)
        narration_event = NarrationEvent(
            event_type=event.type.value,
            description=description,
            structured_data=structured_data,
        )
        narrations.append(_narrator.narrate(narration_event, context))

    return narrations
