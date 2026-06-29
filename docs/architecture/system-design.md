# Satori Internal Affairs — System Design

**Status:** Current — reflects Phase 1 reality and Phase 2 commitments
**Kamae 2 artifact** — the architectural commitments the project is being built against
**Last updated:** 2026-06-29

---

## What This Document Is

This is the System Design in the Kamae chain: it takes the seed's architectural opinions and turns them into committed decisions. It is the canonical reference for what the system is, how it's structured, and what's locked vs. what's deferred.

It supersedes `phase-1-gameplan.md` as the architectural reference. That document remains in place as historical record of how Phase 1 was planned and built.

Detail documents that elaborate specific subsystems are linked as appendices and are not re-summarised here.

---

## System Purpose

Satori Internal Affairs is an interactive medical mystery simulator. The player takes the role of a clinician investigating a patient under time pressure. Cases are frozen artifacts (LLM-generated, schema-validated, immutable at play-time). The engine interprets cases deterministically. The LLM narrates from deterministic state but never alters truth.

The system serves the seed's three purposes — teach medical reasoning, teach medicine as a human system, preserve the dramatic core of medical drama — through one mechanical commitment: **separate case generation from case play.**

---

## The Four Boundaries

These are non-negotiable. Every component is positioned relative to them.

| Boundary | Separates | What It Enforces |
|---|---|---|
| **Freeze Line** (B1) | Anamnesis → Satori | Cases are immutable once validated. No facts invented at play time. |
| **Truth Line** (B2) | Satori → Internal Affairs | Frontend renders truth; never determines it. All medical logic in the engine. |
| **Narration Line** (B3) | Satori → LLM Client | LLM produces text from deterministic state. Strip narration and the game still works. |
| **Provider Line** (B4) | Domain → LLM implementation | All LLM calls flow through one interface. Providers are swappable. |

---

## Component Architecture

```
                         ┌─────────────────────┐
                         │    SEEDS (YAML)     │
                         │  human-authored     │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │      ANAMNESIS      │
                         │ (case generation)   │
                         │                     │
                         │  seed → prompt →    │
                         │  LLM → validate →   │
                         │  retry/repair →     │
                         │  frozen case JSON   │
                         └──────────┬──────────┘
                                    │  Boundary 1: Freeze Line
                                    ▼
                         ┌─────────────────────┐
                         │   CASES (JSON)      │
                         │  immutable artifacts│
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │       SATORI        │
                         │ (deterministic      │
                         │  game engine)       │
                         │                     │
                         │  nodes · flags ·    │
                         │  timers · effects   │
                         └──────────┬──────────┘
                                    │  Boundary 2: Truth Line
                                    ▼
                         ┌─────────────────────┐
                         │     SATORI-API      │
                         │  (FastAPI bridge)   │
                         │                     │
                         │  sessions ·         │
                         │  serialisation ·    │
                         │  narrator bridge ───┼──┐
                         └──────────┬──────────┘  │
                                    │             │ Boundary 3:
                                    │             │ Narration Line
                                    │             ▼
                                    │      ┌─────────────────┐
                                    │      │   LLM-CLIENT    │
                                    │      │ (provider       │
                                    │      │  abstraction)   │
                                    │      │                 │
                                    │      │  Narrator ·     │
                                    │      │  CaseGenerator  │
                                    │      └────────┬────────┘
                                    │               │ Boundary 4:
                                    │               │ Provider Line
                                    │               ▼
                                    │      ┌─────────────────┐
                                    │      │  OpenAI /       │
                                    │      │  Anthropic /    │
                                    │      │  Mock           │
                                    │      └─────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  INTERNAL AFFAIRS   │
                         │  (SvelteKit UI)     │
                         │                     │
                         │  mission-control    │
                         │  dashboard          │
                         └─────────────────────┘
```

### Components

**Satori** — the deterministic game engine. Loads case JSON, executes player actions, advances time, evaluates conditions, fires effects, emits events. Pure logic; no LLM, no text generation, no I/O beyond case loading.

**Anamnesis** — the case generation pipeline. Accepts a `CreativeSeed`, builds a structured prompt, calls the LLM through `llm-client`, validates the response against the JSON Schema, retries with repair prompts on failure, persists validated cases to `cases/generated/`. Runs at design time; never at play time.

