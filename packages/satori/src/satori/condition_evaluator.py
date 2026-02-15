"""Condition evaluation logic for activation rules, reveal gates, and end conditions.

Implements OR-of-ANDs logic: a rule is satisfied if ANY path is satisfied,
and a path is satisfied if ALL conditions in it are true.
"""

from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    Comparator,
    Condition,
    ConditionType,
    RevealRule,
)


class ConditionEvaluator:
    """Evaluates activation, reveal, and end conditions against game state."""

    def evaluate_activation_rule(
        self, rule: ActivationRule, state: GameState
    ) -> bool:
        """Evaluate if activation rule is satisfied.

        OR-of-ANDs logic:
        - Rule satisfied if ANY path is satisfied
        - Path satisfied if ALL conditions in path are true
        - If rule.paths is None and starts_active is False, never activates by path
        - If rule.starts_active is True, this is only called for re-evaluation
          (node was already activated at init)

        Args:
            rule: The activation rule to evaluate
            state: Current game state

        Returns:
            True if the rule is satisfied
        """
        if rule.paths is None:
            return False

        return any(
            all(self._evaluate_condition(cond, state) for cond in path.conditions)
            for path in rule.paths
        )

    def evaluate_reveal_rule(
        self,
        rule: RevealRule,
        state: GameState,
        base_action: str | None,
        action_param: str | None,
    ) -> bool:
        """Evaluate if reveal rule is satisfied by the given action.

        Matching logic:
        1. If rule.auto_reveal is True → always True (handled separately, but
           this returns True for consistency)
        2. If rule.action is not None:
           - base_action must match rule.action
           - If rule.subcategory is not None, action_param must match rule.subcategory
        3. If rule.conditions is not None, all must be satisfied

        Args:
            rule: The reveal rule to evaluate
            state: Current game state
            base_action: Base portion of the action (before colon)
            action_param: Parameter portion (after colon), or None

        Returns:
            True if the reveal rule is satisfied
        """
        if rule.auto_reveal:
            return True

        # Action matching
        if rule.action is not None:
            if base_action != rule.action:
                return False
            if rule.subcategory is not None and action_param != rule.subcategory:
                return False

        # Additional conditions
        if rule.conditions:
            if not all(self._evaluate_condition(c, state) for c in rule.conditions):
                return False

        return True

    def _evaluate_condition(self, condition: Condition, state: GameState) -> bool:
        """Evaluate a single condition against current state.

        Args:
            condition: The condition to evaluate
            state: Current game state

        Returns:
            True if the condition is satisfied

        Raises:
            ValueError: If condition type is unknown
        """
        match condition.type:
            case ConditionType.FLAG_SET:
                return condition.target in state.flags
            case ConditionType.FLAG_NOT_SET:
                return condition.target not in state.flags
            case ConditionType.NODE_ACTIVE:
                return condition.target in state.active_nodes
            case ConditionType.NODE_REVEALED:
                return condition.target in state.revealed_nodes
            case ConditionType.NODE_EXPIRED:
                return condition.target in state.expired_nodes
            case ConditionType.TIME_ELAPSED:
                return self._compare(
                    state.current_time_minutes,
                    condition.value,
                    condition.comparator or Comparator.GTE,
                )
            case ConditionType.VITAL_THRESHOLD:
                return self._evaluate_vital_threshold(condition, state)
            case _:
                raise ValueError(f"Unknown condition type: {condition.type}")

    def _compare(
        self, actual: float, threshold: float, comp: Comparator
    ) -> bool:
        """Apply comparator to two values.

        Args:
            actual: The actual value
            threshold: The threshold to compare against
            comp: The comparison operator

        Returns:
            True if the comparison holds
        """
        match comp:
            case Comparator.GT:
                return actual > threshold
            case Comparator.LT:
                return actual < threshold
            case Comparator.GTE:
                return actual >= threshold
            case Comparator.LTE:
                return actual <= threshold
            case Comparator.EQ:
                return actual == threshold

    def _evaluate_vital_threshold(
        self, condition: Condition, state: GameState
    ) -> bool:
        """Evaluate a vital threshold condition.

        condition.target = vital name (e.g., "heart_rate", "o2_saturation")
        condition.value = threshold value
        condition.comparator = comparison operator

        Args:
            condition: The vital threshold condition
            state: Current game state

        Returns:
            True if the vital threshold condition is satisfied
        """
        vital_value = getattr(state.current_vitals, condition.target, None)
        if vital_value is None:
            return False
        return self._compare(
            vital_value, condition.value, condition.comparator or Comparator.GTE
        )
