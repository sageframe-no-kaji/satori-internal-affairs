"""Unit tests for StateCheckers.

Tests auto-reveals, action reveals (delayed vs immediate), interventions,
cascade_activations (including 10-round limit), recompute_vitals, and
check_end_conditions (NODE_ACTIVATED, TIME_ELAPSED, FLAG_SET + outcome tiers).
"""

from dataclasses import replace
from uuid import uuid4

from satori.condition_evaluator import ConditionEvaluator
from satori.effect_executor import EffectExecutor
from satori.events import (
    CaseEndedEvent,
    NodeRevealedEvent,
    PendingRevealStartedEvent,
    VitalsChangedEvent,
)
from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    CaseDefinition,
    Condition,
    ConditionPath,
    ConditionType,
    Effect,
    EffectType,
    EndCondition,
    EndConditionType,
    InterventionEffect,
    Node,
    NodeContent,
    NodeEffects,
    NodeTimer,
    NodeType,
    OutcomeEvaluation,
    OutcomeTier,
    OutcomeTierLevel,
    RevealRule,
    TimeCost,
    VitalSigns,
)
from satori.state_checkers import StateCheckers
from satori.vitals_computer import VitalsComputer

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _base_state() -> GameState:
    return GameState(
        case_id=uuid4(),
        current_time_minutes=30,
        flags=frozenset(),
        active_nodes=frozenset(),
        revealed_nodes=frozenset(),
        expired_nodes=frozenset(),
        pending_reveals={},
        timers={},
        timer_stages={},
        current_vitals=VitalSigns(
            heart_rate=80,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            temperature=98.6,
            respiratory_rate=16,
            o2_saturation=97,
        ),
        available_actions=frozenset({"history_general", "history_focused", "order_labs", "start_treatment"}),
    )


def _load_base_case() -> CaseDefinition:
    import json
    from pathlib import Path

    case_path = Path(__file__).resolve().parents[2] / ".." / "cases" / "example-neurocysticercosis.json"
    with case_path.open() as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


def _make_case(
    nodes: list[Node],
    action_costs: dict[str, TimeCost] | None = None,
    outcome_evaluation: OutcomeEvaluation | None = None,
) -> CaseDefinition:
    base = _load_base_case()
    data = base.model_dump(mode="json")
    data["nodes"] = [n.model_dump(mode="json") for n in nodes]
    if action_costs is not None:
        data["action_costs"] = {k: v.model_dump(mode="json") for k, v in action_costs.items()}
    if outcome_evaluation is not None:
        data["outcome_evaluation"] = outcome_evaluation.model_dump(mode="json")
    return CaseDefinition.model_validate(data)


def _make_node(
    node_id: str,
    node_type: NodeType = NodeType.MEDICAL_FINDING,
    reveal: RevealRule | None = None,
    effects: NodeEffects | None = None,
    activation: ActivationRule | None = None,
    vital_signs: VitalSigns | None = None,
    timer: NodeTimer | None = None,
) -> Node:
    return Node(
        id=node_id,
        type=node_type,
        content=NodeContent(narrative_text=f"Content for {node_id}"),
        activation=activation or ActivationRule(starts_active=False),
        reveal=reveal,
        effects=effects,
        vital_signs=vital_signs,
        timer=timer,
    )


def _build_checkers(case: CaseDefinition) -> StateCheckers:
    node_map = {n.id: n for n in case.nodes}
    return StateCheckers(
        node_map=node_map,
        case=case,
        condition_eval=ConditionEvaluator(),
        effect_exec=EffectExecutor(),
        vitals_comp=VitalsComputer(),
    )


# ---------------------------------------------------------------------------
# check_auto_reveals
# ---------------------------------------------------------------------------


