"""Unit tests for EffectExecutor.

Tests all 9 EffectType handlers, idempotency guards, and error handling.
"""

from uuid import uuid4

import pytest

from satori.effect_executor import EffectExecutor
from satori.events import (
    ActionLockedEvent,
    ActionUnlockedEvent,
    CaseEndedEvent,
    FlagClearedEvent,
    FlagSetEvent,
    NodeActivatedEvent,
)
from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    CaseDefinition,
    Effect,
    EffectType,
    Node,
    NodeContent,
    NodeTimer,
    NodeType,
    VitalSigns,
)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _base_state() -> GameState:
    return GameState(
        case_id=uuid4(),
        current_time_minutes=30,
        flags=frozenset(),
        active_nodes=frozenset(),
        revealed_nodes=frozenset(),
        expired_nodes=frozenset(),
        pending_reveals={},
        timers={},
        timer_stages={},
        current_vitals=VitalSigns(heart_rate=80, o2_saturation=97),
        available_actions=frozenset({"history_general"}),
    )


def _minimal_case(nodes: list[Node] | None = None) -> CaseDefinition:
    """Build a bare-bones case definition with an optional node list."""
    import json
    from pathlib import Path

    case_path = Path(__file__).resolve().parents[2] / ".." / "cases" / "example-neurocysticercosis.json"
    with case_path.open() as f:
        data = json.load(f)

    if nodes:
        data["nodes"] = [n.model_dump(mode="json") for n in nodes]

    return CaseDefinition.model_validate(data)


def _make_node(
    node_id: str,
    node_type: NodeType = NodeType.MEDICAL_FINDING,
    timer: NodeTimer | None = None,
) -> Node:
    return Node(
        id=node_id,
        type=node_type,
        content=NodeContent(narrative_text="test"),
        activation=ActivationRule(starts_active=False),
        timer=timer,
    )


@pytest.fixture
def executor() -> EffectExecutor:
    return EffectExecutor()


# ---------------------------------------------------------------------------
# SET_FLAG
# ---------------------------------------------------------------------------


class TestSetFlag:
    def test_sets_new_flag(self, executor: EffectExecutor):
        state = _base_state()
        effect = Effect(type=EffectType.SET_FLAG, target="foo")
        case = _minimal_case()
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "foo" in new_state.flags
        assert len(events) == 1
        assert isinstance(events[0], FlagSetEvent)
        assert events[0].flag == "foo"

    def test_idempotent_already_set(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), flags=frozenset({"foo"}))
        effect = Effect(type=EffectType.SET_FLAG, target="foo")
        case = _minimal_case()
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state  # no change
        assert events == []


# ---------------------------------------------------------------------------
# CLEAR_FLAG
# ---------------------------------------------------------------------------


class TestClearFlag:
    def test_clears_existing_flag(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), flags=frozenset({"bar"}))
        effect = Effect(type=EffectType.CLEAR_FLAG, target="bar")
        case = _minimal_case()
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "bar" not in new_state.flags
        assert len(events) == 1
        assert isinstance(events[0], FlagClearedEvent)

    def test_idempotent_not_set(self, executor: EffectExecutor):
        state = _base_state()
        effect = Effect(type=EffectType.CLEAR_FLAG, target="bar")
        case = _minimal_case()
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# ACTIVATE_NODE
# ---------------------------------------------------------------------------


class TestActivateNode:
    def test_activates_node(self, executor: EffectExecutor):
        node = _make_node("n1")
        case = _minimal_case([node])
        state = _base_state()
        effect = Effect(type=EffectType.ACTIVATE_NODE, target="n1")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "n1" in new_state.active_nodes
        assert any(isinstance(e, NodeActivatedEvent) and e.node_id == "n1" for e in events)

    def test_activates_node_with_timer(self, executor: EffectExecutor):
        timer = NodeTimer(duration_minutes=120, on_expire=[Effect(type=EffectType.SET_FLAG, target="x")])
        node = _make_node("n2", timer=timer)
        case = _minimal_case([node])
        state = _base_state()
        effect = Effect(type=EffectType.ACTIVATE_NODE, target="n2")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "n2" in new_state.active_nodes
        assert new_state.timers["n2"] == 120
        assert new_state.timer_stages["n2"] == 0

    def test_idempotent_already_active(self, executor: EffectExecutor):
        from dataclasses import replace

        node = _make_node("n1")
        case = _minimal_case([node])
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))
        effect = Effect(type=EffectType.ACTIVATE_NODE, target="n1")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []

    def test_activate_nonexistent_node(self, executor: EffectExecutor):
        case = _minimal_case([_make_node("other")])
        state = _base_state()
        effect = Effect(type=EffectType.ACTIVATE_NODE, target="missing")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# DEACTIVATE_NODE
