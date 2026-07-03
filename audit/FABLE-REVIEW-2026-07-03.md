# Satori Internal Affairs — Full Review (FABLE REVIEW)

**Date:** 2026-07-03
**Reviewed at:** HEAD `e42884d` (feat(P2-H06): wait/observe action in the action bar)
**Method:** Read-only audit. Verification stack executed and observed; four boundaries traced; the Maria Santos case driven through the live engine; frontend audited against the P2-H02 UD constraints. Seven parallel specialized audits (boundaries, engine determinism, case integrity, frontend UD, test quality, security/hygiene, type safety) synthesized into this report.

**Verification stack, observed:** 528 tests pass (satori 265, anamnesis 105 + 7 deselected `live_llm`, llm-client 80 + 25 skipped, satori-api 78). `ruff check`: 1 error (E501, `packages/llm-client/tests/test_schema_conformance.py:52`). `ruff format --check`: **12 files would be reformatted** (anamnesis src + tests, llm-client tests). Mypy true strict register: **25 errors** (18 satori, 7 satori-api) — details in §2. `svelte-check`: 0 errors, 0 warnings. Note: the case file has **19 nodes** (node_00–node_18), not 18 — node_00 is a lock controller.

---

## 1. Critical findings

### C-1 · BLOCKER — `node_15_steroid_response` fires in every playthrough, corrupting the case's pacing and its central teaching mechanic
`cases/example-neurocysticercosis.json` (~line 959). The steroid-rebound node has `"activation": {"starts_active": true}` **and** a 60-minute timer. Because it starts active at t=0, its `on_expire` (set `steroid_rebound`, `modify_timer node_09 −60`) executes at T+60 in **every** game — whether or not the player ever gives steroids. Verified by driving the engine: on a pure-inaction run, the seizure-crisis clock is silently ~120 minutes instead of the authored 180; the crisis fires ~t135–149 and death ~t154–165. Downstream: the steroid red-herring is broken (the punishment fires *before* the drug is given; administering steroids now only sets `wrong_treatment_steroids`), and the GOOD tier's `before_minutes: 180` deadline is never the binding constraint. Every play-test conducted to date has been playing a different case than the one authored.
**Fix approach:** gate activation on the steroid action — split into a controller node (reveals on `start_treatment:steroids`, sets `wrong_treatment_steroids`) and a response node activated by `flag_set wrong_treatment_steroids` carrying the 60-min timer. Add a case-level regression test: inaction run must reach crisis at ~T+180. Per forward-only discipline this is a new ho, not a reopening of H07.

### C-2 · HIGH (structural) / LOW (current case) — determinism is not held across processes
`packages/satori/src/satori/state_checkers.py:70, 134, 215`. `check_auto_reveals`, `check_action_reveals`, and `check_interventions` iterate `state.active_nodes` — a `frozenset[str]` — and apply effects/emit events in iteration order. Python randomizes string hashing per process, so that order differs between runs (empirically confirmed: the two `auto_reveal` nodes, seizure-crisis and patient-death, swap relative order under different `PYTHONHASHSEED` values). If two nodes ever reveal in the same tick with non-commutative effects, the outcome can depend on the process's hash seed. The Maria Santos case happens to mask it (reveal rules are unique per action/subcategory; a 15-action path was byte-identical across four seeds), and `test_engine_determinism.py` cannot catch it because both engines share one process. The README's core promise — "same case, same actions, same result, every time" — is not structurally true.
**Fix approach:** `sorted()` on those three iterations; add a subprocess-based determinism test (same action script, two interpreters, diff serialized event streams). Small, surgical, high-value.