class TestAutoReveals:
    def test_auto_reveal_active_unrevealed(self):
        node = _make_node("n1", reveal=RevealRule(auto_reveal=True))
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_auto_reveals(state)
        assert "n1" in new_state.revealed_nodes
        assert any(isinstance(e, NodeRevealedEvent) and e.node_id == "n1" for e in events)

    def test_already_revealed_skipped(self):
        node = _make_node("n1", reveal=RevealRule(auto_reveal=True))
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            revealed_nodes=frozenset({"n1"}),
        )
        new_state, events = sc.check_auto_reveals(state)
        assert events == []

    def test_non_auto_reveal_skipped(self):
        node = _make_node("n1", reveal=RevealRule(action="history_general"))
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))
        new_state, events = sc.check_auto_reveals(state)
        assert "n1" not in new_state.revealed_nodes

    def test_auto_reveal_with_on_reveal_effects(self):
        node = _make_node(
            "n1",
            reveal=RevealRule(auto_reveal=True),
            effects=NodeEffects(on_reveal=[Effect(type=EffectType.SET_FLAG, target="auto_flag")]),
        )
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_auto_reveals(state)
        assert "n1" in new_state.revealed_nodes
        assert "auto_flag" in new_state.flags


# ---------------------------------------------------------------------------
# check_action_reveals
# ---------------------------------------------------------------------------


