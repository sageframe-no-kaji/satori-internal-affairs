# P1-H05: Minimal Playable Frontend

**Status:** DONE
**Phase:** 1
**Ho:** 05
**Depends on:** P1-H04 (case generation pipeline, satori package, llm-client package)

---

## Objective

Deliver a minimal but end-to-end playable experience: a browser-based UI where a human can load a case, read patient context, issue actions, see vitals update, read narrated events, and reach a case outcome. The full data-flow path — case JSON → engine → HTTP → browser — must work in one session.

---

## Key Decisions

### Decision 1: FastAPI HTTP bridge (satori-api package)

Rationale: F-006 mandates that the frontend never imports Python code directly (Boundary 2 — the truth line). All engine interaction must cross a well-defined HTTP boundary. FastAPI + Pydantic 2 provides automatic request/response validation, OpenAPI docs, and clean JSON serialisation.

Architecture: `packages/satori-api/` is a new Python package, installed editable, running as a local dev server on port 8000. The SvelteKit dev server proxies `/api` to `http://localhost:8000`.

### Decision 2: In-memory sessions + stateless-shaped responses (F-008 / DIP)

Phase 1 sessions are stored in a module-level `dict[str, SatoriEngine]` keyed by UUID4. The session store is isolated in `session_manager.py` so any future evolution (stateless replay, Redis, DB) only touches that module.

Every API response is self-contained (DIP — dependency inversion principle for the client): `SessionResponse` and `ActionResponse` both include full `GameState`, `PatientCondition`, and `available_actions`. The frontend never needs to maintain incremental state; it replaces state wholesale on each response.

### Decision 3: Server-side narration via MockNarrator

The `narrate_events()` function in `narrator_bridge.py` uses a module-level `MockNarrator` instance. Narration runs server-side, synchronously, after every `execute_action()` call. This satisfies Boundary 3 (the narration line) and makes the MockNarrator a drop-in replacement for a real LLM narrator without changing the frontend or API contract.

---

## Deliverables

### New package: `packages/satori-api/`

| File | Purpose |
|------|---------|
| `pyproject.toml` | fastapi, uvicorn, pydantic, satori, llm-client deps |
| `README.md` | Package documentation |
| `src/satori_api/__init__.py` | Package version |
| `src/satori_api/main.py` | FastAPI app + 6 endpoints |
| `src/satori_api/models.py` | Pydantic request/response models |
| `src/satori_api/session_manager.py` | In-memory session store (F-008 isolation point) |
| `src/satori_api/narrator_bridge.py` | narrate_events() via MockNarrator |
| `src/satori_api/serialisation.py` | Domain object → response converters |
| `tests/__init__.py` | Test package |
| `tests/test_api.py` | ~30 end-to-end API tests |
| `tests/test_serialisation.py` | ~10 serialisation unit tests |
| `tests/test_narrator_bridge.py` | ~4 narrator bridge unit tests |

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check + active session count |
| POST | `/api/sessions` | Create session from case file → `SessionResponse` |
| GET | `/api/sessions/{id}` | Read current session state → `SessionResponse` |
| DELETE | `/api/sessions/{id}` | Destroy session (idempotent, 204) |
| POST | `/api/sessions/{id}/actions` | Execute action → `ActionResponse` (events + narrations + new state) |
| GET | `/api/sessions/{id}/nodes/{node_id}` | Read raw node content → `NodeContentResponse` |

### New/updated frontend files: `packages/internal-affairs/`

| File | Purpose |
|------|---------|
| `src/lib/types.ts` | TypeScript types mirroring all satori-api response models |
| `src/lib/api.ts` | Typed HTTP client, ApiError, all five API calls |
| `src/lib/stores/gameStore.svelte.ts` | Svelte 5 runes game store: state + startSession/performAction/reset |
| `src/lib/components/PatientHeader.svelte` | Patient identity display |
| `src/lib/components/VitalsPanel.svelte` | Vital signs grid with colour-coded status bands |
| `src/lib/components/ActionMenu.svelte` | Grouped action buttons with humanised labels |
| `src/lib/components/EventLog.svelte` | Newest-first narrated turn log with raw event debug |
| `src/lib/components/OutcomeScreen.svelte` | Case resolution screen with tier badge |
| `src/routes/+page.svelte` | Three-view SPA: start → play → outcome |
| `vite.config.ts` | Added /api proxy to localhost:8000 |

### New/updated docs

| File | Change |
|------|--------|
| `docs/architecture/satori-engine-api.md` | New — authoritative API reference for satori + llm-client public surface |
| `docs/architecture/future-features.md` | F-008 appended: session management evolution + DIP principle |
| `docs/project-map.md` | Updated with all new files, descriptions, Makefile targets |
| `Makefile` | Added: dev-api, dev-all; extended: setup, lint, typecheck, test |

---

## Acceptance Criteria

- [ ] `pytest packages/satori-api/tests -v` — all tests pass
- [ ] `cd packages/internal-affairs && npm run check` — no TypeScript errors
- [ ] Manual playthrough: `make dev-api` + `make dev-frontend` → browser → load case → actions logged → reach outcome
- [ ] Determinism: two identical action sequences in separate sessions produce identical final `GameState`
- [ ] Boundary check: no Python import in TypeScript; no satori/llm-client direct usage outside Python packages

---

## Architecture boundaries respected

- **Boundary 1 (the case line):** Frontend never reads case JSON directly. All case data arrives via API responses.
- **Boundary 2 (the truth line):** Frontend never imports Python. All engine interaction is over HTTP.
- **Boundary 3 (the narration line):** Frontend never calls the LLM. Narrations arrive as `string[]` in `ActionResponse`.

---

## Notes

- `serialisation.py` was not in the original wireframe but was extracted from `main.py` during implementation to keep files focused. It is covered by `test_serialisation.py`.
- The frontend default case path (`DEFAULT_CASE_PATH`) is hardcoded as `'cases/example-neurocysticercosis.json'` in `gameStore.svelte.ts`. Ho 06 or later should consider a case picker / upload flow.
- Session cleanup (TTL eviction) is deferred to F-008 Phase 2.
