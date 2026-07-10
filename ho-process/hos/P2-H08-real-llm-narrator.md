# P2-H08: Real LLM Narrator

**Status:** PLUMBING LANDED (2026-07-10, practitioner-authorized split) — VOICE WORK PENDING PRACTITIONER
**Phase:** 2
**Ho:** 08
**Depends on:** P2-H02 (narrative feed), P2-H03 (concerns panel carries non-narrative content), P2-H05 (emergency events styled distinctly in the feed)

> This document specifies the technical plumbing only. The narrator's voice —
> register, prompt content, tone constraints, examples — is the practitioner's
> work and is deliberately absent. Do not write prompt content until the voice
> work happens in a thinking conversation.
>
> **Split (practitioner-authorized, 2026-07-10):** the voice-independent
> plumbing (AnthropicNarrator, per-session cache, env wiring, timeout +
> fallback) landed ahead of the voice work with a clearly-marked PLACEHOLDER
> system prompt in `llm_client/narration_prompts.py`. **Remaining for H08
> completion:** the voice session's output (`docs/architecture/narrator-voice.md`,
> per `prompts/h08-voice-session.md`) replaces the placeholder and fills the
> `EVENT_GUIDANCE` slots; the live smoke test runs behind the `live_llm`
> marker; the llm-client coverage floor is restored. The default provider
> stays `mock` until then — the placeholder never narrates in anyone's game
> unless explicitly enabled by env.

---

## Objective

Replace `MockNarrator` with a live provider behind the existing `Narrator` interface, without moving any architectural boundary: the narrator returns text only (Narration Line), provider SDKs import only inside `packages/llm-client` (Provider Line), play stays deterministic — narration decorates events, never produces state (Freeze Line).

---

## Current plumbing (verified against the code, 2026-07-10)

- `llm_client.interfaces.Narrator` — `narrate(NarrationEvent, NarrationContext) -> str`, `explain(ExplanationContext) -> str`. The interface is already what H08 needs; no signature changes.
- `llm_client.config.create_narrator(ModelConfig)` — dispatches MOCK; raises `LLMClientError("No live Narrator implementation…")` for other providers. H08 fills in the ANTHROPIC branch.
- `satori_api.narrator_bridge` — module-singleton `MockNarrator`; `_describe_event()` already produces a templated description + structured data per event type; `narrate_events()` is guarded (audit C-5 fix, commit `1973887`): a narrator failure degrades to the templated description and never poisons the gameplay response. H08 builds on this — the fallback path already exists and is tested.
- `anamnesis`'s `AnthropicGenerator` in `llm-client` is the sibling implementation to model client construction, retry shape, and error taxonomy on.

## Deliverables (plumbing)

### 1. `AnthropicNarrator` (`packages/llm-client/src/llm_client/anthropic_narrator.py`)

- Implements `Narrator` against the Anthropic SDK (ho-overview recommendation: Anthropic — the practitioner's default for narrative work; the sibling generator already exists)
- Construction from `ModelConfig` (provider, model, api_key, and a request timeout — add `timeout_seconds` to `ModelConfig` if not present)
- `create_narrator` dispatches `Provider.ANTHROPIC` to it; OPENAI stays unimplemented until a case for it exists
- Raises the existing `llm_client.exceptions` taxonomy on provider errors — the bridge's guard handles degradation

### 2. Prompt template *structure* (content pending practitioner)

- One base system prompt establishing voice and constraints — **content authored by the practitioner**
- Per-event-type user templates assembled from `NarrationEvent` (type, description, structured_data) + `NarrationContext` (patient identity, setting, vitals, elapsed time) — the 12 event types `_describe_event` already enumerates are the template surface
- Templates live as named constants in one module so Phase 3+ tuning has a single documented home
- Emergency events (P2-H05 feed styling) get a distinct template slot — the moment needs different narration pressure, per ho-overview

### 3. Env-var wiring (`satori_api`)

- `SATORI_NARRATOR_PROVIDER` (`mock` default — absent config must never break local dev), `SATORI_NARRATOR_MODEL`, `ANTHROPIC_API_KEY` read at startup
- Invalid/missing live config at startup: log loudly, fall back to mock — the game always runs
- `.env.example` documents all three with section comments

### 4. Narration cache

- Per-session, in-memory, keyed `(event_type, node_id)` (ho-overview recommendation) — avoids re-calling for identical events mid-session
- Lives with the session (created in `session_manager.create_session`, dropped on delete) — the current module-singleton narrator stays, the cache does not become global state
- No cross-session cache in Phase 2

### 5. Fallback behaviour

- On provider error or timeout: return `_describe_event`'s templated string, log the failure, keep playing — this is the C-5 guard's existing contract; H08 extends it with the timeout case and a counter/log line for observability

### 6. Tests

- Mock-based: template assembly per event type, cache hit/miss, fallback on raised provider errors, env-var config matrix (mock default, valid live, invalid live → mock)
- One live smoke test behind the existing `live_llm` marker (deselected by default)
- **Coverage floor restored:** the llm-client 90% exemption in `.pre-commit-config.yaml` and `Makefile` exists "until P2-H08 rewrites the provider implementations" — this ho removes the exemption

## Out of Scope

- Prompt content / voice / register (practitioner; the ho-overview names the *Grey's Anatomy* register as the target — the target is recorded, the writing is not delegated)
- Multi-provider auto-failover; streaming (Phase 3+)
- Cross-case voice tuning (one case exists)
- `explain()` implementation beyond a stub that raises (the debrief phase owns it)

## Verification Stack

Standard: `uv run --no-sync` ruff / mypy strict / pytest (llm-client floor restored to 90) / `npm run check`; live smoke test run once manually with a real key before commit.

## Commit Message Template

```
feat(P2-H08): live Anthropic narrator — provider, cache, env config, fallback

[to be completed when executed]
```
