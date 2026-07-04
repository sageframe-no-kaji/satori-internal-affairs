"""Crisis rescue, re-arm, and fallthrough-tier tests (P2-H09).

Before P2-H09, node_14_seizure_crisis was unsurvivable: its 5-minute timer
activated node_16_patient_death and the emergency_intervention action was
referenced by nothing — 2 spent minutes that punished the correct instinct.
These tests pin the survivable-crisis mechanic end to end:

- emergency_intervention deactivates the active crisis, sets crisis_managed,
  clears crisis_active, and unlocks the four investigation actions.
- crisis_managed activates node_20_post_crisis_progression (90-minute
  non-diegetic re-arm clock) which expires into a DISTINCT second crisis
  (node_21) that takes the same rescue — the mechanic must not lie the
  second time.
- Death remains reachable from both crises when unrescued.
- GameState.emergency_timer carries the active crisis countdown through the
  separate visibility channel and is None otherwise (including case end).
- The untreated T+360 timeout lands in the fallthrough failure tier with a
  truthful narrative — not the death narrative.

Timeline arithmetic (authored case data): history_general costs 15 min and
starts node_09's 180-minute clock, so the first crisis fires at t=195;
emergency_intervention costs 2 min; node_20 runs 90 minutes from the rescue
tick, so the second crisis fires during the wait that crosses rescue+90.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from satori.engine import SatoriEngine
from satori.game_state import CRISIS_FLAG, compute_emergency_timer
from satori.models.case_definition import CaseDefinition

INVESTIGATION_ACTIONS = (
    "history_general",
    "history_focused",
    "physical_exam_general",
    "physical_exam_focused",
)


@pytest.fixture(scope="module")
def case_def() -> CaseDefinition:
    case_path = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"
    with open(case_path, encoding="utf-8") as f:
        data = json.load(f)
    return CaseDefinition.model_validate(data)


@pytest.fixture
def engine(case_def: CaseDefinition) -> SatoriEngine:
    return SatoriEngine(case_def)


def _drive_to_first_crisis(eng: SatoriEngine) -> None:
    """history_general (t=15, node_09 starts) + 3x wait:60 -> crisis at t=195."""
    eng.execute_action("history_general")
    for _ in range(3):
        eng.execute_action("wait:60")
    state = eng.get_state()
    assert state.current_time_minutes == 195
    assert "node_14_seizure_crisis" in state.active_nodes
    assert CRISIS_FLAG in state.flags


def _rescue(eng: SatoriEngine) -> None:
    eng.execute_action("emergency_intervention")


class TestFirstCrisisRescue:
    def test_intervention_deactivates_the_crisis(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)
        state = engine.get_state()
        assert state.current_time_minutes == 197
        assert "node_14_seizure_crisis" not in state.active_nodes
        assert "node_14_seizure_crisis" not in state.timers
        assert CRISIS_FLAG not in state.flags
        assert "crisis_managed" in state.flags
        assert not state.case_ended

    def test_intervention_unlocks_the_four_investigation_actions(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        state = engine.get_state()
        for action in INVESTIGATION_ACTIONS:
            assert action not in state.available_actions, f"{action} should be locked during the crisis"
        _rescue(engine)
        state = engine.get_state()
        for action in INVESTIGATION_ACTIONS:
            assert action in state.available_actions, f"{action} should be unlocked after rescue"

    def test_vitals_recover_from_crisis_values_after_rescue(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        state = engine.get_state()
        # node_14's crisis vitals dominate worst-wins
        assert state.current_vitals.heart_rate == 148
        assert state.current_vitals.o2_saturation == 86
        _rescue(engine)
        state = engine.get_state()
        # node_14 gone; node_20 (post-crisis, stabilized-but-sick) now carries the picture
        assert state.current_vitals.heart_rate == 108
        assert state.current_vitals.o2_saturation == 95

    def test_intervention_outside_a_crisis_is_a_legal_no_op(self, engine: SatoriEngine) -> None:
        engine.execute_action("emergency_intervention")
        state = engine.get_state()
        assert state.current_time_minutes == 2
        assert "crisis_managed" not in state.flags
        assert not state.case_ended


class TestReArm:
    def test_rescue_starts_the_post_crisis_clock(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)
        state = engine.get_state()
        assert "node_20_post_crisis_progression" in state.active_nodes
        assert state.timers["node_20_post_crisis_progression"] == 90

    def test_post_crisis_clock_expires_into_a_distinct_second_crisis(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)  # t=197; node_20 expires at t=287
        engine.execute_action("wait:60")  # t=257
        state = engine.get_state()
        assert CRISIS_FLAG not in state.flags
        engine.execute_action("wait:60")  # t=317, crossing 287: node_21 activates
        state = engine.get_state()
        assert "node_21_second_seizure_crisis" in state.active_nodes
        assert "node_21_second_seizure_crisis" in state.revealed_nodes
        assert "node_14_seizure_crisis" not in state.active_nodes
        assert CRISIS_FLAG in state.flags
        for action in INVESTIGATION_ACTIONS:
            assert action not in state.available_actions, f"{action} should re-lock in the second crisis"
        # The second crisis is authored worse than the first
        assert state.current_vitals.heart_rate == 152
        assert state.current_vitals.o2_saturation == 84

    def test_second_crisis_takes_the_same_rescue(self, engine: SatoriEngine) -> None:
        """The mechanic must not lie the second time."""
        _drive_to_first_crisis(engine)
        _rescue(engine)
        engine.execute_action("wait:60")
        engine.execute_action("wait:60")  # second crisis active
        _rescue(engine)  # t=319
        state = engine.get_state()
        assert "node_21_second_seizure_crisis" not in state.active_nodes
        assert "node_21_second_seizure_crisis" not in state.timers
        assert CRISIS_FLAG not in state.flags
        assert "second_crisis_managed" in state.flags
        assert not state.case_ended
        for action in INVESTIGATION_ACTIONS:
            assert action in state.available_actions

    def test_no_third_clock_after_the_second_rescue(self, engine: SatoriEngine) -> None:
        """node_20 activates once (expired nodes stay active); after the second
        rescue no progression timer remains — the run can only time out."""
        _drive_to_first_crisis(engine)
        _rescue(engine)
        engine.execute_action("wait:60")
        engine.execute_action("wait:60")
        _rescue(engine)
        state = engine.get_state()
        assert state.timers == {}


class TestDeathStillReachable:
    def test_unrescued_first_crisis_is_fatal(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        engine.execute_action("wait:15")  # crisis timer (5) expires mid-wait
        state = engine.get_state()
        assert state.case_ended
        assert "patient_death" in state.flags
        assert state.outcome_tier == "failure"
        # The death tier's own narrative, recorded from the matched tier
        assert state.outcome_narrative is not None
        assert "died" in state.outcome_narrative

    def test_unrescued_second_crisis_is_fatal(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)
        engine.execute_action("wait:60")
        engine.execute_action("wait:60")  # second crisis active, 5-minute clock
        engine.execute_action("wait:15")
        state = engine.get_state()
        assert state.case_ended
        assert "patient_death" in state.flags
        assert state.outcome_tier == "failure"


class TestEmergencyTimerChannel:
    def test_none_at_case_start(self, engine: SatoriEngine) -> None:
        assert engine.get_state().emergency_timer is None

    def test_none_before_the_crisis(self, engine: SatoriEngine) -> None:
        engine.execute_action("history_general")
        engine.execute_action("wait:60")
        assert engine.get_state().emergency_timer is None

    def test_carries_the_first_crisis_clock_exactly(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        et = engine.get_state().emergency_timer
        assert et is not None
        assert et.node_id == "node_14_seizure_crisis"
        assert et.remaining_minutes == 5  # exact, not approximated — the player races it
        assert et.source == "active_timer"

    def test_cleared_by_rescue(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)
        assert engine.get_state().emergency_timer is None

    def test_carries_the_second_crisis_clock(self, engine: SatoriEngine) -> None:
        _drive_to_first_crisis(engine)
        _rescue(engine)
        engine.execute_action("wait:60")
        engine.execute_action("wait:60")
        et = engine.get_state().emergency_timer
        assert et is not None
        assert et.node_id == "node_21_second_seizure_crisis"
        assert et.remaining_minutes == 5

    def test_none_on_death_even_with_crisis_flag_still_set(self, engine: SatoriEngine) -> None:
        """crisis_active survives into the death state; the outcome screen must
        not render in emergency dress (memo §2: crisis flag AND NOT case_ended)."""
        _drive_to_first_crisis(engine)
        engine.execute_action("wait:15")
        state = engine.get_state()
        assert state.case_ended
        assert CRISIS_FLAG in state.flags
        assert state.emergency_timer is None

    def test_crisis_timer_stays_out_of_visible_timers(self, engine: SatoriEngine) -> None:
        """The diegetic channel stays semantically clean."""
        _drive_to_first_crisis(engine)
        state = engine.get_state()
        assert all(vt.node_id != "node_14_seizure_crisis" for vt in state.visible_timers)

    def test_derivation_is_pure_and_deterministic(self, engine: SatoriEngine, case_def: CaseDefinition) -> None:
        _drive_to_first_crisis(engine)
        state = engine.get_state()
        assert compute_emergency_timer(state, case_def) == state.emergency_timer


class TestTimeoutFallthroughTier:
    def test_double_rescue_then_timeout_lands_the_fallthrough_tier(self, engine: SatoriEngine) -> None:
        """Two survived crises, no treatment: the T+360 limit ends the case in
        the failure register with the truthful transferred-alive narrative —
        previously this run matched no tier and showed the death narrative."""
        _drive_to_first_crisis(engine)
        _rescue(engine)  # t=197
        engine.execute_action("wait:60")  # t=257
        engine.execute_action("wait:60")  # t=317, second crisis
        _rescue(engine)  # t=319
        engine.execute_action("wait:60")  # t=379 >= 360
        state = engine.get_state()
        assert state.case_ended
        assert state.current_time_minutes == 379
        assert "patient_death" not in state.flags
        assert state.outcome_tier == "failure"
        assert state.end_reason is not None
        assert "Time limit" in state.end_reason
        assert state.outcome_narrative is not None
        assert "died" not in state.outcome_narrative
        assert "transferred" in state.outcome_narrative
