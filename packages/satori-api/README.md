# satori-api

FastAPI bridge server that exposes the Satori game engine over HTTP.

## Purpose

This package sits at Boundary 2 (the truth line) between the Satori engine
and the Internal Affairs frontend. It wraps `SatoriEngine` in a thin HTTP
API so the frontend never imports Python directly.

## Architecture decisions

- **FastAPI** — speaks Pydantic natively, mandated by F-006 (clean API boundary)
- **In-memory sessions** — `dict[str, SatoriEngine]` keyed by UUID. Sessions are
  lost on restart. Documented as F-008 for future evolution.
- **Stateless-shaped responses** — every response is self-contained (DIP principle).
  The frontend depends on the response contract, not on session state.
- **Server-side narration** — `MockNarrator` runs here. The frontend receives
  narrated text, never raw events for text generation.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create session, get initial state |
| `GET` | `/api/sessions/{id}` | Get current session state |
| `POST` | `/api/sessions/{id}/actions` | Execute action, get events + new state |
| `GET` | `/api/sessions/{id}/nodes/{node_id}` | Get revealed node content |

## Running

```bash
# From repo root
make dev-api
# or directly:
uvicorn satori_api.main:app --reload --port 8000
```

## Testing

```bash
pytest packages/satori-api/tests
```
