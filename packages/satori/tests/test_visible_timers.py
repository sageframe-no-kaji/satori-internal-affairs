"""Tests for compute_visible_timers and GameState.visible_timers.

Covers the derivation logic: pending_reveals (always diegetic), active nodes
with diegetic timers, non-diegetic timers excluded, deterministic ordering.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from satori.game_state import GameState, _humanise_node_id, compute_visible_timers
from satori.models.case_definition import (
    ActivationRule,
    CaseDefinition,
    Effect,
    EffectType,
    EndCondition,
    EndConditionType,
    GroundTruth,
    Metadata,
    NarrativeHook,
    NarrativeHookType,
    Node,
    NodeContent,
    NodeTimer,
    OptimalStep,
    OutcomeEvaluation,
    OutcomeTier,
    OutcomeTierLevel,
    PatientContext,
    Sex,
    TimeCost,
    VitalSigns,
)

EXAMPLE_CASE_PATH = Path(__file__).parent.parent.parent.parent / "cases" / "example-neurocysticercosis.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vitals() -> VitalSigns:
    return VitalSigns(
        heart_rate=80,
        blood_pressure_systolic=120,
        blood_pressure_diastolic=80,
        temperature=98.6,
        respiratory_rate=16,
        o2_saturation=99,
    )


def _make_minimal_case(nodes: list[Node]) -> CaseDefinition:
    """Build the smallest valid CaseDefinition for testing."""
    return CaseDefinition(
        id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        version="1.0.0",
        metadata=Metadata(
            difficulty="beginner",
            estimated_duration_minutes=10,
            simulated_duration_minutes=60,
            learning_objectives=["test"],
            dramatic_tone="medical_mystery",
        ),
        patient=PatientContext(
            name="Test Patient",
            age=30,
            sex=Sex.FEMALE,
            setting="ED",
            chief_complaint="test",
            appearance="test",
            arriving_vitals=_make_vitals(),
        ),
        ground_truth=GroundTruth(
            diagnosis="test",
            differential=["test"],
            mechanism="test",
            key_insight="test",
            optimal_path=[OptimalStep(action="history_general", description="test", time_minutes=15)],
            narrative_hooks=[
                NarrativeHook(
                    type=NarrativeHookType.HIDDEN_CONNECTION,
                    description="test",
                    structural_role="test",
                )
            ],
        ),
        action_costs={"history_general": TimeCost(action_minutes=15)},
        nodes=nodes if nodes else [_make_base_node()],
        outcome_evaluation=OutcomeEvaluation(
            tiers=[OutcomeTier(tier=OutcomeTierLevel.FAILURE, narrative="test")],
            end_conditions=[
                EndCondition(
                    type=EndConditionType.TIME_ELAPSED,
                    value=300,
                    description="time limit",
                )
            ],
        ),
    )


def _make_base_node() -> Node:
    """Minimal node that won't do anything interesting."""
    return Node(
        id="node_00_base",
        type="behavioral",
        content=NodeContent(narrative_text="base"),
        activation=ActivationRule(starts_active=True),
        reveal=None,
    )


def _make_state(
    pending_reveals: dict[str, int] | None = None,
    timers: dict[str, int] | None = None,
    active_nodes: frozenset[str] | None = None,
) -> GameState:
    """Build a minimal GameState for testing visible_timers derivation."""
    return GameState(
        case_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        current_time_minutes=0,
        flags=frozenset(),
        active_nodes=active_nodes or frozenset(),
        revealed_nodes=frozenset(),
        expired_nodes=frozenset(),
        pending_reveals=pending_reveals or {},
        timers=timers or {},
        timer_stages={},
        current_vitals=_make_vitals(),
        available_actions=frozenset(),
    )


# ---------------------------------------------------------------------------
# _humanise_node_id
# ---------------------------------------------------------------------------


def test_humanise_strips_node_prefix() -> None:
    assert _humanise_node_id("node_04_cbc_results") == "Cbc Results"


def test_humanise_no_prefix() -> None:
    # No node_NN_ prefix — capitalise all words
    assert _humanise_node_id("my_timer") == "My Timer"


def test_humanise_single_word() -> None:
    assert _humanise_node_id("node_01_history") == "History"


def test_humanise_empty_remainder() -> None:
    # Pathological case: only "node_01" with no trailing words
    result = _humanise_node_id("node_01")
    # Falls back to the original string when no label parts
    assert result == "node_01"


