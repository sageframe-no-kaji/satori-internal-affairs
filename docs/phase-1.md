# Phase 1 — Architectural Foundation

## Internal Affairs / Satori / Anamnesis

**Project:** Medical Mystery Simulator
**Phase Goal:** Build a vertical slice — one complete case, playable end-to-end, with all three layers functioning and separated.
**Authoritative Spec:** `satori-internal-affairs-seed.md`

---

## What Phase 1 Produces

A **vertical slice**: one complete case, playable end-to-end, with all three layers functioning and separated. Not feature-complete. Not polished. But architecturally correct — every boundary real, every layer doing its own job, the LLM properly constrained.

At the end of Phase 1, you can load a frozen case, play through it with structured actions, watch a patient deteriorate or stabilize based on your choices, and read LLM-narrated descriptions of what's happening. The teaching layer doesn't need to be rich yet. The UI doesn't need to be beautiful yet. But the skeleton is honest.

---

## System Boundaries

These are the four boundaries that must exist before anything else matters. Phase 1 is about making these boundaries real — not aspirational, not "we'll separate later," but enforced in the architecture from day one.

### Boundary 1: Anamnesis → Satori (the freeze line)

Anamnesis produces a case definition. That definition crosses the boundary as a validated, schema-conformant artifact. Once it crosses, it's frozen. Satori never asks Anamnesis for more information during play. This is the generation-time / play-time wall.

### Boundary 2: Satori → Internal Affairs (the truth line)

Satori emits structured events: what information is now available, what the vitals are, what state transitions occurred, what actions are legal. Internal Affairs receives these events and presents them. Internal Affairs never decides what's medically true. It renders what Satori says.

### Boundary 3: Satori → LLMClient (the narration line)

When Satori emits an event, it can be handed to the LLM for narration. The LLM receives the event and current game state as context. It returns text. It never returns state modifications. The narration is cosmetic — if you stripped it out and showed raw events, the game would still be mechanically playable.

### Boundary 4: LLMClient abstraction (the provider line)

All LLM calls — case generation, narration, explanation — go through a single interface. The rest of the system doesn't know or care what model is behind it. This is the swap layer.

---

## Milestone Dependency Map

```
M1 (Case Schema)
├── M2 (Satori Engine) — needs schema to know what it's interpreting
├── M4 (Anamnesis Pipeline) — needs schema to know what it's generating
│
M3 (LLM Abstraction)
├── M4 (Anamnesis Pipeline) — calls LLMClient.generateCase
├── M5 (Internal Affairs) — calls LLMClient.narrate
│
M2 + M3 + M4 + M5 → M6 (Vertical Slice)
```

M1 and M3 can be developed in parallel — they have no mutual dependency. M2 and M4 both depend on M1. M5 depends on M2 and M3. M6 is pure integration.

---

## Milestones

### Milestone 1: The Case Schema

The JSON/YAML schema that defines a complete case. This is the contract between Anamnesis and Satori. It's the single most important design artifact in the system, because everything downstream depends on it.

**What it must encode:**

- Patient identity and presentation (demographics, chief complaint, appearance)
- Ground truth diagnosis and differential
- Information nodes: what data exists, which action reveals it, what preconditions gate it
- Time model: how simulated time advances, what triggers progression
- State progression: compensation → decompensation → collapse (or recovery), with conditions
- Vital sign trajectories tied to state
- Action catalog: what the player can do, what each action costs in time, what it reveals
- Failure states: what kills the patient, what causes permanent harm, what constitutes a miss
- Success conditions: what constitutes a good outcome, partial success, optimal path
- Metadata: difficulty, learning objectives, dramatic tone, content boundaries

**Why it's first:** Until this schema exists, Anamnesis can't generate and Satori can't execute. Everything else is downstream.

**Design pattern:** Data-driven architecture. The schema is the instruction set. Satori is the interpreter. The richer and more precise the schema, the simpler and more reliable the engine.

