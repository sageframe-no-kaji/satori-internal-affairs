# P2-H01: Engine Surface Prep

**Status:** READY
**Phase:** 2
**Ho:** 01
**Depends on:** Phase 1 complete (P1-H06)

---

## Objective

Add the small set of engine-level surface primitives that the rest of Phase 2's UI work needs. Three things land together in one cohesive engine ho:

1. A **`diegetic: bool`** field on `NodeTimer` so cases can mark which timers the player's character would know about.
2. A derived **`visible_timers: list[VisibleTimer]`** field on `GameState` that the API surfaces and the UI renders.
3. A built-in **`wait`** action with `wait:15`, `wait:30`, `wait:60` subcategories that advances the clock without other clinical effects.

Plus updating the Maria Santos case to mark its lab and imaging timers as diegetic, and surfacing `visible_timers` through the satori-api response.

**No UI work in this ho.** The frontend doesn't render any of this yet — that's later hos. This ho gives them the data they need.

---

## Context: Why This Comes First

The Phase 2 [System Design](../satori-internal-affairs-system-design.md) commits to a diegetic / non-diegetic timer split (the player sees the timers their character would know about; deterioration stays hidden). The Phase 2 [Ho Overview](../ho-overview.md) commits to the wait/observe action as first-class. Both need engine-level support before any UI can show or use them.

Phase 1 already exposes timers and pending reveals on `GameState`, but the UI today can't distinguish "you ordered this lab and you know it takes 30 minutes" from "the patient is silently deteriorating on a 180-minute clock." The diegetic flag is how the case tells the engine which is which; `visible_timers` is what the engine exposes for the UI to render.

---

## Design Decisions

### Diegetic flag

Add `diegetic: bool` as an optional field on the `NodeTimer` model and JSON Schema. Default `false`. Backward-compatible — existing cases (the only one is Maria Santos) declare it explicitly per timer.

```python
class NodeTimer(BaseModel):
    duration_minutes: int
    stages: list[TimerStage] = []
    diegetic: bool = False   # NEW
    # ... existing fields
```

### `VisibleTimer` dataclass

Lives in `packages/satori/src/satori/game_state.py` alongside the other engine value types. Frozen dataclass.

```python
@dataclass(frozen=True)
class VisibleTimer:
    label: str                # derived from node.display_name
    remaining_minutes: int
    source: Literal["pending_reveal", "active_timer"]
    node_id: str              # for the UI to key off
```

`label` comes from the source node's `display_name` field (`Node.display_name`, already exists per the Phase 1 schema). If `display_name` is missing or empty, fall back to a humanised version of `node_id`.

### `GameState.visible_timers` derivation

Add as a derived field on `GameState`. Since `GameState` is a frozen dataclass with immutable updates, `visible_timers` must be computed and set whenever a new `GameState` is constructed via the engine's tick logic — not lazily, so equality and serialisation behave predictably.

The simplest path: add a helper on the engine (or as a free function in `game_state.py`) called `compute_visible_timers(state, case) -> tuple[VisibleTimer, ...]` and call it from the same code paths that already construct new `GameState` instances.

**What counts as visible:**

1. **Every entry in `state.pending_reveals`** (these are diegetic by definition — the player ordered the lab/imaging and knows it takes time). Source: `"pending_reveal"`.
2. **Every node in `state.active_nodes`** whose `node.timer is not None` AND `node.timer.diegetic is True`. The timer's remaining time comes from `state.timers[node_id]`. Source: `"active_timer"`.

Order the list deterministically (by `remaining_minutes` ascending, then by `node_id` alphabetical) so test assertions and UI rendering are stable.

Use `tuple[VisibleTimer, ...]` not `list[VisibleTimer]` since `GameState` is frozen and immutable.

### Built-in `wait` action

The wait action is not authored in cases — it's a built-in. Cases never declare it in `action_costs`, never wire it into nodes, never reveal it.

**Engine handling:**

