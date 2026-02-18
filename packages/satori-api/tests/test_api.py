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
    assert new_time >= initial_time  # time never goes backwards


def test_execute_action_state_is_self_contained():
    """After an action, the response state + available_actions must be complete."""
    sid = _start_session()
    action = _get_first_action(sid)
    resp = client.post(f"/api/sessions/{sid}/actions", json={"action": action})
    data = resp.json()
    # state.available_actions and top-level available_actions must match
    assert sorted(data["state"]["available_actions"]) == sorted(data["available_actions"])


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
    if events:
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
    assert len(data["narrative_text"]) > 0
