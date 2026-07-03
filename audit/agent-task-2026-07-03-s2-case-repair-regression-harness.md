---
created: 2026-07-03
type: agent-task
status: ready
parent: audit/FABLE-REVIEW-2026-07-03.md
project: satori-internal-affairs
---

# S2 — Case repair + case-level regression harness

**Goal**

Fix finding C-1 (the steroid-rebound node fires unconditionally in every playthrough) so the Maria Santos case plays with its authored 180-minute crisis clock and the steroid red-herring punishes the steroid *decision*, and add a scripted-playthrough regression module that pins the case's timeline invariants so this class of authoring bug cannot recur silently.

**Problem**

`node_15_steroid_response` in `cases/example-neurocysticercosis.json` has `"activation": {"starts_active": true}` plus a 60-minute timer whose `on_expire` sets `steroid_rebound` and applies `modify_timer node_09 −60`. It therefore executes at T+60 in every game regardless of player action: the seizure crisis arrives ~T+120 instead of ~T+180, death ~T+155 instead of ~T+195, and giving steroids no longer causes the acceleration it is authored to teach. Verified against the live engine during the review.

**Files**

- Modify: `cases/example-neurocysticercosis.json`
- Create: `packages/satori/tests/test_case_maria_santos.py`
- Read-only: `packages/satori/src/satori/` (engine semantics reference — activation paths, timers, effects)
- Read-only: `schemas/` (case schema — the fix must validate against it unchanged)

**Required Changes**

1. **Gate node_15 on the steroid action.** Restructure so the rebound activates only when steroids are actually administered: a controller element that reveals on `start_treatment:steroids` and sets `wrong_treatment_steroids`, and a response node whose activation path is `flag_set wrong_treatment_steroids`, carrying the 60-minute timer and the `modify_timer node_09 −60` on_expire. (The engine starts timers at *activation*, not reveal — the split exists so the timer starts when the flag lands.) Remove `starts_active: true` from the rebound. Preserve the authored narrative text and teaching notes.
2. **Orphan-flag cleanup, folded in per report §8:** remove the redundant `cysticercosis_confirmed` setters (fully co-set with `diagnosis_confirmed`, never read) and either drop or document `steroid_rebound` (never read; the mechanical effect is the `modify_timer`). Leave `family_alienated` untouched — its fate is a design decision (see Stop Condition).
3. **Regression harness** `test_case_maria_santos.py` — scripted playthroughs of the *shipped case artifact* through the real engine, asserting timeline invariants:
   - **Inaction path:** no player action after intake → seizure crisis fires ~T+180 (not ~T+120), death ~T+195. Assert `steroid_rebound`/acceleration never occurs without steroids.
   - **Empirical path:** eosinophilia + ring-enhancing CT → treat on suspicion → tier GOOD, `diagnosis_confirmed` unset.
   - **Confirmed path:** confirmation node before albendazole → tier OPTIMAL reachable.
   - **Steroids path:** give steroids at time T → rebound/acceleration occurs at T+60 (not before), final tier PARTIAL.
   - **Blocked path:** `start_treatment` before any evidence → `InvalidActionError`.
4. **Case still validates:** the edited JSON passes the anamnesis validator / Pydantic `CaseDefinition` load unchanged — no schema modifications.

**Do Not**

- Do not modify the engine or schema. This is case data + tests only. If the fix seems to require an engine change, stop and surface.
- Do not widen the OPTIMAL time window or wire `family_alienated` — both are design decisions for the practitioner (report C-9), fed by the SP spike.
- Do not add `timer.diegetic: true` to any node without the practitioner's explicit choice of which timers are diegetic (report C-10 / §8 — the plausible candidate is the husband-arrival timer, but it is a design call).

**Stop Condition**

If restructuring node_15 within the existing schema proves impossible (e.g., activation paths can't express the gating), stop and surface the constraint — schema changes belong to the Kamae chain. Likewise stop if the regression harness reveals further timeline anomalies beyond C-1: report them, don't fix them in this task.

**Acceptance**

- [ ] Edited case validates: `CaseDefinition` loads it, anamnesis validator passes it.
- [ ] All five regression scenarios in `test_case_maria_santos.py` pass.
- [ ] The inaction-path test fails when run against the pre-fix case JSON (proves the test detects C-1).
- [ ] Full satori suite still passes; coverage floor holds.
- [ ] `ruff`, `mypy` clean (per S1's now-working gate).

**Verification**

```bash
pytest packages/satori/tests/test_case_maria_santos.py -v
pytest packages/satori -q
python -c "import json; from satori.case_definition import CaseDefinition; CaseDefinition.model_validate(json.load(open('cases/example-neurocysticercosis.json')))"
pre-commit run --all-files
```

**Commit**

Single commit (case fix + harness land together — the harness is the proof):

```
fix(case): gate steroid rebound on the steroid action — restore 180-min crisis clock

node_15 was starts_active:true, firing the rebound at T+60 in every
playthrough (audit C-1). Split into steroid-gated controller/response.
Adds scripted-playthrough regression harness pinning the case's
timeline invariants.
```