# ---------------------------------------------------------------------------


class TestDeactivateNode:
    def test_deactivates_active_node(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            timers={"n1": 50},
            timer_stages={"n1": 0},
        )
        case = _minimal_case()
        effect = Effect(type=EffectType.DEACTIVATE_NODE, target="n1")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "n1" not in new_state.active_nodes
        assert "n1" not in new_state.timers
        assert "n1" not in new_state.timer_stages

    def test_idempotent_not_active(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.DEACTIVATE_NODE, target="n1")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# MODIFY_TIMER
# ---------------------------------------------------------------------------


class TestModifyTimer:
    def test_subtract_time(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), timers={"n1": 100})
        case = _minimal_case()
        effect = Effect(type=EffectType.MODIFY_TIMER, target="n1", value=-60)
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.timers["n1"] == 40

    def test_add_time(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), timers={"n1": 100})
        case = _minimal_case()
        effect = Effect(type=EffectType.MODIFY_TIMER, target="n1", value=30)
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.timers["n1"] == 130

    def test_clamp_to_zero(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), timers={"n1": 20})
        case = _minimal_case()
        effect = Effect(type=EffectType.MODIFY_TIMER, target="n1", value=-100)
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.timers["n1"] == 0

    def test_no_timer_no_change(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.MODIFY_TIMER, target="n1", value=-60)
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# UNLOCK / LOCK ACTION
# ---------------------------------------------------------------------------


class TestUnlockAction:
    def test_unlocks_new_action(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.UNLOCK_ACTION, target="order_labs")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "order_labs" in new_state.available_actions
        assert any(isinstance(e, ActionUnlockedEvent) for e in events)

    def test_idempotent_already_unlocked(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.UNLOCK_ACTION, target="history_general")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


class TestLockAction:
    def test_locks_existing_action(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.LOCK_ACTION, target="history_general")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert "history_general" not in new_state.available_actions
        assert any(isinstance(e, ActionLockedEvent) for e in events)

    def test_idempotent_not_available(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.LOCK_ACTION, target="nonexistent")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# OVERRIDE_VITALS
# ---------------------------------------------------------------------------


class TestOverrideVitals:
    def test_override_heart_rate(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.OVERRIDE_VITALS, target="heart_rate", value=150)
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.current_vitals.heart_rate == 150
        assert events == []  # no event for override (engine emits vitals changed)

    def test_override_unknown_vital_no_crash(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.OVERRIDE_VITALS, target="nonexistent_vital", value=42)
        # Should not crash, just leave vitals unchanged
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.current_vitals.heart_rate == state.current_vitals.heart_rate


# ---------------------------------------------------------------------------
# END_CASE
# ---------------------------------------------------------------------------


class TestEndCase:
    def test_ends_case(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effect = Effect(type=EffectType.END_CASE, target="failure")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state.case_ended is True
        assert new_state.outcome_tier == "failure"
        assert any(isinstance(e, CaseEndedEvent) and e.outcome_tier == "failure" for e in events)

    def test_idempotent_already_ended(self, executor: EffectExecutor):
        from dataclasses import replace

        state = replace(_base_state(), case_ended=True, outcome_tier="optimal")
        case = _minimal_case()
        effect = Effect(type=EffectType.END_CASE, target="failure")
        new_state, events = executor._apply_single_effect(effect, state, case)
        assert new_state is state
        assert events == []


# ---------------------------------------------------------------------------
# apply_effects (list dispatch)
# ---------------------------------------------------------------------------


class TestApplyEffects:
    def test_none_effects(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        new_state, events = executor.apply_effects(None, state, case)
        assert new_state is state
        assert events == []

    def test_empty_effects(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        new_state, events = executor.apply_effects([], state, case)
        assert new_state is state
        assert events == []

    def test_multiple_effects_applied_sequentially(self, executor: EffectExecutor):
        state = _base_state()
        case = _minimal_case()
        effects = [
            Effect(type=EffectType.SET_FLAG, target="a"),
            Effect(type=EffectType.SET_FLAG, target="b"),
            Effect(type=EffectType.UNLOCK_ACTION, target="order_labs"),
        ]
        new_state, events = executor.apply_effects(effects, state, case)
        assert "a" in new_state.flags
        assert "b" in new_state.flags
        assert "order_labs" in new_state.available_actions
        assert len(events) == 3  # FlagSet, FlagSet, ActionUnlocked
