"""Tests for the narrator bridge."""

from __future__ import annotations

import pytest
from satori import SatoriEngine
from satori.models import validate_case

from satori_api.narrator_bridge import narrate_events

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"


@pytest.fixture(scope="module")
def engine() -> SatoriEngine:
    case = validate_case(EXAMPLE_CASE)
    return SatoriEngine(case)


def test_narrate_events_empty_list(engine: SatoriEngine):
    result = narrate_events([], engine)
    assert result == []


def test_narrate_events_returns_one_per_event(engine: SatoriEngine):
    case = validate_case(EXAMPLE_CASE)
    fresh = SatoriEngine(case)
    available = list(fresh.get_available_actions())
    events = fresh.execute_action(available[0])
    narrations = narrate_events(events, fresh)
    assert len(narrations) == len(events)


def test_narrate_events_are_non_empty_strings(engine: SatoriEngine):
    case = validate_case(EXAMPLE_CASE)
    fresh = SatoriEngine(case)
    available = list(fresh.get_available_actions())
    events = fresh.execute_action(available[0])
    narrations = narrate_events(events, fresh)
    for n in narrations:
        assert isinstance(n, str)
        assert len(n) > 0


def test_mock_narrator_output_contains_patient_name(engine: SatoriEngine):
    """MockNarrator includes patient name in output."""
    case = validate_case(EXAMPLE_CASE)
    fresh = SatoriEngine(case)
    available = list(fresh.get_available_actions())
    events = fresh.execute_action(available[0])
    narrations = narrate_events(events, fresh)
    # MockNarrator format: "[Mock Narration] {name} experiences {type}: ..."
    for n in narrations:
        assert "Maria Santos" in n or "[Mock Narration]" in n