---

### Milestone 2: Satori Core Engine

The deterministic state machine that plays a case. Given a frozen case definition and a sequence of player actions, Satori produces a deterministic sequence of state transitions and outcomes.

**What it must do:**

- Load a validated case definition
- Initialize game state (time, vitals, known information, available actions)
- Accept player actions and validate them against current state
- Advance simulated time based on action costs
- Reveal information nodes whose conditions are met
- Evaluate state progression triggers (time-based deterioration, action-based stabilization)
- Track vital sign trajectories
- Emit structured events for each state change
- Evaluate win/loss/partial conditions
- Be fully deterministic: same case + same actions = same outcome, every time

**What it must NOT do:**

- Generate text
- Call the LLM
- Invent facts not in the case definition
- Make probabilistic decisions (all randomness belongs in case generation, not execution)

**Design pattern:** Finite state machine with a discrete event simulation layer for time. The state machine handles patient condition (stable → compensating → decompensating → critical → dead/recovered). The event simulation handles clock advancement and trigger evaluation.

---

### Milestone 3: LLM Abstraction Layer

The single interface through which all LLM calls flow. In Phase 1, this is thin — just enough to prove the boundary works.

**What it must provide:**

- `generateCase(seed) → CaseDefinition` — takes a structured seed, returns a case that conforms to the schema
- `narrate(event, state) → string` — takes a Satori event and current game state, returns narrative text
- `explain(context) → string` — takes a teaching context, returns an explanation

**What it enforces:**

- No LLM call happens outside this interface
- The return types are constrained (structured data for generation, string for narration)
- The caller never receives state-modifying instructions from the LLM

**Phase 1 scope:** Implementation A is the ChatGPT API. The interface is designed so Implementation B (any other provider) can be swapped without changing callers.

---

### Milestone 4: Anamnesis — Seed-to-Case Pipeline

The pipeline that takes a structured seed and produces a validated, frozen case definition.

**What the pipeline does:**

1. Accept a seed (medical core, difficulty, tone, complications, boundaries)
2. Construct a structured prompt from the seed
3. Call `LLMClient.generateCase(seed)`
4. Validate the returned JSON against the case schema
5. Reject or flag cases that fail validation
6. Store the validated case as an immutable artifact

**Phase 1 scope:** One working seed → one validated case. The pipeline doesn't need to be robust, elegant, or fast. It needs to prove the concept: structured input → LLM → structured output → schema validation → frozen artifact.

**Design pattern:** Structured prompt pipeline with schema validation as a gate. The LLM is a generator; the schema is the quality check. Nothing passes to Satori that hasn't been validated.

---

### Milestone 5: Internal Affairs — Minimal Playable Frontend

A UI that lets a player load a case, see the presentation, choose actions, and watch the case unfold. In Phase 1, this is functional, not beautiful.

**What it must do:**

- Display initial patient presentation
- Show available actions (structured menu, not free text)
- Send chosen action to Satori
- Receive state update from Satori
- Display narrated results (from LLM) or raw event data (fallback)
- Show current vitals and time
- Display outcome when the case resolves

**What it does NOT need in Phase 1:**

- Rich narrative atmosphere
- Tooltips and teaching layer
- Debrief system
- Multiple case selection
- User accounts or persistence
- Polish

**Design pattern:** Thin client over Satori. It renders state. It sends actions. It never reasons about medicine.

---

### Milestone 6: The Vertical Slice

The integration milestone. All five previous milestones connected, running end-to-end.

**The proof:**

- A seed is defined
- Anamnesis generates a case from it
- The case passes schema validation
- Satori loads the case and initializes state
- Internal Affairs presents the case
- The player makes a sequence of actions
- Satori advances state deterministically
- The LLM narrates each transition
- The patient either deteriorates or stabilizes based on choices
- The case resolves with a clear outcome
- The same actions on the same case produce the same outcome every time

