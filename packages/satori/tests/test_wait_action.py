"""Tests for the built-in wait action.

Covers: valid durations, error cases, clock advance, WaitedEvent emission,
pending reveal maturation, tick integration (timers, vitals, end conditions),
and determinism.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from satori.engine import WAIT_DURATIONS, InvalidActionError, SatoriEngine
from satori.events import (
    NodeRevealedEvent,
    TimeAdvancedEvent,
    WaitedEvent,
)
from satori.models.case_definition import validate_case

EXAMPLE_CASE_PATH = Path(__file__).parent.parent.parent.parent / "cases" / "example-neurocysticercosis.json"


@pytest.fixture
def engine() -> SatoriEngine:
    case = validate_case(EXAMPLE_CASE_PATH)
    return SatoriEngine(case)


@pytest.fixture
def engine_after_history(engine: SatoriEngine) -> SatoriEngine:
    """Engine after executing history_general — unlocks lab ordering."""
    engine.execute_action("history_general")
    return engine


# ---------------------------------------------------------------------------
# Valid durations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("duration", [15, 30, 60])
def test_wait_valid_duration_returns_events(engine: SatoriEngine, duration: int) -> None:
    """All three allowed wait durations return a non-empty event list."""
    events = engine.execute_action(f"wait:{duration}")
    assert len(events) > 0


@pytest.mark.parametrize("duration", [15, 30, 60])
def test_wait_emits_waited_event_first(engine: SatoriEngine, duration: int) -> None:
    """WaitedEvent must be the first event in the returned list."""
    events = engine.execute_action(f"wait:{duration}")
    assert isinstance(events[0], WaitedEvent)
    waited = events[0]
    assert waited.duration_minutes == duration


@pytest.mark.parametrize("duration", [15, 30, 60])
def test_wait_emits_time_advanced_event(engine: SatoriEngine, duration: int) -> None:
    """A TimeAdvancedEvent must be emitted (after WaitedEvent)."""
    events = engine.execute_action(f"wait:{duration}")
    time_events = [e for e in events if isinstance(e, TimeAdvancedEvent)]
    assert len(time_events) == 1
    te = time_events[0]
    assert te.new_time - te.old_time == duration


@pytest.mark.parametrize("duration", [15, 30, 60])
def test_wait_advances_clock_by_duration(engine: SatoriEngine, duration: int) -> None:
    """Game clock advances by exactly the wait duration."""
    initial_time = engine.get_state().current_time_minutes
    engine.execute_action(f"wait:{duration}")
    assert engine.get_state().current_time_minutes == initial_time + duration


def test_wait_does_not_appear_in_playable_actions(engine: SatoriEngine) -> None:
    """wait is built-in; it must not appear in get_playable_actions()."""
    playable = engine.get_playable_actions()
    assert not any(a.startswith("wait") for a in playable)


def test_wait_does_not_appear_in_available_actions(engine: SatoriEngine) -> None:
    """wait is built-in; it must not appear in get_available_actions()."""
    available = engine.get_available_actions()
    assert "wait" not in available


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_wait_no_subcategory_raises(engine: SatoriEngine) -> None:
    """Bare 'wait' without a duration raises InvalidActionError."""
    with pytest.raises(InvalidActionError, match="requires a duration"):
        engine.execute_action("wait")


def test_wait_zero_raises(engine: SatoriEngine) -> None:
    """wait:0 is not in the allowed set and must raise."""
    with pytest.raises(InvalidActionError, match="must be one of"):
        engine.execute_action("wait:0")


def test_wait_45_raises(engine: SatoriEngine) -> None:
    """wait:45 is not in the allowed set and must raise."""
    with pytest.raises(InvalidActionError, match="must be one of"):
        engine.execute_action("wait:45")


def test_wait_non_integer_raises(engine: SatoriEngine) -> None:
    """wait:foo must raise with a message about non-integer input."""
    with pytest.raises(InvalidActionError, match="must be an integer"):
        engine.execute_action("wait:foo")


def test_wait_negative_raises(engine: SatoriEngine) -> None:
    """wait:-5 is not in the allowed set and must raise."""
    with pytest.raises(InvalidActionError, match="must be one of"):
        engine.execute_action("wait:-5")


def test_wait_after_case_ended_raises(engine: SatoriEngine) -> None:
    """Wait on an ended game raises InvalidActionError like other actions."""
    # Force the case to end via a long wait sequence
    # Use repeated waits to push past time limit (360 min simulated)
    for _ in range(7):  # 7 × 60 = 420 min > 360 min limit
        try:
            engine.execute_action("wait:60")
        except InvalidActionError:
            break
    # Now the case must be ended
    assert engine.get_state().case_ended
    with pytest.raises(InvalidActionError, match="already ended"):
        engine.execute_action("wait:15")


# ---------------------------------------------------------------------------
# Tick integration
# ---------------------------------------------------------------------------


def test_wait_matures_pending_reveal(engine_after_history: SatoriEngine) -> None:
    """If wait duration covers a pending_reveal's remaining time, the reveal fires."""
    e = engine_after_history
    # Order CBC — pending reveal of 30 minutes
    e.execute_action("order_labs:cbc")
    state_before = e.get_state()
    assert "node_04_cbc_results" in state_before.pending_reveals

    # Wait 30 minutes — should mature the CBC
    events = e.execute_action("wait:30")
    revealed_ids = {ev.node_id for ev in events if isinstance(ev, NodeRevealedEvent)}
    assert "node_04_cbc_results" in revealed_ids

    # CBC should no longer be pending
    state_after = e.get_state()
    assert "node_04_cbc_results" not in state_after.pending_reveals
    assert "node_04_cbc_results" in state_after.revealed_nodes


