"""Tests for satori-api sessions, actions, and response shapes."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from satori_api import session_manager
from satori_api.main import app

EXAMPLE_CASE = "cases/example-neurocysticercosis.json"

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions() -> Generator[None, None, None]:
    """Reset session store between tests to prevent leakage."""
    session_manager._sessions.clear()
    yield
    session_manager._sessions.clear()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "active_sessions" in data
    assert data["active_sessions"] == 0


def test_health_reflects_session_count():
    client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    data = client.get("/health").json()
    assert data["active_sessions"] == 1


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------


def test_create_session_success():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert isinstance(data["session_id"], str)
    assert len(data["session_id"]) > 0


def test_create_session_returns_full_state():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    data = resp.json()
    # Must be self-contained
    assert "state" in data
    assert "patient" in data
    assert "patient_condition" in data
    assert "available_actions" in data


def test_create_session_state_shape():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    state = resp.json()["state"]
    assert "case_id" in state
    assert "current_time_minutes" in state
    assert isinstance(state["flags"], list)
    assert isinstance(state["active_nodes"], list)
    assert isinstance(state["revealed_nodes"], list)
    assert isinstance(state["expired_nodes"], list)
    assert isinstance(state["available_actions"], list)
    assert isinstance(state["case_ended"], bool)
    assert state["case_ended"] is False


def test_create_session_patient_shape():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    patient = resp.json()["patient"]
    assert patient["name"] == "Maria Santos"
    assert patient["age"] == 28
    assert patient["sex"] == "female"
    assert "chief_complaint" in patient
    assert "appearance" in patient
    assert "arriving_vitals" in patient


def test_create_session_available_actions_is_list():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    data = resp.json()
    assert isinstance(data["available_actions"], list)
    assert len(data["available_actions"]) > 0


def test_create_session_patient_condition_is_valid():
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    condition = resp.json()["patient_condition"]
    valid = {"stable", "compensating", "decompensating", "critical", "dead", "recovered"}
    assert condition in valid


def test_create_session_bad_path():
    resp = client.post("/api/sessions", json={"case_path": "nonexistent.json"})
    assert resp.status_code == 400


def test_create_session_increments_session_count():
    assert session_manager.session_count() == 0
    client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    assert session_manager.session_count() == 1
    client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    assert session_manager.session_count() == 2


# ---------------------------------------------------------------------------
# GET session
# ---------------------------------------------------------------------------


def test_get_session_returns_same_state():
    post_resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    session_id = post_resp.json()["session_id"]

    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    # State should be identical (no action taken)
    assert post_resp.json()["state"] == get_resp.json()["state"]


def test_get_session_not_found():
    resp = client.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE session
# ---------------------------------------------------------------------------


def test_delete_session():
    post_resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    session_id = post_resp.json()["session_id"]
    del_resp = client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 204
    # Should be gone now
    assert client.get(f"/api/sessions/{session_id}").status_code == 404


def test_delete_session_idempotent():
    resp = client.delete("/api/sessions/does-not-exist")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


def _start_session() -> str:
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    return str(resp.json()["session_id"])


def _get_first_action(session_id: str) -> str:
    resp = client.get(f"/api/sessions/{session_id}")
    actions: list[str] = resp.json()["available_actions"]
    assert len(actions) > 0, "No actions available in initial state"
    return actions[0]


def test_execute_action_success():
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    assert resp.status_code == 200


def test_execute_action_response_shape():
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    data = resp.json()
    assert "events" in data
    assert "narrations" in data
    assert "state" in data
    assert "patient_condition" in data
    assert "available_actions" in data
    assert "case_ended" in data
    assert isinstance(data["events"], list)
    assert isinstance(data["narrations"], list)


def test_execute_action_narrations_parallel_to_events():
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    data = resp.json()
    # narrations list must be same length as events list
    assert len(data["narrations"]) == len(data["events"])


def test_execute_action_narrations_are_strings():
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    for narration in resp.json()["narrations"]:
        assert isinstance(narration, str)
        assert len(narration) > 0


def test_execute_action_advances_time():
    sid = _start_session()
    initial_time = client.get(f"/api/sessions/{sid}").json()["state"]["current_time_minutes"]
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    new_time = resp.json()["state"]["current_time_minutes"]
    assert new_time > initial_time  # every action must consume game time


def test_execute_action_state_is_self_contained():
    """After an action, the response state + available_actions must be complete."""
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    data = resp.json()
    # state.available_actions and top-level available_actions must match
    assert sorted(data["state"]["available_actions"]) == sorted(data["available_actions"])


def test_execute_action_response_has_outcome_fields():
    """ActionResponse must always carry outcome_tier and end_reason (null when game ongoing)."""
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    data = resp.json()
    assert "outcome_tier" in data
    assert "end_reason" in data
    # Game not ended yet — both should be null
    assert data["case_ended"] is False
    assert data["outcome_tier"] is None
    assert data["end_reason"] is None


def test_execute_action_state_contains_gamestate_subfields():
    """GameStateResponse must include pending_reveals and timers dict fields."""
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    state = resp.json()["state"]
    assert "pending_reveals" in state
    assert "timers" in state
    assert "timer_stages" in state
    assert isinstance(state["pending_reveals"], dict)
    assert isinstance(state["timers"], dict)
    assert isinstance(state["timer_stages"], dict)


def test_execute_action_invalid():
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "this_is_not_valid"})
    assert resp.status_code == 400


def test_execute_action_session_not_found():
    resp = client.post("/api/sessions/ghost/actions", json={"action": "history_general"})
    assert resp.status_code == 404


def test_event_response_shape():
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    events = resp.json()["events"]
    # Every action must emit at least one event (at minimum a time_advanced)
    assert len(events) > 0, "Expected at least one event from a valid action"
    event = events[0]
    assert "type" in event
    assert "timestamp_minutes" in event
    assert "data" in event
    assert isinstance(event["type"], str)
    assert isinstance(event["timestamp_minutes"], int)
    assert isinstance(event["data"], dict)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_two_identical_action_sequences_produce_identical_states():
    """Core determinism contract: same case + same actions = same outcome."""

    def run_sequence(actions: list[str]) -> dict:  # type: ignore[type-arg]
        sid = _start_session()
        state = None
        for action in actions:
            resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
            assert resp.status_code == 200, f"Action '{action}' failed: {resp.text}"
            state = resp.json()["state"]
        return state  # type: ignore[return-value]

    # Get the first two available actions from a fresh session to use as sequence
    sid_probe = _start_session()
    actions_probe = client.get(f"/api/sessions/{sid_probe}").json()["available_actions"]
    # Use at most 2 actions; fewer if not enough are available
    sequence = actions_probe[:2]
    if not sequence:
        pytest.skip("No actions available in initial state")

    state_a = run_sequence(sequence)
    state_b = run_sequence(sequence)
    assert state_a == state_b


# ---------------------------------------------------------------------------
# playable_actions field
# ---------------------------------------------------------------------------


def test_create_session_returns_playable_actions():
    """SessionResponse must include a playable_actions list."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    data = resp.json()
    assert "playable_actions" in data
    assert isinstance(data["playable_actions"], list)
    assert len(data["playable_actions"]) > 0


