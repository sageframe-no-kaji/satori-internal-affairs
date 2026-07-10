# P2-H05: Emergency Mode

**Status:** IN PROGRESS — visual decisions taken (banner + grayed inline); implementing
**Phase:** 2
**Ho:** 05
**Depends on:** P2-H01 (VisibleTimer), P2-H02 (dashboard), P2-H04 (countdowns render), P2-H09 (survivable crisis, `emergency_timer` channel, `crisis_active` convention)

---

## Objective

When a crisis node fires, the dashboard visibly takes over; when the crisis resolves — by rescue, by treatment, or by case end — it visibly lets go. Three layers land together:

1. **Engine:** `emergency_active: bool` derived on `GameState` from the reserved `crisis_active` flag convention P2-H09 established.
2. **API:** `emergency_active` (and the already-present `emergency_timer`) surfaced on `GameStateResponse`; TypeScript mirror updated.
3. **Frontend:** emergency rendering mode driven by `state.emergency_active` — the emergency signature (visual decision 1), the locked-action treatment (visual decision 2), the emergency timer rendered exactly, wait correctly disabled (closing the `TODO(P2-H05)` in `ActionBar.svelte`), and a dedicated emergency event style in the narrative feed.

---

## Context

The engine already simulates emergencies; P2-H09 made them survivable and gave the crisis clock its own visibility channel. What is missing is entirely presentational: a player mid-crisis currently sees the same calm dashboard with fewer menu options, a wait button that still works, and no countdown. The design (ho-overview §P2-H05, game-design pitch) calls for the screen to *take over* — because the emergency is the one moment the design most needs to be felt.

Universal Design is load-bearing here, more than anywhere else: the player has severe ataxia, and this is the screen where seconds matter and motor precision collapses under stress. Every choice below is evaluated against that first.

---

## Design Decisions

### `emergency_active` derivation (determined — locked decision 4 + memo §2)

```
emergency_active = CRISIS_FLAG in state.flags and not state.case_ended
```

- **Start:** node_14 / node_21 are auto-reveal; their `on_reveal` sets `crisis_active` the same tick the crisis activates. ✓
- **Resolution:** cleared by `emergency_intervention` (P2-H09) and by node_17's albendazole reveal — both paths, same signal. ✓
- **Death / case end:** `crisis_active` is still set when node_16 ends the case; the `NOT case_ended` guard keeps the outcome screen out of emergency dress. ✓ (Identical condition to `compute_emergency_timer` — the two surfaces can never disagree; `emergency_timer` is non-None only when `emergency_active` is true.)
- **Edge cases (memo §2, verified in P2-H09's tests):** crisis-and-end same tick is deterministic and the API only surfaces final state; a wait that *enters* an emergency stays legal and returns with `emergency_active: true`; wait *during* an emergency is disabled in the UI (H06's decision, wired here).

No new engine mechanism: it is a flag check plus the existing case-ended bit. If implementation reveals that this derivation is insufficient, stop and escalate — do not invent.

### Emergency timer display (determined — ho-overview H05)

Exact remaining minutes, not approximated. The one place precision serves the design: the player is racing it.

### Locked-action knowledge (component shape)

During a crisis the engine removes locked actions from `available_actions`, so they vanish from `playable_actions`. To *show* them as locked (rather than have them disappear), the store snapshots the last non-emergency action groups and, while `emergency_active` is true, presents that snapshot in whatever treatment visual decision 2 selects. This is presentation memory — remembering what the server previously said, for display only. No medical logic crosses the Truth Line; the engine remains the sole authority on what is executable, and any attempt to execute a locked action still fails server-side.

### VISUAL DECISION 1 — Emergency state signature

**How does the screen say "EMERGENCY"?** — **DECIDED (practitioner, 2026-07-10): Option B, top-anchored emergency banner.** Full-width crimson banner at the top of the dashboard grid carrying the crisis label (server-supplied via `emergency_timer.label` — the frontend never names the crisis) and the countdown in exact minutes, large and centered. Rejected: A (screen-edge border) reads as chrome and gives the timer no home; C (central panel) hides vitals/narrative exactly when they matter and doubles the layout churn across two authored crises.

Interpretation detail: "investigation panels dim to ~60%" applies to Active Concerns and Pending Results. The narrative feed stays fully legible (the crisis narration lives there — it is meant to be read mid-crisis) and the vitals strip stays undimmed (the clinician watches the monitor); VitalsStrip already renders the critical register on its own.