# ---------------------------------------------------------------------------
# compute_visible_timers: empty state
# ---------------------------------------------------------------------------


def test_empty_state_gives_empty_visible_timers() -> None:
    state = _make_state()
    case = _make_minimal_case([_make_base_node()])
    result = compute_visible_timers(state, case)
    assert result == ()


# ---------------------------------------------------------------------------
# compute_visible_timers: pending reveals
# ---------------------------------------------------------------------------


def test_pending_reveal_appears_as_pending_reveal_source() -> None:
    node = Node(
        id="node_04_cbc_results",
        type="lab_result",
        content=NodeContent(narrative_text="CBC results"),
        activation=ActivationRule(starts_active=True),
    )
    case = _make_minimal_case([node])
    state = _make_state(
        pending_reveals={"node_04_cbc_results": 25},
        active_nodes=frozenset({"node_04_cbc_results"}),
    )
    result = compute_visible_timers(state, case)
    assert len(result) == 1
    vt = result[0]
    assert vt.source == "pending_reveal"
    assert vt.node_id == "node_04_cbc_results"
    assert vt.remaining_minutes == 25


def test_pending_reveal_label_falls_back_to_humanised_node_id() -> None:
    node = Node(
        id="node_04_cbc_results",
        type="lab_result",
        content=NodeContent(narrative_text="CBC results"),
        activation=ActivationRule(starts_active=True),
    )
    case = _make_minimal_case([node])
    state = _make_state(pending_reveals={"node_04_cbc_results": 25})
    result = compute_visible_timers(state, case)
    assert result[0].label == "Cbc Results"


def test_pending_reveal_for_unknown_node_uses_node_id_as_label() -> None:
    # node not in case.nodes — still appears but label falls back to node_id humanised
    case = _make_minimal_case([_make_base_node()])
    state = _make_state(pending_reveals={"node_99_mystery": 10})
    result = compute_visible_timers(state, case)
    assert len(result) == 1
    assert result[0].node_id == "node_99_mystery"
    assert result[0].label == "Mystery"  # humanised from node_99_mystery


# ---------------------------------------------------------------------------
# compute_visible_timers: active diegetic timers
# ---------------------------------------------------------------------------


def test_active_diegetic_timer_appears_as_active_timer_source() -> None:
    node = Node(
        id="node_10_lab_timer",
        type="lab_result",
        content=NodeContent(narrative_text="timer node"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=45,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="lab_done")],
            diegetic=True,
        ),
    )
    case = _make_minimal_case([node])
    state = _make_state(
        timers={"node_10_lab_timer": 30},
        active_nodes=frozenset({"node_10_lab_timer"}),
    )
    result = compute_visible_timers(state, case)
    assert len(result) == 1
    vt = result[0]
    assert vt.source == "active_timer"
    assert vt.node_id == "node_10_lab_timer"
    assert vt.remaining_minutes == 30


def test_active_non_diegetic_timer_does_not_appear() -> None:
    node = Node(
        id="node_09_progression",
        type="progression",
        content=NodeContent(narrative_text="progression"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=180,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="crisis")],
            diegetic=False,  # explicitly non-diegetic
        ),
    )
    case = _make_minimal_case([node])
    state = _make_state(
        timers={"node_09_progression": 120},
        active_nodes=frozenset({"node_09_progression"}),
    )
    result = compute_visible_timers(state, case)
    assert result == ()


def test_diegetic_timer_not_in_active_nodes_does_not_appear() -> None:
    node = Node(
        id="node_10_lab_timer",
        type="lab_result",
        content=NodeContent(narrative_text="timer node"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=45,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="lab_done")],
            diegetic=True,
        ),
    )
    case = _make_minimal_case([node])
    # node has a diegetic timer in state.timers but is NOT in active_nodes
    state = _make_state(
        timers={"node_10_lab_timer": 30},
        active_nodes=frozenset(),  # not active
    )
    result = compute_visible_timers(state, case)
    assert result == ()


# ---------------------------------------------------------------------------
# compute_visible_timers: mixed sources + ordering
# ---------------------------------------------------------------------------


