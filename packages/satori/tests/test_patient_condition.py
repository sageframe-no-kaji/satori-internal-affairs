"""Unit tests for compute_patient_condition.

Tests all 6 return paths: DEAD, RECOVERED, CRITICAL, DECOMPENSATING,
COMPENSATING, STABLE with carefully crafted GameState fixtures.
"""

from dataclasses import replace
from uuid import uuid4

from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    CaseDefinition,
    Effect,
    EffectType,
    Node,
    NodeContent,
    NodeTimer,
    NodeType,
    VitalSigns,
)
from satori.patient_condition import PatientCondition, compute_patient_condition

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _base_state() -> GameState:
    return GameState(
        case_id=uuid4(),
        current_time_minutes=0,
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
        available_actions=frozenset(),
    )


def _make_case(nodes: list[Node] | None = None) -> CaseDefinition:
    import json
    from pathlib import Path

    case_path = Path(__file__).resolve().parents[2] / ".." / "cases" / "example-neurocysticercosis.json"
    with case_path.open() as f:
        data = json.load(f)
    if nodes is not None:
        data["nodes"] = [n.model_dump(mode="json") for n in nodes]
    return CaseDefinition.model_validate(data)


def _make_progression_node(node_id: str, duration: int = 120) -> Node:
    return Node(
        id=node_id,
        type=NodeType.PROGRESSION,
        content=NodeContent(narrative_text="test"),
        activation=ActivationRule(starts_active=False),
        timer=NodeTimer(
            duration_minutes=duration,
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        ),
    )


# ---------------------------------------------------------------------------
# DEAD
# ---------------------------------------------------------------------------


class TestDead:
    def test_dead_from_patient_death_flag(self):
        state = replace(_base_state(), flags=frozenset({"patient_death"}))
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.DEAD

    def test_dead_from_death_node_active(self):
        state = replace(_base_state(), active_nodes=frozenset({"node_11_patient_death"}))
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.DEAD

    def test_dead_from_death_in_node_name_case_insensitive(self):
        state = replace(_base_state(), active_nodes=frozenset({"outcome_Death_node"}))
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.DEAD


# ---------------------------------------------------------------------------
# RECOVERED
# ---------------------------------------------------------------------------


class TestRecovered:
    def test_recovered_optimal(self):
        state = replace(
            _base_state(),
            case_ended=True,
            outcome_tier="optimal",
            flags=frozenset({"correct_treatment_started"}),
        )
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.RECOVERED

    def test_recovered_good(self):
        state = replace(
            _base_state(),
            case_ended=True,
            outcome_tier="good",
            flags=frozenset({"correct_treatment_started"}),
        )
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.RECOVERED

    def test_not_recovered_without_treatment_flag(self):
        """Case ended optimal but no correct_treatment_started → not RECOVERED."""
        state = replace(_base_state(), case_ended=True, outcome_tier="optimal")
        case = _make_case()
        result = compute_patient_condition(state, case)
        assert result != PatientCondition.RECOVERED

    def test_not_recovered_partial_outcome(self):
        """Case ended partial → not RECOVERED."""
        state = replace(
            _base_state(),
            case_ended=True,
            outcome_tier="partial",
            flags=frozenset({"correct_treatment_started"}),
        )
        case = _make_case()
        result = compute_patient_condition(state, case)
        assert result != PatientCondition.RECOVERED


# ---------------------------------------------------------------------------
# CRITICAL
# ---------------------------------------------------------------------------


class TestCritical:
    def test_critical_low_o2(self):
        vitals = VitalSigns(heart_rate=80, o2_saturation=85, blood_pressure_systolic=120, temperature=98.6)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL

    def test_critical_high_hr(self):
        vitals = VitalSigns(heart_rate=160, o2_saturation=97, blood_pressure_systolic=120, temperature=98.6)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL

    def test_critical_low_hr(self):
        vitals = VitalSigns(heart_rate=35, o2_saturation=97, blood_pressure_systolic=120, temperature=98.6)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL

    def test_critical_low_sbp(self):
        vitals = VitalSigns(heart_rate=80, o2_saturation=97, blood_pressure_systolic=85, temperature=98.6)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL

    def test_critical_high_temp(self):
        vitals = VitalSigns(heart_rate=80, o2_saturation=97, blood_pressure_systolic=120, temperature=105.0)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL

    def test_critical_low_temp(self):
        vitals = VitalSigns(heart_rate=80, o2_saturation=97, blood_pressure_systolic=120, temperature=94.0)
        state = replace(_base_state(), current_vitals=vitals)
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.CRITICAL


# ---------------------------------------------------------------------------
# DECOMPENSATING & COMPENSATING
# ---------------------------------------------------------------------------


class TestDecompensating:
    def test_decompensating_timer_past_50_percent(self):
        """Progression timer >50% elapsed → DECOMPENSATING."""
        node = _make_progression_node("prog_1", duration=100)
        case = _make_case([node])
        # remaining=40 → elapsed=60 → 60% > 50%
        state = replace(
            _base_state(),
            active_nodes=frozenset({"prog_1"}),
            timers={"prog_1": 40},
            timer_stages={"prog_1": 0},
        )
        assert compute_patient_condition(state, case) == PatientCondition.DECOMPENSATING


class TestCompensating:
    def test_compensating_timer_under_50_percent(self):
        """Progression timer ≤50% elapsed → COMPENSATING."""
        node = _make_progression_node("prog_1", duration=100)
        case = _make_case([node])
        # remaining=80 → elapsed=20 → 20% ≤ 50%
        state = replace(
            _base_state(),
            active_nodes=frozenset({"prog_1"}),
            timers={"prog_1": 80},
            timer_stages={"prog_1": 0},
        )
        assert compute_patient_condition(state, case) == PatientCondition.COMPENSATING


# ---------------------------------------------------------------------------
# STABLE
# ---------------------------------------------------------------------------


class TestStable:
    def test_stable_default(self):
        """Default when no danger signals."""
        state = _base_state()
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.STABLE

    def test_stable_non_progression_node_active(self):
        """Active node of non-progression type (no timer) → STABLE."""
        node = Node(
            id="n1",
            type=NodeType.MEDICAL_FINDING,
            content=NodeContent(narrative_text="test"),
            activation=ActivationRule(starts_active=True),
        )
        case = _make_case([node])
        state = replace(_base_state(), active_nodes=frozenset({"n1"}))
        assert compute_patient_condition(state, case) == PatientCondition.STABLE


# ---------------------------------------------------------------------------
# PRIORITY ORDER
# ---------------------------------------------------------------------------


class TestPriority:
    def test_dead_trumps_critical(self):
        """DEAD flag overrides critical vitals."""
        vitals = VitalSigns(heart_rate=160, o2_saturation=85, blood_pressure_systolic=85, temperature=105.0)
        state = replace(
            _base_state(),
            flags=frozenset({"patient_death"}),
            current_vitals=vitals,
        )
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.DEAD

    def test_recovered_trumps_stable(self):
        """RECOVERED when case ended optimally with treatment."""
        state = replace(
            _base_state(),
            case_ended=True,
            outcome_tier="optimal",
            flags=frozenset({"correct_treatment_started"}),
        )
        case = _make_case()
        assert compute_patient_condition(state, case) == PatientCondition.RECOVERED