**What this proves:**

- The boundaries are real
- The deterministic rule holds
- The LLM is properly constrained
- The schema is sufficient for at least one case
- The system is architecturally sound enough to build on

---

## What Phase 1 Does NOT Include

- Multiple cases or case variety
- Case Builder interface
- Teaching layer beyond basic structure
- Debrief system
- UI polish or emotional atmosphere
- User accounts or session persistence
- Content moderation pipeline
- Difficulty scaling
- Case curation workflow
- Performance optimization
- Deployment infrastructure

These all belong in Phase 2 and beyond. Phase 1 builds the skeleton. If the skeleton is wrong, nothing built on top of it will be right.

---

## Technology Decisions Deferred

Phase 1 does not need to lock in:

- Database choice (flat files or simple JSON storage is fine for one case)
- Hosting or deployment
- CI/CD pipeline

Frontend framework and language choices will be decided in Ho 01, as they affect project structure but don't need to be architecturally load-bearing at this stage.

---

## The Principle Underneath

Phase 1 is guided by one idea: **make the boundaries real before you make anything rich.**

Every feature you'll add later — more cases, richer narrative, teaching moments, debrief, atmosphere — hangs on the boundaries being correctly drawn. If Satori accidentally leaks LLM calls, if the case schema is too loose, if Internal Affairs starts making medical decisions, if Anamnesis generates cases that can't be deterministically played — those are structural defects that get harder to fix the more you build on top of them.

Phase 1 is the foundation pour. It should be boring to look at and rock-solid underneath.

---

## Ho Checklist

Each Ho is a focused work session. Complete them in order. Each one builds on the last.

---

### Ho 00: Project Scaffolding & README

**Duration:** 2–3 hours
**Goal:** The project repository exists with a clear file structure, a comprehensive README, and all architectural documentation in place. Anyone reading the repo understands what this project is, how it's organized, and what the layers do.
**Deliverable:** Initialized repository with directory structure, README.md, and the seed document committed. Development environment bootstrapped (package.json or equivalent, linting, formatting, .gitignore).
**Decision Required:** Language and framework choices — TypeScript vs. Python for the backend engine, frontend framework selection, monorepo vs. multi-repo structure. These choices shape the directory layout and must be made before anything else is built.

---

### Ho 01: Case Schema Design

**Duration:** 3–4 hours
**Goal:** A complete, validated JSON Schema exists that defines the contract between Anamnesis and Satori. The schema is precise enough that a case conforming to it contains everything Satori needs to run a full game — no ambiguity, no missing fields, no implicit structure.
**Deliverable:** The case schema file (JSON Schema), a written schema design document explaining the major modeling decisions, and one hand-written example case (not LLM-generated) that validates against the schema.
**Decision Required:** How to model time progression and state transitions within a static data structure. This is the hardest design problem in the schema — encoding dynamic behavior (deterioration, stabilization, branching paths) into a frozen artifact that a state machine can interpret deterministically.

---

### Ho 02: Satori — State Machine Core

**Duration:** 3–4 hours
**Goal:** Satori can load a case definition, accept a sequence of player actions, and produce a deterministic sequence of state transitions. Given the same case and the same actions, it produces the same outcome every time. No LLM calls. No text generation. Pure logic.
**Deliverable:** The Satori engine module with: case loader, game state initializer, action validator, time advancement, information reveal logic, state transition evaluator, and event emitter. Plus a test harness that runs the hand-written case from Ho 01 through multiple action sequences and verifies determinism.
**Decision Required:** State machine architecture — how to represent patient condition states, how to evaluate transition triggers, and how the time model interacts with state progression. Flat state enum vs. hierarchical state chart vs. condition-based evaluation.

---

### Ho 03: LLM Abstraction Layer

