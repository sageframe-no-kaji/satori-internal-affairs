# P2-H09: Crisis Mechanic and Scoring

**Status:** READY
**Phase:** 2
**Ho:** 09
**Depends on:** P2-H01 (visible_timers / VisibleTimer), P2-H07 (diagnostic rigor scoring), audit close-out (`e55e7b1`), emergency-mode design spike (`audit/emergency-mode-decision-memo.md`)

---

## Objective

Make the seizure crisis survivable, honest, and correctly scored. Six decisions land together as one case-authoring ho with one small engine addition:

1. **Survivable crisis.** `emergency_intervention` on node_14 deactivates the crisis node, sets `crisis_managed`, clears `crisis_active`, and unlocks the four investigation actions node_14 locked.
2. **Post-crisis re-arm.** `crisis_managed` activates a new post-crisis progression node (`node_20`) with a 90-minute non-diegetic timer expiring into a **distinct second seizure crisis node** (`node_21`). The second crisis also takes `emergency_intervention` rescue — the mechanic must not lie the second time.
3. **Timeout fallthrough tier.** T+360 with no treatment and no death currently matches no tier; the engine defaults to "failure" and the API returns the *death* narrative for a patient who is alive. Add a failure-register fallthrough tier with a truthful narrative.
4. **`emergency_timer` visibility channel.** New `emergency_timer: VisibleTimer | None` field on `GameState` (and the API response). Populated only while a crisis is active and the case has not ended; carries the currently-active crisis node's timer. `visible_timers` stays semantically clean (diegetic-only).
5. **OPTIMAL window: 150 minutes.** `outcome_evaluation.tiers.optimal.time_constraints.before_minutes: 120` → `150`.
6. **`family_alienated` becomes mechanical.** Added to GOOD's `excluded_flags`; relational failure costs one tier. PARTIAL's narrative retouched (one sentence) to cover both the late-diagnosis route and the relational-failure route.

**No UI work in this ho.** Pure case JSON + small engine surface addition + tests. P2-H05 (Emergency Mode) renders what this ho makes true.

---

## Context: Why This Comes Before H05

The audit's emergency-mode design spike (`audit/emergency-mode-decision-memo.md`) established that once `node_14_seizure_crisis` activates, death is unavoidable: its 5-minute timer activates `node_16_patient_death`, and the `emergency_intervention` action — declared in `action_costs` — is referenced by nothing. It spends 2 minutes and does nothing, which punishes the correct instinct. H05's UI premise ("only emergency-relevant actions surfaced") needs at least one emergency-relevant action to *exist* before there is anything to render.

The spike also identified the one genuine engine-surface question (audit C-10): the emergency timer must be visible during a crisis, but node_14's timer is non-diegetic by design and `compute_visible_timers` filters on the static `timer.diegetic` flag. There is no mechanism to flip diegetic at crisis time, and overloading `visible_timers` would dirty its diegetic-only semantics. Hence decision 4: a **separate channel**.

All six decisions were blessed in the practitioner's thinking conversation of 2026-07-04 and are locked. This ho executes them; it does not re-litigate them.

---

## Design Decisions

### Survivable crisis — memo recommendation, adopted verbatim

From the spike memo (§1, Option A — recommended):

> ### Option A — Intervention deactivates the crisis node **[case-authoring]** *(recommended)*
> Author on node_14: `on_intervene: {treatment: "emergency_intervention", effects: [deactivate_node node_14, clear_flag crisis_active, set_flag crisis_managed]}`.
> - **Mechanics:** death timer removed outright; `crisis_managed` is available for outcome tiers (e.g., a managed-crisis run can still reach PARTIAL/GOOD; an unmanaged one cannot).
> - **Felt experience:** benzodiazepines/airway control end the seizure — clinically the right shape (status epilepticus care is exactly this).
> - **Caveats:** deactivation also removes node_14's crisis vitals from worst-wins, so vitals visibly recover — desirable. But the patient is "stabilized, still sick": node_09 has already expired, so no second crisis clock exists. See the re-arm question below.
> - **H05 implication:** emergency mode ends when `crisis_active` clears — same signal as the treatment path; clean for the `emergency_active` derivation (§2).

The locked decision extends the memo's effect list with the four `unlock_action` effects reversing node_14's locks (`history_general`, `history_focused`, `physical_exam_general`, `physical_exam_focused`), and resolves the memo's open re-arm question: **yes, a managed crisis re-arms** — decision 2.

