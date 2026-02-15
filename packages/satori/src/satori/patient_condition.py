"""Patient condition computation utility.

Derives a human-readable condition label from game state for display and narration.
This is NOT stored in GameState - it's computed on demand.
"""

from enum import StrEnum

from satori.game_state import GameState
from satori.models.case_definition import CaseDefinition


class PatientCondition(StrEnum):
    """Derived patient condition for display and narration."""

    STABLE = "stable"
    COMPENSATING = "compensating"
    DECOMPENSATING = "decompensating"
    CRITICAL = "critical"
    DEAD = "dead"
    RECOVERED = "recovered"


def compute_patient_condition(state: GameState, case: CaseDefinition) -> PatientCondition:
    """Derive patient condition from current state.

    This is a READ-ONLY convenience for frontend and narration.
    It does not affect engine logic.

    Heuristics:
    - DEAD: "patient_death" flag set or death outcome node active
    - RECOVERED: "correct_treatment_started" flag set and case ended with optimal/good
    - CRITICAL: any vital in critical range (O2 < 88, HR > 150 or < 40, etc.)
    - DECOMPENSATING: any progression node timer past 50% elapsed
    - COMPENSATING: any progression node timer active but < 50% elapsed
    - STABLE: default when no danger signals present

    The thresholds here are heuristic defaults for Phase 1. In future
    phases, cases may define their own condition-mapping rules.

    Args:
        state: Current game state
        case: Case definition

    Returns:
        Computed patient condition
    """
    # Check for death
    if "patient_death" in state.flags:
        return PatientCondition.DEAD

    # Check for death nodes being active (any outcome node with "death" in name)
    for node_id in state.active_nodes:
        if "death" in node_id.lower():
            return PatientCondition.DEAD

    # Check for recovery
    if state.case_ended and state.outcome_tier in ("optimal", "good"):
        if "correct_treatment_started" in state.flags:
            return PatientCondition.RECOVERED

    # Check vitals for critical state
    vitals = state.current_vitals
    if vitals.o2_saturation is not None and vitals.o2_saturation < 88:
        return PatientCondition.CRITICAL
    if vitals.heart_rate is not None and (vitals.heart_rate > 150 or vitals.heart_rate < 40):
        return PatientCondition.CRITICAL
    if vitals.blood_pressure_systolic is not None and vitals.blood_pressure_systolic < 90:
        return PatientCondition.CRITICAL
    if vitals.temperature is not None and (vitals.temperature > 104.0 or vitals.temperature < 95.0):
        return PatientCondition.CRITICAL

    # Check for progression nodes with timers
    # Build node map
    node_map = {n.id: n for n in case.nodes}

    # Look for progression nodes
    progression_timers = []
    for node_id in state.active_nodes:
        node = node_map.get(node_id)
        if node and node.type == "progression" and node_id in state.timers and node.timer:
            remaining = state.timers[node_id]
            duration = node.timer.duration_minutes
            elapsed_pct = ((duration - remaining) / duration) * 100
            progression_timers.append(elapsed_pct)

    # Check progression timer status
    if progression_timers:
        max_elapsed = max(progression_timers)
        if max_elapsed > 50:
            return PatientCondition.DECOMPENSATING
        else:
            return PatientCondition.COMPENSATING

    # Default to stable
    return PatientCondition.STABLE