Known costs, managed: one-time downward shift when the banner enters (the body row absorbs it; the action bar does not move; slide animation suppressed under `prefers-reduced-motion`); eye-up/hand-down split (answered by decision 2 — the intervention button gets louder in a bar whose layout never changes, and receives focus when the crisis starts).

### VISUAL DECISION 2 — Locked action treatment

**How do investigation actions render while locked?** — **DECIDED (practitioner, 2026-07-10): Option A, grayed inline with reason.** Locked actions stay in their exact positions at `--emergency-locked-opacity` (0.35) with "Locked: emergency in progress" visible on keyboard focus as well as hover, and in the `aria-label`. Playable and locked lists both arrive sorted, so merging and re-sorting reproduces the calm ordering — no button moves when a crisis starts or ends. `emergency_intervention` renders as a single prominent one-press button during crises (no dropdown between the player and the rescue) and is focused when the emergency begins. Rejected: B (emergency-only bar) forces target re-acquisition after every rescue; C (sidebar) shrinks targets and adds a second scan region.

---

## Deliverables

### 1. Engine: `packages/satori/src/satori/game_state.py` + `engine.py`

- `GameState.emergency_active: bool = False`
- `compute_emergency_active(state) -> bool` beside `compute_emergency_timer`
- Set at the three derived-state sites (`_initialize_state`, `execute_action`, `_execute_wait`)

### 2. API: `models.py`, `serialisation.py`

- `GameStateResponse.emergency_active: bool = False`; serialised from state. Additive.

### 3. Frontend: types + store

- `types.ts`: `emergency_active: boolean`, `emergency_timer: VisibleTimer | null` on `GameState` (the latter mirrors the P2-H09 API field; H05 is its first consumer)
- `gameStore.svelte.ts`: `emergencyActive`, `emergencyTimer` getters; last-known action-groups snapshot for the locked-action treatment

### 4. Frontend: emergency rendering

- Dashboard-level emergency dress per visual decision 1 (tokens only; new tokens added to `tokens.css` as needed — no component-local hex/px)
- `ActionBar.svelte`: wait disabled during emergencies with reason (closes `TODO(P2-H05)`); locked investigation actions per visual decision 2; `emergency_intervention` surfaced prominently during crises
- `NarrativeFeedPanel.svelte`: emergency event entries styled distinctly (crisis reveals / crisis narration)
- Emergency timer rendered inside the emergency signature, exact minutes

### 5. Tests

- Engine: `emergency_active` lifecycle across crisis → rescue → second crisis → death/treatment/timeout (extends `test_crisis_rescue.py`)
- API: `emergency_active` in responses (serialisation + endpoint)
- `npm run check` for the frontend (no component test harness exists in this project yet; visual verification is the practitioner's watch)

---

## Universal Design checklist (verify before commit)

- Emergency action button ≥ `--touch-target-pref`; all interactives ≥ 60px with 16px gaps
- Lock reasons visible on focus as well as hover (no hover-only)
- Countdown legible at `--font-size-xl` or larger; WCAG AA contrast in the emergency palette
- No layout shift that forces re-acquiring targets mid-crisis beyond what the chosen signature itself introduces
- Keyboard: emergency action reachable and focusable first in the action bar during a crisis

---

## Out of Scope

- Audio cues (Phase 6)
- Multiple concurrent emergencies (schema allows; the case doesn't author; noted limitation)
- Live LLM narration of emergency events (P2-H08 — the feed styles whatever text it has)
- Any engine mechanism beyond the flag-check derivation (escalate instead)

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
feat(P2-H05): emergency mode — engine signal, API surface, dashboard takeover

Engine:
- GameState.emergency_active derived from the reserved crisis_active flag
  AND NOT case_ended (memo §2); computed alongside emergency_timer at all
  derived-state sites — the two surfaces cannot disagree

API:
- GameStateResponse.emergency_active (additive); TS types mirror both
  emergency fields

Frontend:
- [emergency signature per visual decision 1]
- [locked-action treatment per visual decision 2]
- emergency timer rendered exact; wait disabled during emergencies with
  reason (closes TODO(P2-H05) in ActionBar)
- narrative feed emergency event style
- tokens extended: [list]

UD: 60px+ targets, 16px gaps, focus-visible reasons, AA contrast maintained
under the emergency palette.
```
