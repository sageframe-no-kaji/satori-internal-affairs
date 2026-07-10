"""Timer management for node timers and pending reveals.

Handles countdown timers, stage transitions, and delayed reveal queues.
"""

from dataclasses import replace

from satori.condition_evaluator import ConditionEvaluator
from satori.events import (
    Event,
    NodeExpiredEvent,
    NodeRevealedEvent,
    TimerStageEvent,
)
from satori.game_state import GameState
from satori.models.case_definition import CaseDefinition, Condition


class TimerManager:
    """Manages node timers, stage transitions, and pending reveals."""

    def __init__(self, condition_evaluator: ConditionEvaluator):
        """Initialize timer manager.

        Args:
            condition_evaluator: Evaluator for pause conditions
        """
        self.condition_eval = condition_evaluator

    def advance_timers(
        self, state: GameState, minutes_elapsed: int, case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """Advance all active node timers by minutes_elapsed.

        For each timer (node_id in state.timers):
        1. Check pause conditions — if ALL pause conditions met, skip
        2. Subtract minutes_elapsed from remaining time
        3. Check if timer crossed any stage boundaries (at_minutes thresholds)
           - For each crossed stage: emit TimerStageEvent, apply stage effects,
             update timer_stages tracking
        4. Check if timer expired (remaining <= 0)
           - Emit NodeExpiredEvent
           - Apply on_expire effects from the NodeTimer
           - Apply on_expire effects from NodeEffects (if present)
           - Move node_id to expired_nodes

        Returns updated state and list of events.

        IMPORTANT: Stage boundaries are checked by comparing the timer's
        elapsed time (duration_minutes - remaining) against stage.at_minutes.
        A stage at_minutes=60 triggers when 60 minutes have elapsed since
        the timer started, NOT when 60 minutes remain.

        Args:
            state: Current game state
            minutes_elapsed: Time to advance
            case: Case definition (for node lookups)

        Returns:
            Updated state and list of events
        """
        new_state = state
        events: list[Event] = []

        # Build node map for lookups
        node_map = {n.id: n for n in case.nodes}

        # Track which timers to remove (expired)
        expired_timer_ids: set[str] = set()

        # Process each active timer
        new_timers = dict(state.timers)
        new_timer_stages = dict(state.timer_stages)

        for node_id, remaining in state.timers.items():
            node = node_map.get(node_id)
            if not node or not node.timer:
                continue

            # Check pause conditions
            if self._check_pause_conditions(node.timer.pause_conditions, new_state):
                # Timer is paused, don't advance
                continue

            # Calculate old and new elapsed time
            old_remaining = remaining
            new_remaining = old_remaining - minutes_elapsed
            duration = node.timer.duration_minutes

            old_elapsed = duration - old_remaining
            new_elapsed = duration - new_remaining

            # Check for stage transitions
            if node.timer.stages:
                for stage in node.timer.stages:
                    # Did we cross this stage boundary?
                    if old_elapsed < stage.at_minutes <= new_elapsed:
                        # Stage triggered
                        events.append(
                            TimerStageEvent(
                                timestamp_minutes=new_state.current_time_minutes,
                                node_id=node_id,
                                stage_index=stage.at_minutes,  # Use at_minutes as index
                                stage_at_minutes=stage.at_minutes,
                                vital_signs_changed=stage.vital_signs is not None,
                            )
                        )
                        # Update timer_stages tracking with the at_minutes value
                        new_timer_stages[node_id] = stage.at_minutes

                        # Stage effects will be applied by effect_executor later
                        # (engine will need to handle this)

            # Update timer
            new_timers[node_id] = new_remaining

            # Check expiry
            if new_remaining <= 0:
                # Timer expired
                events.append(
                    NodeExpiredEvent(
                        timestamp_minutes=new_state.current_time_minutes,
                        node_id=node_id,
                    )
                )
                expired_timer_ids.add(node_id)

                # on_expire effects will be handled by engine
                # (needs access to effect_executor)

        # Remove expired timers and mark nodes as expired
        for node_id in expired_timer_ids:
            new_timers.pop(node_id, None)
            new_timer_stages.pop(node_id, None)

        new_expired = set(state.expired_nodes) | expired_timer_ids

        # Update state
        new_state = replace(
            new_state,
            timers=new_timers,
            timer_stages=new_timer_stages,
            expired_nodes=frozenset(new_expired),
        )

        return new_state, events

    def advance_pending_reveals(
        self, state: GameState, minutes_elapsed: int, case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """Tick down all pending reveals by minutes_elapsed.

        For each pending reveal whose remaining time reaches 0:
        1. Move node_id to revealed_nodes
        2. Look up the Node to get content for the event
        3. Apply on_reveal effects (from node.effects, if present)
        4. Emit NodeRevealedEvent with content

        Args:
            state: Current game state
            minutes_elapsed: Time to advance
            case: Case definition (for node lookups)

        Returns:
            Updated state and list of events
        """
        new_state = state
        events: list[Event] = []

        # Build node map
        node_map = {n.id: n for n in case.nodes}

        # Track which reveals completed
        completed_reveal_ids: set[str] = set()

        # Process pending reveals
        new_pending = dict(state.pending_reveals)

        for node_id, remaining in state.pending_reveals.items():
            new_remaining = remaining - minutes_elapsed

            if new_remaining <= 0:
                # Reveal completes
                node = node_map.get(node_id)
                if node:
                    events.append(
                        NodeRevealedEvent(
                            timestamp_minutes=new_state.current_time_minutes,
                            node_id=node_id,
                            node_type=node.type,
                            content_text=node.content.narrative_text,
                            structured_data=node.content.structured_data,
                        )
                    )
                completed_reveal_ids.add(node_id)
            else:
                # Update remaining time
                new_pending[node_id] = new_remaining

        # Remove completed reveals and add to revealed_nodes.
        # Sorted: revealed_at insertion order must not depend on set iteration
        # order, which varies with the per-process hash seed (audit C-2).
        new_revealed_at = dict(state.revealed_at)
        for node_id in sorted(completed_reveal_ids):
            new_pending.pop(node_id, None)
            new_revealed_at[node_id] = new_state.current_time_minutes

        new_revealed = set(state.revealed_nodes) | completed_reveal_ids

        # Update state
        new_state = replace(
            new_state,
            pending_reveals=new_pending,
            revealed_nodes=frozenset(new_revealed),
            revealed_at=new_revealed_at,
        )

        return new_state, events

    def _check_pause_conditions(self, pause_conditions: list[Condition] | None, state: GameState) -> bool:
        """Check if timer is currently paused.

        Timer pauses when ALL pause conditions are satisfied.
        Returns True if paused.

        Args:
            pause_conditions: List of conditions that pause the timer
            state: Current game state

        Returns:
            True if timer is paused
        """
        if not pause_conditions:
            return False
        return all(self.condition_eval._evaluate_condition(c, state) for c in pause_conditions)
