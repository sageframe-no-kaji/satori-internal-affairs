"""Case-level regression harness for the Maria Santos case (audit S2).

The engine's unit tests specify engine behavior; nothing previously tested
the shipped case artifact as a whole. Audit finding C-1 (a steroid-rebound
node that fired in every playthrough, silently cutting the crisis clock
from 180 to ~120 minutes) lived undetected in exactly that gap. These tests
drive the real case JSON through the real engine and pin its timeline
invariants:

- Inaction: the crisis arrives on the authored 180-minute progression
  clock, and the steroid rebound never fires when steroids are never given.
- Empirical path: treating on suspicion (eosinophilia + ring-enhancing
  lesion, no confirmation) earns GOOD.
- Confirmed path: confirmation + family engagement + treatment before 120
  minutes earns OPTIMAL.
- Steroids: the rebound fires 60 minutes AFTER administration (not before),
  and a steroids run scores at most PARTIAL.
- Blocked: treatment without any evidence is rejected.

Timeline arithmetic used throughout (from the authored case data):
history_general costs 15 min and activates node_09 (180-min progression
timer), so node_09 expires at t=195 on an untreated run; the seizure
crisis (node_14) carries a 5-minute timer to death (node_16).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from satori.engine import InvalidActionError, SatoriEngine
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
# Scripted openings shared by several scenarios
# ---------------------------------------------------------------------------


def _open_to_empirical_unlock(eng: SatoriEngine) -> None:
    """Drive to t=74: eosinophilia + ring_enhancing_lesion revealed.

    t=0   history_general        -> t=15  (node_09 timer starts: 180)
    t=15  physical_exam_focused:neuro -> t=25
    t=25  order_labs:cbc         -> t=27  (result due t=57)
    t=27  order_imaging:ct_head  -> t=29  (result due t=74)
    t=29  wait:30                -> t=59  (cbc reveals at 57)
    t=59  wait:15                -> t=74  (CT reveals at 74; node_18
                                           activates, start_treatment unlocks)
    """
    eng.execute_action("history_general")
    eng.execute_action("physical_exam_focused:neuro")
    eng.execute_action("order_labs:cbc")
    eng.execute_action("order_imaging:ct_head")
    eng.execute_action("wait:30")
    eng.execute_action("wait:15")
    state = eng.get_state()
    assert state.current_time_minutes == 74
    assert "eosinophilia" in state.flags
    assert "ring_enhancing_lesion" in state.flags
    assert "diagnosis_confirmed" not in state.flags


def _wait_until_end(eng: SatoriEngine, step: int = 60, max_steps: int = 10) -> None:
    for _ in range(max_steps):
        if eng.get_state().case_ended:
            return
        eng.execute_action(f"wait:{step}")
    raise AssertionError(f"Case did not end within {max_steps} wait:{step} steps")


# ---------------------------------------------------------------------------
# Scenario: inaction — the authored 180-minute clock holds
# ---------------------------------------------------------------------------


class TestInactionTimeline:
    def test_progression_clock_is_not_pre_accelerated(self, engine: SatoriEngine) -> None:
        """The C-1 regression: with no steroids given, node_09 must still
        hold its full authored timeline at t=75. Pre-fix, the always-active
        rebound node had already stolen 60 minutes by now (remaining 60)."""
        engine.execute_action("history_general")  # t=15, node_09 starts at 180
        engine.execute_action("wait:60")  # t=75
        state = engine.get_state()
        assert state.current_time_minutes == 75
        assert state.timers["node_09_headache_progression"] == 120
        assert "steroid_rebound" not in state.flags
        assert "wrong_treatment_steroids" not in state.flags

    def test_crisis_fires_on_the_authored_clock_and_death_follows(self, engine: SatoriEngine) -> None:
        """node_09 expires at t=195 (15 + 180); the crisis activates on that
        tick; the untreated crisis is fatal and scores failure."""
        engine.execute_action("history_general")  # t=15
        for _ in range(3):  # t=75, 135, 195
            engine.execute_action("wait:60")
        state = engine.get_state()
        assert state.current_time_minutes == 195
        assert "node_14_seizure_crisis" in state.active_nodes
        assert not state.case_ended

        _wait_until_end(engine, step=15)
        state = engine.get_state()
        assert "patient_death" in state.flags
        assert state.outcome_tier == "failure"

    def test_crisis_does_not_fire_early(self, engine: SatoriEngine) -> None:
        """At t=135 (where the pre-fix accelerated clock produced the crisis)
        the crisis node must not be active."""
        engine.execute_action("history_general")  # t=15
        engine.execute_action("wait:60")  # t=75
        engine.execute_action("wait:60")  # t=135
        state = engine.get_state()
        assert "node_14_seizure_crisis" not in state.active_nodes
        assert not state.case_ended


# ---------------------------------------------------------------------------
# Scenario: empirical treatment on suspicion -> GOOD
# ---------------------------------------------------------------------------


class TestEmpiricalPath:
    def test_empirical_treatment_scores_good(self, engine: SatoriEngine) -> None:
        _open_to_empirical_unlock(engine)
        engine.execute_action("wait:15")  # t=89 (mirror of audit trace)
        engine.execute_action("start_treatment:albendazole")  # t=94
        state = engine.get_state()
        assert state.case_ended
        assert "correct_treatment_started" in state.flags
        assert "diagnosis_confirmed" not in state.flags
        assert state.outcome_tier == "good"


# ---------------------------------------------------------------------------
# Scenario: confirmed diagnosis + family engagement -> OPTIMAL
# ---------------------------------------------------------------------------


class TestConfirmedPath:
    def test_confirmed_rigorous_path_scores_optimal(self, engine: SatoriEngine) -> None:
        """The rigor path: confirm via thigh X-ray (calcified cysticerci)
        with the family visit overlapped into result-delay windows, landing
        treatment inside the 120-minute OPTIMAL constraint.

        t=0   history_general              -> 15
        t=15  physical_exam_focused:neuro  -> 25
        t=25  order_labs:cbc               -> 27  (due 57)
        t=27  order_imaging:ct_head        -> 29  (due 74)
        t=29  wait:30                      -> 59  (cbc reveals: eosinophilia)
        t=59  history_focused:dietary      -> 69  (pork exposure; xray unlocks)
        t=69  wait:15                      -> 84  (CT reveals at 74)
        t=84  order_imaging_xray:extremity -> 86  (due 106)
        t=86  history_focused:family       -> 96  (family_engaged)
        t=96  wait:15                      -> 111 (xray reveals: confirmed)
        t=111 start_treatment:albendazole  -> 116 (< 120)
        """
        engine.execute_action("history_general")
        engine.execute_action("physical_exam_focused:neuro")
        engine.execute_action("order_labs:cbc")
        engine.execute_action("order_imaging:ct_head")
        engine.execute_action("wait:30")
        engine.execute_action("history_focused:dietary")
        engine.execute_action("wait:15")
        engine.execute_action("order_imaging_xray:extremity")
        engine.execute_action("history_focused:family")
        engine.execute_action("wait:15")
        state = engine.get_state()
        assert "diagnosis_confirmed" in state.flags
        assert "family_engaged" in state.flags

        engine.execute_action("start_treatment:albendazole")
        state = engine.get_state()
        assert state.case_ended
        assert state.current_time_minutes == 116
        assert state.outcome_tier == "optimal"


# ---------------------------------------------------------------------------
# Scenario: steroids — the rebound fires at administration + 60, not before
# ---------------------------------------------------------------------------


class TestSteroidsPath:
    def test_rebound_fires_sixty_minutes_after_administration(self, engine: SatoriEngine) -> None:
        """Steroids given at t=74 (done t=79): the rebound must NOT have
        touched node_09 at t=124, and must have stolen 60 minutes once the
        rebound timer expires at t=139."""
        _open_to_empirical_unlock(engine)
        engine.execute_action("start_treatment:steroids")  # t=79
        state = engine.get_state()
        assert "wrong_treatment_steroids" in state.flags

        for _ in range(3):  # t=94, 109, 124
            engine.execute_action("wait:15")
        state = engine.get_state()
        assert state.current_time_minutes == 124
        # Untouched authored clock: 180 - (124 - 15) = 71
        assert state.timers["node_09_headache_progression"] == 71

        engine.execute_action("wait:15")  # t=139: rebound expires, -60
        state = engine.get_state()
        # 180 - (139 - 15) = 56, minus the 60-minute rebound, clamped at 0
        assert state.timers["node_09_headache_progression"] == 0

    def test_untreated_steroid_run_is_fatal(self, engine: SatoriEngine) -> None:
        _open_to_empirical_unlock(engine)
        engine.execute_action("start_treatment:steroids")  # t=79
        _wait_until_end(engine, step=15, max_steps=12)
        state = engine.get_state()
        assert "patient_death" in state.flags
        assert state.outcome_tier == "failure"

    def test_steroids_then_correct_treatment_scores_partial(self, engine: SatoriEngine) -> None:
        _open_to_empirical_unlock(engine)
        engine.execute_action("start_treatment:steroids")  # t=79
        engine.execute_action("start_treatment:albendazole")  # t=84
        state = engine.get_state()
        assert state.case_ended
        assert "correct_treatment_started" in state.flags
        assert state.outcome_tier == "partial"


# ---------------------------------------------------------------------------
# Scenario: treatment without evidence is blocked
# ---------------------------------------------------------------------------


class TestTreatmentBlocked:
    def test_treatment_locked_at_case_start(self, engine: SatoriEngine) -> None:
        with pytest.raises(InvalidActionError, match="locked"):
            engine.execute_action("start_treatment:albendazole")

    def test_steroids_also_locked_at_case_start(self, engine: SatoriEngine) -> None:
        with pytest.raises(InvalidActionError, match="locked"):
            engine.execute_action("start_treatment:steroids")