def test_wait_advances_all_active_timers(engine: SatoriEngine) -> None:
    """All active node timers tick by the wait duration.

    node_09_headache_progression activates after history_general sets the
    headaches_two_weeks flag. Do that first, then verify the timer ticks.
    """
    engine.execute_action("history_general")
    state_before = engine.get_state()
    assert "node_09_headache_progression" in state_before.timers
    initial_remaining = state_before.timers["node_09_headache_progression"]

    engine.execute_action("wait:30")
    state_after = engine.get_state()
    # If not expired yet, remaining should decrease by 30
    if "node_09_headache_progression" in state_after.timers:
        assert state_after.timers["node_09_headache_progression"] == initial_remaining - 30


def test_wait_triggers_timer_stage_effects(engine: SatoriEngine) -> None:
    """Waiting past a timer stage boundary applies the stage's effects.

    node_09_headache_progression activates after history_general. Its first
    stage at 60 min (elapsed) changes vitals. Wait 60 min to trigger it.
    """
    # Activate node_09 via history_general (sets headaches_two_weeks flag)
    engine.execute_action("history_general")
    # node_09 now has 180 min remaining. Its first stage fires at 60 min elapsed,
    # i.e., when the remaining time reaches 120. Wait 60 min to cross it.
    initial_vitals = engine.get_state().current_vitals
    engine.execute_action("wait:60")
    new_vitals = engine.get_state().current_vitals
    # Stage at 60 min elapsed raises HR from 92 to 97 — vitals must have changed
    assert new_vitals.heart_rate != initial_vitals.heart_rate


def test_wait_updates_visible_timers(engine_after_history: SatoriEngine) -> None:
    """After ordering a lab and waiting, visible_timers reflects the pending reveal."""
    e = engine_after_history
    e.execute_action("order_labs:cbc")
    state = e.get_state()
    assert any(vt.node_id == "node_04_cbc_results" for vt in state.visible_timers)
    # Wait 15 min — remaining should decrease
    e.execute_action("wait:15")
    state_after = e.get_state()
    pending_vt = next((vt for vt in state_after.visible_timers if vt.node_id == "node_04_cbc_results"), None)
    if pending_vt is not None:
        # Still pending — remaining decreased
        assert pending_vt.remaining_minutes < state.visible_timers[0].remaining_minutes


def test_wait_evaluates_end_conditions(engine: SatoriEngine) -> None:
    """Waiting past the time limit ends the case."""
    # Maria Santos: 360 min simulated duration (time limit)
    # Wait 60 × 7 = 420 min — should trigger TIME_ELAPSED end condition
    ended = False
    for _ in range(7):
        engine.execute_action("wait:60")
        if engine.get_state().case_ended:
            ended = True
            break
    assert ended, "Case should have ended after exceeding time limit"
    assert engine.get_state().outcome_tier is not None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_wait_determinism_same_sequence_same_outcome() -> None:
    """Identical wait sequences from identical starting states produce identical results."""
    case = validate_case(EXAMPLE_CASE_PATH)

    def run_sequence() -> dict[str, object]:
        eng = SatoriEngine(case)
        eng.execute_action("history_general")
        eng.execute_action("wait:15")
        eng.execute_action("wait:30")
        s = eng.get_state()
        return {
            "time": s.current_time_minutes,
            "flags": sorted(s.flags),
            "active_nodes": sorted(s.active_nodes),
            "revealed_nodes": sorted(s.revealed_nodes),
            "pending_reveals": dict(s.pending_reveals),
        }

    result_a = run_sequence()
    result_b = run_sequence()
    assert result_a == result_b


# ---------------------------------------------------------------------------
# WAIT_DURATIONS constant
# ---------------------------------------------------------------------------


def test_wait_durations_constant() -> None:
    """WAIT_DURATIONS must be exactly {15, 30, 60}."""
    assert WAIT_DURATIONS == frozenset({15, 30, 60})
