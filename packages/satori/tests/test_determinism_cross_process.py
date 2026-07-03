"""Cross-process determinism test (audit S3, finding C-2).

The engine's core guarantee — same case, same actions, same result — must
hold across process boundaries, not just within one interpreter. Python
randomizes string hashing per process, so set iteration order differs
between runs; before the sorted-iteration fix in state_checkers.py, two
same-tick reveals could apply effects in seed-dependent order. The existing
determinism suite runs both engines in ONE process (same hash seed) and
structurally cannot detect that.

This test runs an identical scripted playthrough in separate interpreters
under different PYTHONHASHSEED values and asserts the serialized event
stream and final state are byte-identical. The script takes the steroids
path deliberately: it exercises reveals, cascade activation, mid-wait timer
expiry, the rebound's modify_timer, and the crisis/death auto-reveal pair —
the two auto_reveal nodes whose relative iteration order is exactly what
the hash seed used to perturb.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CASE_PATH = Path(__file__).parents[3] / "cases" / "example-neurocysticercosis.json"

SCRIPT = """
import dataclasses, json, sys
from satori.engine import SatoriEngine
from satori.models.case_definition import CaseDefinition

with open(sys.argv[1], encoding="utf-8") as f:
    case = CaseDefinition.model_validate(json.load(f))
eng = SatoriEngine(case)

actions = [
    "history_general", "physical_exam_focused:neuro", "order_labs:cbc",
    "order_imaging:ct_head", "wait:30", "wait:15",
    "start_treatment:steroids", "wait:60", "wait:60", "wait:60",
]
log = []
for action in actions:
    if eng.get_state().case_ended:
        break
    for event in eng.execute_action(action):
        log.append(json.dumps(dataclasses.asdict(event), sort_keys=True, default=str))

state = eng.get_state()
log.append(json.dumps({
    "time": state.current_time_minutes,
    "flags": sorted(state.flags),
    "active": sorted(state.active_nodes),
    "revealed": sorted(state.revealed_nodes),
    "expired": sorted(state.expired_nodes),
    "timers": dict(sorted(state.timers.items())),
    "ended": state.case_ended,
    "tier": state.outcome_tier,
}, sort_keys=True))
sys.stdout.write("\\n".join(log))
"""


# A synthetic case whose only job is to put six auto-reveal nodes into the
# SAME tick: all six activate at t=10 (cascade, deterministic list order),
# then the next tick's check_auto_reveals reveals all six — in set-iteration
# order before the fix, sorted order after. The Maria Santos case never
# authors a same-tick collision, so it cannot discriminate; this can.
COLLISION_SCRIPT = """
import dataclasses, json, sys
from satori.engine import SatoriEngine
from satori.models.case_definition import CaseDefinition

node_ids = ["node_echo", "node_alpha", "node_foxtrot", "node_bravo", "node_delta", "node_charlie"]
case = CaseDefinition.model_validate({
    "id": "00000000-0000-0000-0000-000000000001",
    "version": "1.0.0",
    "metadata": {
        "difficulty": "beginner",
        "estimated_duration_minutes": 20,
        "simulated_duration_minutes": 180,
        "learning_objectives": ["Determinism collision fixture"],
        "dramatic_tone": "medical_mystery",
    },
    "patient": {
        "name": "Test Patient", "age": 35, "sex": "male",
        "setting": "Emergency Department", "chief_complaint": "Test",
        "appearance": "Test",
        "arriving_vitals": {
            "heart_rate": 80, "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80, "temperature": 98.6,
            "respiratory_rate": 16, "o2_saturation": 98,
        },
    },
    "ground_truth": {
        "diagnosis": "Test", "differential": [], "mechanism": "Test",
        "key_insight": "Test", "optimal_path": [], "narrative_hooks": [],
    },
    "action_costs": {"history_general": {"action_minutes": 10}},
    "nodes": [
        {
            "id": nid,
            "type": "medical_finding",
            "content": {"narrative_text": f"Finding {nid}"},
            "activation": {"paths": [{"conditions": [
                {"type": "time_elapsed", "target": "", "value": 10},
            ]}]},
            "reveal": {"auto_reveal": True},
        }
        for nid in node_ids
    ],
    "outcome_evaluation": {
        "tiers": [{"tier": "optimal", "narrative": "n/a"}],
        "end_conditions": [
            {"type": "time_elapsed", "value": 180, "description": "timeout"},
        ],
    },
})
eng = SatoriEngine(case)
log = []
for action in ["history_general", "wait:15"]:
    for event in eng.execute_action(action):
        log.append(json.dumps(dataclasses.asdict(event), sort_keys=True, default=str))
sys.stdout.write("\\n".join(log))
"""


def _run_subprocess(script: str, hash_seed: str, *args: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    result = subprocess.run(
        [sys.executable, "-c", script, *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"seed {hash_seed} run failed:\n{result.stderr}"
    return result.stdout


def _run_scripted_playthrough(hash_seed: str) -> str:
    return _run_subprocess(SCRIPT, hash_seed, str(CASE_PATH))


class TestCrossProcessDeterminism:
    def test_event_stream_identical_across_hash_seeds(self) -> None:
        outputs = {seed: _run_scripted_playthrough(seed) for seed in ("0", "1", "777")}

        # The run must have gone deep enough to exercise the auto-reveal
        # collision surface (crisis + death), or identity proves nothing.
        assert '"patient_death"' in outputs["0"]
        assert '"ended": true' in outputs["0"]

        assert outputs["0"] == outputs["1"] == outputs["777"], (
            "Event stream or final state diverged between interpreter hash "
            "seeds — set-iteration order is leaking into engine behavior "
            "(audit C-2)."
        )

    def test_same_tick_auto_reveal_order_identical_across_hash_seeds(self) -> None:
        """Six nodes auto-revealing in one tick must produce the same event
        order in every interpreter. This is the direct discriminator for
        C-2: before the sorted-iteration fix, this order follows frozenset
        iteration and varies with PYTHONHASHSEED."""
        outputs = {seed: _run_subprocess(COLLISION_SCRIPT, seed) for seed in ("0", "1", "777")}

        # All six reveals must actually have fired in the second tick.
        assert outputs["0"].count('"node_revealed"') == 6

        assert outputs["0"] == outputs["1"] == outputs["777"], (
            "Same-tick auto-reveal event order diverged between hash seeds (audit C-2)."
        )
