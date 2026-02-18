"""Tests for the narrator bridge."""

from __future__ import annotations

import pytest
from satori import SatoriEngine
from satori.models import validate_case

from satori_api.narrator_bridge import _describe_event, narrate_events

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"


@pytest.fixture(scope="module")
def engine() -> SatoriEngine:
    case = validate_case(EXAMPLE_CASE)
    return SatoriEngine(case)


def _fresh() -> tuple[SatoriEngine, list[object]]:
    """Return a fresh engine and the events from its first available action."""
    case = validate_case(EXAMPLE_CASE)
    eng = SatoriEngine(case)
    available = list(eng.get_available_actions())
    assert available, "No actions available in initial state"
    return eng, eng.execute_action(available[0])


def test_narrate_events_empty_list(engine: SatoriEngine):
    result = narrate_events([], engine)
    assert result == []


def test_narrate_events_returns_one_per_event(engine: SatoriEngine):
    eng, events = _fresh()
    narrations = narrate_events(events, eng)  # type: ignore[arg-type]
    assert len(narrations) == len(events)


def test_narrate_events_are_non_empty_strings(engine: SatoriEngine):
    eng, events = _fresh()
    narrations = narrate_events(events, eng)  # type: ignore[arg-type]
    for n in narrations:
        assert isinstance(n, str)
        assert len(n) > 0


def test_mock_narrator_output_contains_mock_prefix(engine: SatoriEngine):
    """MockNarrator always tags output with [Mock Narration]."""
    eng, events = _fresh()
    narrations = narrate_events(events, eng)  # type: ignore[arg-type]
    for n in narrations:
        assert "[Mock Narration]" in n


def test_mock_narrator_output_contains_patient_name(engine: SatoriEngine):
    """MockNarrator embeds the patient name in every narration."""
    eng, events = _fresh()
    narrations = narrate_events(events, eng)  # type: ignore[arg-type]
    for n in narrations:
        assert "Maria Santos" in n


def test_describe_event_time_advanced():
    from satori import TimeAdvancedEvent

    event = TimeAdvancedEvent(timestamp_minutes=5, old_time=0, new_time=5, cause="action")
    desc, data = _describe_event(event)
    assert "0" in desc and "5" in desc
    assert data is not None
    assert data["old_time"] == 0
    assert data["new_time"] == 5


def test_describe_event_node_revealed():
    from satori import NodeRevealedEvent

    event = NodeRevealedEvent(
        timestamp_minutes=5,
        node_id="test_node",
        node_type="lab_result",
        content_text="The result is positive.",
        structured_data={"key": "val"},
    )
    desc, data = _describe_event(event)
    assert desc == "The result is positive."
    assert data == {"key": "val"}


def test_describe_event_case_ended():
    from satori import CaseEndedEvent

    event = CaseEndedEvent(
        timestamp_minutes=60,
        outcome_tier="optimal",
        end_reason="Patient stabilised and discharged.",
    )
    desc, data = _describe_event(event)
    assert "optimal" in desc
    assert data is not None
    assert data["outcome_tier"] == "optimal"
    assert data["end_reason"] == "Patient stabilised and discharged."


def test_describe_event_fallback():
    """Fallback branch returns a safe (str, None) for any unrecognised event type."""
    from unittest.mock import MagicMock

    # Build a mock that pretends to be an Event but doesn't match any isinstance check
    mock_event = MagicMock()
    mock_event.type = MagicMock()
    mock_event.type.__str__ = lambda _: "future_event"

    # isinstance checks against the real classes will return False for a MagicMock
    desc, data = _describe_event(mock_event)
    assert isinstance(desc, str)
    assert len(desc) > 0
    assert data is None