### C-3 · HIGH — the verification stack is not actually running as declared
Three compounding facts. (1) `make typecheck` runs mypy from the repo root, where **no mypy config exists** — mypy logs `Config File: Default` and runs **non-strict**, so the per-package `strict = true` blocks are never applied by the project's own gate (verified: root invocation of satori-api reports 0 errors; in-package strict reports 7). (2) There is **no `.pre-commit-config.yaml`** anywhere, so nothing enforces lint/type/test/coverage at commit despite the discipline mandating it — corroborated by 12 files of format drift and a live E501 sitting at HEAD. (3) No coverage configuration exists in any `pyproject.toml`; the 90% floor is unmeasured, and llm-client is at 69% (§3).
**Fix approach:** root-level `[tool.mypy]` (strict + the llm-client override) so root invocation is strict; add a pre-commit config running ruff check/format, mypy, pytest with `--cov-fail-under=90`; format the 12 files; fix the E501.

### C-4 · HIGH — no reproducible environment
No venv, no Python lockfile, and JS lockfiles are **actively gitignored** (`.gitignore:34-36` ignores `package-lock.json` et al.). A fresh checkout cannot run the test suite; `make setup` installs into whatever `pip` is ambient (its own echo claims "Python venvs" but creates none). This violates the operating discipline's pinned-dependencies rule directly.
**Fix approach:** adopt uv (workspace or per-package), commit `uv.lock` and `package-lock.json`, update the Makefile.

