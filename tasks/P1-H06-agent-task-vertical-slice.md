# P1-H06: Vertical Slice Integration

**Status:** DONE
**Phase:** 1
**Ho:** 06
**Depends on:** P1-H05 (all five prior milestones complete and passing)

---

## Objective

Connect all layers into a playable end-to-end game, fix the one known broken loop (the action grammar gap), and verify that the architectural boundaries are real and enforced. The deliverable is a working vertical slice plus a boundary verification checklist.

**Phase 2 mechanics and UI/UX redesign are explicitly out of scope.** This Ho makes the system work correctly as designed. Phase 2 makes it richly playable. The seams between them must be clean.

---

## Context: What's Complete

All five prior milestones are production-quality:

- **Satori engine** — 247 tests passing, deterministic, full flag/timer/cascade system
- **satori-api** — FastAPI bridge with in-memory sessions, all endpoints tested
- **Internal Affairs frontend** — SvelteKit UI with ActionMenu, EventLog, VitalsPanel, OutcomeScreen
- **LLM narration** — MockNarrator in place; real LLM drop-in is a one-line swap
- **Case** — 18-node neurocysticercosis case with gated unlock chains

---

## The One Broken Loop: Action Grammar Gap

**The problem:** `available_actions` in `GameState` contains only base action keys (`order_labs`, `history_focused`, `start_treatment`). The UI renders these as buttons. Clicking one submits just `"order_labs"` — but every meaningful node in the case is triggered by subcategory actions like `"order_labs:cbc"`, `"history_focused:dietary"`, `"start_treatment:albendazole"`. The engine validates subcategory actions correctly (it checks the base key), but the frontend never learns which subcategories are available.

**The result:** A player can click buttons and see narration for base actions that auto-reveal. But the entire gated unlock chain — the actual case — is unreachable through the UI.

**The fix:** Compute `playable_actions` at the engine level — the full set of currently executable `base:subcategory` strings — and surface this through the API. The frontend's `ActionMenu` already handles subcategory rendering correctly (`"order_labs:cbc"` → "Order Labs: CBC"). It only needs the right data.

---

## Design Decision: How to Compute Playable Actions

The source of truth for what subcategory actions exist is the case's node definitions. Each unrevealed node has a `reveal_rule` containing:
- `action`: the base action that triggers it (`"order_labs"`)
- `subcategory`: the parameter that specifies it (`"cbc"`)
- `conditions`: optional additional flag gates

**Algorithm:**
For every case node:
1. Skip if already in `state.revealed_nodes` (done)
2. Skip if already in `state.pending_reveals` (ordered, waiting for results)
3. Skip if not in `state.active_nodes` (not yet activated by flag gates)
4. Skip if `node.reveal` is `None` (controller nodes like `node_00_initial_locks`)
5. Skip if `node.reveal.auto_reveal` is `True` (handled automatically, not player-triggered)
6. Skip if `node.reveal.action` is `None` (no player action triggers it)
7. Check: is `node.reveal.action` (the base key) in `state.available_actions`? If not, skip (locked)
8. Check: if `node.reveal.conditions` is not `None`, evaluate all via `ConditionEvaluator`. If any fail, skip
9. Build action string: if `node.reveal.subcategory` is set → `"base:subcategory"`, else `"base"`
10. Add to result set (deduplication is implicit via `set`)

**Collisions:** Multiple nodes can share the same `"order_labs:cbc"` action key (future cases may have parallel nodes). Deduplicate. A playable action appears once regardless of how many nodes it would trigger.

**Base-only actions:** Some nodes trigger on `action="history_general"` with no subcategory. These should appear as `"history_general"` (no colon). This maintains the current behavior for free-form base actions.

**Orphan base actions:** `emergency_intervention` is in `action_costs` (and thus `available_actions`) but no node uses it as a reveal trigger. It should still appear in `playable_actions` as a base key if it's unlocked, so the player can submit it (the engine accepts it — it just won't reveal anything). Include any unlocked base action that has no subcategory nodes as itself.

**Placement:** New method `get_playable_actions() -> frozenset[str]` on `SatoriEngine`. This is the authority. The engine already has `_node_map` and the condition evaluator; this is a read-only scan over it.

---

## Deliverables

### 1. Engine: `get_playable_actions()`

**File:** `packages/satori/src/satori/engine.py`

New public method alongside the existing `get_available_actions()`:

```python
def get_playable_actions(self) -> frozenset[str]:
    """Return all currently executable action strings, including subcategories.

    Scans unrevealed nodes for their reveal rules. For each node whose
    base action is unlocked and whose conditions are satisfied, includes
    the fully-qualified action string (base:subcategory or base).

    This is what the UI should display — not the raw available_actions
    frozenset, which only contains base keys.
    """
```

**Expected initial playable set (after `node_00_initial_locks` locks fire):**
Only `history_general`, `physical_exam_general`, and `emergency_intervention` are unlocked. Nodes `node_01` and `node_02` are starts_active and use those base actions with no subcategory. `emergency_intervention` has no nodes but is unlocked.