**LLM Client** — the provider-agnostic abstraction layer. Defines `CaseGenerator`, `Narrator`, and `ActionInterpreter` interfaces plus all boundary types (`CaseSeed`, `NarrationEvent`, `NarrationContext`, etc.). Implementations: `MockCaseGenerator`, `MockNarrator`, `OpenAICaseGenerator`, `AnthropicCaseGenerator`. Phase 2 adds live narrator implementations.

**Satori-API** — the FastAPI bridge. In-memory session store, stateless-shaped responses (every response carries full renderable state — see F-008), server-side narration via `narrator_bridge.py`. Sits between Satori and the frontend. Enforces Boundaries 2 and 3.

**Internal Affairs** — the SvelteKit frontend. Pure client of `satori-api`. Never imports Python; never decides medical truth. Phase 1 shipped a minimal-but-playable UI; Phase 2 replaces it with a mission-control dashboard.

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Engine, generation, abstraction | Python 3.11+ | Practitioner-default; Pydantic + mypy strict provides the static guarantees the engine needs. |
| API server | FastAPI + uvicorn | Async-ready, Pydantic-native, lightweight. |
| Frontend | SvelteKit 2.x + Svelte 5 runes + TypeScript | Reactive primitives without Redux ceremony; first-class TypeScript. |
| Build / dev | Vite, pnpm | Standard SvelteKit. |
| Case format | JSON validated against JSON Schema 2020-12 + Pydantic models | The schema is the contract between Anamnesis and Satori. Two-level validation (schema + structural). |
| LLM providers | OpenAI and Anthropic, swappable via factory | Phase 2 picks one as primary narrator; both remain supported for case generation. |
| Verification | ruff, mypy strict, pytest with 90% floor, svelte-check | Practitioner discipline. |

Deployment, hosting, and persistence are deferred to Phase 6.

---

## Data Model: The Frozen Case

Cases are directed graphs of **nodes** wired by **flags**, animated by **timers**, and changed by **effects**. The schema is `schemas/case-definition.schema.json`. The Pydantic mirror is `packages/satori/src/satori/models/case_definition.py`.

The deep treatment lives in [`case-data-structure.md`](case-data-structure.md). The public engine API lives in [`satori-engine-api.md`](satori-engine-api.md). This document does not duplicate them.

### Phase 1 commitments still in force

- Nodes carry both `structured_data` (medical facts) and `narrative_text` (description). The narrative slot exists today as frozen text; Phase 2 makes it dynamic for selected event classes (see Phase 2 commitments below). The schema does not change.
- Actions are structured (`base` + optional `subcategory`); the engine never sees free text. Action strings travel as `base:subcategory` between API and UI.
- Relational and emotional node types are first-class in the schema even though Phase 1 cases under-author them. Outcome evaluation scores relational outcomes separately from medical.
- Outcome evaluation is multi-tier (Optimal / Good / Partial / Failure), driven by flag presence/absence and time thresholds.

---

## Phase 2 Commitments

Phase 2 makes the existing simulation *felt*. The engine already simulates concurrent timers, emergency state, deteriorating vitals, NPC arrival/departure, and treatment consequences. The Phase 1 UI surfaces almost none of it. Phase 2 closes that gap and adds the narrative voice that the seed promises.

### 1. Turn structure: turn-based with variable-length turns

The engine already advances the clock by action time cost. Phase 2 affirms this as the committed turn model. There is no real-time mode. There is no fixed turn length. Each action's `action_cost` (already in the schema) drives the clock.

### 2. Diegetic vs non-diegetic timer split

The engine tracks every timer the same way. The UI surfaces them asymmetrically:

- **Diegetic (visible)** — timers the player's character would know about. Lab turnaround, imaging queues, consult ETAs, NPC arrival windows the character has been told about. Sourced from `state.pending_reveals` and any node whose `timer.diegetic` flag is true.
- **Non-diegetic (hidden)** — biological deterioration, cascade triggers, NPC patience the character has no clock for. Sourced from any node whose timer is not diegetic. The player infers these from vitals and emerging symptoms.

**Schema change required:** add an optional `diegetic: bool` field on `NodeTimer` (default `false`). Backward-compatible with the existing case.

