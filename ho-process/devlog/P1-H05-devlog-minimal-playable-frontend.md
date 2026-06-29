# Phase 1 Devlog: Minimal Playable Frontend (Ho 05)

**Date:** 2026-02-18
**Milestone:** Ho 05 — Minimal Playable Frontend
**Status:** ✅ Complete
**Commits:** `125a91d`, `8746400`, `f5b06d0`, `b251428`

---

## Summary

Built the full data-flow path from case JSON to browser: `satori-api` (new FastAPI package) as the HTTP bridge, plus a complete SvelteKit frontend (`internal-affairs`) wired to it. A human can now load the neurocysticercosis case in a browser, read patient context, issue actions, watch vitals change, read narrated event descriptions, and reach a case outcome.

**Result:** two new packages (`satori-api`, updated `internal-affairs`), 49 API tests passing, 0 TypeScript errors, 3 hard architectural boundaries enforced end-to-end.

Known limitation at end of Ho 05: the action menu correctly rendered base-level unlocked actions but could not surface subcategory actions (e.g. `order_labs:cbc`) — the "action grammar gap" was identified and deferred to Ho 06.

---

## What Was Built

### `packages/satori-api/` — the HTTP bridge

A new Python package wrapping the engine behind 6 FastAPI endpoints. Built from first principles rather than scaffolded.

| File | Role |
|---|---|
| `main.py` | FastAPI app, CORS, all 6 endpoint handlers |
| `models.py` | Pydantic request/response models — `SessionResponse`, `ActionResponse`, `GameStateResponse`, `PatientContextResponse`, `EventResponse`, `NodeContentResponse`, `ErrorResponse` |
| `session_manager.py` | In-memory `dict[str, SatoriEngine]` keyed by UUID4. Isolated as a future swap point (F-008). |
| `narrator_bridge.py` | `narrate_events(events, engine)` — runs `MockNarrator` server-side, produces one narration string per event |
| `serialisation.py` | Domain object → response model converters: `state_to_response`, `patient_to_response`, `events_to_responses`, `build_session_response` |
| `tests/test_api.py` | 34 end-to-end API tests via FastAPI `TestClient` |
| `tests/test_serialisation.py` | 11 unit tests for serialisation helpers |
| `tests/test_narrator_bridge.py` | 4 unit tests for narrator bridge |

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness + active session count |
| POST | `/api/sessions` | Load case → initialise engine → `SessionResponse` |
| GET | `/api/sessions/{id}` | Current state → `SessionResponse` |
| DELETE | `/api/sessions/{id}` | Destroy session (idempotent, 204) |
| POST | `/api/sessions/{id}/actions` | Execute action → `ActionResponse` |
| GET | `/api/sessions/{id}/nodes/{node_id}` | Raw node content → `NodeContentResponse` |

### `packages/internal-affairs/` — the SvelteKit UI

Five new components and a complete store, all on Svelte 5 runes.

| File | Role |
|---|---|
| `src/lib/types.ts` | TypeScript interfaces mirroring all API response models |
| `src/lib/api.ts` | Typed HTTP client; `ApiError` class; `createSession`, `executeAction`, `getSession`, `getNodeContent` |
| `src/lib/stores/gameStore.svelte.ts` | Svelte 5 runes store: `sessionId`, `gameState`, `patient`, `patientCondition`, `availableActions`, `eventLog`, `view`, `isLoading`, `error`; `startSession()`, `performAction()`, `reset()` |
| `src/lib/components/PatientHeader.svelte` | Patient identity, setting, chief complaint, condition badge |
| `src/lib/components/VitalsPanel.svelte` | Six vital signs in a grid with colour-coded status bands |
| `src/lib/components/ActionMenu.svelte` | Grouped action buttons; `humanise()` converts `"order_labs:cbc"` → `"Order Labs: CBC"` |
| `src/lib/components/EventLog.svelte` | Newest-first turn log with narration text and raw event debug accordion |
| `src/lib/components/OutcomeScreen.svelte` | Case-end screen with tier badge and restart button |
| `src/routes/+page.svelte` | Three-view SPA: `start` → `play` → `outcome` |
| `vite.config.ts` | `/api` proxy to `localhost:8000` |

### Supporting files

- `docs/architecture/satori-engine-api.md` — 584-line authoritative reference for every public symbol in `satori` + `llm-client`
- `docs/architecture/future-features.md` — F-008 entry: session management evolution + DIP principle
- `Makefile` — `dev-api`, `dev-all` targets added; `satori-api` added to `lint`, `typecheck`, `test`

---

## Architecture Decisions

### Decision 1: FastAPI HTTP bridge as a separate package

**Choice:** `packages/satori-api/` is a standalone editable Python package. The SvelteKit dev server proxies `/api` to `localhost:8000`.

**Why:** Boundary 2 (the truth line) from the original architecture mandates that the frontend never imports Python code. A hard HTTP boundary is the contract. FastAPI + Pydantic 2 gives request/response validation for free, auto-generates OpenAPI docs, and makes the boundary explicit and testable.

**Alternative rejected:** SvelteKit server-side routes calling Python via a subprocess or socket. Muddier boundary, harder to test, tighter coupling. A clean HTTP boundary means the frontend can eventually point at a remote server without changes.

---

### Decision 2: Every response is self-contained (DIP principle)

**Choice:** Both `SessionResponse` and `ActionResponse` carry the **full** current state: `GameState`, `available_actions`, `PatientCondition`, and patient context where applicable. The frontend never relies on anything it wasn't told in the most recent response.

**Why:** This is the Dependency Inversion Principle applied to a client/server boundary. The frontend depends on the response shape, not on server memory. If the session store later changes from in-memory to stateless replay, the frontend requires zero changes. It also makes the state trivially testable: assert on the response, not on hidden server-side objects.