def test_initial_playable_actions_content():
    """At game start playable_actions must contain exactly the three root actions."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    playable = set(resp.json()["playable_actions"])
    assert playable == {"history_general", "physical_exam_general", "emergency_intervention"}


def test_execute_action_response_has_playable_actions():
    """ActionResponse must include a playable_actions list."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    data = resp.json()
    assert "playable_actions" in data
    assert isinstance(data["playable_actions"], list)


def test_playable_actions_updates_after_history_general():
    """After history_general, subcategory actions must surface and history_general must drop."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    playable = set(resp.json()["playable_actions"])
    # Subcategory actions must appear
    assert "order_labs:cbc" in playable
    assert "order_labs:metabolic_panel" in playable
    assert "history_focused:medications" in playable
    assert "physical_exam_focused:neuro" in playable
    # history_general must drop — node_01 is now revealed
    assert "history_general" not in playable
    # physical_exam_general still available (not yet revealed)
    assert "physical_exam_general" in playable


def test_get_session_returns_playable_actions():
    """GET /api/sessions/{id} must also include playable_actions."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    sid = resp.json()["session_id"]
    get_resp = client.get(f"/api/sessions/{sid}")
    assert "playable_actions" in get_resp.json()


# ---------------------------------------------------------------------------
# Node content
# ---------------------------------------------------------------------------


