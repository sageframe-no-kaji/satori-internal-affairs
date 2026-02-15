"""Main Satori engine - deterministic case execution.

This is the core state machine that plays medical mystery cases.
Fully deterministic: same case + same actions = same outcome.
"""

from dataclasses import replace

from satori.action_parser import parse_action
from satori.condition_evaluator import ConditionEvaluator
from satori.effect_executor import EffectExecutor
from satori.events import (
    Event,
    NodeRevealedEvent,
    PendingRevealStartedEvent,
    TimeAdvancedEvent,
    VitalsChangedEvent,
)
from satori.game_state import GameState
from satori.models.case_definition import CaseDefinition, Node, NodeContent
from satori.timer_manager import TimerManager
from satori.vitals_computer import VitalsComputer


class InvalidActionError(Exception):
    """Raised when a player attempts an unavailable or malformed action."""

    pass


class CaseValidationError(Exception):
    """Raised when case definition has structural issues."""

    pass


class SatoriEngine:
    """Deterministic case execution engine.

    PUBLIC API — this is what Ho 05 (frontend) and Ho 06 (integration) consume.

    Methods:
        __init__(case): Load case and initialize state
        execute_action(action) -> list[Event]: Process a player action
        get_state() -> GameState: Get current immutable state snapshot
        get_available_actions() -> frozenset[str]: Convenience accessor
        get_node_content(node_id) -> NodeContent | None: Get revealed node content
    """

    def __init__(self, case: CaseDefinition):
        """Initialize engine with a case definition.

        Performs load-time validation beyond Pydantic checks.

        Args:
            case: Validated case definition

        Raises:
            CaseValidationError: If case has structural issues
        """
        self.case = case
        self._node_map: dict[str, Node] = {n.id: n for n in case.nodes}

        # Validate case structure
        self._validate_case_structure()

        # Initialize components
        self.condition_eval = ConditionEvaluator()
        self.timer_mgr = TimerManager(self.condition_eval)
        self.vitals_comp = VitalsComputer()
        self.effect_exec = EffectExecutor()

        # Initialize game state
        self.state = self._initialize_state()

    def _validate_case_structure(self) -> None:
        """Perform load-time structural validation.

        Checks:
        - All node IDs referenced in effects/conditions exist
        - All flags referenced are set somewhere (or are system flags)
        - All action references in reveal rules exist in action_costs
        - Timer stages are sorted by at_minutes ascending

        Raises:
            CaseValidationError: If validation fails
        """
        issues: list[str] = []

        # System flags that don't need to be explicitly set
        system_flags = {"case_start"}

        # Collect all flags that get set
        flags_set: set[str] = set()

        # Check each node
        for node in self.case.nodes:
            # Check activation effects for flag sets
            if node.activation.on_activate:
                for effect in node.activation.on_activate:
                    if effect.type == "set_flag":
                        flags_set.add(effect.target)

            # Check node effects
            if node.effects:
                if node.effects.on_reveal:
                    for effect in node.effects.on_reveal:
                        if effect.type == "set_flag":
                            flags_set.add(effect.target)
                if node.effects.on_expire:
                    for effect in node.effects.on_expire:
                        if effect.type == "set_flag":
                            flags_set.add(effect.target)
                if node.effects.on_intervene:
                    for effect in node.effects.on_intervene.effects:
                        if effect.type == "set_flag":
                            flags_set.add(effect.target)

            # Check timer for flag sets
            if node.timer:
                for effect in node.timer.on_expire:
                    if effect.type == "set_flag":
                        flags_set.add(effect.target)
                if node.timer.stages:
                    for stage in node.timer.stages:
                        for effect in stage.effects:
                            if effect.type == "set_flag":
                                flags_set.add(effect.target)

            # Check reveal rule action references
            if node.reveal and node.reveal.action:
                if node.reveal.action not in self.case.action_costs:
                    issues.append(
                        f"Node {node.id} reveal action '{node.reveal.action}' not in action_costs"
                    )

            # Check timer stages are sorted
            if node.timer and node.timer.stages:
                at_minutes_values = [s.at_minutes for s in node.timer.stages]
                if at_minutes_values != sorted(at_minutes_values):
                    issues.append(f"Node {node.id} timer stages not sorted by at_minutes")

        # Note: More comprehensive validation (checking all node/flag references
        # in conditions/effects) would be good but is complex. Skipping for Phase 1.

        if issues:
            raise CaseValidationError("\n".join(issues))

    def _initialize_state(self) -> GameState:
        """Initialize game state from case definition.

        Steps:
        1. Set current_time_minutes = 0
        2. Set flags = frozenset({"case_start"})
        3. Set available_actions from case.action_costs keys
        4. Find all nodes with activation.starts_active == True:
           a. Add to active_nodes
           b. If node has a timer, add to state.timers with duration_minutes
           c. Apply activation.on_activate effects (null-safe)
        5. Evaluate all non-starts_active nodes' activation rules
           (some might activate immediately due to flags/conditions from step 4)
        6. Check for auto-reveal nodes among newly activated nodes
        7. Compute initial vitals from baseline + active nodes

        Returns:
            Initial GameState
        """
        # Build initial state
        state = GameState(
            case_id=self.case.id,
            current_time_minutes=0,
            flags=frozenset({"case_start"}),
            active_nodes=frozenset(),
            revealed_nodes=frozenset(),
            expired_nodes=frozenset(),
            pending_reveals={},
            timers={},
            timer_stages={},
            current_vitals=self.case.patient.arriving_vitals,
            available_actions=frozenset(self.case.action_costs.keys()),
            case_ended=False,
            outcome_tier=None,
            end_reason=None,
        )

        # Activate starts_active nodes
        for node in self.case.nodes:
            if node.activation.starts_active:
                # Activate the node
                new_active = set(state.active_nodes) | {node.id}
                state = replace(state, active_nodes=frozenset(new_active))

                # Start timer if present
                if node.timer:
                    new_timers = dict(state.timers)
                    new_timers[node.id] = node.timer.duration_minutes
                    state = replace(state, timers=new_timers)

                    new_timer_stages = dict(state.timer_stages)
                    new_timer_stages[node.id] = 0
                    state = replace(state, timer_stages=new_timer_stages)

                # Apply on_activate effects
                if node.activation.on_activate:
                    state, _ = self.effect_exec.apply_effects(
                        node.activation.on_activate, state, self.case
                    )

        # Check for activation cascade (other nodes might activate immediately)
        state, _ = self._cascade_activations(state)

        # Check for auto-reveals
        state, _ = self._check_auto_reveals(state)

        # Compute initial vitals
        state, _ = self._recompute_vitals(state)

        return state

    def execute_action(self, action: str) -> list[Event]:
        """Execute a player action and return events.

        THIS IS THE CORE GAME LOOP.

        1. Parse action into (base_action, parameter)
        2. Validate base_action exists in case.action_costs
        3. Validate action string is in available_actions OR base_action is
           (base actions are available at the base level; parameters refine them)
        4. Look up time cost: case.action_costs[base_action].action_minutes
        5. Advance time by action_minutes
        6. Advance all active timers by action_minutes
        7. Advance all pending reveals by action_minutes
        8. Check for auto-reveal nodes (activation met, auto_reveal=True)
        9. Check for action-triggered reveals
        10. Check for intervention matches
        11. Check for newly activated nodes (cascade)
        12. Recompute vitals
        13. Check end conditions
        14. If not ended, evaluate outcome tier readiness

        Args:
            action: Player action string (base:param or just base)

        Returns:
            List of events in causal order

        Raises:
            InvalidActionError: If action is not available
        """
        if self.state.case_ended:
            raise InvalidActionError("Case has already ended")

        events: list[Event] = []
        base_action, param = parse_action(action)

        # Validate
        if base_action not in self.case.action_costs:
            raise InvalidActionError(f"Unknown action type: {base_action}")

        if base_action not in self.state.available_actions:
            raise InvalidActionError(f"Action {base_action} is currently locked")

        # 1. Time advancement
        time_cost = self.case.action_costs[base_action].action_minutes
        new_state, time_events = self._advance_time(time_cost, action)
        events.extend(time_events)

        # 2. Timer advancement
        new_state, timer_events = self.timer_mgr.advance_timers(
            new_state, time_cost, self.case
        )
        events.extend(timer_events)

        # Apply effects from expired timers
        # (timer_events includes NodeExpiredEvent, need to apply on_expire effects)
        for event in timer_events:
            if hasattr(event, "node_id") and event.type == "node_expired":
                node = self._node_map.get(event.node_id)
                if node:
                    # Apply on_expire from timer
                    if node.timer:
                        new_state, expire_events = self.effect_exec.apply_effects(
                            node.timer.on_expire, new_state, self.case
                        )
                        events.extend(expire_events)
                    # Apply on_expire from effects
                    if node.effects and node.effects.on_expire:
                        new_state, expire_events = self.effect_exec.apply_effects(
                            node.effects.on_expire, new_state, self.case
                        )
                        events.extend(expire_events)

        # Apply effects from timer stages that were crossed
        for event in timer_events:
            if hasattr(event, "node_id") and event.type == "timer_stage":
                node = self._node_map.get(event.node_id)
                if node and node.timer and node.timer.stages:
                    # Find the stage that was just crossed
                    for stage in node.timer.stages:
                        if stage.at_minutes == event.stage_at_minutes:
                            new_state, stage_events = self.effect_exec.apply_effects(
                                stage.effects, new_state, self.case
                            )
                            events.extend(stage_events)
                            break

        # 3. Pending reveal advancement
        new_state, pending_events = self.timer_mgr.advance_pending_reveals(
            new_state, time_cost, self.case
        )
        events.extend(pending_events)

        # Apply on_reveal effects for completed pending reveals
        for event in pending_events:
            if isinstance(event, NodeRevealedEvent):
                node = self._node_map.get(event.node_id)
                if node and node.effects and node.effects.on_reveal:
                    new_state, reveal_events = self.effect_exec.apply_effects(
                        node.effects.on_reveal, new_state, self.case
                    )
                    events.extend(reveal_events)

        # 4. Auto-reveals
        new_state, auto_events = self._check_auto_reveals(new_state)
        events.extend(auto_events)

        # 5. Action-triggered reveals
        new_state, reveal_events = self._check_action_reveals(
            new_state, base_action, param
        )
        events.extend(reveal_events)

        # 6. Intervention matching
        new_state, intervene_events = self._check_interventions(
            new_state, base_action, param
        )
        events.extend(intervene_events)

        # 7. Activation cascade
        new_state, activation_events = self._cascade_activations(new_state)
        events.extend(activation_events)

        # 8. Vitals recomputation
        new_state, vital_events = self._recompute_vitals(new_state)
        events.extend(vital_events)

        # 9. End condition check
        new_state, end_events = self._check_end_conditions(new_state)
        events.extend(end_events)

        self.state = new_state
        return events

    def _advance_time(
        self, minutes: int, cause: str
    ) -> tuple[GameState, list[Event]]:
        """Advance clock. Emit TimeAdvancedEvent.

        Args:
            minutes: Minutes to advance
            cause: The action that caused time to advance

        Returns:
            Updated state and events
        """
        old_time = self.state.current_time_minutes
        new_time = old_time + minutes

        new_state = replace(self.state, current_time_minutes=new_time)

        events = [
            TimeAdvancedEvent(
                timestamp_minutes=new_time,
                old_time=old_time,
                new_time=new_time,
                cause=cause,
            )
        ]

        return new_state, events

    def _check_auto_reveals(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
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

        for node_id in state.active_nodes:
            if node_id in state.revealed_nodes:
                continue

            node = self._node_map.get(node_id)
            if not node or not node.reveal:
                continue

            if node.reveal.auto_reveal:
                # Reveal the node
                new_revealed = set(state.revealed_nodes) | {node_id}
                new_state = replace(new_state, revealed_nodes=frozenset(new_revealed))

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

    def _check_action_reveals(
        self, state: GameState, base_action: str, param: str | None
    ) -> tuple[GameState, list[Event]]:
        """Check if the current action reveals any nodes.

        For each active, unrevealed node:
        - If node.reveal is None → skip
        - If node.reveal.auto_reveal → skip (handled by _check_auto_reveals)
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

        for node_id in state.active_nodes:
            if node_id in state.revealed_nodes or node_id in state.pending_reveals:
                continue

            node = self._node_map.get(node_id)
            if not node or not node.reveal:
                continue

            if node.reveal.auto_reveal:
                continue

            # Evaluate reveal rule
            if self.condition_eval.evaluate_reveal_rule(
                node.reveal, new_state, base_action, param
            ):
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
                        new_state, revealed_nodes=frozenset(new_revealed)
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

    def _check_interventions(
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

        for node_id in state.active_nodes:
            node = self._node_map.get(node_id)
            if not node or not node.effects or not node.effects.on_intervene:
                continue

            if node.effects.on_intervene.treatment == match_value:
                # Apply intervention effects
                new_state, intervene_effects = self.effect_exec.apply_effects(
                    node.effects.on_intervene.effects, new_state, self.case
                )
                events.extend(intervene_effects)

        return new_state, events

    def _cascade_activations(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
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
        for round_num in range(max_rounds):
            activations_this_round = []

            for node in self.case.nodes:
                if node.id in new_state.active_nodes:
                    continue

                # Skip nodes that only activate via starts_active
                if node.activation.paths is None:
                    continue

                # Evaluate activation rule
                if self.condition_eval.evaluate_activation_rule(
                    node.activation, new_state
                ):
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

                events.extend(
                    [event for _, evts in [self.effect_exec._activate_node(node.id, new_state, self.case)] for event in evts]
                )

                # Apply on_activate effects
                if node.activation.on_activate:
                    new_state, activate_effects = self.effect_exec.apply_effects(
                        node.activation.on_activate, new_state, self.case
                    )
                    events.extend(activate_effects)

        return new_state, events

    def _recompute_vitals(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """Recompute vitals from baseline + active nodes + timer stages.

        If vitals changed, emit VitalsChangedEvent.

        Args:
            state: Current game state

        Returns:
            Updated state and events
        """
        # Get active nodes
        active_nodes = [
            self._node_map[node_id]
            for node_id in state.active_nodes
            if node_id in self._node_map
        ]

        # Compute new vitals
        new_vitals = self.vitals_comp.compute_vitals(
            self.case.patient.arriving_vitals, active_nodes, state
        )

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

            events = [
                VitalsChangedEvent(
                    timestamp_minutes=state.current_time_minutes,
                    old_vitals=old_vitals_dict,
                    new_vitals=new_vitals_dict,
                )
            ]

            return new_state, events

        return state, []

    def _check_end_conditions(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
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
        from satori.events import CaseEndedEvent
        from satori.models.case_definition import EndConditionType

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
            break

        # End the case
        new_state = replace(
            state,
            case_ended=True,
            outcome_tier=outcome_tier,
            end_reason=end_reason,
        )

        events = [
            CaseEndedEvent(
                timestamp_minutes=state.current_time_minutes,
                outcome_tier=outcome_tier,
                end_reason=end_reason,
            )
        ]

        return new_state, events

    def get_state(self) -> GameState:
        """Get current immutable state snapshot.

        Returns:
            Current GameState
        """
        return self.state

    def get_available_actions(self) -> frozenset[str]:
        """Get currently available base actions.

        Returns:
            Frozenset of available action keys
        """
        return self.state.available_actions

    def get_node_content(self, node_id: str) -> NodeContent | None:
        """Get content for a revealed node.

        Returns None if node is not revealed or doesn't exist.

        This is how the frontend gets displayable text for revealed
        information. The frontend should call this for each node_id
        in state.revealed_nodes.

        Args:
            node_id: ID of the node

        Returns:
            NodeContent if node is revealed, None otherwise
        """
        if node_id not in self.state.revealed_nodes:
            return None
        node = self._node_map.get(node_id)
        return node.content if node else None
