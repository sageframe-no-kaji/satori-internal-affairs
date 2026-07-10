"""Tests for narration prompt assembly (P2-H08 plumbing).

Pins the template STRUCTURE — the placeholder voice is deliberately not
pinned beyond its hard rules, since the voice document replaces it.
"""

from __future__ import annotations

import pytest

from llm_client.interfaces import NarrationContext, NarrationEvent
from llm_client.narration_prompts import EVENT_GUIDANCE, build_system_prompt, build_user_prompt

CONTEXT = NarrationContext(
    patient_name="Maria Santos",
    patient_age=28,
    patient_sex="female",
    setting="Emergency Department",
    current_vitals={"heart_rate": 92, "o2_saturation": 97},
    elapsed_minutes=15,
)

EVENT = NarrationEvent(
    event_type="node_revealed",
    description="Eosinophils 8% (normal 1 to 3%).",
    structured_data={"eosinophils_flag": "HIGH"},
)


def test_system_prompt_is_nonempty_and_carries_the_hard_rules():
    prompt = build_system_prompt()
    assert len(prompt) > 0
    # The boundaries survive any voice replacement — these are load-bearing
    assert "Never diagnose" in prompt or "never diagnose" in prompt.lower()
    assert "foreshadow" in prompt.lower()


def test_user_prompt_carries_event_and_context_facts():
    prompt = build_user_prompt(EVENT, CONTEXT)
    assert "Maria Santos" in prompt
    assert "Emergency Department" in prompt
    assert "15 minutes" in prompt
    assert "Eosinophils 8%" in prompt
    assert "node_revealed" in prompt
    assert "eosinophils_flag=HIGH" in prompt
    assert "heart_rate=92" in prompt


def test_user_prompt_omits_empty_sections():
    event = NarrationEvent(event_type="waited", description="30 minutes pass.")
    context = NarrationContext(
        patient_name="Maria Santos",
        patient_age=28,
        patient_sex="female",
        setting="Emergency Department",
        current_vitals={},
        elapsed_minutes=45,
    )
    prompt = build_user_prompt(event, context)
    assert "Current vitals" not in prompt
    assert "Event data" not in prompt


def test_event_guidance_slot_is_appended_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(EVENT_GUIDANCE, "node_revealed", "GUIDANCE-SENTINEL")
    assert "GUIDANCE-SENTINEL" in build_user_prompt(EVENT, CONTEXT)


def test_guidance_covers_every_bridge_event_type():
    """The slots exist for exactly the event surface the bridge narrates."""
    expected = {
        "node_revealed",
        "node_activated",
        "node_expired",
        "timer_stage",
        "vitals_changed",
        "waited",
        "time_advanced",
        "flag_set",
        "flag_cleared",
        "action_unlocked",
        "action_locked",
        "pending_reveal_started",
        "case_ended",
    }
    assert set(EVENT_GUIDANCE) == expected