**Engine change required:** `GameState` exposes a `visible_timers: list[VisibleTimer]` field derived from active timers + `pending_reveals` filtered by diegetic flag and node visibility rules. Hidden timers stay in `state.timers` (engine-only).

**UI change required:** the dashboard's Pending Results panel renders `visible_timers` only.

### 3. Mission-control dashboard

The committed UI layout is the one in `game-design-pitch.md`:

```
┌──────────────────────────────────────────────────────────┐
│  VITALS STRIP (always visible, updates every turn)       │
├──────────────┬───────────────────────┬───────────────────┤
│  ACTIVE      │    NARRATIVE FEED     │   PENDING         │
│  CONCERNS    │  (story / dialogue /  │   RESULTS         │
│  (evidence   │   exam descriptions / │   (diegetic       │
│   board —    │   character moments)  │    countdowns)    │
│   findings   │                       │                   │
│   accumulate)│                       │   CONSULTS        │
├──────────────┴───────────────────────┴───────────────────┤
│  ACTION BAR  [grouped, dropdown subcategories]           │
│              [Wait/Observe]                Clock: T+75   │
└──────────────────────────────────────────────────────────┘
```

The current single-page Phase 1 UI is replaced. The components from Phase 1 (`PatientHeader`, `VitalsPanel`, `ActionMenu`, `EventLog`, `OutcomeScreen`) are either rebuilt or repurposed; nothing in the API or store needs to break.

### 4. Emergency mode

When a crisis node fires (e.g. `node_14_seizure_crisis`), the engine already locks investigation actions via effects. Phase 2 makes this visually distinct:

- The dashboard enters emergency rendering: red border, locked actions visibly disabled with a reason, emergency-only actions surfaced.
- The triggering timer becomes visible (this is the one case where a non-diegetic timer is shown — because the emergency itself is visible to the character).
- The narrative feed gets a dedicated emergency event style.

**Schema change required:** add an optional `emergency: bool` field on `Effect` actions of type `lock_action`, or a node-level `emergency_state: bool` flag on `NodeRevealed`. Concrete shape decided in the relevant ho.

**Engine change required:** `GameState` exposes `emergency_active: bool` derived from the relevant signal.

### 5. Wait / observe as a first-class action

Players can advance time without doing a clinical investigation. This is clinically realistic and load-bearing for the design — sometimes the right move is to watch.

- **Engine:** new built-in base action `wait` with subcategory time durations (`wait:15`, `wait:30`, `wait:60`). No effects; only advances the clock by its action_cost.
- **Schema:** `wait` is reserved as a built-in action key; cases do not need to author it.
- **UI:** the Wait/Observe button sits in the action bar as a sibling to clinical action categories.

### 6. Diagnosis as treatment commitment (no new mechanic)

The player does not declare a diagnosis. The treatment they choose **is** the diagnostic commitment. The outcome tells them whether they were right.

- **No engine gate.** Treatment subcategories (e.g. `start_treatment:albendazole`, `start_treatment:steroids`) already act as differential commitments. They unlock based on the existing flag-graph activation system; cases author the gating they need.
- **Scoring extension.** Outcome evaluation gains a "diagnostic rigor" dimension that rewards confirming before committing. Cases author this as a flag (e.g. `confirmed_lesion_on_imaging` set if the player ordered imaging before treatment). Tier rules check it.

**Schema change required:** outcome rules already check flag presence/absence; this is case-authoring, not schema. Verified.

**Engine change required:** none.

### 7. Real LLM narrator

The Phase 1 `MockNarrator` is replaced with a live narrator using the existing `Narrator` interface in `llm-client`. Phase 2 commits to:

- A provider implementation of `Narrator` (`OpenAINarrator` or `AnthropicNarrator` — decision in the relevant ho).
- Prompt engineering for the *Grey's Anatomy* register: patient dialogue, family scenes, exam descriptions with emotional texture. The narrator receives the structured `NarrationEvent` + `NarrationContext` already defined in `llm-client/interfaces.py` and returns text.
- A narration cache or per-session memoization so identical events don't re-call the LLM mid-session (cost + latency).
- Configuration plumbing in `satori-api` so the deployed provider is selected via env var, not hard-coded.