class TestActionReveals:
    def test_immediate_reveal(self):
        node = _make_node("n1", reveal=RevealRule(action="history_general"))
        action_costs = {"history_general": TimeCost(action_minutes=10)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_action_reveals(state, "history_general", None)
        assert "n1" in new_state.revealed_nodes
        assert any(isinstance(e, NodeRevealedEvent) for e in events)

    def test_delayed_reveal_from_node(self):
        node = _make_node("n1", reveal=RevealRule(action="order_labs", subcategory="cbc", delay_minutes=15))
        action_costs = {"order_labs": TimeCost(action_minutes=5)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_action_reveals(state, "order_labs", "cbc")
        assert "n1" not in new_state.revealed_nodes
        assert new_state.pending_reveals["n1"] == 15
        assert any(isinstance(e, PendingRevealStartedEvent) and e.node_id == "n1" for e in events)

    def test_delayed_reveal_from_action_cost(self):
        """Use action_costs result_delay_minutes when node has no delay."""
        node = _make_node("n1", reveal=RevealRule(action="order_labs", subcategory="cbc"))
        action_costs = {"order_labs": TimeCost(action_minutes=5, result_delay_minutes=20)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_action_reveals(state, "order_labs", "cbc")
        assert new_state.pending_reveals["n1"] == 20

    def test_wrong_action_no_reveal(self):
        node = _make_node("n1", reveal=RevealRule(action="history_general"))
        action_costs = {"order_labs": TimeCost(action_minutes=5)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_action_reveals(state, "order_labs", None)
        assert "n1" not in new_state.revealed_nodes
        assert events == []

    def test_already_in_pending_skipped(self):
        node = _make_node("n1", reveal=RevealRule(action="order_labs"))
        action_costs = {"order_labs": TimeCost(action_minutes=5)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            pending_reveals={"n1": 10},
        )
        new_state, events = sc.check_action_reveals(state, "order_labs", None)
        assert events == []


# ---------------------------------------------------------------------------
# check_interventions
# ---------------------------------------------------------------------------


class TestInterventions:
    def test_intervention_matches_param(self):
        node = _make_node(
            "n1",
            effects=NodeEffects(
                on_intervene=InterventionEffect(
                    treatment="albendazole",
                    effects=[Effect(type=EffectType.SET_FLAG, target="correct_treatment_started")],
                )
            ),
        )
        action_costs = {"start_treatment": TimeCost(action_minutes=10)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_interventions(state, "start_treatment", "albendazole")
        assert "correct_treatment_started" in new_state.flags

    def test_intervention_wrong_treatment(self):
        node = _make_node(
            "n1",
            effects=NodeEffects(
                on_intervene=InterventionEffect(
                    treatment="albendazole",
                    effects=[Effect(type=EffectType.SET_FLAG, target="correct_treatment_started")],
                )
            ),
        )
        action_costs = {"start_treatment": TimeCost(action_minutes=10)}
        case = _make_case([node], action_costs=action_costs)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_interventions(state, "start_treatment", "steroids")
        assert "correct_treatment_started" not in new_state.flags
        assert events == []

    def test_no_effects_no_crash(self):
        node = _make_node("n1")  # no effects
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.check_interventions(state, "start_treatment", "albendazole")
        assert events == []


# ---------------------------------------------------------------------------
# cascade_activations
# ---------------------------------------------------------------------------


class TestCascadeActivations:
    def test_single_activation(self):
        node = _make_node(
            "n1",
            activation=ActivationRule(
                paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="x")])],
            ),
        )
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), flags=frozenset({"x"}))

        new_state, events = sc.cascade_activations(state)
        assert "n1" in new_state.active_nodes

    def test_cascade_chain(self):
        """Node A's activation sets flag that activates Node B."""
        node_a = _make_node(
            "a",
            activation=ActivationRule(
                paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="trigger")])],
                on_activate=[Effect(type=EffectType.SET_FLAG, target="a_active")],
            ),
        )
        node_b = _make_node(
            "b",
            activation=ActivationRule(
                paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="a_active")])],
            ),
        )
        case = _make_case([node_a, node_b])
        sc = _build_checkers(case)
        state = replace(_base_state(), flags=frozenset({"trigger"}))

        new_state, events = sc.cascade_activations(state)
        assert "a" in new_state.active_nodes
        assert "b" in new_state.active_nodes

    def test_already_active_node_skipped(self):
        node = _make_node(
            "n1",
            activation=ActivationRule(
                paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="x")])],
            ),
        )
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), flags=frozenset({"x"}), active_nodes=frozenset({"n1"}))

        new_state, events = sc.cascade_activations(state)
        assert events == []  # no new activations

    def test_no_paths_skipped(self):
        """starts_active nodes (paths=None) are skipped in cascade."""
        node = _make_node("n1", activation=ActivationRule(starts_active=True))
        case = _make_case([node])
        sc = _build_checkers(case)
        state = _base_state()

        new_state, events = sc.cascade_activations(state)
        assert "n1" not in new_state.active_nodes  # cascade doesn't handle starts_active

    def test_activation_with_timer(self):
        timer = NodeTimer(duration_minutes=60, on_expire=[Effect(type=EffectType.SET_FLAG, target="expired")])
        node = _make_node(
            "n1",
            activation=ActivationRule(
                paths=[ConditionPath(conditions=[Condition(type=ConditionType.FLAG_SET, target="x")])],
            ),
            timer=timer,
        )
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), flags=frozenset({"x"}))

        new_state, events = sc.cascade_activations(state)
        assert "n1" in new_state.active_nodes
        assert new_state.timers["n1"] == 60
        assert new_state.timer_stages["n1"] == 0


# ---------------------------------------------------------------------------
# recompute_vitals
# ---------------------------------------------------------------------------


class TestRecomputeVitals:
    def test_vitals_changed_emits_event(self):
        node = _make_node("n1", vital_signs=VitalSigns(heart_rate=140))
        case = _make_case([node])
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))

        new_state, events = sc.recompute_vitals(state)
        assert new_state.current_vitals.heart_rate != state.current_vitals.heart_rate
        assert any(isinstance(e, VitalsChangedEvent) for e in events)

    def test_vitals_unchanged_no_event(self):
        node = _make_node("n1")  # no vital_signs → baseline stays
        case = _make_case([node])
        sc = _build_checkers(case)
        # State already has baseline vitals
        state = replace(
            _base_state(),
            active_nodes=frozenset({"n1"}),
            current_vitals=case.patient.arriving_vitals,
        )

        new_state, events = sc.recompute_vitals(state)
        assert events == []


# ---------------------------------------------------------------------------
# check_end_conditions
# ---------------------------------------------------------------------------


