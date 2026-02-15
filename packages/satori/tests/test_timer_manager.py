"""Unit tests for TimerManager.

Tests advance_timers (pause, countdown, stage crossings, expiry),
advance_pending_reveals, and _check_pause_conditions.
"""

from dataclasses import replace
from uuid import uuid4

import pytest

from satori.condition_evaluator import ConditionEvaluator
from satori.events import NodeExpiredEvent, NodeRevealedEvent, TimerStageEvent
from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    CaseDefinition,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    Node,
    NodeContent,
    NodeTimer,
    NodeType,
    TimerStage,
    VitalSigns,
)
from satori.timer_manager import TimerManager

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _base_state() -> GameState:
    return GameState(
        case_id=uuid4(),
        current_time_minutes=0,
        flags=frozenset(),
        active_nodes=frozenset(),
        revealed_nodes=frozenset(),
        expired_nodes=frozenset(),
        pending_reveals={},
        timers={},
        timer_stages={},
        current_vitals=VitalSigns(heart_rate=80, o2_saturation=97),
        available_actions=frozenset(),
    )


def _load_case() -> CaseDefinition:
    import json
    from pathlib import Path

    case_path = Path(__file__).resolve().parents[2] / ".." / "cases" / "example-neurocysticercosis.json"
    with case_path.open() as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


def _make_node(
    node_id: str,
    timer: NodeTimer | None = None,
    node_type: NodeType = NodeType.PROGRESSION,
) -> Node:
    return Node(
        id=node_id,
        type=node_type,
        content=NodeContent(narrative_text="test"),
        activation=ActivationRule(starts_active=False),
        timer=timer,
    )


@pytest.fixture
def tm() -> TimerManager:
    return TimerManager(ConditionEvaluator())


# ---------------------------------------------------------------------------
# advance_timers — basic countdown
# ---------------------------------------------------------------------------


class TestAdvanceTimersBasic:
    def test_timer_decrements(self, tm: TimerManager):
        timer = NodeTimer(duration_minutes=120, on_expire=[Effect(type=EffectType.SET_FLAG, target="x")])
        node = _make_node("n1", timer=timer)
        case = _load_case()
        # Build case with our node
        case_data = case.model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 120},
            timer_stages={"n1": 0},
        )

        new_state, events = tm.advance_timers(state, 15, case)
        assert new_state.timers["n1"] == 105  # 120 - 15

    def test_no_timers_no_change(self, tm: TimerManager):
        case = _load_case()
        state = _base_state()
        new_state, events = tm.advance_timers(state, 15, case)
        assert new_state.timers == {}
        assert events == []


# ---------------------------------------------------------------------------
# advance_timers — expiry
# ---------------------------------------------------------------------------


class TestAdvanceTimersExpiry:
    def test_timer_expires_at_zero(self, tm: TimerManager):
        timer = NodeTimer(duration_minutes=60, on_expire=[Effect(type=EffectType.SET_FLAG, target="expired_flag")])
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 10},
            timer_stages={"n1": 0},
        )

        new_state, events = tm.advance_timers(state, 15, case)
        # Timer expired → removed from timers, added to expired_nodes
        assert "n1" not in new_state.timers
        assert "n1" not in new_state.timer_stages
        assert "n1" in new_state.expired_nodes
        assert any(isinstance(e, NodeExpiredEvent) and e.node_id == "n1" for e in events)

    def test_timer_expires_exactly(self, tm: TimerManager):
        timer = NodeTimer(duration_minutes=60, on_expire=[Effect(type=EffectType.SET_FLAG, target="x")])
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 15},
            timer_stages={"n1": 0},
        )
        new_state, events = tm.advance_timers(state, 15, case)
        assert "n1" not in new_state.timers
        assert "n1" in new_state.expired_nodes


# ---------------------------------------------------------------------------
# advance_timers — stage transitions
# ---------------------------------------------------------------------------


