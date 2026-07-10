"""State checking operations for the Satori engine.

These methods check various state transitions: auto-reveals, action-triggered reveals,
interventions, node activations, vitals changes, and end conditions.

Extracted from engine.py to keep the main orchestrator under 500 lines.
"""

from dataclasses import replace

from satori.condition_evaluator import ConditionEvaluator
from satori.effect_executor import EffectExecutor
from satori.events import (
    CaseEndedEvent,
    Event,
    NodeActivatedEvent,
    NodeRevealedEvent,
    PendingRevealStartedEvent,
    VitalsChangedEvent,
)
from satori.game_state import GameState
from satori.models.case_definition import CaseDefinition, EndConditionType, Node
from satori.vitals_computer import VitalsComputer


class StateCheckers:
    """Handles state checking operations for the engine.

    This class contains methods that check and update game state based on various
    conditions: auto-reveals, action reveals, interventions, activations, vitals, and end conditions.
    """

    def __init__(
        self,
        node_map: dict[str, Node],
        case: CaseDefinition,
        condition_eval: ConditionEvaluator,
        effect_exec: EffectExecutor,
        vitals_comp: VitalsComputer,
    ):
        """Initialize state checkers.

        Args:
            node_map: Mapping of node IDs to Node objects
            case: Case definition
            condition_eval: Condition evaluator instance
            effect_exec: Effect executor instance
            vitals_comp: Vitals computer instance
        """
        self.node_map = node_map
        self.case = case
        self.condition_eval = condition_eval
        self.effect_exec = effect_exec
        self.vitals_comp = vitals_comp

    def check_auto_reveals(self, state: GameState) -> tuple[GameState, list[Event]]:
        """Check all active, unrevealed nodes for auto_reveal=True.

        If a node is active, has reveal.auto_reveal=True, and hasn't been
        revealed yet, reveal it immediately.

        Args:
            state: Current game state

        Returns:
            Updated state and events
        """
        new_state = state
        events: list[Event] = []

        # Sorted: effect/event order must not depend on set iteration order,
        # which varies with the per-process hash seed (audit C-2).
        for node_id in sorted(state.active_nodes):
            if node_id in state.revealed_nodes:
                continue

            node = self.node_map.get(node_id)
            if not node or not node.reveal:
                continue

            if node.reveal.auto_reveal:
                # Reveal the node
                new_revealed = set(state.revealed_nodes) | {node_id}
                new_state = replace(
                    new_state,
                    revealed_nodes=frozenset(new_revealed),
                    revealed_at={**new_state.revealed_at, node_id: state.current_time_minutes},
                )

                events.append(
                    NodeRevealedEvent(
                        timestamp_minutes=state.current_time_minutes,
                        node_id=node_id,
                        node_type=node.type,
                        content_text=node.content.narrative_text,
                        structured_data=node.content.structured_data,
                    )
                )

                # Apply on_reveal effects
                if node.effects and node.effects.on_reveal:
                    new_state, reveal_effects = self.effect_exec.apply_effects(
                        node.effects.on_reveal, new_state, self.case
                    )
                    events.extend(reveal_effects)

        return new_state, events

    def check_action_reveals(
        self, state: GameState, base_action: str, param: str | None
    ) -> tuple[GameState, list[Event]]:
        """Check if the current action reveals any nodes.

        For each active, unrevealed node:
        - If node.reveal is None → skip
        - If node.reveal.auto_reveal → skip (handled by check_auto_reveals)
        - Evaluate reveal rule against (base_action, param, state)
        - If matched AND reveal.delay_minutes is set:
            → Add to pending_reveals, emit PendingRevealStartedEvent
        - If matched AND no delay:
            → Reveal immediately, apply on_reveal effects, emit NodeRevealedEvent

        Also check case.action_costs[base_action].result_delay_minutes:
        - If present AND the node's own delay_minutes is None, use the action's
          result_delay_minutes as the delay

        Args:
            state: Current game state
            base_action: Base action type
            param: Action parameter

        Returns:
            Updated state and events
        """
        new_state = state
        events: list[Event] = []

        # Get action's default delay
        action_default_delay = self.case.action_costs[base_action].result_delay_minutes

        # Sorted: effect/event order must not depend on set iteration order,
        # which varies with the per-process hash seed (audit C-2).
        for node_id in sorted(state.active_nodes):
            if node_id in state.revealed_nodes or node_id in state.pending_reveals:
                continue

            node = self.node_map.get(node_id)
            if not node or not node.reveal:
                continue

            if node.reveal.auto_reveal:
                continue

            # Evaluate reveal rule
            if self.condition_eval.evaluate_reveal_rule(node.reveal, new_state, base_action, param):
                # Determine delay
                delay = node.reveal.delay_minutes
                if delay is None and action_default_delay is not None:
                    # Use action's default delay
                    delay = action_default_delay

                if delay is not None and delay > 0:
                    # Add to pending reveals
                    new_pending = dict(new_state.pending_reveals)
                    new_pending[node_id] = delay
                    new_state = replace(new_state, pending_reveals=new_pending)

                    events.append(
                        PendingRevealStartedEvent(
                            timestamp_minutes=state.current_time_minutes,
                            node_id=node_id,
                            delay_minutes=delay,
                        )
                    )
                else:
                    # Immediate reveal
                    new_revealed = set(new_state.revealed_nodes) | {node_id}
                    new_state = replace(
                        new_state,
                        revealed_nodes=frozenset(new_revealed),
                        revealed_at={**new_state.revealed_at, node_id: state.current_time_minutes},
                    )

                    events.append(
                        NodeRevealedEvent(
                            timestamp_minutes=state.current_time_minutes,
                            node_id=node_id,
                            node_type=node.type,
                            content_text=node.content.narrative_text,
                            structured_data=node.content.structured_data,
                        )
                    )

                    # Apply on_reveal effects
                    if node.effects and node.effects.on_reveal:
                        new_state, reveal_effects = self.effect_exec.apply_effects(
                            node.effects.on_reveal, new_state, self.case
                        )
                        events.extend(reveal_effects)

        return new_state, events

    def check_interventions(
        self, state: GameState, base_action: str, param: str | None
    ) -> tuple[GameState, list[Event]]:
        """Check if the action triggers any intervention effects.

        For each active node:
        - If node.effects is None → skip
        - If node.effects.on_intervene is None → skip
        - If on_intervene.treatment matches param (or base_action if no param):
            → Apply on_intervene.effects

        Args:
            state: Current game state
            base_action: Base action type
            param: Action parameter

        Returns:
            Updated state and events
        """
        new_state = state
        events: list[Event] = []

        # The intervention treatment can match either the param or the full action
        match_value = param if param is not None else base_action

        # Sorted: effect/event order must not depend on set iteration order,
        # which varies with the per-process hash seed (audit C-2).
        for node_id in sorted(state.active_nodes):
            node = self.node_map.get(node_id)
            if not node or not node.effects or not node.effects.on_intervene:
                continue

            if node.effects.on_intervene.treatment == match_value:
                # Apply intervention effects
                new_state, intervene_effects = self.effect_exec.apply_effects(
                    node.effects.on_intervene.effects, new_state, self.case
                )
                events.extend(intervene_effects)

        return new_state, events

    def cascade_activations(self, state: GameState) -> tuple[GameState, list[Event]]:
        """Check all inactive nodes for activation.

        Repeat until no new activations occur (cascade — one activation may enable another).

        For each node not in active_nodes:
        - Evaluate activation.paths using ConditionEvaluator
        - If satisfied: activate node, start timer if present,
          apply on_activate effects
        - After each round, re-check (new flags/nodes may trigger more)

        Limit cascade depth to prevent infinite loops (max 10 rounds).

        Args:
            state: Current game state

        Returns:
            Updated state and events
        """
        new_state = state
        events: list[Event] = []

        max_rounds = 10
        for _round_num in range(max_rounds):
            activations_this_round = []

            for node in self.case.nodes:
                if node.id in new_state.active_nodes:
                    continue

                # Skip nodes that only activate via starts_active
                if node.activation.paths is None:
                    continue

                # Evaluate activation rule
                if self.condition_eval.evaluate_activation_rule(node.activation, new_state):
                    activations_this_round.append(node)

            if not activations_this_round:
                # No new activations, done
                break

            # Activate all nodes from this round
            for node in activations_this_round:
                new_active = set(new_state.active_nodes) | {node.id}
                new_state = replace(new_state, active_nodes=frozenset(new_active))

                # Start timer if present
                if node.timer:
                    new_timers = dict(new_state.timers)
                    new_timers[node.id] = node.timer.duration_minutes
                    new_state = replace(new_state, timers=new_timers)

                    new_timer_stages = dict(new_state.timer_stages)
                    new_timer_stages[node.id] = 0
                    new_state = replace(new_state, timer_stages=new_timer_stages)

                # Emit directly: _activate_node early-returns empty once the
                # node is already in active_nodes, which it is by this point,
                # so harvesting its events silently dropped every cascade
                # NodeActivatedEvent (audit C-6).
                events.append(
                    NodeActivatedEvent(
                        timestamp_minutes=new_state.current_time_minutes,
                        node_id=node.id,
                        node_type=node.type,
                    )
                )

                # Apply on_activate effects
                if node.activation.on_activate:
                    new_state, activate_effects = self.effect_exec.apply_effects(
                        node.activation.on_activate, new_state, self.case
                    )
                    events.extend(activate_effects)

        return new_state, events

    def recompute_vitals(self, state: GameState) -> tuple[GameState, list[Event]]:
        """Recompute vitals from baseline + active nodes + timer stages.

        If vitals changed, emit VitalsChangedEvent.

        Args:
            state: Current game state

        Returns:
            Updated state and events
        """
        # Get active nodes
        active_nodes = [self.node_map[node_id] for node_id in state.active_nodes if node_id in self.node_map]

        # Compute new vitals
        new_vitals = self.vitals_comp.compute_vitals(self.case.patient.arriving_vitals, active_nodes, state)

        # Check if changed
        if new_vitals != state.current_vitals:
            old_vitals_dict = {
                "heart_rate": state.current_vitals.heart_rate,
                "blood_pressure_systolic": state.current_vitals.blood_pressure_systolic,
                "blood_pressure_diastolic": state.current_vitals.blood_pressure_diastolic,
                "temperature": state.current_vitals.temperature,
                "respiratory_rate": state.current_vitals.respiratory_rate,
                "o2_saturation": state.current_vitals.o2_saturation,
            }

            new_vitals_dict = {
                "heart_rate": new_vitals.heart_rate,
                "blood_pressure_systolic": new_vitals.blood_pressure_systolic,
                "blood_pressure_diastolic": new_vitals.blood_pressure_diastolic,
                "temperature": new_vitals.temperature,
                "respiratory_rate": new_vitals.respiratory_rate,
                "o2_saturation": new_vitals.o2_saturation,
            }

            new_state = replace(state, current_vitals=new_vitals)

            events: list[Event] = [
                VitalsChangedEvent(
                    timestamp_minutes=state.current_time_minutes,
                    old_vitals=old_vitals_dict,
                    new_vitals=new_vitals_dict,
                )
            ]

            return new_state, events

        return state, []

    def check_end_conditions(self, state: GameState) -> tuple[GameState, list[Event]]:
        """Check all end conditions and determine outcome tier.

        EndConditionType handling:
        - NODE_ACTIVATED: check if target node_id is in active_nodes
        - TIME_ELAPSED: check if current_time_minutes >= value
        - FLAG_SET: check if target flag is in state.flags
        - ALL_CRITICAL_RESOLVED: check if all critical nodes are resolved

        If any end condition is met:
        1. Determine outcome tier by evaluating case.outcome_evaluation.tiers
           in order (optimal first, failure last)
        2. A tier matches if:
           - All required_flags are in state.flags (if specified)
           - No excluded_flags are in state.flags (if specified)
           - All time_constraints are satisfied (flag set before deadline)
        3. First matching tier = the outcome
        4. If no tier matches, default to "failure"
        5. Set case_ended=True, outcome_tier, end_reason
        6. Emit CaseEndedEvent

        Args:
            state: Current game state

        Returns:
            Updated state and events
        """
        # Check if any end condition is met
        end_triggered = False
        end_reason = ""

        for end_cond in self.case.outcome_evaluation.end_conditions:
            match end_cond.type:
                case EndConditionType.NODE_ACTIVATED:
                    if end_cond.target in state.active_nodes:
                        end_triggered = True
                        end_reason = f"Node {end_cond.target} activated"
                        break
                case EndConditionType.TIME_ELAPSED:
                    if end_cond.value is not None and isinstance(end_cond.value, int):
                        if state.current_time_minutes >= end_cond.value:
                            end_triggered = True
                            end_reason = f"Time limit reached ({end_cond.value} minutes)"
                            break
                case EndConditionType.FLAG_SET:
                    if end_cond.target in state.flags:
                        end_triggered = True
                        end_reason = f"Flag {end_cond.target} set"
                        break
                case EndConditionType.ALL_CRITICAL_RESOLVED:
                    # Check if all nodes with CRITICAL impact are resolved
                    # (for Phase 1, we'll skip this complex check)
                    pass

        if not end_triggered:
            return state, []

        # Determine outcome tier
        outcome_tier = "failure"  # default
        # Tier levels are not unique (two tiers can share the "failure"
        # register), so record the matched tier's own authored narrative —
        # a level-keyed lookup downstream would return the wrong text.
        outcome_narrative: str | None = None

        for tier in self.case.outcome_evaluation.tiers:
            # Check required flags
            if tier.required_flags:
                if not all(f in state.flags for f in tier.required_flags):
                    continue

            # Check excluded flags
            if tier.excluded_flags:
                if any(f in state.flags for f in tier.excluded_flags):
                    continue

            # Check time constraints
            if tier.time_constraints:
                constraints_met = True
                for tc in tier.time_constraints:
                    # Check if flag was set before deadline
                    # For now, we just check if the flag is set and time is before deadline
                    if tc.flag not in state.flags:
                        constraints_met = False
                        break
                    if state.current_time_minutes > tc.before_minutes:
                        constraints_met = False
                        break
                if not constraints_met:
                    continue

            # This tier matches
            outcome_tier = tier.tier
            outcome_narrative = tier.narrative
            break

        # End the case
        new_state = replace(
            state,
            case_ended=True,
            outcome_tier=outcome_tier,
            end_reason=end_reason,
            outcome_narrative=outcome_narrative,
        )

        events: list[Event] = [
            CaseEndedEvent(
                timestamp_minutes=state.current_time_minutes,
                outcome_tier=outcome_tier,
                end_reason=end_reason,
            )
        ]

        return new_state, events