def test_get_node_content_session_not_found():
    resp = client.get("/api/sessions/ghost/nodes/some_node")
    assert resp.status_code == 404


def test_get_unrevealed_node_returns_404():
    sid = _start_session()
    resp = client.get(f"/api/sessions/{sid}/nodes/nonexistent_node_id")
    assert resp.status_code == 404


def test_get_revealed_node_after_action():
    """After an action that reveals a node, the content endpoint should work."""
    sid = _start_session()
    # Execute actions until we get a NodeRevealed event
    available = client.get(f"/api/sessions/{sid}").json()["available_actions"]
    revealed_node_id: str | None = None
    for action in available:
        resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
        if resp.status_code == 200:
            for event in resp.json()["events"]:
                if event["type"] == "node_revealed":
                    revealed_node_id = event["data"].get("node_id")
                    break
        if revealed_node_id:
            break

    if not revealed_node_id:
        pytest.skip("No node was revealed by available actions — try a longer sequence")

    content_resp = client.get(f"/api/sessions/{sid}/nodes/{revealed_node_id}")
    assert content_resp.status_code == 200
    data = content_resp.json()
    assert data["node_id"] == revealed_node_id
    assert isinstance(data["narrative_text"], str)
    assert len(data["narrative_text"]) > 0, "narrative_text must not be empty"
    assert "structured_data" in data
    assert len(data["narrative_text"]) > 0


# ---------------------------------------------------------------------------
# visible_timers in API responses
# ---------------------------------------------------------------------------


def test_create_session_state_has_visible_timers():
    """POST /api/sessions response state must include visible_timers list."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    state = resp.json()["state"]
    assert "visible_timers" in state
    assert isinstance(state["visible_timers"], list)


def test_initial_visible_timers_empty():
    """At game start, visible_timers is empty (no pending reveals, no diegetic timers)."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    state = resp.json()["state"]
    assert state["visible_timers"] == []


def test_visible_timers_populated_after_lab_order():
    """After ordering a lab, visible_timers must include the pending result."""
    sid = _start_session()
    # Unlock labs
    client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    # Order CBC
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "order_labs:cbc"})
    state = resp.json()["state"]
    visible_timers = state["visible_timers"]
    assert len(visible_timers) > 0
    cbc_vt = next((vt for vt in visible_timers if vt["node_id"] == "node_04_cbc_results"), None)
    assert cbc_vt is not None, "CBC pending reveal should appear in visible_timers"
    assert cbc_vt["source"] == "pending_reveal"
    assert isinstance(cbc_vt["label"], str) and len(cbc_vt["label"]) > 0
    assert cbc_vt["remaining_minutes"] > 0


def test_visible_timers_shape():
    """Each visible_timer entry has the expected four fields."""
    sid = _start_session()
    client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "order_labs:cbc"})
    state = resp.json()["state"]
    for vt in state["visible_timers"]:
        assert "label" in vt
        assert "remaining_minutes" in vt
        assert "source" in vt
        assert "node_id" in vt
        assert vt["source"] in ("pending_reveal", "active_timer")
        assert isinstance(vt["remaining_minutes"], int)


def test_execute_action_response_has_visible_timers():
    """ActionResponse state must include visible_timers."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    state = resp.json()["state"]
    assert "visible_timers" in state
    assert isinstance(state["visible_timers"], list)


# ---------------------------------------------------------------------------
# Wait action via API
# ---------------------------------------------------------------------------


def test_wait_action_succeeds_via_api():
    """POST /api/sessions/{id}/actions with wait:15 must succeed."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait:15"})
    assert resp.status_code == 200


def test_wait_action_advances_time():
    """wait:30 must advance the game clock by 30 minutes."""
    sid = _start_session()
    initial_time = client.get(f"/api/sessions/{sid}").json()["state"]["current_time_minutes"]
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait:30"})
    new_time = resp.json()["state"]["current_time_minutes"]
    assert new_time == initial_time + 30