- `SatoriEngine.execute_action(action_str)` recognises the `wait` base key BEFORE the standard `_is_valid_action()` gate.
- Subcategory must parse as an integer minute count from the allowed set `{15, 30, 60}`. Any other subcategory (`wait`, `wait:0`, `wait:45`, `wait:foo`) raises `InvalidActionError` (or the existing engine error class — match the project's convention).
- The wait action advances the game clock by the parsed minute count, lets all the standard tick logic run (timers tick, pending reveals advance, activations cascade, vitals recompute, end conditions evaluate), and emits a new `Waited` event with the duration.
- The wait action is disabled during emergency (P2-H05 will set the gate via the same mechanism that locks other actions — for this ho, no special emergency handling is required; the action remains available).

**Why not just author it as a case action?** It would force every case to know about it, every case author to repeat themselves, and would let cases accidentally redefine the cost. Built-in is cleaner.

### New event type: `Waited`

Add `Waited` to `events.py` alongside the existing event types. Fields: `duration_minutes: int`. Used by the UI (later) to narrate "30 minutes pass" in the event log.

### `available_actions` does NOT list wait

`wait` is built-in; it doesn't appear in `state.available_actions`. The UI knows wait exists (it's spec'd in the action bar). The engine accepts `wait:N` regardless of `available_actions`.

`get_playable_actions()` does NOT include wait actions either — same reason. The action bar surfaces wait separately.

---

## Deliverables

### 1. Schema: `schemas/case-definition.schema.json`

Add the `diegetic` field to the `NodeTimer` definition. Boolean, default false, not required.

### 2. Pydantic model: `packages/satori/src/satori/models/case_definition.py`

```python
class NodeTimer(BaseModel):
    # ... existing fields ...
    diegetic: bool = False
```

Make sure model_validate accepts both the field present and absent.

### 3. `VisibleTimer` dataclass + GameState field: `packages/satori/src/satori/game_state.py`

```python
from typing import Literal

@dataclass(frozen=True)
class VisibleTimer:
    label: str
    remaining_minutes: int
    source: Literal["pending_reveal", "active_timer"]
    node_id: str

@dataclass(frozen=True)
class GameState:
    # ... existing fields ...
    visible_timers: tuple[VisibleTimer, ...] = ()
```

Default empty tuple so any code constructing a `GameState` directly still works.

### 4. `compute_visible_timers` helper

Pick the cleanest location — likely `state_checkers.py` since it already coordinates derived-state computation. Sketch:

```python
def compute_visible_timers(
    state: GameState,
    case: CaseDefinition,
) -> tuple[VisibleTimer, ...]:
    timers: list[VisibleTimer] = []

    # Pending reveals: always diegetic
    for node_id, remaining in state.pending_reveals.items():
        node = case.nodes_by_id.get(node_id)   # or however nodes are indexed
        label = (node.display_name if node and node.display_name else _humanise(node_id))
        timers.append(VisibleTimer(
            label=label,
            remaining_minutes=remaining,
            source="pending_reveal",
            node_id=node_id,
        ))

    # Active timers: only if node.timer.diegetic
    for node_id, remaining in state.timers.items():
        node = case.nodes_by_id.get(node_id)
        if node is None or node.timer is None or not node.timer.diegetic:
            continue
        if node_id not in state.active_nodes:
            continue
        label = (node.display_name if node.display_name else _humanise(node_id))
        timers.append(VisibleTimer(
            label=label,
            remaining_minutes=remaining,
            source="active_timer",
            node_id=node_id,
        ))

    timers.sort(key=lambda t: (t.remaining_minutes, t.node_id))
    return tuple(timers)
```

Use whatever node-indexing scheme already exists in the engine (don't invent one). If there isn't a fast lookup, a list scan over `case.nodes` is fine for ≤50 nodes.

### 5. Wire `visible_timers` into every GameState construction site

Every place the engine constructs a new `GameState` (in `state_checkers.py`, `effect_executor.py`, etc.) must include `visible_timers=compute_visible_timers(new_state, self.case)`. The engine has the case reference; helpers may need it passed in.

### 6. Wait action handling: `packages/satori/src/satori/engine.py`

Intercept in `execute_action`:

```python
WAIT_DURATIONS = {15, 30, 60}

def execute_action(self, action_str: str) -> tuple[GameState, list[Event]]:
    base, subcategory = parse_action(action_str)
    if base == "wait":
        return self._execute_wait(subcategory)
    # ... existing logic
```

```python
def _execute_wait(self, subcategory: str | None) -> tuple[GameState, list[Event]]:
    if subcategory is None:
        raise InvalidActionError("wait requires a duration: wait:15, wait:30, or wait:60")
    try:
        duration = int(subcategory)
    except ValueError:
        raise InvalidActionError(f"wait duration must be an integer, got {subcategory!r}")
    if duration not in WAIT_DURATIONS:
        raise InvalidActionError(f"wait duration must be one of {sorted(WAIT_DURATIONS)}, got {duration}")

    waited_event = Waited(duration_minutes=duration)
    new_state, tick_events = self._tick(duration)   # whatever the engine calls its time-advance method
    return new_state, [waited_event, *tick_events]
```

Match the existing engine's error-class convention; the project may use a different name than `InvalidActionError`.

### 7. New event: `Waited`

In `packages/satori/src/satori/events.py`:

```python
@dataclass(frozen=True)
class Waited(Event):
    duration_minutes: int
```

Export from `__init__.py` alongside the other event types.

### 8. Case update: `cases/example-neurocysticercosis.json`

Mark every timer on a lab/imaging result node as `diegetic: true`. Inspect each node with a `timer` block; the diegetic ones are the ones that represent things the player ordered (CBC, metabolic panel, CT, MRI). The biological deterioration timers (`node_09_headache_progression`, etc.) stay non-diegetic (default false; can be omitted).

Read the case file, identify each timer, set the flag, save.

### 9. API: `packages/satori-api/src/satori_api/models.py`

Add `VisibleTimerResponse`:

```python
class VisibleTimerResponse(BaseModel):
    label: str
    remaining_minutes: int
    source: Literal["pending_reveal", "active_timer"]
    node_id: str
```

Add `visible_timers: list[VisibleTimerResponse]` to `GameStateResponse`.

### 10. API: `packages/satori-api/src/satori_api/serialisation.py`

Serialize `state.visible_timers` (tuple) → list of `VisibleTimerResponse` in `build_session_response` and any other site that constructs `GameStateResponse`.

---

## Tests

### Engine

New test file: `packages/satori/tests/test_visible_timers.py`

Cases to cover:
- Empty state → empty visible_timers
- Pending reveal present → appears as `source="pending_reveal"`
- Active diegetic timer → appears as `source="active_timer"`
- Active non-diegetic timer → does NOT appear
- Active timer whose node is not in `active_nodes` → does NOT appear
- Multiple of each kind → all appear, sorted by `(remaining_minutes, node_id)`
- Label falls back to humanised node_id when `display_name` missing/empty

New test file: `packages/satori/tests/test_wait_action.py`

Cases to cover:
- `wait:15` advances clock by 15, emits Waited, returns expected tick events
- `wait:30`, `wait:60` likewise
- `wait` (no subcategory) raises
- `wait:0`, `wait:45`, `wait:foo` raise with informative messages
- Wait correctly triggers pending reveal that becomes ready in the interval
- Wait correctly triggers a deterioration timer stage if duration crosses the threshold
- Wait integrates with the standard tick (vitals recompute, end conditions evaluate)
- Determinism: same wait sequence from same start state → same outcome

### Existing tests

Run the full Phase 1 test suite. Anything that constructs `GameState` directly may need updating to include `visible_timers=()`. Anything that asserts the shape of state may need adjustment. **Do not change test semantics** — only the mechanical surface.

### Case schema

`packages/satori/tests/test_case_schema.py` may need a test that the updated example case still validates (it should — `diegetic` is optional).

### API

`packages/satori-api/tests/test_api.py`: assert `visible_timers` appears in `GameStateResponse`, is a list, and reflects the engine's state. New assertions on existing tests are fine; consider one new test that orders a lab and verifies the response's `visible_timers` includes it.

`packages/satori-api/tests/test_serialisation.py`: unit test for the VisibleTimer → VisibleTimerResponse conversion.

---

## Acceptance Criteria

1. `pytest packages/satori packages/satori-api` is green. Full Phase 1 suite still passes; new tests pass.
2. `ruff check` clean on all touched packages.
3. `mypy --strict` clean on all touched packages.
4. `pre-commit run --all-files` clean.
5. The Maria Santos case still loads and plays (sanity-run a CBC order through the engine; verify `visible_timers` contains the pending CBC result).
6. `svelte-check` in the frontend remains clean (frontend isn't touched, but verify no API contract change breaks types — the new field is additive).

---

## Out of Scope

- Any UI rendering of `visible_timers` (dashboard work — P2-H02 and panels)
- Emergency-state lock on the wait action (P2-H05)
- Wait action's visual treatment in the action bar (P2-H06)
- Diagnostic-rigor scoring (P2-H07)
- Real LLM narration of Waited events (P2-H08)
- Any new diegetic non-pending-reveal timers in the example case (only lab/imaging timers in Maria Santos should be marked diegetic; if there are NPC-arrival timers and you're unsure, leave them non-diegetic and surface the question)

If you encounter a structural problem that requires changing the visible_timers data model or the wait action contract, **stop and escalate** — do not redesign mid-implementation.

---

## Verification Stack

In order:

1. `ruff check packages/satori packages/satori-api && ruff format --check packages/satori packages/satori-api`
2. `mypy --strict packages/satori/src packages/satori-api/src`
3. `pytest packages/satori packages/satori-api -q`
4. `cd packages/internal-affairs && npm run check` (sanity — should be unaffected)
5. `git status` — verify only expected files changed

---

## Commit Message Template

```
feat(P2-H01): engine surface prep — diegetic timers, visible_timers, wait action

- Schema + Pydantic: NodeTimer.diegetic field (default false, backward-compat)
- GameState: VisibleTimer frozen dataclass; visible_timers tuple field
- Engine: compute_visible_timers from pending_reveals + diegetic active timers,
  deterministic ordering by (remaining_minutes, node_id)
- Engine: built-in wait action (wait:15, wait:30, wait:60) — advances clock,
  emits Waited event, integrates with standard tick
- Events: new Waited event type
- Case: example-neurocysticercosis lab/imaging timers marked diegetic
- API: VisibleTimerResponse on GameStateResponse; serialisation wired
- Tests: test_visible_timers.py (computation logic); test_wait_action.py
  (wait durations, error cases, determinism, tick integration)

Foundation for P2-H02 (dashboard) and P2-H04 (pending results panel).
```
