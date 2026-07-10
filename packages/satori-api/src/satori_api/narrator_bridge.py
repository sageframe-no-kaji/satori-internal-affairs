"""
Server-side narration bridge.

Converts Satori events into narrated text. Narration runs on the API server
(Boundary 3 — the narration line). The frontend receives pre-narrated
strings, never raw events for text generation.

Provider selection (P2-H08) is environment-driven at import time:
  SATORI_NARRATOR_PROVIDER  mock (default) | anthropic
  SATORI_NARRATOR_MODEL     model id (default: claude-sonnet-4-6)
  ANTHROPIC_API_KEY         required for the anthropic provider
Invalid or missing live config falls back to mock with a loud log line —
absent configuration must never break local dev.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from llm_client import (
    ModelConfig,
    NarrationContext,
    NarrationEvent,
    Narrator,
    Provider,
    create_narrator,
)
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

# ---------------------------------------------------------------------------
# Module-level narrator (singleton)
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

DEFAULT_NARRATOR_MODEL = "claude-sonnet-4-6"
# Narration is a sentence or two — a tight token budget keeps latency and
# cost proportionate to the output.
NARRATION_MAX_TOKENS = 300


def _narrator_from_env() -> Narrator:
    """Build the narrator from environment configuration.

    Mock is the default and the fallback: a missing key, an unknown provider
    string, or a failed client init logs loudly and returns mock — the game
    always runs.
    """
    provider_name = os.environ.get("SATORI_NARRATOR_PROVIDER", "mock").strip().lower()
    if provider_name in ("", "mock"):
        return create_narrator(ModelConfig(provider=Provider.MOCK, model="mock"))
    try:
        config = ModelConfig(
            provider=Provider(provider_name),
            model=os.environ.get("SATORI_NARRATOR_MODEL", DEFAULT_NARRATOR_MODEL),
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            max_tokens=NARRATION_MAX_TOKENS,
        )
        narrator = create_narrator(config)
        _logger.info("Live narrator active: provider=%s model=%s", provider_name, config.model)
        return narrator
    except Exception:  # noqa: BLE001 — config failure degrades to mock; the game must start regardless
        _logger.exception("Failed to build '%s' narrator from environment; falling back to mock", provider_name)
        return create_narrator(ModelConfig(provider=Provider.MOCK, model="mock"))


_narrator: Narrator = _narrator_from_env()


# ---------------------------------------------------------------------------
# Event → description helpers
# ---------------------------------------------------------------------------


def _describe_event(event: Event) -> tuple[str, dict[str, Any] | None]:
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


def narrate_events(
    events: list[Event],
    engine: SatoriEngine,
    cache: dict[tuple[str, str], str] | None = None,
) -> list[str]:
    """
    Narrate a list of events in the context of the current engine state.

    Returns a list of narration strings parallel to ``events``.
    Events that are not player-facing (e.g. internal flags) still receive
    a narration string — the frontend can choose to filter by event type.

    ``cache`` is the per-session narration cache (P2-H08), keyed
    ``(event_type, node_id)`` — identical node events mid-session reuse
    their narration instead of re-calling the provider. Only node-bearing
    events cache; waits and time advances vary by content. Fallback strings
    are never cached (a transient provider failure should not pin the
    templated text for the rest of the session).
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

        node_id = getattr(event, "node_id", None)
        cache_key: tuple[str, str] | None = (
            (event.type.value, node_id) if cache is not None and isinstance(node_id, str) else None
        )
        if cache_key is not None and cache is not None and cache_key in cache:
            narrations.append(cache[cache_key])
            continue

        narration_event = NarrationEvent(
            event_type=event.type.value,
            description=description,
            structured_data=structured_data,
        )
        try:
            narration = _narrator.narrate(narration_event, context)
        except Exception:  # noqa: BLE001 — narration is cosmetic (Narration Line): any narrator failure degrades to the plain description; it must never break gameplay
            _logger.exception("Narrator failed for %s; using fallback description", event.type.value)
            narrations.append(description)
            continue

        if cache_key is not None and cache is not None:
            cache[cache_key] = narration
        narrations.append(narration)

    return narrations
