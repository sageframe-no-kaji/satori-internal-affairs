"""Unit tests for ConditionEvaluator.

Tests all 7 ConditionType branches, all 5 Comparator branches,
OR-of-ANDs activation logic, reveal rule evaluation, vital threshold
evaluation, and error handling.
"""

from uuid import uuid4

import pytest

from satori.condition_evaluator import ConditionEvaluator
from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    Comparator,
    Condition,
    ConditionPath,
    ConditionType,
    RevealRule,
    VitalSigns,
)

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------


@pytest.fixture
def evaluator() -> ConditionEvaluator:
    return ConditionEvaluator()


@pytest.fixture
def base_state() -> GameState:
    """Minimal game state for unit tests."""
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
        current_vitals=VitalSigns(
            heart_rate=80,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            temperature=98.6,
            respiratory_rate=16,
            o2_saturation=97,
        ),
        available_actions=frozenset(),
    )


def state_with(base: GameState, **kwargs) -> GameState:
    """Build a state with overrides using dataclasses.replace."""
    from dataclasses import replace

    return replace(base, **kwargs)


# ---------------------------------------------------------------------------
# CONDITION TYPE BRANCHES
# ---------------------------------------------------------------------------


class TestConditionTypes:
    """Each ConditionType arm in _evaluate_condition."""

    def test_flag_set_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.FLAG_SET, target="lesion_found")
        s = state_with(base_state, flags=frozenset({"lesion_found"}))
        assert evaluator._evaluate_condition(cond, s) is True

    def test_flag_set_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.FLAG_SET, target="lesion_found")
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_flag_not_set_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.FLAG_NOT_SET, target="lesion_found")
        assert evaluator._evaluate_condition(cond, base_state) is True

    def test_flag_not_set_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.FLAG_NOT_SET, target="lesion_found")
        s = state_with(base_state, flags=frozenset({"lesion_found"}))
        assert evaluator._evaluate_condition(cond, s) is False

    def test_node_active_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_ACTIVE, target="node_06")
        s = state_with(base_state, active_nodes=frozenset({"node_06"}))
        assert evaluator._evaluate_condition(cond, s) is True

    def test_node_active_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_ACTIVE, target="node_06")
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_node_revealed_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_REVEALED, target="node_02")
        s = state_with(base_state, revealed_nodes=frozenset({"node_02"}))
        assert evaluator._evaluate_condition(cond, s) is True

    def test_node_revealed_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_REVEALED, target="node_02")
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_node_expired_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_EXPIRED, target="node_06")
        s = state_with(base_state, expired_nodes=frozenset({"node_06"}))
        assert evaluator._evaluate_condition(cond, s) is True

    def test_node_expired_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.NODE_EXPIRED, target="node_06")
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_time_elapsed_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.TIME_ELAPSED, target="", value=60, comparator=Comparator.GTE)
        s = state_with(base_state, current_time_minutes=60)
        assert evaluator._evaluate_condition(cond, s) is True

    def test_time_elapsed_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        cond = Condition(type=ConditionType.TIME_ELAPSED, target="", value=60, comparator=Comparator.GTE)
        s = state_with(base_state, current_time_minutes=59)
        assert evaluator._evaluate_condition(cond, s) is False

    def test_time_elapsed_default_comparator_gte(self, evaluator: ConditionEvaluator, base_state: GameState):
        """When comparator is None, defaults to GTE."""
        cond = Condition(type=ConditionType.TIME_ELAPSED, target="", value=30)
        s = state_with(base_state, current_time_minutes=30)
        assert evaluator._evaluate_condition(cond, s) is True

    def test_vital_threshold_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        """O2 saturation < 90 when it's 85."""
        cond = Condition(type=ConditionType.VITAL_THRESHOLD, target="o2_saturation", value=90, comparator=Comparator.LT)
        vitals = VitalSigns(heart_rate=80, o2_saturation=85)
        s = state_with(base_state, current_vitals=vitals)
        assert evaluator._evaluate_condition(cond, s) is True

    def test_vital_threshold_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        """O2 saturation < 90 when it's 97."""
        cond = Condition(type=ConditionType.VITAL_THRESHOLD, target="o2_saturation", value=90, comparator=Comparator.LT)
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_vital_threshold_missing_vital_returns_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        """If the vital field doesn't exist on VitalSigns, return False."""
        cond = Condition(
            type=ConditionType.VITAL_THRESHOLD, target="nonexistent_vital", value=50, comparator=Comparator.GT
        )
        assert evaluator._evaluate_condition(cond, base_state) is False

    def test_time_elapsed_none_value_raises(self, evaluator: ConditionEvaluator, base_state: GameState):
        """A TIME_ELAPSED condition authored without a value fails loud, not with TypeError."""
        cond = Condition(type=ConditionType.TIME_ELAPSED, target="")
        with pytest.raises(ValueError, match="TIME_ELAPSED"):
            evaluator._evaluate_condition(cond, base_state)

    def test_vital_threshold_none_value_raises(self, evaluator: ConditionEvaluator, base_state: GameState):
        """A VITAL_THRESHOLD condition authored without a value fails loud, not with TypeError."""
        cond = Condition(type=ConditionType.VITAL_THRESHOLD, target="o2_saturation")
        with pytest.raises(ValueError, match="VITAL_THRESHOLD"):
            evaluator._evaluate_condition(cond, base_state)


# ---------------------------------------------------------------------------
# COMPARATOR BRANCHES
# ---------------------------------------------------------------------------


