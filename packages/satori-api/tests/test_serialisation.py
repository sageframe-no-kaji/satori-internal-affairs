"""Tests for serialisation helpers."""

from __future__ import annotations

import pytest
from satori import SatoriEngine
from satori.models import validate_case

from satori_api.serialisation import (
    build_session_response,
    events_to_responses,
    patient_to_response,
    state_to_response,
    vitals_to_response,
)

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"


@pytest.fixture(scope="module")
def engine() -> SatoriEngine:
    case = validate_case(EXAMPLE_CASE)
    return SatoriEngine(case)


def test_state_to_response_frozensets_become_lists(engine: SatoriEngine):
    state = engine.get_state()
    resp = state_to_response(state)
    assert isinstance(resp.flags, list)
    assert isinstance(resp.active_nodes, list)
    assert isinstance(resp.revealed_nodes, list)
    assert isinstance(resp.expired_nodes, list)
    assert isinstance(resp.available_actions, list)


def test_state_to_response_lists_are_sorted(engine: SatoriEngine):
    state = engine.get_state()
    resp = state_to_response(state)
    assert resp.flags == sorted(resp.flags)
    assert resp.active_nodes == sorted(resp.active_nodes)
    assert resp.available_actions == sorted(resp.available_actions)


def test_state_to_response_case_id_is_string(engine: SatoriEngine):
    state = engine.get_state()
    resp = state_to_response(state)
    assert isinstance(resp.case_id, str)


def test_state_to_response_vitals_shape(engine: SatoriEngine):
    state = engine.get_state()
    resp = state_to_response(state)
    vitals = resp.current_vitals
    # All fields are int|float|None
    for field in ("heart_rate", "blood_pressure_systolic", "o2_saturation"):
        val = getattr(vitals, field)
        assert val is None or isinstance(val, (int, float))


def test_patient_to_response_shape(engine: SatoriEngine):
    resp = patient_to_response(engine.case)
    assert resp.name == "Maria Santos"
    assert isinstance(resp.age, int)
    assert isinstance(resp.sex, str)
    assert isinstance(resp.arriving_vitals.heart_rate, int)


def test_build_session_response_complete(engine: SatoriEngine):
    resp = build_session_response("test-id", engine)
    assert resp.session_id == "test-id"
    assert resp.state is not None
    assert resp.patient is not None
    assert isinstance(resp.patient_condition, str)
    assert isinstance(resp.available_actions, list)


def test_events_to_responses_empty():
    assert events_to_responses([]) == []


def test_events_to_responses_after_action(engine: SatoriEngine):
    # Use a fresh engine so we don't pollute the module-scoped one
    case = validate_case(EXAMPLE_CASE)
    fresh_engine = SatoriEngine(case)
    available = list(fresh_engine.get_available_actions())
    events = fresh_engine.execute_action(available[0])
    responses = events_to_responses(events)
    assert len(responses) == len(events)
    for r in responses:
        assert isinstance(r.type, str)
        assert isinstance(r.timestamp_minutes, int)
        assert isinstance(r.data, dict)