def test_multiple_timers_sorted_by_remaining_then_node_id() -> None:
    """Multiple visible timers sorted by (remaining_minutes, node_id) ascending."""
    node_a = Node(
        id="node_01_aaa",
        type="lab_result",
        content=NodeContent(narrative_text="a"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=60,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="a_done")],
            diegetic=True,
        ),
    )
    node_b = Node(
        id="node_02_bbb",
        type="lab_result",
        content=NodeContent(narrative_text="b"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=30,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="b_done")],
            diegetic=True,
        ),
    )
    case = _make_minimal_case([node_a, node_b])
    state = _make_state(
        # pending_reveal for node_a remaining 45, active_timer for node_b remaining 20
        pending_reveals={"node_01_aaa": 45},
        timers={"node_02_bbb": 20},
        active_nodes=frozenset({"node_01_aaa", "node_02_bbb"}),
    )
    result = compute_visible_timers(state, case)
    # Sorted: node_02_bbb (20) < node_01_aaa (45)
    assert len(result) == 2
    assert result[0].node_id == "node_02_bbb"
    assert result[0].remaining_minutes == 20
    assert result[1].node_id == "node_01_aaa"
    assert result[1].remaining_minutes == 45


def test_tie_in_remaining_sorted_by_node_id_alphabetical() -> None:
    """When remaining_minutes are equal, sort by node_id alphabetically."""
    node_z = Node(
        id="node_02_zzz",
        type="lab_result",
        content=NodeContent(narrative_text="z"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=30,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="z_done")],
            diegetic=True,
        ),
    )
    case = _make_minimal_case([node_z])
    state = _make_state(
        # Two pending reveals with same remaining time
        pending_reveals={"node_99_zzz": 15, "node_01_aaa": 15},
    )
    result = compute_visible_timers(state, case)
    assert len(result) == 2
    # Alphabetically: node_01_aaa < node_99_zzz
    assert result[0].node_id == "node_01_aaa"
    assert result[1].node_id == "node_99_zzz"


def test_pending_reveal_and_active_timer_both_appear() -> None:
    """Both a pending_reveal and a diegetic active_timer can coexist."""
    node_lab = Node(
        id="node_04_cbc",
        type="lab_result",
        content=NodeContent(narrative_text="cbc"),
        activation=ActivationRule(starts_active=True),
    )
    node_timer = Node(
        id="node_10_consult",
        type="lab_result",
        content=NodeContent(narrative_text="consult"),
        activation=ActivationRule(starts_active=True),
        timer=NodeTimer(
            duration_minutes=60,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="consult_done")],
            diegetic=True,
        ),
    )
    case = _make_minimal_case([node_lab, node_timer])
    state = _make_state(
        pending_reveals={"node_04_cbc": 25},
        timers={"node_10_consult": 45},
        active_nodes=frozenset({"node_04_cbc", "node_10_consult"}),
    )
    result = compute_visible_timers(state, case)
    sources = {vt.source for vt in result}
    assert "pending_reveal" in sources
    assert "active_timer" in sources
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Integration: engine populates visible_timers on state
# ---------------------------------------------------------------------------


def test_engine_initial_state_has_empty_visible_timers() -> None:
    """At game start with no pending reveals and no diegetic timers, visible_timers is empty."""
    from satori.models.case_definition import validate_case

    case = validate_case(EXAMPLE_CASE_PATH)
    from satori.engine import SatoriEngine

    engine = SatoriEngine(case)
    state = engine.get_state()
    assert isinstance(state.visible_timers, tuple)
    # Maria Santos has no diegetic timers and no pending reveals at start
    assert state.visible_timers == ()


def test_engine_visible_timers_populated_after_lab_order() -> None:
    """After ordering a lab (pending_reveal created), visible_timers includes it."""
    from satori.models.case_definition import validate_case

    case = validate_case(EXAMPLE_CASE_PATH)
    from satori.engine import SatoriEngine

    engine = SatoriEngine(case)
    # Unlock labs via history_general first
    engine.execute_action("history_general")
    # Order CBC — this creates a pending_reveal
    engine.execute_action("order_labs:cbc")
    state = engine.get_state()
    # CBC result is pending — should appear in visible_timers
    assert any(vt.node_id == "node_04_cbc_results" for vt in state.visible_timers)
    pending_vt = next(vt for vt in state.visible_timers if vt.node_id == "node_04_cbc_results")
    assert pending_vt.source == "pending_reveal"
    assert pending_vt.remaining_minutes > 0
