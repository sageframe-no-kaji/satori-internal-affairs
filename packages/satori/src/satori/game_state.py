"""Game state representation for Satori engine.

GameState is immutable - all updates create new instances.
This enables deterministic replay and state snapshots.
"""

from dataclasses import dataclass
from uuid import UUID

from satori.models.case_definition import VitalSigns


@dataclass(frozen=True)
class GameState:
    """Immutable game state snapshot.

    All updates return new GameState instances via dataclasses.replace().
    No hidden state - everything affecting outcomes is visible here.
    """

    # Identity
    case_id: UUID

    # Time
    current_time_minutes: int

    # Flags (set/cleared by effects)
    flags: frozenset[str]

    # Node lifecycle states
    active_nodes: frozenset[str]  # node IDs currently live in simulation
    revealed_nodes: frozenset[str]  # node IDs whose content is visible to player
    expired_nodes: frozenset[str]  # node IDs whose timers have expired

    # Pending reveals: {node_id: minutes_remaining}
    # For labs/imaging with result_delay_minutes
    # NOTE: Using dict (not frozenset) because we need to track remaining time
    # Treat as immutable by convention - copy on write in updates
    pending_reveals: dict[str, int]

    # Timers: {node_id: remaining_minutes}
    # Tracks countdown timers for progression/crisis nodes
    timers: dict[str, int]

    # Current timer stages: {node_id: highest_stage_index_reached}
    # Tracks which timer stage each timed node is currently at
    timer_stages: dict[str, int]

    # Current vitals (computed from baseline + active nodes + timer stages)
    current_vitals: VitalSigns

    # Available actions (initialized from action_costs keys, modified by effects)
    available_actions: frozenset[str]

    # Case resolution
    case_ended: bool = False
    outcome_tier: str | None = None
    end_reason: str | None = None
