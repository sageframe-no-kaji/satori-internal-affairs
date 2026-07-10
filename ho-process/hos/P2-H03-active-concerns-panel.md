# P2-H03: Active Concerns Panel

**Status:** IN PROGRESS — card-language decision taken (bordered cards, category sections); implementing
**Phase:** 2
**Ho:** 03
**Depends on:** P2-H02 (panel shell, design tokens), P2-H01 (engine surface conventions)

---

## Objective

The Active Concerns panel becomes the player's evidence board: every revealed clinical finding accumulates there as a card and persists for the whole case. Three layers land together:

1. **Engine:** `GameState.revealed_at` — node_id → game-minutes at reveal, recorded at all three reveal sites. The evidence board is chronological; the engine currently forgets *when* the character learned things.
2. **API:** `GameStateResponse.findings` — the revealed clinical findings composed server-side from state + case data (category, label, authored content, structured data, reveal time). Additive.
3. **Frontend:** the panel renders findings as cards in whatever language visual decision 1 selects; grouping, empty state, and scroll behavior land with it.

---

## Context

The panel shell has existed since P2-H02 with `findings={[]}` hardwired. The ho-overview (§P2-H03) frames the panel as "what makes the player's reasoning visible to themselves": the diagnostic whiteboard, rendering structured node data rather than narration. The narrative feed tells the story of the case; this panel holds the *evidence* — what is known, when it was learned, organized for skim-reading while the player weighs the diagnosis.

---

## Design Decisions

### Findings are composed server-side (Truth Line)

The frontend must not decide what counts as clinical evidence. `state_to_response` gains a `case` parameter (both call sites hold the engine) and composes `findings` from `state.revealed_nodes` ∩ the evidence-board node types:

```
FINDING_NODE_TYPES = {history, medical_finding, lab_result, imaging, relational}
```

`emotional` would belong here too if a case authored one (none does yet); `progression`, `behavioral`, `intervention_response`, `outcome` are narrative events, not evidence — they live in the feed. Findings sort by `(revealed_at_minutes, node_id)`: chronological, deterministic.

### `revealed_at` is engine state, not presentation memory

Unlike H05's locked-action snapshot (pure display memory), *when the character learned a fact* is game truth — the debrief phase (Phase 5) will want it, and without it the findings list has no stable order (`revealed_nodes` is a frozenset). Recorded at the three sites that add to `revealed_nodes`: auto-reveals, action-triggered reveals (`state_checkers.py`), completed pending reveals (`timer_manager.py`). Invariant, tested: `revealed_at.keys() == revealed_nodes` at every state.

### Category taxonomy (ho-overview decision — resolved)

Existing `node_type` verbatim, no new schema field (the overview's recommendation). The API passes it through as `category`; the frontend maps it to display sections — History, Exam (`medical_finding`), Labs (`lab_result`), Imaging, Family (`relational`). Display labeling is cosmetic; the taxonomy itself is case data.

### Card content (ho-overview decision — resolved)

- **Label:** humanised node id with the `node_NN_` prefix stripped, server-side ("Cbc Results" → the same `_humanise_node_id` convention the timer channel uses).
- **Body:** the node's authored `narrative_text` — this is case content (the result text, the patient's own words), not narrator output; the "no narration" rule distinguishes authored findings from LLM voice.
- **Flag chips:** entries in `structured_data` whose key ends in `_flag` render as accent chips ("Eosinophils: HIGH") — the skim-reading layer.
- **Timestamp:** `T+N min`, matching the clock idiom.

### Accumulation behavior (ho-overview decision — resolved)

Scroll, no collapse: the panel body already scrolls; collapsing would hide state behind extra interactions (UD: no hidden state, no added motor cost). Panel stays populated at case end — the outcome screen overlays rather than replaces (already how the page composes).

### VISUAL DECISION 1 — Card language and grouping

**How do findings look as they accumulate, and how are they organized?** — **DECIDED (practitioner, 2026-07-10): Option A, bordered cards under category section headers.** Sections render in fixed order (History, Exam, Labs, Imaging, Family, Emotional; unknown categories fall through to Other) with a rule between them; cards are chronological within each section. The panel exists for re-consultation — stable category regions make "what did the labs say?" a glance, not a scan — and chronology is preserved on every card via the `T+N min` stamp while the narrative feed carries the story in time order. Rejected: B (flat chronological list) makes re-finding a fact a full-column scan since position encodes time, not kind; C (tabs) adds hit-targets in a narrow column and hides state — new evidence in a hidden tab is invisible.

---

## Deliverables

### 1. Engine: `packages/satori/src/satori/game_state.py`, `state_checkers.py`, `timer_manager.py`, `engine.py`

- `GameState.revealed_at: Mapping[str, int]` (default empty), updated wherever `revealed_nodes` grows
- Initial state: empty (nothing is revealed at t=0)

### 2. API: `models.py`, `serialisation.py`

- `FindingResponse`: `node_id`, `category`, `label`, `narrative_text`, `structured_data | None`, `revealed_at_minutes`
- `GameStateResponse.findings: list[FindingResponse] = []`; `state_to_response(state, case)` composes, filters, sorts

### 3. Frontend: types + store + panel

- `types.ts`: `Finding` interface; `findings` on `GameState`
- `gameStore.svelte.ts`: `findings` getter
- `ActiveConcernsPanel.svelte`: card rendering per visual decision 1; typed props replace `unknown[]`; empty state kept
- `+page.svelte`: passes `game.findings`

### 4. Tests

- Engine: `revealed_at` at each reveal site; invariant with `revealed_nodes`; determinism (same run → same map)
- API: findings shape, node-type filtering, chronological ordering, presence in session + action responses
- `npm run check` for the frontend

---

## Universal Design checklist (verify before commit)

- Cards are non-interactive in this ho — no touch-target constraints beyond panel scroll; if any interaction is added later, targets ≥ 60px (noted for Phase 5 annotations)
- Body text at `--font-size-base` (18px), WCAG AA on card backgrounds
- Category grouping/labels legible at a glance; no information conveyed by color alone (chips carry text)
- No hover-only content; nothing collapses or hides

---

## Out of Scope

- Player annotations, pinning, re-ordering (Phase 5 / deferred)
- Links to teaching notes (Phase 5)
- New schema fields (`concern_category` rejected — existing `node_type` suffices)
- Vitals-derived "secret" findings (no case authors them; noted limitation)

---

## Verification Stack

1. `ruff check packages/satori packages/satori-api && ruff format --check packages/satori packages/satori-api`
2. `mypy --strict packages/satori/src packages/satori-api/src`
3. `pytest packages/satori packages/satori-api -q`
4. `cd packages/internal-affairs && npm run check`
5. `git status` — only expected files changed

---

## Commit Message Template

```
feat(P2-H03): active concerns panel — evidence board with server-composed findings

Engine:
- GameState.revealed_at records the game-minute each node revealed, at all
  three reveal sites (auto, action, pending); keys invariant with
  revealed_nodes

API:
- FindingResponse + GameStateResponse.findings (additive): evidence-board
  node types only, chronological deterministic order, authored content and
  structured data with reveal timestamps

Frontend:
- [card language and grouping per visual decision 1]
- flag chips from structured_data; T+N min reveal timestamps
- panel persists through case end beneath the outcome overlay

UD: 18px body text, AA contrast, no hover-only content, no hidden state.
```
