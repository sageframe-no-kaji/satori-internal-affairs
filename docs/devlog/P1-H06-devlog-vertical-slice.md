# Phase 1 Devlog 004 — Vertical Slice (Ho 06)

**Date:** 2025-07
**Task:** `tasks/P1-H06-agent-task-vertical-slice.md`
**Status:** Complete

---

## What Was Built

Ho 06 closes the "action grammar gap": before this work, the engine's
`available_actions` frozenset contained only base keys (`order_labs`,
`history_focused`, …) but every meaningful node in the case required a
fully-qualified `base:subcategory` string. The UI had no way to know
which subcategory strings existed, so the game was unplayable beyond the
three root-level actions.

### Changes

| Layer | File | Change |
|---|---|---|
| Engine | `packages/satori/src/satori/engine.py` | `get_playable_actions() -> frozenset[str]` added |
| Engine tests | `packages/satori/tests/test_engine_playable_actions.py` | 15 new tests |
| API models | `packages/satori-api/src/satori_api/models.py` | `playable_actions: list[str]` on `SessionResponse` + `ActionResponse` |
| API serialiser | `packages/satori-api/src/satori_api/serialisation.py` | `build_session_response()` populates `playable_actions` |
| API main | `packages/satori-api/src/satori_api/main.py` | `execute_action()` inline response populates `playable_actions` |
| API tests | `packages/satori-api/tests/test_api.py` | 5 new assertions on `playable_actions` field |
| Frontend types | `packages/internal-affairs/src/lib/types.ts` | `playable_actions: string[]` on both response interfaces |
| Frontend store | `packages/internal-affairs/src/lib/stores/gameStore.svelte.ts` | `availableActions` now reads `resp.playable_actions` |
| Frontend component | `packages/internal-affairs/src/lib/components/ActionMenu.svelte` | `groupActions()` bug fixed (was splitting on `_`, now splits on `:` then on `_`) |

---

## Algorithm: `get_playable_actions()`

The method scans all nodes in the case and for each applies a six-step
filter. If a node passes all six, it contributes an action string to the
result set.

```
for node in case.nodes:
  1. skip if already in revealed_nodes
  2. skip if in pending_reveals (lab ordered, awaiting timer)
  3. skip if not in active_nodes (activation conditions not met)
  4. skip if node.reveal is None (controller node — e.g. node_00_initial_locks)
  5. skip if node.reveal.auto_reveal is True (engine-triggered — e.g. node_14_seizure_crisis)
  6. skip if node.reveal.action is None
  7. skip if node.reveal.action not in available_actions (base action locked)
  8. skip if node.reveal.conditions fail evaluation

  → emit "base:subcategory" if subcategory present, else "base"

for base_action in available_actions:
  if base_action not in ANY node's reveal.action across the entire case:
    → emit bare base_action (true orphan with no content node)
```

The orphan logic specifically excludes actions whose nodes happen to be
all-revealed (e.g. `history_general` after `node_01` is revealed). Only
actions that have **zero** nodes anywhere in the case definition are
treated as orphans. This ensures `emergency_intervention` (no node) is
always surfaceable, while spent actions cleanly drop out.

---

## Boundary Checklist

| Boundary | Node / Scenario | Expected Behaviour | Verified |
|---|---|---|---|
| Null-reveal controller | `node_00_initial_locks` (reveal=null) | Never appears in playable set | ✅ |
| Auto-reveal crisis | `node_14_seizure_crisis` (auto_reveal=True) | Never player-triggered | ✅ |
| Locked base action | `node_15_steroid_response` (start_treatment locked) | `start_treatment:steroids` absent at init | ✅ |
| Orphan bare action | `emergency_intervention` (no node) | Always present when unlocked | ✅ |
| Spent action drops | `history_general` after node_01 revealed | `history_general` exits playable set | ✅ |
| Pending reveal excluded | `order_labs:cbc` after execution | Drops from playable set while timer runs | ✅ |
| Flag-gated activation | `node_03_neuro_exam` needs `seizure_with_aphasia` | `physical_exam_focused:neuro` absent until flag set | ✅ |
| Subcategory collision | Multiple nodes per base (`order_labs:cbc`, `order_labs:metabolic_panel`) | Both surface independently | ✅ |
| Return type contract | `frozenset[str]` | Confirmed immutable, hashable | ✅ |

