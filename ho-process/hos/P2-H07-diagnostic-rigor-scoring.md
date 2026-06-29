# P2-H07: Diagnostic Rigor Scoring

**Status:** READY
**Phase:** 2
**Ho:** 07
**Depends on:** Phase 1 complete. (Independent of other Phase 2 hos. Can be done in parallel with everything except other case-file edits.)

---

## Objective

Without changing the engine, tune the Maria Santos case and the outcome screen so the scoring rewards **diagnostic confirmation before treatment commitment** — and the result of that rigor (or its absence) is legible to the player.

Concretely:

1. **Audit the case** to verify `diagnosis_confirmed` is set only by genuine confirmation events (MRI showing the scolex sign, positive cysticercosis serology) — never as a side effect of treatment.
2. **Add an earlier `start_treatment` unlock path** so the player can commit to empirical treatment on suspicion alone (eosinophilia + ring-enhancing lesion is enough to *suspect* neurocysticercosis even before serology or scolex MRI). The existing post-confirmation unlock stays.
3. **Surface the tier narrative on the outcome screen** so the player sees the consequence of their diagnostic path (the existing `tier.narrative` field in `outcome_evaluation`; the OutcomeScreen doesn't render it yet).

The whole point: the player who waits for MRI confirmation gets Optimal. The player who commits to albendazole empirically based on clinical suspicion gets Good. The current case structure almost supports this; this ho tightens it and makes the scoring visible.

---

## Context: What's Already in Place

The Phase 1 case (`cases/example-neurocysticercosis.json`) already separates the tiers correctly:

- **Optimal** requires `diagnosis_confirmed`, `correct_treatment_started`, `family_engaged`. Excludes `patient_death`, `wrong_treatment_steroids`. Time constraint: treatment before 120 min.
- **Good** requires `correct_treatment_started` only. Excludes `patient_death`, `wrong_treatment_steroids`. Treatment before 180 min.
- **Partial** requires `correct_treatment_started`, excludes `patient_death`. No time constraint.
- **Failure** requires `patient_death`.

The structure is correct: Optimal demands confirmation, Good rewards correct-by-suspicion. **But the current case unlocks `start_treatment` only AFTER `diagnosis_confirmed` is set** (via the MRI and serology nodes that set `diagnosis_confirmed` and unlock treatment in the same effect block). That means the Good tier's "correct treatment without confirmation" path is unreachable — you can't physically treat without confirming first.

This ho relaxes the unlock path so the Good tier is reachable, while keeping the Optimal tier's harder bar (you confirmed before you treated) intact.

The OutcomeScreen renders the tier label and `end_reason`. It does NOT render the rich `tier.narrative` text that's already authored in the case for each tier. This ho adds that.

---

## Design Decisions

### Diagnostic suspicion → empirical treatment unlock

Add an early unlock path for `start_treatment` that fires on **suspicion-grade** evidence:
- `eosinophilia` (set by CBC) AND
- `ring_enhancing_lesion` (set by CT scan)

This combination is genuine clinical suspicion for neurocysticercosis without confirmation. With this unlock, the player can choose:

- **Cautious path:** Wait for MRI/serology → `diagnosis_confirmed` fires → treatment unlocks → treat → **Optimal** possible.
- **Empirical path:** Order CBC + CT → eosinophilia + ring lesion → treatment unlocks early → treat → **Good** possible.
- **Reckless path:** Treat without supporting evidence (e.g., guessing based on chief complaint) → if treatment was incorrect, harmful outcome; if correct by luck, **Good** tier with very fast time.

The mechanism: a new `unlock_action` effect tied to a controller node or to the existing CT/CBC nodes. The cleanest approach: extend the existing `node_05_ct_result` (or whichever node reveals the ring lesion) to include an `unlock_action` effect for `start_treatment` whose preconditions reference both flags. The agent decides exactly where to wire it after reading the case.

**If the case structure makes this awkward,** add a new controller-style node `node_XX_empirical_unlock` that activates when both flags are set and whose `on_activate` effects unlock `start_treatment`. The agent picks the cleanest path; both are valid.

### `diagnosis_confirmed` is genuine confirmation only

Audit the case and confirm that `diagnosis_confirmed` is set ONLY by:
- The MRI brain node when the scolex sign is visible
- The cysticercosis serology node when positive
- Any future tissue biopsy node (none currently)

`diagnosis_confirmed` must NOT be set by:
- Treatment nodes (treatment starts a flag; it doesn't confirm the diagnosis)
- CT scan revealing ring-enhancing lesion (this is suggestive, not confirmatory)
- Any history or exam node

If any node currently sets `diagnosis_confirmed` incorrectly, fix it. (From the initial scan, the only place this *might* exist is in treatment-success cascades — the agent should grep for every `target: "diagnosis_confirmed"` occurrence and verify each one.)

### Outcome screen — tier narrative rendering

The OutcomeScreen receives `outcome_tier` and `end_reason` props today. Extend it to also receive and render the tier's `narrative` text from the case's `outcome_evaluation.tiers[].narrative` field.

The narrative is already authored per tier in the case (see `cases/example-neurocysticercosis.json` lines ~1129, 1146, 1156, 1163). The pipeline question is: where does it become available to the frontend?

**Cleanest path:**
1. The API includes the matched tier's narrative in the response when the case ends.
2. The frontend's `gameStore` exposes it; the OutcomeScreen renders it under the existing `end_reason` block (or replaces `end_reason` with it if `end_reason` is currently just a paraphrase of the same content).

Inspect the existing API response structure (`packages/satori-api/src/satori_api/serialisation.py`) and engine state. If the engine's `GameState` already carries the matched tier's narrative (likely as part of the end-of-case computation), the API just needs to surface it. If not, add a small derivation (matched tier rule → narrative text) in `serialisation.py`.

If the existing `end_reason` and the tier `narrative` would render redundantly, replace `end_reason` with `narrative` on the OutcomeScreen. Whichever is more informative to the player wins.

---

## Deliverables

### 1. Case audit and amendment: `cases/example-neurocysticercosis.json`

- Grep for every `"target": "diagnosis_confirmed"` set_flag effect. Verify each one is on a genuine confirmation node (MRI scolex, serology positive). Remove any that are not.
- Add the empirical-suspicion unlock path: when `eosinophilia` AND `ring_enhancing_lesion` are both set, `start_treatment` action unlocks (without requiring `diagnosis_confirmed`). Wire this via the cleanest mechanism in the existing case structure (extend an existing node's effects, or add a small controller node).
- Verify the case still validates against the schema.

### 2. Outcome screen narrative rendering

**Engine + API:** Determine how the matched tier's narrative reaches the frontend. Options:
- a) `GameState` already exposes it on case end — surface in `serialisation.py`.
- b) Engine doesn't track it — add a small derivation in `state_checkers.py` (or wherever end-of-case evaluation lives) so `GameState` carries it, plus serialise it.
- c) API computes it from `case.outcome_evaluation` + `state.outcome_tier` — this is fragile (couples API to case structure) but minimal. Avoid unless (a) and (b) are awkward.