def test_wait_action_emits_waited_event():
    """wait:15 must emit a 'waited' event in the response."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait:15"})
    events = resp.json()["events"]
    waited_events = [e for e in events if e["type"] == "waited"]
    assert len(waited_events) == 1
    assert waited_events[0]["data"]["duration_minutes"] == 15


def test_wait_invalid_duration_returns_400():
    """wait:45 is not allowed and must return 400."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait:45"})
    assert resp.status_code == 400


def test_wait_no_subcategory_returns_400():
    """Bare 'wait' without a duration must return 400."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "wait"})
    assert resp.status_code == 400


def test_wait_not_in_playable_actions():
    """wait must NOT appear in playable_actions list."""
    resp = client.post("/api/sessions", json={"case_path": EXAMPLE_CASE})
    playable = resp.json()["playable_actions"]
    assert not any(a.startswith("wait") for a in playable)


# ---------------------------------------------------------------------------
# Tier narrative in API response (P2-H07)
# ---------------------------------------------------------------------------


def _wait_for_pending(sid: str, node_id: str, step: str = "wait:15") -> None:
    """Poll until node_id is no longer in pending_reveals."""
    for _ in range(12):
        resp = client.post(f"/api/sessions/{sid}/actions", json={"action": step})
        data = resp.json()
        if resp.status_code != 200:
            break  # action may fail if case ended
        if node_id not in data.get("state", {}).get("pending_reveals", {}):
            break


def _advance_to_empirical_treatment(sid: str) -> None:
    """Helper: reach the empirical unlock (eosinophilia + ring_enhancing_lesion)
    and execute start_treatment:albendazole to end the case in Good tier."""
    client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "physical_exam_focused:neuro"})
    # Order CBC (30-min delay) and CT (45-min delay), then wait for results
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_labs:cbc"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_imaging:ct_head"})
    _wait_for_pending(sid, "node_04_cbc_results", step="wait:15")
    _wait_for_pending(sid, "node_06_ct_lesion", step="wait:15")
    client.post(f"/api/sessions/{sid}/actions", json={"action": "start_treatment:albendazole"})


def test_action_response_has_outcome_narrative_field():
    """Every ActionResponse must include an outcome_narrative field (null when game ongoing)."""
    sid = _start_session()
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    data = resp.json()
    assert "outcome_narrative" in data
    assert data["outcome_narrative"] is None


def test_outcome_narrative_populated_on_case_end():
    """On case end, outcome_narrative must be a non-empty string."""
    sid = _start_session()
    client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "physical_exam_focused:neuro"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_labs:cbc"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_imaging:ct_head"})
    _wait_for_pending(sid, "node_04_cbc_results")
    _wait_for_pending(sid, "node_06_ct_lesion")
    final = client.post(f"/api/sessions/{sid}/actions", json={"action": "start_treatment:albendazole"})
    data = final.json()
    assert data["case_ended"] is True
    assert data["outcome_narrative"] is not None
    assert isinstance(data["outcome_narrative"], str)
    assert len(data["outcome_narrative"]) > 0


def test_outcome_narrative_matches_case_tier_text():
    """The outcome_narrative must match the authored narrative for the matched tier."""
    import json as _json
    from pathlib import Path

    # Load the case to get the authored narrative
    case_path = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"
    with open(case_path, encoding="utf-8") as f:
        case_data = _json.load(f)
    tiers_by_name = {t["tier"]: t["narrative"] for t in case_data["outcome_evaluation"]["tiers"]}

    sid = _start_session()
    client.post(f"/api/sessions/{sid}/actions", json={"action": "history_general"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "physical_exam_focused:neuro"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_labs:cbc"})
    client.post(f"/api/sessions/{sid}/actions", json={"action": "order_imaging:ct_head"})
    _wait_for_pending(sid, "node_04_cbc_results")
    _wait_for_pending(sid, "node_06_ct_lesion")
    final = client.post(f"/api/sessions/{sid}/actions", json={"action": "start_treatment:albendazole"})
    data = final.json()
    assert data["case_ended"] is True
    tier = data["outcome_tier"]
    assert tier is not None
    expected_narrative = tiers_by_name[tier]
    assert data["outcome_narrative"] == expected_narrative
