"""Tests for the empirical treatment unlock path (P2-H07).

Three properties verified:
1. Empirical unlock: eosinophilia + ring_enhancing_lesion unlocks start_treatment
   WITHOUT requiring diagnosis_confirmed.
2. Post-confirmation path preserved: MRI scolex still unlocks start_treatment.
3. Diagnosis integrity: treatment nodes do not set diagnosis_confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from satori.engine import SatoriEngine
from satori.models.case_definition import CaseDefinition

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def case_def() -> CaseDefinition:
    case_path = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"
    with open(case_path, encoding="utf-8") as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


@pytest.fixture
def engine(case_def: CaseDefinition) -> SatoriEngine:
    return SatoriEngine(case_def)


# ---------------------------------------------------------------------------
# Helper: advance time past any pending reveals
# ---------------------------------------------------------------------------


def _flush_pending(eng: SatoriEngine, node_id: str, step: int = 15) -> None:
    """Wait in increments until the given node is no longer pending.

    Uses wait:30 for the serology node (120-min delay) to stay within the
    180-min progression timer; defaults to wait:15 for shorter delays.
    """
    wait_action = f"wait:{step}"
    for _ in range(20):
        state = eng.get_state()
        if node_id not in state.pending_reveals:
            return
        if state.case_ended:
            raise AssertionError(f"Case ended while waiting for {node_id}")
        eng.execute_action(wait_action)
    raise AssertionError(f"Node {node_id} still pending after 20 wait steps")


# ---------------------------------------------------------------------------
# 1. Empirical unlock path
# ---------------------------------------------------------------------------


def test_start_treatment_locked_before_cbc_and_ct(engine: SatoriEngine) -> None:
    """start_treatment must not be available before any evidence is gathered."""
    # Unlock labs + imaging via general history + neuro exam
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    playable = engine.get_playable_actions()
    assert "start_treatment:albendazole" not in playable
    assert "start_treatment:steroids" not in playable


def test_ct_alone_does_not_unlock_treatment(engine: SatoriEngine) -> None:
    """CT scan sets ring_enhancing_lesion but treatment must remain locked
    until eosinophilia is also present."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state = engine.get_state()
    assert "ring_enhancing_lesion" in state.flags
    assert "eosinophilia" not in state.flags

    playable = engine.get_playable_actions()
    assert "start_treatment:albendazole" not in playable
    assert "start_treatment:steroids" not in playable


def test_cbc_alone_does_not_unlock_treatment(engine: SatoriEngine) -> None:
    """CBC alone (eosinophilia only) must not unlock start_treatment."""
    engine.execute_action("history_general")
    engine.execute_action("order_labs:cbc")
    _flush_pending(engine, "node_04_cbc_results")

    state = engine.get_state()
    assert "eosinophilia" in state.flags
    assert "ring_enhancing_lesion" not in state.flags

    playable = engine.get_playable_actions()
    assert "start_treatment:albendazole" not in playable
    assert "start_treatment:steroids" not in playable


def test_empirical_unlock_fires_on_eosinophilia_plus_ring_lesion(
    engine: SatoriEngine,
) -> None:
    """After CBC (eosinophilia) + CT (ring_enhancing_lesion), start_treatment
    must unlock WITHOUT diagnosis_confirmed being set."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")

    # Order CBC first
    engine.execute_action("order_labs:cbc")
    _flush_pending(engine, "node_04_cbc_results")

    # Order CT
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state = engine.get_state()
    assert "eosinophilia" in state.flags
    assert "ring_enhancing_lesion" in state.flags
    # Diagnosis must NOT be confirmed by this path
    assert "diagnosis_confirmed" not in state.flags

    playable = engine.get_playable_actions()
    assert "start_treatment:albendazole" in playable


def test_diagnosis_confirmed_absent_before_confirmatory_test(
    engine: SatoriEngine,
) -> None:
    """Empirical path sets up treatment but must leave diagnosis_confirmed unset."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    engine.execute_action("order_labs:cbc")
    _flush_pending(engine, "node_04_cbc_results")
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state = engine.get_state()
    assert "diagnosis_confirmed" not in state.flags