**Tests:** `packages/satori/tests/test_engine_playable_actions.py`
- At initialization: returns `{"history_general", "physical_exam_general", "emergency_intervention"}`
- After executing `history_general` (reveals `node_01`, unlocks `history_focused`, `order_labs`, `physical_exam_focused`): subcategory actions appear (e.g., `order_labs:cbc`, `history_focused:dietary`, `physical_exam_focused:neuro`)
- `history_general` is no longer in playable set after `node_01` is revealed (no remaining nodes use it)
- Revealed node: its action is no longer in playable set (unless another unrevealed node shares the same action key)
- Locked base action: its subcategory actions are absent even if node is active (e.g., `start_treatment:steroids` is not playable because `start_treatment` is locked)
- Condition-gated subcategory: absent until flag is set
- Pending reveal: node in `pending_reveals` does not contribute to playable actions (already ordered)
- Null reveal node: `node_00_initial_locks` (reveal=null) does not contribute to playable actions
- Auto-reveal node: `node_14_seizure_crisis` (auto_reveal=True) does not appear in playable actions

### 2. API: Thread `playable_actions` through responses

**Files:** `packages/satori-api/src/satori_api/models.py`, `serialisation.py`

Add `playable_actions: list[str]` field to `SessionResponse` and `ActionResponse`, alongside the existing `available_actions`. Call `engine.get_playable_actions()` in both response construction sites.

Keep `available_actions` (base keys) in the response — it's consumed by tests and may be useful for Phase 2 UI logic (e.g., showing which categories are unlocked at the category level).

**Two construction sites need updating (not one):**

1. `serialisation.py` → `build_session_response()` — already receives the engine instance. Add `playable_actions=sorted(engine.get_playable_actions())` to the `SessionResponse` constructor.

2. `main.py` → `execute_action()` endpoint — builds `ActionResponse` **inline** (not via `serialisation.py`). Add `playable_actions=sorted(engine.get_playable_actions())` to the `ActionResponse` constructor call in this endpoint.

**Tests:** `packages/satori-api/tests/test_api.py`
- New session response includes `playable_actions`
- `playable_actions` contains `"history_general"` and `"physical_exam_general"` at start (auto-unlocked)
- After executing `"history_general"`, `playable_actions` updates correctly
- `available_actions` (base keys) still present in response

### 3. Frontend: Use `playable_actions` in the store

**File:** `packages/internal-affairs/src/lib/stores/gameStore.svelte.ts`

The store currently maintains an `availableActions` state variable, populated from `resp.available_actions` in both `startSession()` and `performAction()`. Change both to read from `resp.playable_actions` instead.

Update `types.ts`:
- Add `playable_actions: string[]` to both `SessionResponse` and `ActionResponse` interfaces

The store passes `game.availableActions` to `ActionMenu` via the `+page.svelte` component's `actions` prop. No changes needed to `ActionMenu.svelte` — it already handles subcategory rendering correctly (`"order_labs:cbc"` → "Order Labs: CBC").

Also update the `groupActions()` function in `ActionMenu.svelte` — it currently groups by the first word before `_` (e.g., `history_general → "History"`, `history_focused:dietary → "History"`). With subcategory actions, the grouping should use the full base action (everything before `:`), not just the first word. Currently `order_labs:cbc` groups under "Order" and `order_imaging:ct_head` also groups under "Order" — they should be separate groups. Fix: split on `:` first, then humanise the base as the group key.

### 4. Vertical Slice Verification

**File:** `docs/devlog/phase-1-devlog-004-vertical-slice.md`

A documented manual playthrough proving the system works end-to-end. Must include:

- Startup sequence: `make dev-api` + `make dev-frontend`
- Initial state: actions visible in UI match expected unlocked set
- Action sequence through key decision points:
  1. `history_general` → narration fires, stats update
  2. `history_focused:dietary` → unlocks if conditions met
  3. `order_labs:cbc` → pending result queued, clock advances
  4. Wait actions / additional history until CBC returns
  5. Branch point: steroid path vs. albendazole path
  6. Case resolution screen with outcome tier
- Determinism check: two identical action sequences produce identical final `flags` set
- Screenshot or terminal output evidence for each key step

### 5. Boundary Verification Checklist

Included in the devlog above. Confirm each boundary holds:

| Boundary | Description | Verification method |
|---|---|---|
| Boundary 1 — The Case Line | Frontend never reads case JSON directly | `grep -r "neurocysticercosis.json" packages/internal-affairs/src/` returns nothing |
| Boundary 2 — The Truth Line | Frontend never imports Python code | `packages/internal-affairs/src/` contains no `.py` imports |
| Boundary 3 — The Narration Line | Frontend never calls LLM directly | No API key or LLM call in any `.svelte` or `.ts` file |
| Boundary 4 — The Determinism Rule | Same case + same actions = same outcome | Run test_engine_determinism.py, plus manual two-session check |

### 6. Phase 2 Extensibility Audit

Review the following integration points and confirm they require no engine surgery to implement in Phase 2. Document findings in the devlog.

