"""Game state representation for Satori engine.

GameState is immutable - all updates create new instances.
This enables deterministic replay and state snapshots.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from satori.models.case_definition import CaseDefinition, EffectType, NodeEffects, VitalSigns

# Reserved flag convention: a node whose on_reveal effects set this flag is a
# crisis node. Cases declare emergencies via flag effects (no schema field);
# the engine derives emergency surfaces (emergency_timer, and P2-H05's
# emergency_active) from it.
CRISIS_FLAG = "crisis_active"


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

    # Derived: whether an emergency is in progress — the reserved crisis flag
    # is set and the case has not ended. The UI's emergency-mode switch.
    # Computed by compute_emergency_active() and set on every state update.
    emergency_active: bool = False

    # Derived: the currently-active crisis node's countdown, or None outside
    # emergencies. The one non-diegetic timer the player is shown — the
    # emergency itself is visible to the character. Kept separate so
    # visible_timers stays semantically clean (diegetic-only).
    # Computed by compute_emergency_timer() and set on every state update.
    emergency_timer: VisibleTimer | None = None

    # The authored narrative of the outcome tier that actually matched at
    # case end. Tier *levels* are not unique (two tiers can share the
    # "failure" register), so a level-keyed lookup can return the wrong
    # narrative; this records the matched tier's own text. None until the
    # case ends via tier evaluation.
    outcome_narrative: str | None = None


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


def compute_emergency_active(state: "GameState") -> bool:
    """Derive whether the dashboard should be in emergency mode.

    True while the reserved crisis flag is set AND the case has not ended —
    the guard keeps the outcome screen out of emergency dress when death (or
    a same-tick resolution) ends the case with the flag still set (emergency-
    mode decision memo, §2). Same condition compute_emergency_timer gates on,
    so the two surfaces can never disagree.
    """
    return CRISIS_FLAG in state.flags and not state.case_ended


def _sets_crisis_flag(node_effects: NodeEffects) -> bool:
    """True if a node's on_reveal effects set the reserved crisis flag."""
    if not node_effects.on_reveal:
        return False
    return any(e.type == EffectType.SET_FLAG and e.target == CRISIS_FLAG for e in node_effects.on_reveal)


def compute_emergency_timer(state: "GameState", case: CaseDefinition) -> VisibleTimer | None:
    """Derive the active crisis countdown, if an emergency is in progress.

    Returns None unless the reserved crisis flag is set AND the case has not
    ended (a death or same-tick resolution must not leave the outcome screen
    dressed as an emergency — see the emergency-mode decision memo, §2).

    A crisis node is any node whose on_reveal effects set CRISIS_FLAG (the
    convention node_14 established and P2-H09's second crisis follows). Among
    active crisis nodes with a running timer, the one with the least remaining
    time wins; ties break by node_id so the derivation is deterministic. In
    authored cases exactly one crisis runs at a time — the ordering is a
    guarantee, not a gameplay mechanic.

    Args:
        state: Current game state snapshot.
        case: Case definition providing node metadata.

    Returns:
        A VisibleTimer for the active crisis node, or None.
    """
    if state.case_ended or CRISIS_FLAG not in state.flags:
        return None

    candidates: list[VisibleTimer] = []
    for node_id, remaining in state.timers.items():
        if node_id not in state.active_nodes:
            continue
        node = next((n for n in case.nodes if n.id == node_id), None)
        if node is None or node.effects is None or not _sets_crisis_flag(node.effects):
            continue
        candidates.append(
            VisibleTimer(
                label=_humanise_node_id(node_id),
                remaining_minutes=remaining,
                source="active_timer",
                node_id=node_id,
            )
        )

    if not candidates:
        return None
    return min(candidates, key=lambda t: (t.remaining_minutes, t.node_id))