### C-5 · MEDIUM (blocking for P2-H08) — narration failure poisons the gameplay response
`packages/satori-api/src/satori_api/main.py:165-172`. `engine.execute_action(...)` commits state, then `narrate_events(...)` runs **outside** the try/except (which catches only `InvalidActionError`). A live narrator that raises → HTTP 500 *after* state advanced: the player's action succeeded server-side but they get an error and no state payload, and the action can't be cleanly retried. Latent today (MockNarrator can't raise); guaranteed to bite in H08.
**Fix approach:** wrap narration, degrade to templated strings on any failure — which is exactly the fallback behavior H08's spec already commits to; land the guard before the live provider.

### C-6 · MEDIUM — cascade-activated nodes emit no `NodeActivatedEvent`
`packages/satori/src/satori/state_checkers.py:272-292`. The node is added to `active_nodes` at :274, then `_activate_node` is called at :289 to harvest events — but it early-returns empty when the node is already active (`effect_executor.py:155`). State is correct (timer initialized); the event is silently lost, breaking the event contract narration and the frontend consume.
**Fix approach:** emit the event directly in the cascade loop, or reorder the activation.

### C-7 · MEDIUM — two latent crash paths from untyped schema values
`packages/satori/src/satori/effect_executor.py:79→247`: a `MODIFY_TIMER` effect authored without `value` reaches `current_remaining + None` → `TypeError` mid-simulation. `condition_evaluator.py:112,160→120`: a `TIME_ELAPSED`/`VITAL_THRESHOLD` condition without `value` → `None` compared to a number → `TypeError`. Both are the runtime face of mypy errors (§2) and share one deferred architectural question: `Effect.value`/`Condition.value` are `Any | None` (`case_definition.py:248,257`) — should they be discriminated per effect/condition type? That's a Kamae-chain question; the None-guards are the immediate fix.

### C-8 · MEDIUM — API concurrency: unbounded session store and lost-update race
`packages/satori-api/src/satori_api/session_manager.py:25` — sessions only die on explicit DELETE; no TTL/cap; each holds a live engine + full case. `main.py:151` — handlers are sync `def`, so FastAPI runs them on a threadpool; two concurrent actions on one session race on `engine.state` read-modify-write with no per-session lock (last writer wins, other action silently lost). Calibration: single local player, one tab — real severity is low *today*; it becomes real the day this is hosted. Fix approach: per-session `threading.Lock` + TTL sweep, in one small ho, or defer to the hosting phase with a documented note.

### C-9 · MEDIUM — case design integrity issues (beyond C-1), for a thinking conversation
- **The seizure crisis is unsurvivable.** Once `node_14` fires (5-min timer → death), nothing stops it: `node_17` clears `crisis_active` but doesn't deactivate node_14; the `emergency_intervention` action exists in `action_costs` (~line 155) but **no node references it** — it's inert. Verified: albendazole during the crisis → death anyway. This collides with **P2-H05**, whose entire UI premise is "only emergency-relevant actions surfaced" — currently there are none.
- **OPTIMAL tier requires frame-perfect play.** The confirmed path lands treatment at t=114 against a 120-minute constraint only by overlapping the family visit inside the X-ray delay window; any natural thorough play lands GOOD. If OPTIMAL is meant to reward rigor rather than scheduling micro-optimization, the window needs widening.
- **`family_alienated` is an orphan** — the Diego-leaves penalty writes a flag nothing reads; the relational-failure branch has zero consequence.
- Clinical review flags (human/physician): steroids are coded purely as "wrong," but real neurocysticercosis care co-administers corticosteroids with albendazole — the case may teach the wrong lesson; anti-seizure management is narratively present but mechanically absent (`no_prior_aeds` never read); the serology path (120-min delay) is a de-facto death trap rather than a merely-suboptimal choice.

### C-10 · MEDIUM — H01's diegetic-timer deliverable didn't land in the case
No node in the case has `timer.diegetic: true` — the lab/imaging nodes use `result_delay_minutes`/`pending_reveals`, not node timers, so H01 deliverable #8 ("mark lab and imaging timers diegetic") had nothing to mark, and the `active_timer` branch of `compute_visible_timers` (`game_state.py:97`) is dead code against the real case, exercised only by synthetic fixtures. Pending-reveal countdowns still work (that's what H04 renders), so the player-visible feature functions — but confirm intent: if the design wants any always-visible diegetic countdown, no case data produces one.

### Lower-severity register
- **Truth-line smell (medium):** `VitalsStrip.svelte:33-66` re-derives per-vital criticality with hardcoded thresholds byte-identical to `patient_condition.py:64-71`. Not a state-determining leak (the authoritative badge is server-fed), but duplicated medical truth that will drift. Fix: server sends per-vital status.
- **Boundary smells (low):** `NarrativeFeedPanel.svelte:45-63` hardcodes engine event-type names and *synthesizes* narration client-side for `waited` events (self-acknowledged H08 gap); `ActionBar.svelte:86-101` hardcodes `wait:15/30/60` and a `false` placeholder for `emergency_active`.
- **Time-constraint tiers are latently wrong (low):** `state_checkers.py:426-438` checks case-end time, not flag-set time; correct today only because `correct_treatment_started` itself ends the case.
- **Product question (low):** `wait:30` ≠ guaranteed `2×wait:15` (pause conditions evaluate once per tick over the whole interval). Spec is silent; should be a conscious decision.
- **Dead surface (low):** `SatoriEngine.get_available_actions` (`engine.py:489`) referenced only by tests; `GET /sessions/{id}`, `DELETE /sessions/{id}`, `GET .../nodes/{node_id}` have no frontend callers.
- **Hygiene (low):** `pytest packages/...` from root fails on duplicate `test_placeholder.py` basenames (the Makefile's per-package form works); `pytest.mark.integration` unregistered in llm-client; debug `<details>` raw-events dump ships to players (`NarrativeFeedPanel.svelte:89-92`); `.gitignore` has duplicate/unanchored `build/`/`dist/`; P2 ho files aren't renamed `-DONE-` like P1's.
- **Security: clean.** No secrets in tree or history; `.env` untracked; CORS is an explicit localhost allowlist, `credentials=False`; uvicorn binds 127.0.0.1. Production-only notes: `case_path` traversal guard (`session_manager.py:49`), disable `/docs`, seed free-text → prompt interpolation unsanitized (matters only if community-authored seeds/cases ever arrive), `narrator_bridge.py:59-62` will pass case-authored prose into live narrator prompts unsanitized when H08 lands.

---

## 2. Type-safety register

The true strict register is **25 errors**: 18 in satori, 7 in satori-api. The extra 3 seen from a bare root run (`openai`/`anthropic` import-not-found, yaml stubs) are environment artifacts — properly suppressed by llm-client's scoped `ignore_missing_imports` override and by anamnesis's declared `types-PyYAML` dev dependency.

| File | Errors | Category | Resolution |
|---|---|---|---|
| `satori/events.py:64,107,108` | 3 × `type-arg` (bare `dict`) | Incomplete annotation, no runtime risk | Annotate `dict[str, Any]`. Note: `narrator_bridge.py:48` has the identical construct *silenced* with an ignore — same issue, two treatments; fix both. |
| `satori/vitals_computer.py:65-70` | 5 × `arg-type` | Real type inconsistency, low runtime risk — correctness rests on a hand-maintained `is_int_vital` string set (:138-144) the checker can't see; drifts silently if `NORMAL_RANGES` and the set diverge | Split `_worst_value` into typed `_worst_int`/`_worst_float` (or `@overload`). Not an ignore. |
| `satori/effect_executor.py:112,135,190,279,302,372` | 6 × `return-value` (list invariance) | Benign — `list[FlagSetEvent]` ⊄ `list[Event]` | Annotate locals `events: list[Event] = [...]`. Trivial. |
| `satori/effect_executor.py:79` | `arg-type` | **Real latent bug** — `_modify_timer` adds `None` (C-7) | None-guard with a clear `ValueError`; the deeper fix is the `Effect.value` typing question |
| `satori/effect_executor.py:335` | `arg-type` | Mixed — `OVERRIDE_VITALS` with malformed value crashes at Pydantic | Explicit named-arg construction + value validation |
| `satori/condition_evaluator.py:112,160` | 2 × `arg-type` | **Real latent bug** — `None` threshold comparison (C-7) | None-guard naming the malformed condition |
| `satori-api/serialisation.py:43,46-51` | 7 × `unused-ignore` | Dead suppressions — :43 is misapplied entirely (no generic on that line) | Delete all 7. These persisted precisely because `make typecheck` runs non-strict (C-3). |

**Ignore discipline:** the project rule (every ignore names its code *and* carries a reason) has **0% explanation compliance across all 43 suppressions**. Production is at least 14/14 on naming codes; tests have **15 bare `# type: ignore`** with no code at all (`test_interfaces.py:59,94,147,153,159,165`; `test_boundary_types_comprehensive.py:210-222`; `test_schema_conformance.py:7,8`; `test_config.py:61,174`). Many test ignores are legitimately intentional (assigning to frozen fields to prove immutability) — they still need the code and the one-line reason.

**Config observations:** `pyrightconfig.json` points at a `.venv` that doesn't exist, runs `basic` (far weaker than mypy strict — two disagreeing sources of truth), and omits `llm-client/tests` from its include list while including every other package's tests. Meanwhile mypy never checks tests at all. Recommend either deleting pyrightconfig or aligning it; and adding tests to the strict mypy targets over time.

---

## 3. Test-quality register

**Coverage** (measured; not configured or enforced anywhere — itself a finding):

| Package | Coverage | Floor |
|---|---|---|
| satori | 96% | pass |
| satori-api | 96% | pass |
| anamnesis | 94% | pass |
| llm-client | **69%** | **fail** |
| internal-affairs | no test framework exists | n/a |

- **llm-client's failure is one root cause:** `openai_generator.py` (38%) and `anthropic_generator.py` (36%) are covered by `test_providers.py` (345 lines, 18 tests) that `pytest.importorskip` the SDKs — with neither installed, the entire file is inert and reports as "80 passed, 25 skipped," which reads healthy while covering nothing. Fix: mock at the SDK boundary instead of import-skipping, or install the SDKs in the dev environment and let the existing tests run. This is the single biggest test-quality gap and it sits exactly on the files P2-H08 will extend.
- **Vacuous tests** in `test_engine_determinism.py`: `test_vitals_worst_wins_computation` (:606-619) asserts only `vitals is not None` — the named behavior (worst-wins) is unspecified by its own test (high); `test_timer_stage_events_emitted` (:286), `test_flag_set_and_cleared_events` (:640), `test_vitals_changed_event` (:656) assert only `hasattr(...)` and pass vacuously if zero matching events fire (medium).
- **Missing negative paths (medium):** engine-level `CaseValidationError` from `_validate_case_structure` never triggered (`engine.py:133,139,145` uncovered); API path where a case file exists but fails Pydantic validation (`main.py:101-104`); 7 of 11 `_describe_event` branches lack direct unit tests; tier `time_constraints` evaluation (`state_checkers.py:426-438`) has zero coverage — the exact code C-9/C-1 interact with.
- **Meaningful uncovered engine branches:** dual `on_expire` handling (`engine.py:290-293,401-404`), reveal-condition gating in `get_playable_actions` (:541-542).
- Clean: no snapshot/tautology patterns beyond the above, no xfails, anamnesis's `live_llm` deselection is properly configured and documented, condition/effect/timer/patient-condition suites are genuine behavioral specifications with good boundary tests.

---

## 4. Frontend accessibility audit (severity weighted for the ataxia constraint)

- **UD-1 · HIGH** — `OutcomeScreen.svelte:96-107`: "Play Again" (~40px tall, `padding: 10px 28px`, no min-height) is below the 60px floor — and it's the sole control at case end. The Phase-1 deferral on this file covers hex codes, not UD. Fix: `min-height: var(--touch-target-pref)`.
- **UD-2 · HIGH** — `OutcomeScreen.svelte:109-111`: no `:focus-visible` ring on that same button; keyboard/switch users can't see focus.
- **CON-1 · MEDIUM** — `--color-text-dim` `#6b7280` measures 3.57:1 on panel / 3.88:1 on app background — fails WCAG AA (4.5:1) at the 16–18px sizes it's used at (empty states, vital units, entry times). One-token fix: lighten to ≥ ~`#868e9e`.
- **UD-3 · MEDIUM** — disabled-action reasons conveyed only via `title` (`CategoryDropdown.svelte:75`, `ActionBar.svelte:79,94`) — hover-only, invisible on touch. Render as visible text / `aria-describedby`.
- **UD-4/UD-5 · MEDIUM** — dropdown doesn't move focus to first option on open (a P2-H02 deliverable, spec'd and unimplemented) and drops focus to `<body>` on close; no arrow-key navigation between `role="option"` items.
- **UD-6 · MEDIUM** — outcome overlay declares `aria-modal="true"` (`+page.svelte:90`) but doesn't move or trap focus — announced modal, isn't one.
- **UD-7 / CON-2 · LOW** — dropdown options at 60px min vs the 72px the component's own comment claims; critical-badge text at 4.19:1.
- **Clean:** 18px base font applied globally; triggers/action bar/start button all at 72px with correct focus rings and 16px gaps; all click handlers have keyboard equivalents; no motion beyond 0.1s color transitions; the token palette otherwise clears AA comfortably (most pairs 7:1–15:1).

---

## 5. Design-token / architectural drift

- **TOK-1 · MEDIUM** — `VitalsStrip.svelte:147,199,200`: raw `80px` min-width, `2px` padding, `999px` radius in a component built fresh under token discipline whose own acceptance criteria demand a clean grep.
- **TOK-2 · LOW** — honest gaps rather than violations: no tokens exist for focus-ring width (`2px` at `CategoryDropdown.svelte:132,191`, `+page.svelte:173`), accent border (`NarrativeFeedPanel.svelte:147`), or layout max-widths (`+page.svelte:132`). Consider `--focus-ring-width` etc. on the next design pass.
- **Confirmed deferred, not findings:** `PatientHeader.svelte` and `OutcomeScreen.svelte` Phase-1 hex/px (except UD-1/UD-2 above, which are UD failures, not token drift).
- **Boundary fuzz gathering at the edges:** the frontend increasingly knows engine vocabulary — event-type strings, wait keys, the synthesized "waited" narration, the `emergency_active` placeholder, the duplicated vital thresholds. Individually small; collectively the Truth/Narration lines are fraying at the *frontend* end even while holding structurally at the engine end. H05/H08 are the natural points to pull each back server-side.

---

## 6. Overall critical feedback

**Where it's strong.** The four boundaries genuinely hold — this is rare and worth saying plainly. The engine has zero network surface, zero wall-clock/RNG, immutable state transitions via frozen dataclasses, and a validation gate that provably fires before every case write. The Truth Line's store design (wholesale state replacement, no client deltas) is exemplary. Case reference integrity is fully clean — every flag, node, and action reference resolves; the `diagnosis_confirmed` setters sit on exactly the three genuine confirmation nodes and the three rigor-scoring scenarios all trace correctly through the live engine, with no tier-ordering hazard. Security is clean. The test suites for the engine's core evaluators are real behavioral specifications.

**Where the assumptions break.** Three of them:

1. *"The verification stack runs at every commit"* — it doesn't. No pre-commit config exists, `make typecheck` silently runs non-strict, coverage is unenforced, and 12 files of format drift at HEAD prove it. The discipline is declared but not mechanically encoded — precisely the failure mode the encoded-environment thesis warns about. Every finding in §2 that persisted (7 dead ignores) persisted *because* of this.
2. *"Same case, same actions, same result, every time"* — true within a process, unproven across processes, and the test that claims to verify it structurally cannot (C-2). Cheap to make true; expensive to discover later via an unreproducible bug report.
3. *"The case is playable as designed"* — it isn't (C-1). Every playtest so far ran a 120-minute crisis clock against 180-minute pacing, with the steroid mechanic firing before the player acts. Any felt-experience judgments made from Phase 2 playtesting to date are suspect. There is currently no case-level simulation harness (script the full inaction path, the steroid path, the optimal path, assert timeline invariants) — the engine's unit tests are excellent, but nothing tests the *case as an artifact*, which is where this bug lived undetected.

**For a colleague inheriting this:** the codebase is honest — what the docs say about architecture is what the code does, which is the highest compliment a doc chain can get. The debt is concentrated in the enforcement plumbing and in one case-authoring bug, not in the architecture. Fix the plumbing before adding the next layer, because H08 (LLM narrator) is exactly the kind of work where a silently-weak verification stack starts letting real defects through.

---

## 7. 8-hour work plan

Findings re-prioritize the day: H03/H05/H08 remain the right sequence, but **none of them should start until the trust substrate is repaired** — H05's design premise (emergency the player responds to) doesn't even exist in the case yet (C-9), and H08 lands on the two least-tested files in the repo behind an unguarded API path (C-5). Each item below should enter as a new ho in the current build slot per forward-only discipline.

**Sprint 1 (~2.5h) — Verification-stack repair.** Root `[tool.mypy]` strict config (or per-package cwd in the Makefile); delete the 7 dead ignores in `serialisation.py`; apply the trivial strict fixes (`list[Event]` locals, `dict[str, Any]` annotations, the `_worst_value` split); add the two None-guards from C-7; `ruff format` the 12 files + fix the E501; add `.pre-commit-config.yaml` running ruff check/format, mypy strict, pytest with `--cov-fail-under=90` (llm-client will fail the floor — see Sprint 4); register the `integration` mark; rename the duplicate `test_placeholder.py`. *Why first: every subsequent session's green light is meaningless until the gate actually gates. This clears ~23 of the 25 mypy errors as a side effect.*

**Sprint 2 (~2h) — Case repair + case-level regression harness.** Fix C-1 (gate node_15 on the steroids action, controller/response split); add a scripted-playthrough test module that drives the real engine through the inaction path (crisis ~T+180, death ~T+195), the empirical path (GOOD), the confirmed path (OPTIMAL), and the steroids path (rebound at administration+60, PARTIAL) asserting timeline invariants; decide and author `timer.diegetic` on whichever timers the design wants visible (C-10). *Why second: until this lands, all playtesting measures the wrong game — it invalidates the very evaluations Phase 2 exists to enable.*

**Sprint 3 (~1.5h) — Determinism hardening + event contract.** `sorted()` in the three `state_checkers.py` loops; subprocess determinism test; fix the missing cascade `NodeActivatedEvent` (C-6). *Why third: closes the gap under the project's foundational guarantee while the engine context from Sprint 2 is warm.*

**Spike (~1h) — Emergency-mode design reconnaissance (feeds H05 and the Kamae chain).** Time-boxed: trace exactly what a survivable crisis requires — wiring `emergency_intervention` to a node_14 rescue (pause/deactivate path), what `crisis_active`-flag semantics H05's `emergency_active` derivation needs, and whether the OPTIMAL window widens. Output is a decision memo for a thinking conversation, not code — these are case-design/Kamae decisions (C-9) that touch design authority the coding session shouldn't exercise alone.

**Sprint 4 (~1h) — Ataxia-critical frontend fixes + narrator guard.** UD-1, UD-2, CON-1 (three small changes: min-height, focus ring, one token value — highest leverage per minute in the whole report); wrap `narrate_events` in the fallback path (C-5) so H08's provider work starts on a safe substrate.

**Deferred beyond the 8 hours, and why:** llm-client provider test coverage (fold into H08, which rewrites those files anyway — fixing tests twice is waste); session-store TTL + per-session lock (real only at hosting time; document as a known limit); UD-3–UD-6 dropdown/modal focus work (legitimate, medium, but below the two HIGHs — batch into H03's panel session where those components are already open); environment reproducibility/uv migration (C-4 — genuinely important but a half-day of its own; schedule as the next infrastructure ho); frontend test framework; pyright config reconciliation; dead-endpoint cleanup.

---

## 8. What to skip

- **H01's "mark lab/imaging timers diegetic" as originally worded** — the lab/imaging nodes don't *have* timers; they use result delays, which already surface through `pending_reveals`. The deliverable was unfulfillable as written. Decide in Sprint 2 whether any timer should be diegetic (the husband-arrival timer is the plausible candidate); don't retrofit the original wording.
- **Multiple concurrent emergencies** (H05 out-of-scope note) — confirmed right to skip; the case can't author it and the engine handles one cleanly.
- **Per-session narration cache beyond a plain dict** (H08) — the ho's in-memory `(event_type, node_id)` dict is correct; anything fancier is waste for one case and one player.
- **Prompt-injection sanitization** in anamnesis and the narrator bridge — defer until community-authored seeds/cases are a real feature; note it in H08's spec so the surface is named (calibrated black box), but don't build it.
- **Production hardening of satori-api** (case_path guard, docs exposure, CORS for real origins, session eviction) — defer wholesale to a hosting-phase ho; local posture is currently correct.
- **`cysticercosis_confirmed` / `steroid_rebound` orphan-flag cleanup** — fold into Sprint 2's case edit rather than treating as separate work; but *don't* skip `family_alienated`: either wire it into a tier or cut the Diego-leaves timer, because an inert punishment is worse than none.
- **Wait-additivity (`wait:30` vs 2×`wait:15`)** — don't build anything; just record the product decision in the next thinking conversation. The current tick-granularity behavior is defensible.

---

**Bottom line:** architecture sound, boundaries holding, one case-authoring blocker silently reshaping every playthrough, and a verification stack that declares strictness it isn't executing. Fix the gate, fix the case, prove determinism across processes — then H03/H05/H08 proceed on solid ground.

---

## Appendix — review environment note

The repo had no venv and packages were not installed in the system Python at review time. A throwaway venv was built in the session scratchpad to run the suite. One review subagent additionally installed the four packages editable into the system Python (plus `jsonschema`, `pytest-cov`); `pip uninstall satori anamnesis llm-client satori-api` reverses that if unwanted. No repo files were modified during the review.