### The OPTIMAL window — memo design note, pasted verbatim

> **The math (post-S2 verified by the regression harness):** fastest rigorous path — CT at t=74, dietary history for the X-ray unlock, thigh X-ray (20-min delay), family visit overlapped into result windows — lands `correct_treatment_started` at **t=116** against `before_minutes: 120`. Four minutes of slack, achievable only with delay-overlap scheduling the case never teaches. A thorough player who sequences naturally (family visit not overlapped, or MRI instead of X-ray) lands t≈130–160 → GOOD.
>
> Options:
>
> - **A. Widen to 150 [case-authoring]** *(recommended)* — keeps time pressure meaningful (still well inside the 180 GOOD bound and the 195 crisis), but rewards *rigor* rather than scheduling micro-optimization. A confirmed + family-engaged run that doesn't dawdle lands OPTIMAL.
> - **B. Keep 120 [case-authoring]** — OPTIMAL as a mastery tier for replayers who learn to overlap delays. Defensible if the design wants a "perfect run" concept; the debrief (Phase 5) would need to teach the overlap explicitly or it reads as arbitrary.
> - **C. Drop the time constraint from OPTIMAL entirely [Kamae-chain]** — rigor and family engagement alone define OPTIMAL; time pressure lives only in the crisis clock and GOOD's 180. This changes what the tier system expresses (the seed's "timing and deterioration" pillar), so it is not a case-local call.

Locked: **Option A, widen to 150.**

### `family_alienated` — memo design note, pasted verbatim

