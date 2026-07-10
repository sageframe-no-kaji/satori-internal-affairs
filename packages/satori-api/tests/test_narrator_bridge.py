"""Tests for the narrator bridge."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from satori import Event, SatoriEngine
from satori.models import validate_case

from satori_api.narrator_bridge import _describe_event, narrate_events

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"


@pytest.fixture(scope="module")
def engine() -> SatoriEngine:
    case = validate_case(EXAMPLE_CASE)
    return SatoriEngine(case)


def _fresh() -> tuple[SatoriEngine, Sequence[Event]]:
    """Return a fresh engine and the events from its first available action."""
    case = validate_case(EXAMPLE_CASE)
    eng = SatoriEngine(case)
    available = list(eng.get_available_actions())
    assert available, "No actions available in initial state"
    return eng, eng.execute_action(available[0])


def test_narrate_events_empty_list(engine: SatoriEngine):
    result = narrate_events([], engine)
    assert result == []


def test_narrate_events_returns_one_per_event(engine: SatoriEngine):
    eng, events = _fresh()
    narrations = narrate_events(list(events), eng)
    assert len(narrations) == len(events)


def test_narrate_events_are_non_empty_strings(engine: SatoriEngine):
    eng, events = _fresh()
    narrations = narrate_events(list(events), eng)
    for n in narrations:
        assert isinstance(n, str)
        assert len(n) > 0


def test_mock_narrator_output_contains_mock_prefix(engine: SatoriEngine):
    """MockNarrator always tags output with [Mock Narration]."""
    eng, events = _fresh()
    narrations = narrate_events(list(events), eng)
    for n in narrations:
        assert "[Mock Narration]" in n


def test_mock_narrator_output_contains_patient_name(engine: SatoriEngine):
    """MockNarrator embeds the patient name in every narration."""
    eng, events = _fresh()
    narrations = narrate_events(list(events), eng)
    for n in narrations:
        assert "Maria Santos" in n


def test_describe_event_time_advanced():
    from satori import TimeAdvancedEvent

    event = TimeAdvancedEvent(timestamp_minutes=5, old_time=0, new_time=5, cause="action")
    desc, data = _describe_event(event)
    assert "0" in desc and "5" in desc
    assert data is not None
    assert data["old_time"] == 0
    assert data["new_time"] == 5


def test_describe_event_node_revealed():
    from satori import NodeRevealedEvent

    event = NodeRevealedEvent(
        timestamp_minutes=5,
        node_id="test_node",
        node_type="lab_result",
        content_text="The result is positive.",
        structured_data={"key": "val"},
    )
    desc, data = _describe_event(event)
    assert desc == "The result is positive."
    assert data == {"key": "val"}


def test_describe_event_case_ended():
    from satori import CaseEndedEvent

    event = CaseEndedEvent(
        timestamp_minutes=60,
        outcome_tier="optimal",
        end_reason="Patient stabilised and discharged.",
    )
    desc, data = _describe_event(event)
    assert "optimal" in desc
    assert data is not None
    assert data["outcome_tier"] == "optimal"
    assert data["end_reason"] == "Patient stabilised and discharged."


def test_describe_event_fallback():
    """Fallback branch returns a safe (str, None) for any unrecognised event type."""
    from unittest.mock import MagicMock

    # Build a mock that pretends to be an Event but doesn't match any isinstance check
    mock_event = MagicMock()
    mock_event.type = MagicMock()
    mock_event.type.__str__ = lambda _: "future_event"

    # isinstance checks against the real classes will return False for a MagicMock
    desc, data = _describe_event(mock_event)
    assert isinstance(desc, str)
    assert len(desc) > 0
    assert data is None


# ---------------------------------------------------------------------------
# Narration failure isolation (audit C-5 / S4)
# ---------------------------------------------------------------------------


class _RaisingNarrator:
    """Stand-in for a live narrator whose provider call fails."""

    def narrate(self, event: object, context: object) -> str:
        raise RuntimeError("provider timeout")


def test_narrator_failure_degrades_to_description(monkeypatch: pytest.MonkeyPatch):
    """A raising narrator must never propagate: each event degrades to its
    plain description string (the Narration Line — cosmetic, strippable)."""
    import satori_api.narrator_bridge as bridge

    monkeypatch.setattr(bridge, "_narrator", _RaisingNarrator())
    eng, events = _fresh()
    narrations = narrate_events(list(events), eng)

    assert len(narrations) == len(events)
    for narration, event in zip(narrations, events, strict=True):
        expected_description, _ = _describe_event(event)
        assert narration == expected_description


def test_action_endpoint_survives_narrator_failure(monkeypatch: pytest.MonkeyPatch):
    """Gameplay must return 200 with advanced state even when the narrator
    raises after the engine has committed the action (audit C-5)."""
    from fastapi.testclient import TestClient

    import satori_api.narrator_bridge as bridge
    from satori_api.main import app

    monkeypatch.setattr(bridge, "_narrator", _RaisingNarrator())
    client = TestClient(app)

    created = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    assert created.status_code == 201, created.text
    session_id = created.json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/actions",
        json={"action": "history_general"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["state"]["current_time_minutes"] > 0
    assert len(payload["narrations"]) == len(payload["events"])


# ---------------------------------------------------------------------------
# Narration cache (P2-H08)
# ---------------------------------------------------------------------------


class _CountingNarrator:
    """Counts narrate calls; returns a distinct string per call."""

    def __init__(self) -> None:
        self.calls = 0

    def narrate(self, event: object, context: object) -> str:
        self.calls += 1
        return f"narration-{self.calls}"


def _fresh_with_reveal() -> tuple[SatoriEngine, list[Event]]:
    """Deterministic node-bearing events: history_general reveals node_01.
    (_fresh() picks list(frozenset)[0] — hash-seed-dependent, and some
    actions produce no node events.)"""
    case = validate_case(EXAMPLE_CASE)
    eng = SatoriEngine(case)
    return eng, list(eng.execute_action("history_general"))


def test_cache_reuses_narration_for_repeated_node_events(monkeypatch: pytest.MonkeyPatch):
    import satori_api.narrator_bridge as bridge

    counting = _CountingNarrator()
    monkeypatch.setattr(bridge, "_narrator", counting)
    eng, events = _fresh_with_reveal()
    node_events = [e for e in events if hasattr(e, "node_id")]
    assert node_events, "expected at least one node-bearing event"

    cache: dict[tuple[str, str], str] = {}
    first = narrate_events(node_events, eng, cache)
    calls_after_first = counting.calls
    second = narrate_events(node_events, eng, cache)

    assert counting.calls == calls_after_first  # every repeat was a cache hit
    assert second == first


def test_no_cache_means_no_reuse(monkeypatch: pytest.MonkeyPatch):
    import satori_api.narrator_bridge as bridge

    counting = _CountingNarrator()
    monkeypatch.setattr(bridge, "_narrator", counting)
    eng, events = _fresh_with_reveal()
    node_events = [e for e in events if hasattr(e, "node_id")]
    assert node_events, "expected at least one node-bearing event"

    narrate_events(node_events, eng)
    calls_after_first = counting.calls
    narrate_events(node_events, eng)
    assert counting.calls == calls_after_first * 2


def test_fallback_strings_are_not_cached(monkeypatch: pytest.MonkeyPatch):
    """A transient provider failure must not pin the templated text for the
    rest of the session — the next occurrence retries the narrator."""
    import satori_api.narrator_bridge as bridge

    counting = _CountingNarrator()
    monkeypatch.setattr(bridge, "_narrator", _RaisingNarrator())
    eng, events = _fresh_with_reveal()
    node_events = [e for e in events if hasattr(e, "node_id")]
    assert node_events, "expected at least one node-bearing event"

    cache: dict[tuple[str, str], str] = {}
    narrate_events(node_events, eng, cache)
    assert cache == {}  # nothing pinned

    monkeypatch.setattr(bridge, "_narrator", counting)
    narrations = narrate_events(node_events, eng, cache)
    assert counting.calls > 0  # retried live
    assert all(n.startswith("narration-") for n in narrations)


# ---------------------------------------------------------------------------
# Env-driven narrator construction (P2-H08)
# ---------------------------------------------------------------------------


def test_env_default_is_mock(monkeypatch: pytest.MonkeyPatch):
    from llm_client.mock import MockNarrator

    from satori_api.narrator_bridge import _narrator_from_env

    monkeypatch.delenv("SATORI_NARRATOR_PROVIDER", raising=False)
    assert isinstance(_narrator_from_env(), MockNarrator)


def test_env_anthropic_with_key_builds_live_narrator(monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("anthropic")
    from llm_client.anthropic_narrator import AnthropicNarrator

    from satori_api.narrator_bridge import _narrator_from_env

    monkeypatch.setenv("SATORI_NARRATOR_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("SATORI_NARRATOR_MODEL", raising=False)
    narrator = _narrator_from_env()
    assert isinstance(narrator, AnthropicNarrator)
    assert narrator.config.model == "claude-sonnet-4-6"


def test_env_anthropic_without_key_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch):
    from llm_client.mock import MockNarrator

    from satori_api.narrator_bridge import _narrator_from_env

    monkeypatch.setenv("SATORI_NARRATOR_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(_narrator_from_env(), MockNarrator)


def test_env_unknown_provider_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch):
    from llm_client.mock import MockNarrator

    from satori_api.narrator_bridge import _narrator_from_env

    monkeypatch.setenv("SATORI_NARRATOR_PROVIDER", "grok")
    assert isinstance(_narrator_from_env(), MockNarrator)