**Trade-off:** Responses are slightly larger than they need to be. At Phase 1 scale (one local session, one case) this is completely immaterial.

---

### Decision 3: Server-side narration via MockNarrator

**Choice:** `narrator_bridge.py` holds a module-level `MockNarrator` instance. Every `execute_action()` call triggers synchronous narration server-side. The frontend receives `narrations: string[]` in `ActionResponse` — one entry per event.

**Why:** Boundary 3 (the narration line) requires that the frontend never calls the LLM directly. Narration is engine-domain logic, not UI logic. Placing it in `narrator_bridge.py` makes it a one-line swap: replace `MockNarrator` with a `GPT4oNarrator` or `ClaudeNarrator` without touching `main.py`, `models.py`, or any frontend file.

**Why synchronous:** Phase 1 cases are short, MockNarrator is instant, and streaming adds frontend complexity with no benefit yet. Streaming narration is logged as a future feature.

---

### Decision 4: `session_manager.py` as an isolated swap point (F-008)

**Choice:** The in-memory session store is a single module with three functions: `create_session()`, `get_engine()`, `delete_session()`. Nothing outside it touches `_sessions` directly (except tests, which clear it between runs).

**Why:** Phase 1 doesn't need persistence, TTL eviction, or horizontal scaling. But the design anticipates needing them. Isolating the store means any future swap only touches `session_manager.py`. The API endpoints call the three functions; they don't know or care what backs them.

---

### Decision 5: `serialisation.py` extracted from `main.py`

**Choice:** Domain-to-response conversion lives in its own module, unit-tested independently.

**Why:** This wasn't in the original wireframe — it emerged during implementation. `main.py` was growing large with conversion logic interspersed with routing logic. Extracting `serialisation.py` kept `main.py` focused on HTTP concerns and made the converters independently testable without spinning up the full FastAPI app.

---

## Test Coverage

The initial commit shipped 38 tests. A follow-up audit (`f5b06d0`) tightened them to 49:

| File | Tests | Key additions |
|---|---|---|
| `test_api.py` | 34 | `test_health_reflects_session_count`, `test_execute_action_response_has_outcome_fields`, `test_execute_action_state_contains_gamestate_subfields`, asserts `len(events) > 0` (removed silent `if events:` guard), `>` vs `>=` for time advancement |
| `test_serialisation.py` | 11 | All 6 vital fields checked; `setting`, `chief_complaint`, `appearance`, `triage_note`, `backstory` asserted on patient response |
| `test_narrator_bridge.py` | 4 | `test_describe_event_time_advanced`, `test_describe_event_node_revealed`, `test_describe_event_case_ended`, `test_describe_event_fallback` |

**Principal weakness closed in the audit:** `test_event_response_shape` had a silent `if events:` guard — if no events were returned the test trivially passed. Replacing with `assert len(events) > 0` made it a real contract assertion.

---

## Issues Found and Fixed

### Lint pass after initial commit (`8746400`)

`ruff --fix` caught unsorted imports in `main.py`, `models.py`, `narrator_bridge.py`, and `test_api.py`, plus one unused import in `test_serialisation.py` and one in `serialisation.py`. All auto-fixed. A `pyrightconfig.json` was added at repo root to make Pylance resolve `satori_api`, `satori`, and `llm_client` correctly across all test files.

`test_api.py::clear_sessions` fixture return type was `Generator` without annotation — added `Generator[None, None, None]` to remove a Pyright misc warning and drop a `type: ignore` comment.

### `_fresh()` return type covariance (`b251428`)

`narrator_bridge.py` had `_fresh()` returning `list[Event]` where the abstract base expected `Sequence[Event]`. `list` is covariant to `Sequence`, but Pyright flagged it. Fixed by changing the return annotation to `Sequence[Event]` and removing a `type: ignore` comment that had been masking it.

---

## Architectural Boundaries Respected

| Boundary | Rule | How enforced |
|---|---|---|
| Boundary 1 (case line) | Frontend never reads case JSON | All case data arrives in `SessionResponse.patient`. No direct file access. |
| Boundary 2 (truth line) | Frontend never imports Python | Zero Python in `src/`. All engine interaction is HTTP. `npm run check` verifies. |
| Boundary 3 (narration line) | Frontend never calls LLM | `ActionResponse.narrations: string[]` is the only path. MockNarrator runs in `narrator_bridge.py`. |

---

## Known Limitation Deferred to Ho 06

At the end of Ho 05 the `ActionMenu` shows only base-level action keys from `available_actions` (e.g. `order_labs`, `history_focused`). These are valid for submission when no subcategory exists, but most unlock-gated nodes require a fully-qualified string like `order_labs:cbc`. The engine validates the base key — it accepts the submission — but the UI has no way to know which subcategory options exist.

The full diagnosis: `available_actions` only carries base keys. The case's node reveal rules carry the subcategory information, but the API never surfaces them to the UI. The engine accepts `order_labs:cbc` correctly once submitted, but nothing shows the player that `cbc` is an option.

**Resolution:** Ho 06 introduced `get_playable_actions()` on `SatoriEngine`, which scans unrevealed active nodes to produce the full `base:subcategory` set, and added `playable_actions` to both API response models.

---

## Phase 2 Notes

- Session cleanup (TTL eviction) deferred to F-008
- The `DEFAULT_CASE_PATH` in `gameStore.svelte.ts` is hardcoded — a case picker or upload flow belongs in Phase 2
- Streaming narration would improve UX for slower LLMs (GPT-4o, Claude) but adds frontend complexity; deferred
- The `GET /api/sessions/{id}/nodes/{node_id}` endpoint is the stub for a future "examine revealed finding" drawer in the UI
