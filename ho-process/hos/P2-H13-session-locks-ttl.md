# P2-H13: Session Locks + TTL

**Status:** IN PROGRESS (autonomous; fully specified by audit C-8, no open decisions)
**Phase:** 2 (API hardening)
**Ho:** 13
**Depends on:** none

---

## Objective

Close audit C-8's two findings on the in-memory session store:

1. **Lost-update race.** FastAPI runs the sync handlers on a threadpool; two concurrent actions on one session race on the engine's read-modify-write — last writer wins, the other action is silently lost. Fix: a per-session `threading.Lock`; the action handler holds it for execute + narrate + serialize (the response must read the state the action produced).
2. **Unbounded store.** Sessions die only on explicit DELETE; each holds a live engine and full case. Fix: idle TTL (60 min, `time.monotonic`) swept on session creation and health checks.

The audit calibrated severity low-today/real-at-hosting; it's a half-hour fix, so it lands now rather than as a documented limit.

## Design notes

- Wall-clock use lives in the API layer only — the engine's no-wall-clock determinism rule is untouched (session expiry is server ops, not gameplay).
- Narration runs inside the lock: same-session actions must serialize through it anyway, and cross-session traffic is unaffected (per-session lock). Noted for P2-H08 — a slow live narrator lengthens the hold for that one session only, which is the correct behavior.
- Read-only endpoints (GET state, node content) stay lock-free: engine state is replaced by single atomic assignment, so readers see a complete before-or-after snapshot, never a partial one.
- The store module stays the only owner of session state (F-008); `main.py` gains one call (`lock_for`) and a `with` block.

## Deliverables

1. `session_manager.py` — `_Session` record (engine, lock, last_access); `lock_for()`; TTL sweep on `create_session()` and `session_count()`; accesses touch `last_access`
2. `main.py` — action handler body under the session lock
3. Tests — concurrent actions serialize (thread pair, final clock = sum of both waits); idle session reaped, fresh one kept; `lock_for` on unknown session; access refreshes the TTL clock

## Verification Stack

Standard full stack via `uv run --no-sync`; new tests in `test_api.py` / `test_session_manager.py`.

## Commit Message Template

```
fix(P2-H13): per-session locks + idle TTL on the session store (audit C-8)
```