---

## Simulated Playthrough

Verified via direct Python invocation against the live engine.

```
Initial playable:
  emergency_intervention
  history_general
  physical_exam_general

→ execute history_general
  - node_01_chief_complaint revealed
  - flags set: headaches_two_weeks, seizure_with_aphasia
  - actions unlocked: history_focused, order_labs, physical_exam_focused

  Playable becomes:
    emergency_intervention
    history_focused:medications
    order_labs:cbc
    order_labs:metabolic_panel
    physical_exam_focused:neuro
    physical_exam_general        ← still unrevealed

→ execute physical_exam_general
  - node_02_general_exam revealed
  - flags set: general_exam_done
  - actions unlocked: order_labs (already unlocked)
  - node_13_husband_diego activates (needs general_exam_done)

  Playable becomes:
    emergency_intervention
    history_focused:family       ← new: node_13 activated
    history_focused:medications
    order_labs:cbc
    order_labs:metabolic_panel
    physical_exam_focused:neuro

→ execute order_labs:cbc
  - node_04 enters pending_reveals (timer running)

  Playable becomes: (order_labs:cbc removed, metabolic_panel remains)
    emergency_intervention
    history_focused:family
    history_focused:medications
    order_labs:metabolic_panel
    physical_exam_focused:neuro
```

---

## `available_actions` vs `playable_actions`

An intentional design decision: both fields are kept in the API response.

- `available_actions` (from `GameState`): the raw engine-level base key
  frozenset. Consumed by the engine itself to validate submitted actions.
  The base key is what `execute_action()` checks via `_is_valid_action()`.
- `playable_actions` (new): the UI-ready set of fully-qualified action
  strings. The frontend uses this exclusively for rendering the action
  menu and submitting actions.

This separation preserves the engine's clean base-key validation contract
while giving the UI exactly the strings it needs.

---

## ActionMenu Grouping Fix

**Bug:** `groupActions()` split action strings on `_` to derive group keys:
```typescript
const base = action.split('_')[0];
// 'order_labs:cbc' → 'order'  ← wrong group key
```

**Fix:** split on `:` first to isolate the base key, then humanise it:
```typescript
const baseKey = action.split(':')[0];          // 'order_labs'
const groupKey = baseKey.split('_')            // ['order', 'labs']
  .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
  .join(' ');                                  // 'Order Labs'
```

Result: `order_labs:cbc` and `order_labs:metabolic_panel` now correctly
appear under a single **Order Labs** group header.

---

## Phase 2 Extensibility Audit

Things that will need revisiting in subsequent phases:

| Area | Note |
|---|---|
| `get_playable_actions()` cost | O(n·c) over all nodes × conditions. Acceptable for ≤50 nodes. For large cases, cache invalidation on state change should be considered. |
| Reveal `conditions` field | Currently only flag conditions are expected. If new condition types are added (e.g. `time_elapsed`, `vitals_threshold`) `_evaluate_condition` already handles them — no change to `get_playable_actions()` needed. |
| Multi-unlock per base | If two nodes share a base but should be offered sequentially (not simultaneously), gating via flags already handles this — no structural change. |
| Timer expiry and re-activation | Nodes that expire and re-activate (if that feature is added) would need `expired_nodes` excluded from playable, which the current active_nodes check does implicitly. |
| Frontend `available_actions` field | The store no longer reads `available_actions` from the API response. The field is still present in the response for engine-level consumers (debug, game master view). Safe to deprecate in P2 if desired. |

---

## Test Coverage Summary

| Suite | Tests | Result |
|---|---|---|
| `test_engine_playable_actions.py` | 15 | ✅ 15 passed |
| `test_api.py` (new assertions) | +5 | ✅ 34 total passed |
| Full Python suite (`satori` + `satori-api`) | 267 | ✅ all passed |
| Frontend `svelte-check` | — | ✅ 0 errors, 0 warnings |
