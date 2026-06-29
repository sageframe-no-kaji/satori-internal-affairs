"""Tests for SatoriEngine.get_playable_actions().

Verifies the action grammar bridge: the method must surface fully-qualified
action strings (base:subcategory or bare base) that the UI can directly submit,
not raw available_actions base keys.
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
def maria_santos_case() -> CaseDefinition:
    case_path = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"
    with open(case_path, encoding="utf-8") as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


@pytest.fixture
def engine(maria_santos_case: CaseDefinition) -> SatoriEngine:
    return SatoriEngine(maria_santos_case)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_playable_actions_exact(engine: SatoriEngine) -> None:
    """At game start the playable set is exactly the three root-level actions."""
    expected = frozenset(
        {
            "emergency_intervention",
            "history_general",
            "physical_exam_general",
        }
    )
    assert engine.get_playable_actions() == expected


def test_returns_frozenset(engine: SatoriEngine) -> None:
    """Return type must be frozenset (immutable, hashable contract)."""
    result = engine.get_playable_actions()
    assert isinstance(result, frozenset)


# ---------------------------------------------------------------------------
# Orphan / bare-base actions
# ---------------------------------------------------------------------------


def test_orphan_action_present_at_init(engine: SatoriEngine) -> None:
    """emergency_intervention has no content node; it must appear as a bare base key."""
    assert "emergency_intervention" in engine.get_playable_actions()


def test_orphan_action_persists_after_reveals(engine: SatoriEngine) -> None:
    """emergency_intervention should remain present after other actions fire."""
    engine.execute_action("history_general")
    assert "emergency_intervention" in engine.get_playable_actions()


# ---------------------------------------------------------------------------
# Null-reveal controller node
# ---------------------------------------------------------------------------


def test_null_reveal_node_does_not_contribute(engine: SatoriEngine) -> None:
    """node_00_initial_locks has reveal=null; it must never contribute an action."""
    playable = engine.get_playable_actions()
    # The node fires lock_action effects on init; it has no reveal action of its own.
    # None of its effects should inject an entry into the playable set.
    # Confirm by ensuring only the expected three keys are present at init.
    assert len(playable) == 3


# ---------------------------------------------------------------------------
# Auto-reveal node
# ---------------------------------------------------------------------------


def test_auto_reveal_node_excluded(engine: SatoriEngine) -> None:
    """node_14_seizure_crisis has auto_reveal=True; player cannot trigger it."""
    playable = engine.get_playable_actions()
    # node_14 has no action field anyway, but auto_reveal guard must reject it
    # before the action check.  Ensure no spurious entry appears.
    for entry in playable:
        assert "seizure_crisis" not in entry


# ---------------------------------------------------------------------------
# Locked base action
# ---------------------------------------------------------------------------


def test_locked_base_action_subcategory_absent_at_init(engine: SatoriEngine) -> None:
    """node_15_steroid_response uses start_treatment (locked at init); must not appear."""
    playable = engine.get_playable_actions()
    assert "start_treatment:steroids" not in playable
    assert "start_treatment" not in playable


# ---------------------------------------------------------------------------
# Subcategory surfacing after history_general
# ---------------------------------------------------------------------------


def test_history_general_drops_after_reveal(engine: SatoriEngine) -> None:
    """Once node_01_chief_complaint is revealed, history_general has no remaining
    content and must drop from the playable set."""
    engine.execute_action("history_general")
    assert "history_general" not in engine.get_playable_actions()


def test_subcategories_appear_after_history_general(engine: SatoriEngine) -> None:
    """history_general unlock cascades: subcategory actions must surface."""
    engine.execute_action("history_general")
    playable = engine.get_playable_actions()
    assert "order_labs:cbc" in playable
    assert "order_labs:metabolic_panel" in playable
    assert "history_focused:medications" in playable
    assert "physical_exam_focused:neuro" in playable


def test_bare_order_labs_absent_after_history_general(engine: SatoriEngine) -> None:
    """order_labs has only subcategory nodes; bare 'order_labs' must not appear."""
    engine.execute_action("history_general")
    assert "order_labs" not in engine.get_playable_actions()


def test_physical_exam_general_still_present_after_history_general(
    engine: SatoriEngine,
) -> None:
    """physical_exam_general is not yet revealed; it must stay in the playable set."""
    engine.execute_action("history_general")
    assert "physical_exam_general" in engine.get_playable_actions()


# ---------------------------------------------------------------------------
# Subcategory surfacing after physical_exam_general
# ---------------------------------------------------------------------------


def test_family_history_appears_after_general_exam(engine: SatoriEngine) -> None:
    """node_13_husband_diego requires general_exam_done flag (set by node_02).
    history_focused:family must appear only after physical_exam_general fires."""
    # Before physical_exam_general: family should be absent
    engine.execute_action("history_general")
    assert "history_focused:family" not in engine.get_playable_actions()

    # After physical_exam_general: general_exam_done flag set → node_13 activates
    engine.execute_action("physical_exam_general")
    assert "history_focused:family" in engine.get_playable_actions()


def test_physical_exam_general_drops_after_reveal(engine: SatoriEngine) -> None:
    """After node_02_general_exam is revealed, physical_exam_general must drop out."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_general")
    assert "physical_exam_general" not in engine.get_playable_actions()


# ---------------------------------------------------------------------------
# Complete post-both-generals playable set
# ---------------------------------------------------------------------------


def test_playable_set_after_both_generals_exact(engine: SatoriEngine) -> None:
    """After history_general + physical_exam_general, verify the full playable set."""
    engine.execute_action("history_general")
    engine.execute_action("physical_exam_general")
    expected = frozenset(
        {
            "emergency_intervention",
            "history_focused:family",
            "history_focused:medications",
            "order_labs:cbc",
            "order_labs:metabolic_panel",
            "physical_exam_focused:neuro",
        }
    )
    assert engine.get_playable_actions() == expected


# ---------------------------------------------------------------------------
# Pending-reveals exclusion (ordered labs)
# ---------------------------------------------------------------------------


def test_pending_reveal_node_excluded(engine: SatoriEngine) -> None:
    """After order_labs:cbc is submitted, node_04 enters pending_reveals and must
    no longer appear in the playable set."""
    engine.execute_action("history_general")
    assert "order_labs:cbc" in engine.get_playable_actions()

    engine.execute_action("order_labs:cbc")
    playable_after = engine.get_playable_actions()
    assert "order_labs:cbc" not in playable_after
    # The other lab subcategory must remain
    assert "order_labs:metabolic_panel" in playable_after