| P2 Feature | What's Already In Place | What Phase 2 Needs to Add |
|---|---|---|
| Visible pending results (lab ETAs) | `state.pending_reveals: dict[str, int]` is in `GameState` and serialised by API | Frontend renders it — no engine/API change |
| Visible deterioration timers (diegetic) | `state.timers: dict[str, int]` is in `GameState` and serialised | Frontend decides which to show — no engine/API change |
| Emergency visual state | `state.flags` includes `crisis_active` when seizure fires | Frontend derives `emergency_active` from flags — no engine change. Phase 2 may add `emergency_active: bool` as a computed field in `GameState` for convenience |
| Emergency action restriction | Lock/unlock mechanism already fires on `node_14_seizure_crisis` reveal | Already works — Phase 2 only needs frontend to visually distinguish restricted state |
| Diagnosis commitment action | `commit_diagnosis` would be a new base action key in `action_costs` + new nodes | Requires only case authoring + a new action category — no engine changes |
| Treatment consequences | Already working via `on_reveal` effects on treatment nodes | Case authoring only |
| LLM narrator swap | `MockNarrator` implements `NarratorProtocol` in `llm-client` | Replace `MockNarrator` instance in `narrator_bridge.py` — one line |
| Difficulty scaling | Not yet designed | Phase 2 decision: timer durations in case JSON, no engine changes |
| Multiple cases | `DEFAULT_CASE_PATH` is hardcoded in `gameStore.svelte.ts` | Phase 2: case picker endpoint + frontend selector |

---

## Acceptance Criteria

- [ ] `pytest packages/satori packages/satori-api --tb=short -q` — all tests pass, including new `test_engine_playable_actions.py`
- [ ] `cd packages/internal-affairs && npm run check` — zero TypeScript errors
- [ ] Manual playthrough: `make dev-api` + `make dev-frontend` → actions include subcategories → `order_labs:cbc` submittable → CBC results arrive → case reaches outcome screen
- [ ] Determinism: two identical action sequences in separate sessions produce identical final `GameState.flags`
- [ ] Boundary checklist: all four boundaries verified
- [ ] Phase 2 extensibility audit: all items confirmed no-engine-surgery required
- [ ] Devlog committed with playthrough evidence and checklist

---

## What Is NOT In Scope

These are deferred to Phase 2. Do not implement them here even if they seem small:

- Visible timer countdowns in the UI (pending results, deterioration)
- Emergency visual state (red border, restricted action bar, audio)
- Diagnosis commitment mechanic (`commit_diagnosis` action)
- Dashboard layout redesign (Active Concerns panel, Pending Results panel)
- Any gameplay tuning (timer durations, RMS scoring, difficulty)
- Multiple case selection or case picker
- User accounts or session persistence
- LLM narrator swap to real API

If any of these are needed to make the vertical slice technically work, that is a sign of a deeper structural problem — escalate rather than patch.

---

## Architecture Notes

### Why `serialisation.py` already has engine access

`build_session_response()` in `serialisation.py` already takes a `SatoriEngine` instance — no signature change needed. Just add `playable_actions=sorted(engine.get_playable_actions())` to the constructor call.

The `execute_action()` endpoint in `main.py` builds `ActionResponse` inline with local variables `engine`, `state`, `events`. It already has the engine reference — just needs the additional field.

### Why `ActionMenu.svelte` needs a grouping fix

The current `groupActions()` function splits on `_` and groups by the first word. This means:
- `order_labs:cbc` → group "Order"
- `order_imaging:ct_head` → group "Order"
- `history_general` → group "History"
- `history_focused:dietary` → group "History"

Labs and imaging end up in the same "Order" group. The fix: split on `:` first to get the base action, then use the full humanised base as the group key:
- `order_labs:cbc` → group "Order Labs"
- `order_imaging:ct_head` → group "Order Imaging"
- `history_general` → group "History General"
- `history_focused:dietary` → group "History Focused"

### Why `available_actions` stays in the response

`available_actions` (base keys) is the *capability* signal — what action categories the player has unlocked. `playable_actions` (full strings) is the *executable* set — what they can actually submit. Both are useful:
- The frontend action menu uses `playable_actions`
- Phase 2 UI may use `available_actions` to show category-level unlock state (e.g., "Labs Unlocked" indicator in the Active Concerns panel)
- Tests already assert on `available_actions` — backward compatibility preserved

---

## Commit Message Template

```
feat(P1-H06): vertical slice — playable subcategory actions + boundary verification

- Engine: SatoriEngine.get_playable_actions() derives full base:subcategory
  action strings from unrevealed node reveal rules
- API: playable_actions added to SessionResponse and ActionResponse
- Frontend: gameStore reads playable_actions; ActionMenu subcategory buttons work
- Tests: test_engine_playable_actions.py covers unlock/lock/condition gates
- Devlog: end-to-end playthrough documented with boundary checklist
- Phase 2 extensibility audit: all P2 features confirmed no-surgery required

Phase 1 complete.
```
