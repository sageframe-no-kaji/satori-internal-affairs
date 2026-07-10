"""GameState.revealed_at tests (P2-H03).

The evidence board needs to know WHEN the character learned each fact:
revealed_nodes is a frozenset and carries no order. revealed_at records the
game-minute of every reveal at all three sites that grow revealed_nodes —
action-triggered immediate reveals, auto-reveals, and completed pending
reveals — and its keys stay in lockstep with revealed_nodes.

Timestamps are tick-granular: a pending reveal that completes mid-wait is
stamped with the state's clock at the end of the advancement (the engine has
no sub-tick states), matching NodeRevealedEvent.timestamp_minutes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from satori.engine import SatoriEngine
from satori.models.case_definition import CaseDefinition


@pytest.fixture(scope="module")
def case_def() -> CaseDefinition:
    case_path = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"
    with open(case_path, encoding="utf-8") as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


@pytest.fixture
def engine(case_def: CaseDefinition) -> SatoriEngine:
    return SatoriEngine(case_def)


def test_empty_at_case_start(engine: SatoriEngine) -> None:
    assert engine.get_state().revealed_at == {}


def test_action_reveal_records_the_post_action_clock(engine: SatoriEngine) -> None:
    """history_general costs 15 minutes; node_01 reveals at t=15."""
    engine.execute_action("history_general")
    state = engine.get_state()
    assert "node_01_chief_complaint" in state.revealed_nodes
    assert state.revealed_at["node_01_chief_complaint"] == 15


def test_pending_reveal_records_the_completing_tick(engine: SatoriEngine) -> None:
    """CBC ordered at t=15 (2-min action, 30-min delay) completes during the
    following wait; the stamp is the clock at the end of that advancement."""
    engine.execute_action("history_general")  # t=15
    engine.execute_action("order_labs:cbc")  # t=17, reveal due at 47
    engine.execute_action("wait:60")  # t=77
    state = engine.get_state()
    assert "node_04_cbc_results" in state.revealed_nodes
    assert state.revealed_at["node_04_cbc_results"] == 77


def test_auto_reveal_records_the_crisis_tick(engine: SatoriEngine) -> None:
    """The seizure crisis auto-reveals the tick it activates (t=195)."""
    engine.execute_action("history_general")
    for _ in range(3):
        engine.execute_action("wait:60")
    state = engine.get_state()
    assert "node_14_seizure_crisis" in state.revealed_nodes
    assert state.revealed_at["node_14_seizure_crisis"] == 195


def test_keys_stay_in_lockstep_with_revealed_nodes(engine: SatoriEngine) -> None:
    """The invariant the findings composition relies on."""
    actions = (
        "history_general",
        "physical_exam_focused:neuro",
        "order_labs:cbc",
        "order_imaging:ct_head",
        "wait:60",
        "wait:60",
        "wait:60",  # crisis at t=195 (auto-reveal)
        "emergency_intervention",
    )
    for action in actions:
        engine.execute_action(action)
        state = engine.get_state()
        assert frozenset(state.revealed_at) == state.revealed_nodes, f"drift after {action}"
    assert all(t >= 0 for t in engine.get_state().revealed_at.values())


def test_deterministic_across_identical_runs(case_def: CaseDefinition) -> None:
    """Same case + same actions = same revealed_at map."""
    actions = ("history_general", "order_labs:cbc", "order_labs:metabolic_panel", "wait:60", "wait:60")
    maps = []
    for _ in range(2):
        eng = SatoriEngine(case_def)
        for action in actions:
            eng.execute_action(action)
        maps.append(dict(eng.get_state().revealed_at))
    assert maps[0] == maps[1]