class TestComparators:
    """All five Comparator arms in _compare."""

    def test_gt_true(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(10, 5, Comparator.GT) is True

    def test_gt_false_equal(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 5, Comparator.GT) is False

    def test_lt_true(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 10, Comparator.LT) is True

    def test_lt_false(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(10, 5, Comparator.LT) is False

    def test_gte_true_equal(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 5, Comparator.GTE) is True

    def test_gte_true_greater(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(6, 5, Comparator.GTE) is True

    def test_gte_false(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(4, 5, Comparator.GTE) is False

    def test_lte_true_equal(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 5, Comparator.LTE) is True

    def test_lte_false(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(6, 5, Comparator.LTE) is False

    def test_eq_true(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 5, Comparator.EQ) is True

    def test_eq_false(self, evaluator: ConditionEvaluator):
        assert evaluator._compare(5, 6, Comparator.EQ) is False


# ---------------------------------------------------------------------------
# ACTIVATION RULE (OR-of-ANDs)
# ---------------------------------------------------------------------------


class TestActivationRule:
    """evaluate_activation_rule: OR-of-ANDs logic."""

    def test_none_paths_returns_false(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = ActivationRule(paths=None, starts_active=False)
        assert evaluator.evaluate_activation_rule(rule, base_state) is False

    def test_single_path_satisfied(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = ActivationRule(
            paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="x")])],
        )
        s = state_with(base_state, flags=frozenset({"x"}))
        assert evaluator.evaluate_activation_rule(rule, s) is True

    def test_single_path_not_satisfied(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = ActivationRule(
            paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="x")])],
        )
        assert evaluator.evaluate_activation_rule(rule, base_state) is False

    def test_or_of_ands_first_path_matches(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Two paths, only first satisfied → True (OR)."""
        rule = ActivationRule(
            paths=[
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="a")]),
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="b")]),
            ],
        )
        s = state_with(base_state, flags=frozenset({"a"}))
        assert evaluator.evaluate_activation_rule(rule, s) is True

    def test_or_of_ands_second_path_matches(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Two paths, only second satisfied → True (OR)."""
        rule = ActivationRule(
            paths=[
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="a")]),
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="b")]),
            ],
        )
        s = state_with(base_state, flags=frozenset({"b"}))
        assert evaluator.evaluate_activation_rule(rule, s) is True

    def test_and_within_path_partial_fails(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Single path with two conditions, only one satisfied → False (AND)."""
        rule = ActivationRule(
            paths=[
                ConditionPath(
                    conditions=[
                        Condition(type=ConditionType.FLAG_SET, target="a"),
                        Condition(type=ConditionType.FLAG_SET, target="b"),
                    ]
                ),
            ],
        )
        s = state_with(base_state, flags=frozenset({"a"}))
        assert evaluator.evaluate_activation_rule(rule, s) is False

    def test_and_within_path_all_met(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Single path with two conditions, both satisfied → True (AND)."""
        rule = ActivationRule(
            paths=[
                ConditionPath(
                    conditions=[
                        Condition(type=ConditionType.FLAG_SET, target="a"),
                        Condition(type=ConditionType.FLAG_SET, target="b"),
                    ]
                ),
            ],
        )
        s = state_with(base_state, flags=frozenset({"a", "b"}))
        assert evaluator.evaluate_activation_rule(rule, s) is True

    def test_no_paths_satisfied(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Two paths, neither satisfied → False."""
        rule = ActivationRule(
            paths=[
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="a")]),
                ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="b")]),
            ],
        )
        assert evaluator.evaluate_activation_rule(rule, base_state) is False


# ---------------------------------------------------------------------------
# REVEAL RULE
# ---------------------------------------------------------------------------


class TestRevealRule:
    """evaluate_reveal_rule: action matching + conditions."""

    def test_auto_reveal_always_true(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(auto_reveal=True)
        assert evaluator.evaluate_reveal_rule(rule, base_state, None, None) is True

    def test_action_match_no_subcategory(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(action="history_general")
        assert evaluator.evaluate_reveal_rule(rule, base_state, "history_general", None) is True

    def test_action_mismatch(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(action="history_general")
        assert evaluator.evaluate_reveal_rule(rule, base_state, "order_labs", None) is False

    def test_action_with_subcategory_match(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(action="history_focused", subcategory="dietary")
        assert evaluator.evaluate_reveal_rule(rule, base_state, "history_focused", "dietary") is True

    def test_action_with_subcategory_mismatch(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(action="history_focused", subcategory="dietary")
        assert evaluator.evaluate_reveal_rule(rule, base_state, "history_focused", "neurological") is False

    def test_reveal_with_additional_conditions_met(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(
            action="order_imaging",
            subcategory="brain_ct",
            conditions=[Condition(type=ConditionType.FLAG_SET, target="lesion_found")],
        )
        s = state_with(base_state, flags=frozenset({"lesion_found"}))
        assert evaluator.evaluate_reveal_rule(rule, s, "order_imaging", "brain_ct") is True

    def test_reveal_with_additional_conditions_not_met(self, evaluator: ConditionEvaluator, base_state: GameState):
        rule = RevealRule(
            action="order_imaging",
            subcategory="brain_ct",
            conditions=[Condition(type=ConditionType.FLAG_SET, target="lesion_found")],
        )
        assert evaluator.evaluate_reveal_rule(rule, base_state, "order_imaging", "brain_ct") is False

    def test_no_action_no_conditions(self, evaluator: ConditionEvaluator, base_state: GameState):
        """Rule with no action requirement and no conditions → always True."""
        rule = RevealRule()
        assert evaluator.evaluate_reveal_rule(rule, base_state, "anything", None) is True