# ---------------------------------------------------------------------------
# 2. Post-confirmation path preserved
# ---------------------------------------------------------------------------


def test_mri_scolex_still_unlocks_treatment(engine: SatoriEngine) -> None:
    """MRI showing the scolex sign must still set diagnosis_confirmed and
    unlock start_treatment (the pre-existing confirmation path)."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    # CT required first (node_10 activates when lesion_found)
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state = engine.get_state()
    assert "lesion_found" in state.flags

    engine.execute_action("order_imaging:mri_brain")
    _flush_pending(engine, "node_10_mri_result")

    state = engine.get_state()
    assert "scolex_visible" in state.flags
    assert "diagnosis_confirmed" in state.flags
    assert "start_treatment:albendazole" in engine.get_playable_actions()


def test_serology_still_unlocks_treatment(engine: SatoriEngine) -> None:
    """Positive cysticercosis serology must still unlock start_treatment.

    Serology has a 120-min delay. Timeline: history(15) + cbc(2) + wait_for_cbc(30)
    + serology_order(2) + wait_for_serology(120) = 169 min — under the 180-min
    crisis timer, so this completes before the case ends.
    """
    engine.execute_action("history_general")
    engine.execute_action("order_labs:cbc")  # eosinophilia required for serology activation
    # CBC has 30-min delay; wait:30 once is enough
    _flush_pending(engine, "node_04_cbc_results", step=30)

    state = engine.get_state()
    assert "eosinophilia" in state.flags

    # Order serology (120-min delay); use wait:30 steps to stay under 180-min timer
    engine.execute_action("order_labs:cysticercosis_serology")
    _flush_pending(engine, "node_11_serology_result", step=30)

    state = engine.get_state()
    assert "serology_positive" in state.flags
    assert "diagnosis_confirmed" in state.flags
    assert "start_treatment:albendazole" in engine.get_playable_actions()


# ---------------------------------------------------------------------------
# 3. Treatment nodes do not set diagnosis_confirmed
# ---------------------------------------------------------------------------


def test_albendazole_does_not_set_diagnosis_confirmed(engine: SatoriEngine) -> None:
    """Correct treatment (albendazole) must NOT set diagnosis_confirmed.
    The flag is a diagnostic finding, not a treatment outcome."""
    # Reach empirical unlock path
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    engine.execute_action("order_labs:cbc")
    _flush_pending(engine, "node_04_cbc_results")
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state_before_treatment = engine.get_state()
    assert "diagnosis_confirmed" not in state_before_treatment.flags

    # Treat empirically
    engine.execute_action("start_treatment:albendazole")

    state_after_treatment = engine.get_state()
    assert "correct_treatment_started" in state_after_treatment.flags
    # Still not confirmed — treatment does not confirm diagnosis
    assert "diagnosis_confirmed" not in state_after_treatment.flags


def test_steroids_do_not_set_diagnosis_confirmed(engine: SatoriEngine) -> None:
    """Wrong treatment (steroids) must also not set diagnosis_confirmed."""
    # Unlock steroids via CT (which also unlocks consult, but not start_treatment
    # anymore unless we use the empirical path — but steroids node is starts_active
    # so we need start_treatment unlocked first)
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_focused:neuro")
    engine.execute_action("order_labs:cbc")
    _flush_pending(engine, "node_04_cbc_results")
    engine.execute_action("order_imaging:ct_head")
    _flush_pending(engine, "node_06_ct_lesion")

    state = engine.get_state()
    assert "start_treatment" in state.available_actions

    engine.execute_action("start_treatment:steroids")

    state_after = engine.get_state()
    assert "wrong_treatment_steroids" in state_after.flags
    assert "diagnosis_confirmed" not in state_after.flags