**Frontend:**
- `packages/internal-affairs/src/lib/types.ts`: add the narrative field to the relevant response type.
- `packages/internal-affairs/src/lib/api.ts` / `gameStore.svelte.ts`: pipe it through.
- `packages/internal-affairs/src/lib/components/OutcomeScreen.svelte`: render the narrative below the tier label. Replace `end_reason` if redundant, or render both with the narrative more prominent.

### 3. Tests

**Engine:**
- A regression test (in `packages/satori/tests/`) that runs a sequence of actions: order CBC → eosinophilia set → order CT → ring lesion set → check that `start_treatment` is now in `available_actions` even without `diagnosis_confirmed`. Add to whichever existing test file covers action-unlock dynamics, or create `test_empirical_treatment_unlock.py`.
- A regression test verifying the existing post-confirmation path still works: MRI → diagnosis_confirmed → treatment unlocks.
- A test verifying `diagnosis_confirmed` is NOT set by any treatment node (run a treatment sequence; assert the flag is set only if a confirmation node was triggered first).

**Outcome:**
- A test that the API response on case end includes the tier narrative for each tier (run a known sequence that ends in each tier and assert the narrative matches the case's authored text).

**Frontend:**
- `svelte-check` passes; no new explicit test required.

### 4. Verification on the playable path

Run the engine through three end-to-end scenarios and confirm tier outcomes:
- A) CBC + CT + MRI (scolex sign) + start_treatment:albendazole → Optimal (assuming family_engaged + within 120 min)
- B) CBC + CT + start_treatment:albendazole (no MRI) → Good (within 180 min, no rebound)
- C) start_treatment:albendazole without any imaging → either should not be reachable (no unlock yet) OR if reachable through some path, should land in Good or below

For each, the API response should contain the matched tier's narrative.

---

## Acceptance Criteria

1. `pytest packages/satori packages/satori-api` is green. New tests pass; Phase 1 suite untouched.
2. `ruff check` clean. `mypy --strict` clean. `pre-commit run --all-files` clean.
3. `cd packages/internal-affairs && npm run check` clean.
4. Manual scenario walk-through (A/B/C above) produces the expected tiers in the engine.
5. The OutcomeScreen, when reached, shows the tier's narrative text (verify by launching the dev frontend if helpful, or just by reading the response — visual polish is not required).
6. The case still validates against `schemas/case-definition.schema.json`.

---

## Out of Scope

- Engine changes to outcome evaluation logic (the existing tier-matching is correct; only case authoring and serialisation change here)
- New tier definitions or new flags beyond what's needed
- Full debrief explanation (Phase 5)
- Phase 2 UI polish on the OutcomeScreen beyond rendering the narrative (e.g., showing what flags were missing to reach the next tier — this is Phase 5 work)
- Authoring this scoring into other cases (only Maria Santos exists)

If the case audit surfaces a structural problem (e.g., `diagnosis_confirmed` being set in a place that's load-bearing for the existing test suite in a way you can't cleanly fix), **stop and escalate** — note it in your final report and do not redesign.

---

## Verification Stack

In order:

1. `ruff check . && ruff format --check .` (run from each touched package or the repo root, whatever the project's existing workflow is)
2. `mypy --strict packages/satori/src packages/satori-api/src`
3. `pytest packages/satori packages/satori-api -q`
4. `cd packages/internal-affairs && npm run check`
5. Manual playthrough scenarios A/B/C — log the achieved tier for each.
6. `git status` — verify only expected files changed.

---

## Commit Message Template

```
feat(P2-H07): diagnostic rigor scoring — empirical treatment path + tier narrative

- Case: diagnosis_confirmed audit — set only by genuine confirmation
  (MRI scolex, cysticercosis serology). Removed any erroneous sets.
- Case: empirical-suspicion unlock — start_treatment unlocks on
  eosinophilia + ring_enhancing_lesion. Cautious path (post-confirmation)
  unchanged. Good tier now reachable; Optimal still demands confirmation.
- API: tier narrative serialised onto case-end response
- Frontend: OutcomeScreen renders the matched tier's narrative text
- Tests: empirical-treatment-unlock regression; post-confirmation path
  preserved; diagnosis_confirmed never set by treatment nodes; tier
  narratives present in API response
- Verified A/B/C scenarios: Optimal, Good, and lower paths produce
  the expected tiers
```