> Diego's timer (`node_13`, 90 minutes from arrival) sets `family_alienated` on expiry if the player never took `history_focused:family`. Nothing reads the flag — the relational-failure branch has zero consequence. An inert punishment is worse than none: the mechanic implies the game noticed, and it didn't.
>
> - **A. Wire it into the tiers [case-authoring]** *(recommended, smallest true fix)* — add `family_alienated` to OPTIMAL's `excluded_flags`. Today it's near-redundant (OPTIMAL already *requires* `family_engaged`, and you can't have engaged Diego *and* let him leave — the reveal sets `family_engaged` before the timer can expire), so the honest version of this option is: **exclude it from GOOD**, making the relational failure cost one tier. That gives the husband thread real mechanical weight, which is what the seed's "medicine as a human system" pillar wants.
> - **B. Cut the timer/flag [case-authoring]** — if the design decides relational consequence belongs to Phase 5's debrief rather than the tier system, delete the `on_expire` and the flag, and let Diego's departure be narrative-only. Cheaper, but it walks back an authored mechanic.
> - Note the audit's determinism nuance either way: Diego's *arrival* is tick-quantized (activates on the first tick crossing T+30), so his departure time varies with action cadence — acceptable, but worth knowing before wiring consequences to it.

Locked: **Option A, exclude from GOOD.** The tick-quantization nuance is documented in node_13's `teaching_note` (one added sentence) so future case authors wiring consequences to Diego's timer know his departure time varies with action cadence. Keep node_13's `on_expire` and the flag as authored.

**Implementation note (correction found while scripting tests).** The memo's parenthetical — "you can't have engaged Diego *and* let him leave — the reveal sets `family_engaged` before the timer can expire" — is only true inside the OPTIMAL window. Revealing a node does not tear down its timer: Diego engaged at t=96 still "leaves" at t≈149, setting `family_alienated` for a player who did the relational work. While the flag was inert this was invisible; wired into GOOD's exclusions it would make GOOD unreachable for any engaged run treating between ~149 and 180, contradicting GOOD's authored bound. Fix: `deactivate_node node_13_husband_diego` appended as the **last** `on_reveal` effect — engagement stops the departure clock. The `on_expire` list and the flag remain exactly as authored (the locked decision's wording); the un-engaged branch is untouched.

### The re-arm shape (decision 2, concrete)

Two new nodes, mirroring the node_09 → node_14 pattern:

- **`node_20_post_crisis_progression`** — `progression`, never revealed (`reveal: null`), activated by `flag_set crisis_managed`. 90-minute **non-diegetic** timer (the player infers it from vitals — same design language as node_09), staged vitals escalating at 30 and 60 minutes, `on_expire: activate_node node_21_second_seizure_crisis`. Pause condition on `correct_treatment_started`, symmetric with node_09 (defensive: treatment ends the case via end condition, but if end-condition semantics ever change, the clock must not keep running under treatment).
- **`node_21_second_seizure_crisis`** — `progression`, `auto_reveal: true`, activated by `node_expired node_20_post_crisis_progression` (both the activation path and node_20's explicit `activate_node`, mirroring the node_09/node_14 belt-and-braces wiring). 5-minute timer expiring into `node_16_patient_death`. On reveal: sets `crisis_active`, re-locks the four investigation actions. On intervene (`emergency_intervention`): deactivates itself, sets `second_crisis_managed` (its cascade-gate flag — see below), clears `crisis_active`, re-unlocks the four actions. Crisis vitals authored slightly worse than node_14's (HR 152, BP 78/44, SpO2 84, RR 5) — the second seizure on an untreated brain is not the same event.

Activation is once-only by construction: expired nodes stay in `active_nodes` (only their timer entry is removed), and both `cascade_activations` and `_activate_node` skip already-active nodes. After the second rescue there is no third clock; an untreated run then idles into the T+360 timeout and lands in the fallthrough tier — which is exactly what that tier is for.

**The cascade re-activation gate (correction found by the test suite).** `deactivate_node` alone does not stick: `cascade_activations` runs every tick and re-activates any *inactive* node whose activation conditions hold, and both `node_expired` and `time_elapsed` conditions are sticky-true forever. Unpatched, the rescue deactivated node_14 and the same tick's cascade re-activated it with a fresh 5-minute death clock — the mechanic would have lied on its first outing. The memo's §1 verified `deactivate_node`'s teardown but not its interaction with the cascade. The schema-free fix is a **gate pattern**: every node that can be explicitly deactivated carries a `flag_not_set` condition on the flag its own resolution sets, inside the same activation path —

- node_14: `node_expired node_09` AND `flag_not_set crisis_managed`
- node_21: `node_expired node_20` AND `flag_not_set second_crisis_managed` (the second rescue sets `second_crisis_managed`, which exists precisely because `crisis_managed` is already set before node_21 is ever born and cannot gate it)
- node_13: `time_elapsed ≥ 30` AND `flag_not_set family_engaged` (pairs with the reveal-deactivation fix above)

Pure case authoring — `flag_not_set` is an existing condition type; no engine or schema change. This pattern is load-bearing for any future case that deactivates nodes with sticky activation conditions and belongs in the case-authoring documentation when Phase 4 scales content.

### `emergency_timer` — the separate channel (decision 4, concrete)

New derived field on `GameState`, populated by a `compute_emergency_timer(state, case)` helper alongside `compute_visible_timers` at every state-construction site (engine init, `execute_action`, `_execute_wait`):

- `None` when `case_ended` or the reserved crisis flag `crisis_active` is not set (the memo's derivation: *crisis flag AND NOT case_ended* — otherwise the outcome screen renders in emergency dress).
- Otherwise: among active nodes with a running timer whose `on_reveal` effects set `crisis_active`, the one with the least remaining time (ties broken by `node_id` — deterministic). Reuses the existing `VisibleTimer` dataclass with `source="active_timer"`.

"A node whose `on_reveal` sets `crisis_active`" is the crisis-node convention this ho establishes: cases declare crises by flag effect, exactly as the ho-overview's reserved-flag recommendation intended, and the engine needs no new schema field. H05's `emergency_active: bool` derivation will read the same flag.

The timer shows **exact** remaining minutes (H05's locked decision: the one place precision serves the design — the player is racing it).

### The fallthrough tier and `outcome_narrative` (decision 3, concrete — includes a small engine addition beyond the brief)

The fallthrough tier is authored last in `tiers`, in the failure register (`"tier": "failure"`), with `excluded_flags: [patient_death, correct_treatment_started]` — explicit rather than empty, so a reader sees what routes here. Runs that time out at T+360 untreated (including steroids-only runs) match it.

**Wrinkle discovered during authoring, and its resolution.** `OutcomeTier.tier` is an enum level, not an identity: two tiers now share the `"failure"` level. The engine picks the right *tier* (first match in authored order), but the API's `resolve_tier_narrative` matches by level and would return the first failure tier's narrative — "Maria died" — for a patient who is alive. Re-implementing tier matching in the API would duplicate medical logic across the Truth Line, which is worse.

Resolution: an additive `outcome_narrative: str | None` field on `GameState`. When `check_end_conditions` matches a tier, it records that tier's authored narrative. The API prefers `state.outcome_narrative` and falls back to `resolve_tier_narrative` (which remains correct for cases ended purely by an `end_case` effect, where no tier walk occurs). This is authored case text flowing through the engine — the same relationship the engine already has to `narrative_text` on events — not the engine generating narrative; the Narration Line is untouched.

This is the one deviation from the letter of the locked decisions ("pure case JSON + small engine addition (`emergency_timer`)"); without it, decision 3 ships a tier whose narrative the player can never see. Recorded here and in the close-out report.

---

## Deliverables

### 1. Case: `cases/example-neurocysticercosis.json`

- **node_14_seizure_crisis:** add `effects.on_intervene` — treatment `emergency_intervention`; effects in order: `deactivate_node node_14_seizure_crisis`, `set_flag crisis_managed`, `clear_flag crisis_active`, `unlock_action` × (history_general, history_focused, physical_exam_general, physical_exam_focused).
- **node_20_post_crisis_progression** (new): as specified above. Base vitals HR 108 / BP 156/96 / SpO2 95 (post-ictal, stabilized-but-sick — node_09's stage vitals are gone after its expiry, so this node carries the post-crisis picture). Stages: at 30 → HR 114, BP 162/100; at 60 → HR 122, BP 170/106, SpO2 93.
- **node_21_second_seizure_crisis** (new): as specified above, narrative text authored in the case's register.
- **Outcome tiers:** optimal `before_minutes` 120 → 150; GOOD `excluded_flags` += `family_alienated`; PARTIAL narrative retouched (one sentence covering both routes); fallthrough failure tier appended.
- **node_13_husband_diego:** `deactivate_node node_13_husband_diego` appended to `on_reveal` (engagement stops the departure clock — see Design Decisions); one sentence added to `teaching_note` documenting tick-quantized arrival/departure.
- **Version:** 2.0.0 → 2.1.0; `_comment` updated.

### 2. Engine: `packages/satori/src/satori/game_state.py`

- `CRISIS_FLAG = "crisis_active"` module constant (the reserved-flag convention, documented).
- `GameState.emergency_timer: VisibleTimer | None = None`.
- `GameState.outcome_narrative: str | None = None`.
- `compute_emergency_timer(state, case) -> VisibleTimer | None` as specified.

### 3. Engine: `packages/satori/src/satori/engine.py`

Set `emergency_timer=compute_emergency_timer(...)` wherever `visible_timers` is computed (three sites: `_initialize_state`, `execute_action`, `_execute_wait`).

### 4. Engine: `packages/satori/src/satori/state_checkers.py`

`check_end_conditions`: when a tier matches, set `outcome_narrative` to the matched tier's narrative on the ended state (and leave it `None` on the no-match default).

### 5. API: `packages/satori-api/src/satori_api/models.py` + `serialisation.py` + `main.py`

- `GameStateResponse.emergency_timer: VisibleTimerResponse | None = None`; serialise from state.
- `main.py` action endpoint: `outcome_narrative=state.outcome_narrative or resolve_tier_narrative(...)`.

Both additive — no breaking API change.

---

## Tests

### New: `packages/satori/tests/test_crisis_rescue.py`

- Rescue: drive to the crisis (history_general + 3×wait:60 → t=195), `emergency_intervention` → node_14 deactivated, `crisis_active` cleared, `crisis_managed` set, four actions unlocked, vitals recovered from crisis values.
- Re-arm: node_20 active with a 90-minute timer after rescue; expires into node_21; `crisis_active` set again; the four actions re-locked.
- Second rescue: `emergency_intervention` deactivates node_21, clears `crisis_active`, unlocks; no third clock exists.
- Death still reachable: unrescued first crisis → node_16 → failure + `patient_death`; unrescued second crisis likewise (the mechanic must not lie the second time — both directions).
- `emergency_timer`: `None` before crisis; populated (node_14, exact remaining) during; `None` after rescue; populated (node_21) during second crisis; `None` on death (case_ended).
- Fallthrough tier: rescue both crises, idle to T+360 → tier `failure`, end_reason time-limit, `outcome_narrative` is the fallthrough narrative, **not** the death narrative; `patient_death` not in flags.
- Intervention outside crisis remains a legal 2-minute no-op (pre-existing behavior, now pinned).

### Extended: `packages/satori/tests/test_case_maria_santos.py`

- Natural-sequence confirmed path (no delay-overlap micro-optimization) lands t≈130–150 → **OPTIMAL** under the widened window; a confirmed path past 150 → GOOD (the boundary is real).
- `family_alienated` run (never take `history_focused:family`, treat correctly before 180 after Diego's timer expires) → PARTIAL, not GOOD.
- Existing assertions (t=116 optimal, empirical good, steroids partial, death failure) unchanged — only the 120-referencing docstring updates.

### API: `packages/satori-api/tests/`

- `test_serialisation.py`: `emergency_timer` None ↔ populated round-trip.
- `test_api.py`: `emergency_timer` present in responses; a timeout run's `outcome_narrative` is the fallthrough narrative.

---

## Acceptance Criteria

1. `pytest packages/satori packages/satori-api` green; full prior suite passes; coverage ≥ 90%.
2. `ruff check` + `ruff format --check` clean; `mypy --strict` clean.
3. `npm run check` clean (API change is additive; frontend untouched).
4. The Maria Santos case validates against the JSON Schema and loads.
5. A scripted run — crisis, rescue, second crisis, rescue, timeout — produces: two survivable crises, truthful vitals arcs, and the fallthrough narrative.
6. `pre-commit run --all-files` clean.

---

## Out of Scope

- All UI rendering (emergency dress, locked-action treatment) — P2-H05.
- `emergency_active: bool` on GameState/API — P2-H05 (it reads the same `crisis_active` convention this ho establishes).
- Locking/unlocking `emergency_intervention` availability outside crises (surfacing emergency actions contextually is H05 UI work; the engine action remains a legal no-op).
- Third-crisis re-arm, crisis-count scoring, `crisis_managed` in tier rules — not in the locked decisions.
- Schema changes. None needed: `on_intervene`, `deactivate_node`, duplicate-level tiers, and optional `required_flags` are all already legal.

If the activation graph does not cleanly support the re-arm as specified, **stop and escalate** — do not redesign mid-implementation.

---

## Verification Stack

In order:

1. `ruff check packages/satori packages/satori-api && ruff format --check packages/satori packages/satori-api`
2. `mypy --strict packages/satori/src packages/satori-api/src`
3. `pytest packages/satori packages/satori-api -q`
4. `cd packages/internal-affairs && npm run check`
5. `git status` — only expected files changed

---

## Commit Message Template

```
feat(P2-H09): survivable crisis, re-arm, fallthrough tier, scoring retune

Case (example-neurocysticercosis v2.1.0):
- node_14 on_intervene: emergency_intervention deactivates the crisis,
  sets crisis_managed, clears crisis_active, unlocks investigation actions
- node_20_post_crisis_progression (new): 90-min non-diegetic re-arm clock
  activated by crisis_managed, staged vitals, expires into second crisis
- node_21_second_seizure_crisis (new): distinct second crisis, auto-reveal,
  5-min death clock, takes the same emergency_intervention rescue
- outcome tiers: OPTIMAL window 120 -> 150; family_alienated excluded from
  GOOD; PARTIAL narrative covers both routes; failure-register fallthrough
  tier for the untreated T+360 timeout (previously matched no tier and
  showed the death narrative for a living patient)
- node_13 teaching_note documents Diego's tick-quantized arrival

Engine:
- GameState.emergency_timer: VisibleTimer | None — separate visibility
  channel for the active crisis clock (visible_timers stays diegetic-only);
  crisis nodes identified by the reserved crisis_active flag convention
- GameState.outcome_narrative — check_end_conditions records the matched
  tier's authored narrative so duplicate-level tiers resolve truthfully

API:
- GameStateResponse.emergency_timer (additive); action endpoint prefers
  state.outcome_narrative over level-keyed narrative lookup

Tests: test_crisis_rescue.py (rescue/re-arm/second-crisis/fallthrough/
emergency_timer lifecycle); Maria Santos harness extended for the widened
OPTIMAL window and the family_alienated tier drop.

Executes the six decisions locked from audit/emergency-mode-decision-memo.md.
Unblocks P2-H05 (Emergency Mode UI).
```