**Duration:** 2–3 hours
**Goal:** A single interface exists through which all LLM interactions flow. The rest of the system calls this interface — never the API directly. The interface is implemented against the ChatGPT API but designed so the provider can be swapped without changing any caller.
**Deliverable:** The LLMClient interface definition, the ChatGPT API implementation of that interface, and a simple integration test proving that `narrate(event, state)` returns text and `generateCase(seed)` returns parseable structured output. Plus a mock implementation for testing without API calls.
**Decision Required:** How to handle structured output from the LLM for case generation — prompt engineering with JSON mode, function calling, or post-processing with validation. This affects reliability and determines how much validation logic Anamnesis needs.

---

### Ho 04: Anamnesis — Seed-to-Case Pipeline

**Duration:** 3–4 hours
**Goal:** A structured seed can be fed into Anamnesis, which calls the LLM through the abstraction layer, receives a case definition, validates it against the schema from Ho 01, and stores it as a frozen artifact. The pipeline either produces a valid case or clearly rejects invalid output.
**Deliverable:** The Anamnesis pipeline module with: seed input structure, prompt construction, LLM call through LLMClient, schema validation gate, and case storage. One LLM-generated case that passes validation and is playable by the Satori engine from Ho 02.
**Decision Required:** Prompt architecture for case generation — how much structure to embed in the prompt, how to handle partial or malformed LLM output, and whether to use single-shot generation or a multi-step pipeline (generate → validate → repair → re-validate).

---

### Ho 05: Internal Affairs — Minimal Playable Frontend

**Duration:** 3–4 hours
**Goal:** A player can open the application, see a patient presentation, choose from structured clinical actions, and watch the case unfold turn by turn. The frontend sends actions to Satori, receives state updates, and displays LLM-narrated results. It never makes medical decisions.
**Deliverable:** The Internal Affairs frontend application with: case loading screen, patient presentation display, action selection menu, turn-by-turn state display with narrated text, vitals panel, and outcome screen. Connected to Satori and the LLM narration layer.
**Decision Required:** Frontend architecture — how the frontend communicates with Satori (direct function calls if monolith, HTTP API if separated, WebSocket if real-time updates matter). This determines whether Satori needs an API layer or can remain a library.

---

### Ho 06: Vertical Slice Integration

**Duration:** 2–3 hours
**Goal:** All layers are connected and a complete game can be played end-to-end. A seed produces a case via Anamnesis, Satori runs the case deterministically, Internal Affairs renders the experience, and the LLM narrates transitions. The four system boundaries are verified to be real and enforced.
**Deliverable:** A documented end-to-end playthrough demonstrating: case generation → schema validation → game initialization → player actions → state transitions → LLM narration → case resolution. Plus a boundary verification checklist confirming each of the four architectural boundaries holds.
**Decision Required:** No major architectural decision. This Ho is integration and verification. The decision space is limited to: what's good enough to call Phase 1 complete, and what gets deferred to Phase 2.

---

## Summary Table

| Ho  | Title                               | Duration | Depends On   | Milestone |
| --- | ----------------------------------- | -------- | ------------ | --------- |
| 00  | Project Scaffolding & README        | 2–3 hrs  | —            | Setup     |
| 01  | Case Schema Design                  | 3–4 hrs  | Ho 00        | M1        |
| 02  | Satori — State Machine Core         | 3–4 hrs  | Ho 01        | M2        |
| 03  | LLM Abstraction Layer               | 2–3 hrs  | Ho 00        | M3        |
| 04  | Anamnesis — Seed-to-Case Pipeline   | 3–4 hrs  | Ho 01, Ho 03 | M4        |
| 05  | Internal Affairs — Minimal Frontend | 3–4 hrs  | Ho 02, Ho 03 | M5        |
| 06  | Vertical Slice Integration          | 2–3 hrs  | Ho 02–05     | M6        |

**Total estimated Phase 1 duration: 18–25 hours across 7 sessions.**

---

_Phase 2 planning begins after Ho 06 is complete and the vertical slice is verified._