class TestAdvanceTimersStages:
    def test_stage_crossed(self, tm: TimerManager):
        stage = TimerStage(
            at_minutes=30,
            effects=[Effect(type=EffectType.SET_FLAG, target="stage_30")],
            vital_signs=VitalSigns(heart_rate=100),
        )
        timer = NodeTimer(
            duration_minutes=120,
            stages=[stage],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        # Timer at full duration → elapsed=0, after 15 min → elapsed=15.
        # Stage at 30 not crossed yet.
        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 120},
            timer_stages={"n1": 0},
        )

        new_state, events = tm.advance_timers(state, 15, case)
        # Stage at 30 not yet crossed (elapsed will be 15)
        stage_events = [e for e in events if isinstance(e, TimerStageEvent)]
        assert len(stage_events) == 0
        assert new_state.timer_stages["n1"] == 0  # unchanged

    def test_stage_crossed_at_threshold(self, tm: TimerManager):
        stage = TimerStage(
            at_minutes=30,
            effects=[Effect(type=EffectType.SET_FLAG, target="stage_30")],
            vital_signs=VitalSigns(heart_rate=100),
        )
        timer = NodeTimer(
            duration_minutes=120,
            stages=[stage],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        # Remaining = 100 → elapsed = 20. Advance 15 → elapsed = 35, crosses 30.
        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 100},
            timer_stages={"n1": 0},
        )

        new_state, events = tm.advance_timers(state, 15, case)
        stage_events = [e for e in events if isinstance(e, TimerStageEvent)]
        assert len(stage_events) == 1
        assert stage_events[0].node_id == "n1"
        assert stage_events[0].stage_at_minutes == 30
        assert stage_events[0].vital_signs_changed is True
        assert new_state.timer_stages["n1"] == 30


# ---------------------------------------------------------------------------
# advance_timers — pause conditions
# ---------------------------------------------------------------------------


class TestAdvanceTimersPause:
    def test_paused_timer_does_not_advance(self, tm: TimerManager):
        """Timer paused when all pause conditions met → no countdown."""
        timer = NodeTimer(
            duration_minutes=60,
            pause_conditions=[Condition(type=ConditionType.FLAG_SET, target="treatment_active")],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 60},
            timer_stages={"n1": 0},
            flags=frozenset({"treatment_active"}),
        )

        new_state, events = tm.advance_timers(state, 15, case)
        assert new_state.timers["n1"] == 60  # unchanged

    def test_unpaused_timer_advances(self, tm: TimerManager):
        """Pause condition not met → timer counts down normally."""
        timer = NodeTimer(
            duration_minutes=60,
            pause_conditions=[Condition(type=ConditionType.FLAG_SET, target="treatment_active")],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 60},
            timer_stages={"n1": 0},
            # NO treatment_active flag
        )

        new_state, events = tm.advance_timers(state, 15, case)
        assert new_state.timers["n1"] == 45  # 60 - 15


# ---------------------------------------------------------------------------
# _check_pause_conditions
# ---------------------------------------------------------------------------


class TestCheckPauseConditions:
    def test_none_returns_false(self, tm: TimerManager):
        state = _base_state()
        assert tm._check_pause_conditions(None, state) is False

    def test_empty_returns_false(self, tm: TimerManager):
        state = _base_state()
        assert tm._check_pause_conditions([], state) is False

    def test_all_met_returns_true(self, tm: TimerManager):
        state = replace(_base_state(), flags=frozenset({"a", "b"}))
        conditions = [
            Condition(type=ConditionType.FLAG_SET, target="a"),
            Condition(type=ConditionType.FLAG_SET, target="b"),
        ]
        assert tm._check_pause_conditions(conditions, state) is True

    def test_partial_met_returns_false(self, tm: TimerManager):
        """ALL conditions must be met → partial fails."""
        state = replace(_base_state(), flags=frozenset({"a"}))
        conditions = [
            Condition(type=ConditionType.FLAG_SET, target="a"),
            Condition(type=ConditionType.FLAG_SET, target="b"),
        ]
        assert tm._check_pause_conditions(conditions, state) is False


# ---------------------------------------------------------------------------
# advance_pending_reveals
# ---------------------------------------------------------------------------


class TestAdvancePendingReveals:
    def test_pending_reveal_completes(self, tm: TimerManager):
        node = _make_node("n1", node_type=NodeType.LAB_RESULT)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            pending_reveals={"n1": 5},
        )

        new_state, events = tm.advance_pending_reveals(state, 10, case)
        assert "n1" not in new_state.pending_reveals
        assert "n1" in new_state.revealed_nodes
        assert any(isinstance(e, NodeRevealedEvent) and e.node_id == "n1" for e in events)

    def test_pending_reveal_not_yet_due(self, tm: TimerManager):
        node = _make_node("n1", node_type=NodeType.LAB_RESULT)
        case_data = _load_case().model_dump(mode="json")
        case_data["nodes"] = [node.model_dump(mode="json")]
        case = CaseDefinition.model_validate(case_data)

        state = replace(
            _base_state(),
            pending_reveals={"n1": 20},
        )

        new_state, events = tm.advance_pending_reveals(state, 10, case)
        assert "n1" in new_state.pending_reveals
        assert new_state.pending_reveals["n1"] == 10  # 20 - 10
        assert "n1" not in new_state.revealed_nodes
        assert events == []

    def test_no_pending_reveals(self, tm: TimerManager):
        case = _load_case()
        state = _base_state()
        new_state, events = tm.advance_pending_reveals(state, 15, case)
        assert new_state.pending_reveals == {}
        assert events == []
