---
created: 2026-07-03
type: agent-task
status: complete
parent: audit/FABLE-REVIEW-2026-07-03.md
project: satori-internal-affairs
---

# S3 — Determinism hardening + event contract

**Goal**

Make the engine's core guarantee — same case, same actions, same result — structurally true across process boundaries (finding C-2), prove it with a subprocess-based test, and fix the lost `NodeActivatedEvent` for cascade-activated nodes (finding C-6).

**Problem**

Three loops in `state_checkers.py` (`check_auto_reveals` :70, `check_action_reveals` :134, `check_interventions` :215) iterate `state.active_nodes` — a `frozenset[str]` — and apply effects/emit events in iteration order, which varies with Python's per-process hash seed. Two same-tick reveals with non-commutative effects can therefore diverge between runs. The existing determinism test runs both engines in one process and structurally cannot detect this. Separately, `cascade_activations` (:272-292) adds a node to `active_nodes` *before* calling `_activate_node`, whose already-active early-return then swallows the `NodeActivatedEvent` — state is correct but the event contract consumed by narration and the frontend is broken.

**Files**

- Modify: `packages/satori/src/satori/state_checkers.py`
- Create: `packages/satori/tests/test_determinism_cross_process.py`
- Modify: existing satori tests only if event-count/order assertions legitimately change with the cascade-event fix

**Required Changes**

1. **Deterministic iteration.** Replace the three `for node_id in state.active_nodes:` (or equivalent) iterations at `check_auto_reveals`, `check_action_reveals`, and `check_interventions` with `sorted(...)` iteration, with a comment stating the invariant (effect/event order must not depend on set iteration order). Sorting other set iterations (e.g. vitals recomputation) is unnecessary — worst-wins is order-independent; leave them.
2. **Cascade event fix.** Emit `NodeActivatedEvent` for cascade-activated nodes — either emit directly in the cascade loop or reorder so `_activate_node` runs before the manual `active_nodes` insertion. Timer initialization behavior must be unchanged.
3. **Cross-process determinism test.** A test that runs a scripted action sequence against the Maria Santos case in two separate Python subprocesses with different `PYTHONHASHSEED` values (e.g. 1 and 777), serializes the full event stream + final state from each, and asserts byte-identical output. Keep the scripted path short enough to run fast (<5s) but covering reveals, a wait, and a timer expiry.
4. **Event-contract test.** A unit test asserting cascade-activated nodes produce exactly one `NodeActivatedEvent`.

**Do Not**

- Do not pin `PYTHONHASHSEED` in test or project config as the *fix* — the sorted iteration is the fix; the subprocess test varies the seed to prove it.
- Do not refactor `state_checkers.py` beyond the named changes (the per-tick `node_map` rebuilds are noted in the report as negligible; leave them).
- Do not touch the case JSON (S2's territory).

**Acceptance**

- [ ] The three loops iterate in sorted order; comments state the invariant.
- [ ] Cross-process test passes; it fails when the `sorted()` calls are reverted (verify once locally by stashing the fix).
- [ ] Cascade-activation emits `NodeActivatedEvent`; new unit test passes.
- [ ] Full satori + satori-api suites pass; coverage floor holds; ruff/mypy clean.

**Verification**

```bash
pytest packages/satori/tests/test_determinism_cross_process.py -v
pytest packages/satori packages/satori-api -q
pre-commit run --all-files
```

**Commit**

Two commits:

```
fix(engine): sort active-node iteration — determinism across processes (audit C-2)
fix(engine): emit NodeActivatedEvent for cascade-activated nodes (audit C-6)
```
