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
    # All six vital fields must be int/float/None
    for field in (
        "heart_rate",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "temperature",
        "respiratory_rate",
        "o2_saturation",
    ):
        val = getattr(vitals, field)
        assert val is None or isinstance(val, (int, float)), f"{field}={val!r} is not numeric"


def test_patient_to_response_shape(engine: SatoriEngine):
    resp = patient_to_response(engine.case)
    assert resp.name == "Maria Santos"
    assert isinstance(resp.age, int)
    assert isinstance(resp.sex, str)
    assert isinstance(resp.setting, str)
    assert len(resp.setting) > 0
    assert isinstance(resp.chief_complaint, str)
    assert len(resp.chief_complaint) > 0
    assert isinstance(resp.appearance, str)
    assert len(resp.appearance) > 0
    assert isinstance(resp.arriving_vitals.heart_rate, int)
    # triage_note and backstory are optional but must be str if present
    if resp.triage_note is not None:
        assert isinstance(resp.triage_note, str)
    if resp.backstory is not None:
        assert isinstance(resp.backstory, str)


def test_build_session_response_complete(engine: SatoriEngine):
    resp = build_session_response("test-id", engine)
    assert resp.session_id == "test-id"
    assert resp.state is not None
    assert resp.patient is not None
    assert isinstance(resp.patient_condition, str)
    assert isinstance(resp.available_actions, list)
    assert len(resp.available_actions) > 0


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


def test_vitals_to_response_all_fields(engine: SatoriEngine):
    """vitals_to_response maps all six fields without dropping any."""
    state = engine.get_state()
    resp = vitals_to_response(state.current_vitals)
    for field in (
        "heart_rate",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "temperature",
        "respiratory_rate",
        "o2_saturation",
    ):
        assert hasattr(resp, field), f"VitalSignsResponse missing field: {field}"


def test_state_to_response_subfields_present(engine: SatoriEngine):
    """GameStateResponse must include pending_reveals, timers, timer_stages."""
    resp = state_to_response(engine.get_state())
    assert isinstance(resp.pending_reveals, dict)
    assert isinstance(resp.timers, dict)
    assert isinstance(resp.timer_stages, dict)


def test_events_to_responses_event_types_are_strings(engine: SatoriEngine):
    """Event type values must be plain strings (enum .value), not enum members."""
    case = validate_case(EXAMPLE_CASE)
    fresh_engine = SatoriEngine(case)
    available = list(fresh_engine.get_available_actions())
    events = fresh_engine.execute_action(available[0])
    responses = events_to_responses(events)
    for r in responses:
        assert isinstance(r.type, str)
        # Must not contain enum class noise like "<EventType.x: 'x'>"
        assert "<" not in r.type and ">" not in r.type


# ---------------------------------------------------------------------------
# visible_timers serialisation
# ---------------------------------------------------------------------------


def test_state_to_response_has_visible_timers_field(engine: SatoriEngine):
    """state_to_response must include a visible_timers list."""
    state = engine.get_state()
    resp = state_to_response(state)
    assert hasattr(resp, "visible_timers")
    assert isinstance(resp.visible_timers, list)


def test_state_to_response_visible_timers_empty_at_start(engine: SatoriEngine):
    """At game start with no diegetic timers, visible_timers is an empty list."""
    resp = state_to_response(engine.get_state())
    assert resp.visible_timers == []


def test_state_to_response_visible_timers_populated_after_lab_order():
    """After ordering a lab, visible_timers contains a pending_reveal entry."""
    case = validate_case(EXAMPLE_CASE)
    fresh_engine = SatoriEngine(case)
    fresh_engine.execute_action("history_general")
    fresh_engine.execute_action("order_labs:cbc")
    resp = state_to_response(fresh_engine.get_state())
    assert len(resp.visible_timers) > 0
    vt = resp.visible_timers[0]
    assert vt.source == "pending_reveal"
    assert vt.node_id == "node_04_cbc_results"
    assert isinstance(vt.label, str) and len(vt.label) > 0
    assert isinstance(vt.remaining_minutes, int) and vt.remaining_minutes > 0


def test_visible_timer_response_has_correct_fields():
    """VisibleTimerResponse has all four required fields."""
    from satori_api.models import VisibleTimerResponse

    vtr = VisibleTimerResponse(
        label="CBC Results",
        remaining_minutes=25,
        source="pending_reveal",
        node_id="node_04_cbc_results",
    )
    assert vtr.label == "CBC Results"
    assert vtr.remaining_minutes == 25
    assert vtr.source == "pending_reveal"
    assert vtr.node_id == "node_04_cbc_results"
