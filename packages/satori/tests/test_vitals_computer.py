"""Unit tests for VitalsComputer.

Tests worst-wins algorithm per vital type, baseline-only, node vitals,
timer stage vitals, and edge cases.
"""

from uuid import uuid4

import pytest

from satori.game_state import GameState
from satori.models.case_definition import (
    ActivationRule,
    Effect,
    EffectType,
    Node,
    NodeContent,
    NodeTimer,
    NodeType,
    TimerStage,
    VitalSigns,
)
from satori.vitals_computer import VitalsComputer

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
        current_vitals=VitalSigns(heart_rate=80, o2_saturation=97),
        available_actions=frozenset(),
    )


def _make_node(
    node_id: str,
    vital_signs: VitalSigns | None = None,
    timer: NodeTimer | None = None,
) -> Node:
    return Node(
        id=node_id,
        type=NodeType.PROGRESSION,
        content=NodeContent(narrative_text="test"),
        activation=ActivationRule(starts_active=False),
        vital_signs=vital_signs,
        timer=timer,
    )


@pytest.fixture
def vc() -> VitalsComputer:
    return VitalsComputer()


BASELINE = VitalSigns(
    heart_rate=80,
    blood_pressure_systolic=120,
    blood_pressure_diastolic=80,
    temperature=98.6,
    respiratory_rate=16,
    o2_saturation=97,
)


# ---------------------------------------------------------------------------
# BASELINE ONLY
# ---------------------------------------------------------------------------


class TestBaselineOnly:
    def test_no_active_nodes_returns_baseline(self, vc: VitalsComputer):
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [], state)
        assert result.heart_rate == 80
        assert result.o2_saturation == 97
        assert result.temperature == 98.6


# ---------------------------------------------------------------------------
# WORST-WINS PER VITAL TYPE
# ---------------------------------------------------------------------------


class TestWorstWins:
    def test_o2_lowest_wins(self, vc: VitalsComputer):
        """O2 → min value is worst."""
        node = _make_node("n1", vital_signs=VitalSigns(o2_saturation=88))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.o2_saturation == 88  # 88 < 97

    def test_bp_systolic_highest_wins(self, vc: VitalsComputer):
        """Systolic BP → max value is worst."""
        node = _make_node("n1", vital_signs=VitalSigns(blood_pressure_systolic=180))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.blood_pressure_systolic == 180  # 180 > 120

    def test_bp_diastolic_highest_wins(self, vc: VitalsComputer):
        """Diastolic BP → max value is worst."""
        node = _make_node("n1", vital_signs=VitalSigns(blood_pressure_diastolic=110))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.blood_pressure_diastolic == 110

    def test_heart_rate_furthest_from_normal_wins_high(self, vc: VitalsComputer):
        """HR → furthest from midpoint (80). Midpoint is (60+100)/2=80."""
        node = _make_node("n1", vital_signs=VitalSigns(heart_rate=140))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.heart_rate == 140  # |140-80|=60 > |80-80|=0

    def test_heart_rate_furthest_from_normal_wins_low(self, vc: VitalsComputer):
        """Low HR is worse than baseline when further from midpoint."""
        node = _make_node("n1", vital_signs=VitalSigns(heart_rate=35))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.heart_rate == 35  # |35-80|=45 > |80-80|=0

    def test_temperature_furthest_from_normal(self, vc: VitalsComputer):
        """Temperature → furthest from midpoint (97+99.5)/2=98.25."""
        node = _make_node("n1", vital_signs=VitalSigns(temperature=104.0))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.temperature == 104.0

    def test_respiratory_rate_furthest_from_normal(self, vc: VitalsComputer):
        """RR → furthest from midpoint (12+20)/2=16."""
        node = _make_node("n1", vital_signs=VitalSigns(respiratory_rate=32))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.respiratory_rate == 32


# ---------------------------------------------------------------------------
# MULTIPLE NODES
# ---------------------------------------------------------------------------


class TestMultipleNodes:
    def test_worst_across_multiple_nodes(self, vc: VitalsComputer):
        node_a = _make_node("na", vital_signs=VitalSigns(o2_saturation=92))
        node_b = _make_node("nb", vital_signs=VitalSigns(o2_saturation=85))
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node_a, node_b], state)
        assert result.o2_saturation == 85  # min(97, 92, 85)


# ---------------------------------------------------------------------------
# TIMER STAGE VITALS
# ---------------------------------------------------------------------------


class TestTimerStageVitals:
    def test_stage_vitals_collected(self, vc: VitalsComputer):
        """Vitals from reached timer stages should be included."""
        from dataclasses import replace as dr

        stage = TimerStage(
            at_minutes=60,
            effects=[Effect(type=EffectType.SET_FLAG, target="s")],
            vital_signs=VitalSigns(heart_rate=120),
        )
        timer = NodeTimer(
            duration_minutes=180,
            stages=[stage],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        # timer_stages shows stage at_minutes=60 has been reached
        state = dr(_base_state(), timer_stages={"n1": 60})
        result = vc.compute_vitals(BASELINE, [node], state)
        # HR: baseline=80 vs stage=120, |120-80|=40>0 → worst=120
        assert result.heart_rate == 120

    def test_unreached_stage_not_collected(self, vc: VitalsComputer):
        """Stages not yet reached should not contribute vitals."""
        from dataclasses import replace as dr

        stage = TimerStage(
            at_minutes=60,
            effects=[Effect(type=EffectType.SET_FLAG, target="s")],
            vital_signs=VitalSigns(heart_rate=120),
        )
        timer = NodeTimer(
            duration_minutes=180,
            stages=[stage],
            on_expire=[Effect(type=EffectType.SET_FLAG, target="x")],
        )
        node = _make_node("n1", timer=timer)
        # timer_stages=0 → stage at 60 not yet reached
        state = dr(_base_state(), timer_stages={"n1": 0})
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.heart_rate == 80  # baseline only


# ---------------------------------------------------------------------------
# EDGE CASES
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_node_without_vitals(self, vc: VitalsComputer):
        """Node with no vital_signs should not affect result."""
        node = _make_node("n1")  # no vital_signs
        state = _base_state()
        result = vc.compute_vitals(BASELINE, [node], state)
        assert result.heart_rate == 80
        assert result.o2_saturation == 97

    def test_empty_values_returns_none(self, vc: VitalsComputer):
        """_worst_value with empty list returns None."""
        assert vc._worst_value("heart_rate", []) is None

    def test_int_vital_returns_int(self, vc: VitalsComputer):
        """Integer vitals should return int, not float."""
        result = vc._worst_value("heart_rate", [80.0, 120.0])
        assert isinstance(result, int)
        assert result == 120

    def test_float_vital_returns_float(self, vc: VitalsComputer):
        """Temperature should return float."""
        result = vc._worst_value("temperature", [98.6, 102.0])
        assert isinstance(result, float)