**Boundary discipline retained.** The narrator returns text only. It never returns state changes. If the LLM is unavailable or times out, the bridge falls back to a templated string and the game keeps running.

---

## What's Out of Scope for Phase 2

These are deferred and addressed in later phases. They are listed so the Ho Overview can refuse to absorb them.

| Deferred | When | Why |
|---|---|---|
| Multiple cases beyond Maria Santos | Phase 4 (Case Library) | Phase 2 needs design feedback from one well-tuned case before scaling content. |
| Case Builder GUI (F-003) | Phase 4 / Phase 5 | Anamnesis CLI is sufficient until case authoring becomes a frequent activity. |
| Teaching layer / debrief depth (F-005) | Phase 5 | The mechanical surface must land first; teaching annotates a working game. |
| Mode 3 fully prompted case generation (F-007) | Phase 4 | First real provider narrator integration validates the prompt strategy; Mode 3 follows. |
| Session persistence (F-008) | Phase 6 or earlier if needed | In-memory sessions are fine until hosting becomes real. |
| Mobile / desktop packaging (F-006) | Phase 6 | Web-first; the dashboard layout will be designed to be responsive but mobile-specific polish is later. |
| Natural-language input (F-002) | Phase 3+ | Structured menu is the committed input model; expert mode is a future overlay. |
| Hosting, domain, deployment | Phase 6 | Local dev is sufficient through Phase 5. |

---

## Project Arc (Phases Beyond Phase 1)

| Phase | Theme | Release | Approximate scope |
|---|---|---|---|
| 1 | Architectural Foundation | v0.6 (de facto, the vertical slice) | Complete |
| 2 | Gameplay Surface + Narrative Voice | v0.7 | Mission-control dashboard, diegetic timers, emergency mode, wait action, diagnostic-rigor scoring, real LLM narrator |
| 3 | (Reserved — see below) | — | If Phase 2 surfaces a missing mechanic, it lands here. Otherwise this slot dissolves into Phase 4. |
| 4 | Case Library | v0.8 | 5–10 cases, batch generation tooling, curation workflow, case-selection screen. Mode 3 generation. |
| 5 | Teaching & Debrief | v0.9 | Debrief screen, optimal-path comparison, teaching annotations, learning objectives surfaced |
| 6 | Polish & Ship | v1.0 | Visual atmosphere, mobile-responsive, hosting, domain, the gift moment |

Phases 3 and beyond are not committed yet. They are the project arc as currently understood and will be re-examined after Phase 2 ships.

---

## Appendices — Detail Documents

These elaborate specific subsystems. They are part of the system design by reference.

- [`case-data-structure.md`](case-data-structure.md) — the node-graph architecture in depth, walked through with the Maria Santos case
- [`satori-engine-api.md`](satori-engine-api.md) — the public API of `satori` and `llm-client` packages
- [`example-case-node-validation.md`](example-case-node-validation.md) — pre-schema validation of the example case
- [`future-features.md`](future-features.md) — the deferred-decisions register (F-001 through F-008)
- [`game-design-pitch.md`](game-design-pitch.md) — public-facing design pitch; source material for the Phase 2 mechanical and UI commitments above
- [`P1-H03-llm-abstraction-layer.md`](P1-H03-llm-abstraction-layer.md) — learning doc on the llm-client design
- [`P1-H04-case-generation-pipeline.md`](P1-H04-case-generation-pipeline.md) — learning doc on Anamnesis
- [`phase-1-gameplan.md`](phase-1-gameplan.md) — historical Phase 1 plan; preserved for record

---

## Open Decisions Carried Into Phase 2

These are not yet decided and will be resolved inline with the ho that needs them:

- **Narrator provider** — OpenAI or Anthropic for the live `Narrator` implementation. Decided in the narrator ho.
- **Narration cache strategy** — per-session in-memory vs. content-hash keyed. Decided in the narrator ho.
- **Emergency state representation** — `Effect`-level flag vs. `GameState.emergency_active` derived field vs. both. Decided in the emergency-mode ho.
- **Dashboard component decomposition** — how `+page.svelte` splits into routes/components for the new layout. Decided in the dashboard ho.
- **Wait action durations** — exact set (`15/30/60` vs. `5/15/30/60` vs. parameterised). Decided in the wait-action ho.

All other Phase 2 commitments above are locked.