class TestCheckEndConditions:
    def _make_outcome_eval(self) -> OutcomeEvaluation:
        return OutcomeEvaluation(
            tiers=[
                OutcomeTier(
                    tier=OutcomeTierLevel.OPTIMAL,
                    required_flags=["correct_treatment_started"],
                    narrative="Perfect outcome!",
                ),
                OutcomeTier(
                    tier=OutcomeTierLevel.FAILURE,
                    narrative="Failed.",
                ),
            ],
            end_conditions=[
                EndCondition(
                    type=EndConditionType.NODE_ACTIVATED,
                    target="death_node",
                    description="Patient death",
                ),
                EndCondition(
                    type=EndConditionType.TIME_ELAPSED,
                    value=360,
                    description="Time limit",
                ),
                EndCondition(
                    type=EndConditionType.FLAG_SET,
                    target="correct_treatment_started",
                    description="Treatment started",
                ),
            ],
        )

    def test_node_activated_end(self):
        node = _make_node("death_node")
        oe = self._make_outcome_eval()
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = replace(_base_state(), active_nodes=frozenset({"death_node"}))

        new_state, events = sc.check_end_conditions(state)
        assert new_state.case_ended is True
        assert any(isinstance(e, CaseEndedEvent) for e in events)

    def test_time_elapsed_end(self):
        node = _make_node("n1")
        oe = self._make_outcome_eval()
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = replace(_base_state(), current_time_minutes=360)

        new_state, events = sc.check_end_conditions(state)
        assert new_state.case_ended is True
        assert "failure" == new_state.outcome_tier  # no flags → failure tier

    def test_flag_set_end(self):
        node = _make_node("n1")
        oe = self._make_outcome_eval()
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = replace(_base_state(), flags=frozenset({"correct_treatment_started"}))

        new_state, events = sc.check_end_conditions(state)
        assert new_state.case_ended is True
        assert new_state.outcome_tier == "optimal"

    def test_no_end_condition_met(self):
        node = _make_node("n1")
        oe = self._make_outcome_eval()
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = _base_state()

        new_state, events = sc.check_end_conditions(state)
        assert new_state.case_ended is False
        assert events == []

    def test_outcome_tier_with_excluded_flags(self):
        oe = OutcomeEvaluation(
            tiers=[
                OutcomeTier(
                    tier=OutcomeTierLevel.OPTIMAL,
                    required_flags=["correct_treatment_started"],
                    excluded_flags=["patient_harm"],
                    narrative="Perfect!",
                ),
                OutcomeTier(
                    tier=OutcomeTierLevel.FAILURE,
                    narrative="Failed.",
                ),
            ],
            end_conditions=[
                EndCondition(
                    type=EndConditionType.FLAG_SET,
                    target="correct_treatment_started",
                    description="Treatment",
                ),
            ],
        )
        node = _make_node("n1")
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = replace(
            _base_state(),
            flags=frozenset({"correct_treatment_started", "patient_harm"}),
        )

        new_state, events = sc.check_end_conditions(state)
        assert new_state.case_ended is True
        assert new_state.outcome_tier == "failure"  # excluded flag blocks optimal

    def test_default_failure_when_no_tier_matches(self):
        oe = OutcomeEvaluation(
            tiers=[
                OutcomeTier(
                    tier=OutcomeTierLevel.OPTIMAL,
                    required_flags=["impossible_flag"],
                    narrative="Can't reach this.",
                ),
            ],
            end_conditions=[
                EndCondition(
                    type=EndConditionType.TIME_ELAPSED,
                    value=360,
                    description="Time limit",
                ),
            ],
        )
        node = _make_node("n1")
        case = _make_case([node], outcome_evaluation=oe)
        sc = _build_checkers(case)
        state = replace(_base_state(), current_time_minutes=400)

        new_state, events = sc.check_end_conditions(state)
        assert new_state.outcome_tier == "failure"
