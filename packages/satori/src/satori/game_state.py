"""Game state representation for Satori engine.

GameState is immutable - all updates create new instances.
This enables deterministic replay and state snapshots.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from satori.models.case_definition import CaseDefinition, VitalSigns


@dataclass(frozen=True)
class VisibleTimer:
    """A timer the player's character is aware of.

    Derived from pending_reveals (always diegetic) and active nodes whose
    timer has diegetic=True. Exposed in GameState.visible_timers for the
    UI's Pending Results / diegetic countdown display.
    """

    label: str  # human-readable name, derived from node display_name or humanised node_id
    remaining_minutes: int
    source: Literal["pending_reveal", "active_timer"]
    node_id: str  # for the UI to key off


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

    # Derived: diegetic timers the player's character knows about.
    # Includes all pending_reveals and any active node whose timer.diegetic is True.
    # Computed by compute_visible_timers() and set on every state update.
    visible_timers: tuple[VisibleTimer, ...] = ()


def _humanise_node_id(node_id: str) -> str:
    """Convert a snake_case node_id to a human-readable label.

    Example: "node_04_cbc_results" -> "CBC Results"
    Strips leading "node_NN_" prefix if present, then title-cases the remainder.
    """
    # Strip optional leading "node_<digits>_" prefix
    parts = node_id.split("_")
    start = 0
    if len(parts) >= 2 and parts[0] == "node" and parts[1].isdigit():
        start = 2
    label_parts = parts[start:]
    return " ".join(p.capitalize() for p in label_parts) if label_parts else node_id


def compute_visible_timers(state: "GameState", case: CaseDefinition) -> tuple[VisibleTimer, ...]:
    """Derive the set of timers the player's character is aware of.

    Two sources:
    1. Every entry in state.pending_reveals — always diegetic (the player ordered
       the lab/imaging and knows it takes time). Source: "pending_reveal".
    2. Every node in state.active_nodes whose node.timer.diegetic is True and
       whose remaining time is tracked in state.timers. Source: "active_timer".

    The result is sorted deterministically by (remaining_minutes, node_id) so
    test assertions and UI rendering are stable.

    Args:
        state: Current game state snapshot.
        case: Case definition providing node metadata.

    Returns:
        Sorted tuple of VisibleTimer instances.
    """
    node_map = {n.id: n for n in case.nodes}
    timers: list[VisibleTimer] = []

    # Source 1: pending reveals — always visible to the player
    for node_id, remaining in state.pending_reveals.items():
        node = node_map.get(node_id)
        label: str
        if node is not None:
            raw_label = getattr(node, "display_name", None) or ""
            label = raw_label if raw_label else _humanise_node_id(node_id)
        else:
            label = _humanise_node_id(node_id)
        timers.append(
            VisibleTimer(
                label=label,
                remaining_minutes=remaining,
                source="pending_reveal",
                node_id=node_id,
            )
        )

    # Source 2: active nodes with diegetic timers
    for node_id, remaining in state.timers.items():
        if node_id not in state.active_nodes:
            continue
        node = node_map.get(node_id)
        if node is None or node.timer is None or not node.timer.diegetic:
            continue
        raw_label = getattr(node, "display_name", None) or ""
        label = raw_label if raw_label else _humanise_node_id(node_id)
        timers.append(
            VisibleTimer(
                label=label,
                remaining_minutes=remaining,
                source="active_timer",
                node_id=node_id,
            )
        )

    timers.sort(key=lambda t: (t.remaining_minutes, t.node_id))
    return tuple(timers)
