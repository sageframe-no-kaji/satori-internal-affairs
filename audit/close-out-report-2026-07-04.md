# Phase 2 Close-Out Report

**Prompt:** `audit/fable-close-out-prompt-2026-07-04.md` (authored 2026-07-04)
**Executed:** 2026-07-04 (Ho A, Ho B engine/API) and 2026-07-10 (Ho B completion, Ho C, Ho D, H08 draft, this report)
**Working discipline:** every commit below passed the full pre-commit gate — ruff check, ruff format, mypy strict, pytest × 4 packages with the 90% coverage floor (llm-client floor deferred to P2-H08 as documented).

---

## Hos executed

### Ho A — P2-H09 crisis mechanic and scoring · `480254b`

All six locked decisions executed: survivable crisis (`emergency_intervention` on node_14), post-crisis re-arm (node_20 → distinct node_21, same rescue), fallthrough failure tier, `emergency_timer` visibility channel, OPTIMAL window 120 → 150, `family_alienated` excluded from GOOD. Committed with the per-ho doc in the prior session; verification stack green at commit.

### Ho B — P2-H05 emergency mode · `0592bb7`

Spanned the session boundary: engine/API surfaces (`emergency_active` derivation, API field, TS mirrors, store getters) landed uncommitted on 2026-07-04; on resume they were verified against the ho doc unchanged, the missing test layer was added (engine lifecycle ×11 including the memo §2 same-tick treatment edge, verified empirically before pinning; API serialisation + endpoint coverage including death-with-flag-still-set), then the two visual decisions were taken and the frontend implemented. Verification: 405 → 418 tests green, mypy strict clean, svelte-check 0/0, coverage 97% on touched packages, banner palette 11.8:1, emergency label token 5.5:1.

### Ho C — P2-H03 active concerns panel · `241f90c`

Authored `ho-process/hos/P2-H03-active-concerns-panel.md`, stopped for the card-language decision, implemented. Engine: `GameState.revealed_at` at all three reveal sites (chronology is engine truth — `revealed_nodes` is unordered and the debrief will want reveal timing). API: server-composed `findings` (Truth Line: the frontend never decides what counts as evidence), filtered to evidence node types, deterministic chronological order. Frontend: bordered cards under fixed category sections, flag chips, `T+N min` stamps. Fixed in passing: `humanise_node_id` promoted public; `state_to_response` takes the case. Verification: 418 tests green, stack clean, chip contrast 6.2:1, stamp 4.8:1.

### Ho D — P2-H10 uv migration · `db6e507`

Audit C-4 closed. Virtual uv workspace over the four packages, committed `uv.lock` + `.python-version` (3.12), `package-lock.json` un-ignored and committed, Makefile and all pre-commit hooks now run `uv run --no-sync` against the pinned environment. Fixed in passing: anamnesis's undeclared `llm-client` dependency (imported throughout, never declared — worked only ambiently); `make dev-api` now runs from the repo root per `session_manager`'s documented case-path contract (the old `cd` broke relative case paths). Verification: full stack through the workspace env — 621 passed / 1 skipped / 13 deselected (live-LLM), all four packages under mypy strict; the commit itself exercised the new hook entries.

### P2-H08 real LLM narrator — draft only · `0bdd987`

Per-ho doc drafted at `ho-process/hos/P2-H08-real-llm-narrator.md`, marked **DRAFT — VOICE WORK PENDING PRACTITIONER**. Plumbing specified (AnthropicNarrator, per-session cache keyed `(event_type, node_id)`, env-var provider selection defaulting to mock, timeout + fallback extending the C-5 guard, llm-client coverage-floor restoration); prompt template *structure* specified; no prompt content written; not executed.

---

## Visual decisions

| Decision | Options presented | Practitioner chose |
|---|---|---|
| H05 · 1 — emergency signature | screen-edge border / top banner / central panel | **B — top-anchored banner** (crisis label from the server's timer channel + exact countdown; side panels dim; narrative feed and vitals stay legible) |
| H05 · 2 — locked actions | grayed inline / emergency-only bar / sidebar | **A — grayed inline with reason** (merged-sorted ordering keeps every button in place; one-press intervention button, focused when the crisis starts) |
| H03 · 1 — card language | bordered cards + category headers / flat chronological list / tabs | **A — bordered cards under category headers** (stable regions for re-consultation; chronology preserved per-card and within sections) |

Both A-choices and the B-choice matched my stated recommendation; rationales and rejected options are recorded in each per-ho doc.

---

## Deviations from the locked decisions

All three are Ho A (P2-H09), recorded in its per-ho doc at the time:

1. **`outcome_narrative` engine field** — beyond the brief's "pure case JSON + small engine addition (`emergency_timer`)". Two tiers now share the `failure` level, and the API's level-keyed narrative lookup would show "Maria died" for a timeout run in which she is alive. The matched tier's authored text is recorded on `GameState` at end-condition time; re-implementing tier matching in the API would have duplicated medical logic across the Truth Line, which is worse.
2. **Cascade re-activation gates** — `deactivate_node` alone does not stick: the every-tick cascade re-activates any inactive node whose (sticky-true) conditions hold, so the rescue would have re-armed node_14 with a fresh death clock in the same tick. Fixed with `flag_not_set` gates on node_14/node_21 activation paths (introducing `second_crisis_managed`). Pure case authoring, existing condition type; found by the test suite, not the memo.
3. **node_13 reveal-deactivation** — decision 6 said "keep node_13's `on_expire` and the flag as authored," which was honored — but revealing a node does not tear down its timer, so an *engaged* Diego still "left" at t≈149, setting `family_alienated` and making GOOD unreachable for engaged runs treating between ~149 and 180. `deactivate_node node_13` appended as the last `on_reveal` effect: engagement stops the departure clock; the un-engaged branch is untouched.

Hos B–D introduced no deviations from locked decisions (their in-flight discoveries — the `--color-emergency-label` AA token, the emotional node type included in the findings whitelist ahead of need, the dev-api working-directory fix — are recorded in the per-ho docs and commit messages).

---

## Escalations

None. No stop condition was met: the emergency signal derived cleanly from flag state, `emergency_timer`/`findings` were additive, no schema changes were needed, and no test failure surfaced an architectural problem.

---

## What remains after this close-out

- **P2-H08 execution** — the only remaining Phase 2 ho; blocked on the practitioner's voice work (register, prompt content). Everything else for `v0.7` is in.
- **llm-client coverage floor** — restored as part of H08 (documented in hooks/Makefile).
- **UD items:** UD-3 (hover-only disabled reasons) was substantially fixed by H05 (visible on focus + `aria-label`; touch still relies on the aria path). **UD-4/UD-5** (dropdown focus management, arrow-key navigation) and **UD-6** (outcome overlay announces modal but doesn't trap focus) remain open — the audit suggested batching them into H03's session; H03's scope as authored didn't include them, so they need a small dedicated UI ho.
- **Session-store TTL + per-session lock (C-8)** — deferred to the hosting phase, as the audit recorded.
- **npm audit** reports fixable advisories in the frontend tree; dependency upgrades were out of H10's scope (lockfile pins current versions only).
- **Frontend test framework** — still absent; visual verification remains the practitioner's watch. Worth an infrastructure ho before Phase 3.
- **Practitioner visual pass** — H05's banner/locked-action dress and H03's cards were verified by stack + contrast math, not by eye; the next play session should confirm the felt experience (especially banner entry under `prefers-reduced-motion` and the crisis-focus move).
