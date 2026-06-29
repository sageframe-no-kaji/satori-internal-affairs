# Project Map

**Last updated:** 2026-06-29

This is an interactive medical mystery game where teenagers play as doctors diagnosing patients. The project is split into five packages inside a monorepo. **Satori** is the game engine — it runs cases deterministically (same actions always produce the same outcome). **Anamnesis** generates those cases using an LLM. **LLM Client** is the provider-agnostic bridge to whatever AI provider we use. **Satori-API** is the FastAPI bridge between engine and frontend. **Internal Affairs** is the SvelteKit frontend players actually see.

Phase 1 is complete: all five packages are built, one reference case (Maria Santos / neurocysticercosis) plays end-to-end, and the four architectural boundaries hold. Phase 2 (Gameplay Surface + Narrative Voice, target release `v0.7`) is in planning — see [system-design.md](architecture/system-design.md) and [phase-2-ho-overview.md](architecture/phase-2-ho-overview.md). The game works like this: a case file describes a patient as a graph of nodes (clues, test results, treatments, crises). Anamnesis generates those files by prompting an LLM, validating the output at Boundary 1 (the freeze line), and saving only valid cases. The engine loads that graph, and as the player takes actions (ask questions, order labs, prescribe treatment), nodes activate and reveal based on flags and timers. Time passes, vitals change, and the patient gets better or worse depending on what the player does.

---

## Full File Tree

```
satori-internal-affairs/
├── LICENSE
├── Makefile
├── README.md
├── .gitignore
├── cases/
│   ├── README.md
│   ├── example-neurocysticercosis.json
│   └── generated/                             ← validated cases saved here (gitignored)
├── seeds/
│   ├── README.md
│   ├── example-pneumothorax.yaml
│   └── example-neurocysticercosis-rich.yaml
├── schemas/
│   ├── README.md
│   └── case-definition.schema.json
├── docs/
│   ├── project-map.md                        ← you are here
│   ├── satori-internal-affairs-seed.md
│   ├── architecture/
│   │   ├── system-design.md                            ← canonical K2 reference (Phase 1 + Phase 2)
│   │   ├── phase-2-ho-overview.md                      ← K4 build sequence for Phase 2
│   │   ├── case-data-structure.md
│   │   ├── example-case-node-validation.md
│   │   ├── future-features.md
│   │   ├── game-design-pitch.md
│   │   ├── satori-engine-api.md                        ← public API reference (Ho 05)
│   │   ├── P1-H03-plan.md
│   │   ├── P1-H03-llm-abstraction-layer.md
│   │   ├── P1-H04-case-generation-pipeline.md
│   │   └── phase-1-gameplan.md                         ← historical Phase 1 plan
│   └── devlog/
│       ├── P1-H00-devlog-notes.md
│       ├── P1-H01-devlog-schema-review.md
│       ├── P1-H02-devlog-engine-core.md
│       ├── P1-H03-devlog-llm-abstraction-layer.md
│       ├── P1-H04-devlog-case-generation-pipeline.md
│       ├── P1-H05-devlog-minimal-playable-frontend.md
│       ├── P1-H06-devlog-vertical-slice.md
│       └── P2-gameplay-seed.md
├── tasks/
│   ├── README.md
│   ├── P1-H00-DONE-agent-task-project-scaffolding.md
│   ├── P1-H01-DONE-agent-task-case-schema.md
│   ├── P1-H02-DONE-agent-task-satori-engine-core.md
│   ├── P1-H03-DONE-agent-task-llm-abstraction-layer.md
│   ├── P1-H03.2-DONE-agent-task-improve-tests.md
│   ├── P1-H04-DONE-agent-task-case-generation-pipeline.md
│   ├── P1-H05-DONE-agent-task-minimal-playable-frontend.md
│   └── P1-H06-DONE-agent-task-vertical-slice.md
└── packages/
    ├── satori/
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── src/satori/
    │   │   ├── __init__.py
    │   │   ├── py.typed
    │   │   ├── engine.py
    │   │   ├── game_state.py
    │   │   ├── condition_evaluator.py
    │   │   ├── effect_executor.py
    │   │   ├── action_parser.py
    │   │   ├── timer_manager.py
    │   │   ├── state_checkers.py
    │   │   ├── events.py
    │   │   ├── vitals_computer.py
    │   │   ├── patient_condition.py
    │   │   └── models/
    │   │       ├── __init__.py
    │   │       └── case_definition.py
    │   └── tests/
    │       ├── test_action_parser.py
    │       ├── test_case_schema.py
    │       ├── test_condition_evaluator.py
    │       ├── test_effect_executor.py
    │       ├── test_engine_determinism.py
    │       ├── test_patient_condition.py
    │       ├── test_state_checkers.py
    │       ├── test_timer_manager.py
    │       └── test_vitals_computer.py
    ├── anamnesis/
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── src/anamnesis/
    │   │   ├── __init__.py
    │   │   ├── __main__.py
    │   │   ├── seed.py
    │   │   ├── validator.py
    │   │   ├── result.py
    │   │   ├── prompts.py
    │   │   └── pipeline.py
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_seed.py
    │       ├── test_validator.py
    │       ├── test_prompts.py
    │       ├── test_result.py
    │       ├── test_pipeline_mock.py
    │       ├── test_retry_logic.py
    │       ├── test_cli.py
    │       ├── test_integration_live.py
    │       └── test_placeholder.py
    ├── llm-client/
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── src/llm_client/
    │   │   ├── __init__.py
    │   │   ├── py.typed
    │   │   ├── interfaces.py
    │   │   ├── config.py
    │   │   ├── exceptions.py
    │   │   ├── mock.py
    │   │   ├── openai_generator.py
    │   │   └── anthropic_generator.py
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_boundary_types_comprehensive.py
    │       ├── test_config.py
    │       ├── test_error_handling.py
    │       ├── test_factory_comprehensive.py
    │       ├── test_integration.py
    │       ├── test_interfaces.py
    │       ├── test_mock.py
    │       ├── test_placeholder.py
    │       ├── test_providers.py
    │       └── test_schema_conformance.py
    ├── satori-api/
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── src/satori_api/
    │   │   ├── __init__.py
    │   │   ├── main.py
    │   │   ├── models.py
    │   │   ├── session_manager.py
    │   │   ├── narrator_bridge.py
    │   │   └── serialisation.py
    │   └── tests/
    │       ├── __init__.py
    │       ├── test_api.py
    │       ├── test_serialisation.py
    │       └── test_narrator_bridge.py
    └── internal-affairs/
        ├── package.json
        ├── README.md
        ├── svelte.config.js
        ├── tsconfig.json
        ├── vite.config.ts
        ├── .gitignore
        ├── .npmrc
        ├── static/
        │   └── robots.txt
        └── src/
            ├── app.html
            ├── app.d.ts
            ├── lib/
            │   ├── index.ts
            │   ├── api.ts
            │   ├── types.ts
            │   ├── assets/
            │   │   └── favicon.svg
            │   ├── stores/
            │   │   └── gameStore.svelte.ts
            │   └── components/
            │       ├── PatientHeader.svelte
            │       ├── VitalsPanel.svelte
            │       ├── ActionMenu.svelte
            │       ├── EventLog.svelte
            │       └── OutcomeScreen.svelte
            └── routes/
                ├── +layout.svelte
                └── +page.svelte
```

---

## Root

- **`LICENSE`** — MIT license (Andrew T Marcus, 2025).
- **`Makefile`** — Build commands: setup, lint, typecheck, test, dev-frontend, dev-api, dev-all, clean.
- **`README.md`** — Project overview, architecture summary, package descriptions.
- **`.gitignore`** — Ignores Python/Node artifacts, IDE files, env files.

## cases/

Example and generated case files that the engine runs. These are the "frozen artifacts" — fully self-contained JSON descriptions of a medical scenario that have passed Boundary 1 validation.

- **`README.md`** — Explains what case files are and how they're used.
- **`example-neurocysticercosis.json`** — Maria Santos, 28 — seizure + speech difficulty → neurocysticercosis. 12 nodes, timers, multiple diagnostic paths, patient death path. This is the reference case used by all engine tests.
- **`generated/`** — Output directory for Anamnesis-generated cases. All files here have passed `validate_case_dict()`. The directory is tracked in git but its contents are gitignored.

## seeds/

Human-authored YAML briefs that Anamnesis uses as generation input. YAML is used here because it supports multiline strings and inline comments, which matter for narrative fields.

- **`README.md`** — Explains the seed file format and both generation modes.
- **`example-pneumothorax.yaml`** — Minimal Mode 1 seed: just medical spec fields.
- **`example-neurocysticercosis-rich.yaml`** — Full Mode 2 seed: medical spec plus complete narrative direction (dramatic hook, red herrings, character notes, emotional core, forbidden tropes).

## schemas/

The formal contract between case generation (Anamnesis) and case execution (Satori). If a case file validates against this schema, the engine can run it.

- **`README.md`** — Explains the schema's role in the pipeline.
- **`case-definition.schema.json`** — JSON Schema (Draft 2020-12) defining every field a case can have: metadata, patient context, ground truth, nodes, timers, activation rules, effects, action costs, outcome evaluation.

## docs/

All design thinking, architecture decisions, and session logs live here.

- **`satori-internal-affairs-seed.md`** — The original vision document — target audience, design goals, four-layer architecture, system boundary definitions.
- **`architecture/`**
  - **`system-design.md`** — Canonical Kamae 2 reference: current architectural commitments. Phase 1 reality + Phase 2 commitments (mission-control dashboard, diegetic vs non-diegetic timer split, emergency mode, wait action, diagnosis-as-treatment scoring, live LLM narrator). Supersedes `phase-1-gameplan.md` as the architectural source of truth.
  - **`phase-2-ho-overview.md`** — Kamae 4 build sequence for Phase 2 (release `v0.7`). Single phase, eight hos (P2-H01–P2-H08), inline deferred decisions resolved by the ho that needs them.
  - **`case-data-structure.md`** — Deep dive into the node-graph architecture with a garden metaphor; walks through the Maria Santos case node by node.
  - **`example-case-node-validation.md`** — Pre-schema plain-language description of all 12 Maria Santos nodes; used to validate the architecture before writing JSON.
  - **`future-features.md`** — Deferred feature register (LLM narration, natural language input, case builder GUI, emotional nodes, Mode 3 full prompt injection, F-008 session management evolution) with Phase 1 compatibility notes.
  - **`game-design-pitch.md`** — Public-facing design overview: core mechanics, hidden-timer / visible-action-economy split, mission-control dashboard concept, outcome scoring. Source material for the Phase 2 commitments lifted into `system-design.md`.
  - **`satori-engine-api.md`** — Authoritative public API reference for the satori and llm-client packages: SatoriEngine methods, GameState fields, all 12 event types, PatientCondition, parse_action, Narrator/NarrationEvent/NarrationContext, ModelConfig factories. Written in Ho 05 to support satori-api development.
  - **`P1-H03-plan.md`** — Pre-build design spec for Ho 03 (LLM abstraction layer): file inventory, boundary types, interface contracts, provider implementations.
  - **`P1-H03-llm-abstraction-layer.md`** — Learning document explaining how llm-client works: interfaces, boundary types, factory pattern, how OpenAI/Anthropic calls work, optional dependencies, mock providers.
  - **`P1-H04-case-generation-pipeline.md`** — Learning document explaining how Anamnesis works: seeds, two-phase validation, `GenerationResult` design, retry loop, Boundary 1 enforcement.
  - **`phase-1-gameplan.md`** — Historical Phase 1 plan: vertical slice goal, milestone dependency graph, ho-by-ho specs. Preserved as record; superseded by `system-design.md`.
- **`devlog/`**
  - **`P1-H00-devlog-notes.md`** — Raw design thinking — how to model conditional reveal, branching trajectories, and outcome evaluation in a frozen data structure.
  - **`P1-H01-devlog-schema-review.md`** — Post-implementation review of the schema task; documents 3 bugs fixed and 3 design observations accepted.
  - **`P1-H02-devlog-engine-core.md`** — Post-implementation review of the engine task; documents the 20/33 → 33/33 test journey and StateCheckers refactoring.
  - **`P1-H03-devlog-llm-abstraction-layer.md`** — Post-implementation review of Ho 03; documents architecture decisions, boundary type ownership, optional dependency strategy.
  - **`P1-H04-devlog-case-generation-pipeline.md`** — Post-implementation review of Ho 04; documents CreativeSeed design, two-phase validation, retry strategy, GenerationResult pattern, Boundary 1 enforcement, 105-test coverage.
  - **`P1-H05-devlog-minimal-playable-frontend.md`** — Post-implementation review of Ho 05; documents the FastAPI bridge, in-memory session strategy, server-side MockNarrator, SvelteKit UI architecture.
  - **`P1-H06-devlog-vertical-slice.md`** — Post-implementation review of Ho 06; documents `get_playable_actions()` algorithm, action grammar gap closure, ActionMenu grouping fix, boundary checklist, Phase 2 extensibility audit.
  - **`P2-gameplay-seed.md`** — Phase 2 design homework: gameplay mechanics seed, design axes (A/B/C), reference games, six concrete design questions. Source material for Phase 2 system design.

## tasks/

Agent task specifications. Each one defines a unit of work with goals, acceptance criteria, and commit message templates.

- **`README.md`** — Explains the task format.
- **`P1-H00-DONE-agent-task-project-scaffolding.md`** — Scaffolding: directory structure, configs, README, Makefile.
- **`P1-H01-DONE-agent-task-case-schema.md`** — Schema: JSON Schema + Pydantic models + example case + tests.
- **`P1-H02-DONE-agent-task-satori-engine-core.md`** — Engine: deterministic game loop, all 9 effect types, 198 tests.
- **`P1-H03-DONE-agent-task-llm-abstraction-layer.md`** — LLM abstraction: interfaces, boundary types, factory pattern, mock + real providers, 99 tests.
- **`P1-H03.2-DONE-agent-task-improve-tests.md`** — Test coverage improvements for Ho 03: factories, schema conformance, error handling, boundary types.
- **`P1-H04-DONE-agent-task-case-generation-pipeline.md`** — Case generation pipeline: CreativeSeed, two-phase validation, retry/repair loop, GenerationResult, Boundary 1 enforcement, 105 tests.
- **`P1-H05-DONE-agent-task-minimal-playable-frontend.md`** — Minimal playable frontend: FastAPI bridge (satori-api), SvelteKit UI (Internal Affairs), in-memory sessions with stateless-shaped responses, server-side MockNarrator.
- **`P1-H06-DONE-agent-task-vertical-slice.md`** — Vertical slice integration: `get_playable_actions()` on the engine, `playable_actions` field on API responses, ActionMenu grouping fix, boundary verification checklist.

## packages/satori/

The deterministic game engine. This is the only package with real code. It loads a case definition, tracks game state, and produces the same outcome every time given the same player actions.

- **`pyproject.toml`** — Package config: Python ≥3.11, depends on pydantic ≥2.0.
- **`README.md`** — What Satori does and doesn't do (no LLM, no UI, no case generation).
- **`src/satori/py.typed`** — PEP 561 marker enabling mypy strict type-checking for packages that import satori.

### src/satori/

- **`__init__.py`** — Public API exports: SatoriEngine, GameState, all event types, PatientCondition, parse_action.
- **`engine.py`** — Main engine class. Public methods: execute_action(), get_state(), get_available_actions(), get_node_content(). Coordinates all other modules during each game tick.
- **`game_state.py`** — Frozen dataclass holding everything about the current game: flags, active/revealed/expired nodes, timers, vitals, pending reveals, endgame status. Immutable — updates create new instances.
- **`condition_evaluator.py`** — Evaluates whether a node should activate or reveal. Implements OR-of-ANDs logic: a node activates if ANY path matches, where each path requires ALL its conditions to be true.
- **`effect_executor.py`** — Applies effects to game state: set/clear flags, activate/deactivate nodes, modify timers, lock/unlock actions, override vitals, end case. Each effect returns a new GameState and emits typed events.
- **`action_parser.py`** — Splits player action strings on ":" into base action + parameter. Example: "order_labs:cbc" → ("order_labs", "cbc").
- **`timer_manager.py`** — Runs node timers: counts down, triggers stage effects at thresholds, evaluates pause conditions, handles acceleration, fires expiration effects. Also manages the pending reveal queue (delayed results).
- **`state_checkers.py`** — Extracted from engine.py to keep files under 500 lines. Handles: activation sweeps, auto-reveals, action-triggered reveals, intervention effects, vitals recomputation, end condition evaluation.
- **`events.py`** — Typed event classes for every state change: NodeActivated, NodeRevealed, NodeExpired, FlagSet, FlagCleared, TimerStage, VitalsChanged, ActionLocked/Unlocked, PendingRevealStarted, CaseEnded. Used by tests and will be used by the frontend.
- **`vitals_computer.py`** — "Worst wins" algorithm: collects vital values from baseline + all active timer stages, picks the most dangerous value for each vital sign (lowest O₂, highest BP, etc.).
- **`patient_condition.py`** — Derives a human-readable label (stable / compensating / decompensating / critical / dead / recovered) from vitals and flags. Read-only convenience for display — not used by engine logic.

### src/satori/models/

- **`__init__.py`** — Re-exports all Pydantic models + validate_case() function.
- **`case_definition.py`** — ~30 Pydantic model classes mirroring the JSON Schema: CaseDefinition, Node, ActivationRule, RevealRule, NodeTimer, Effect, Condition, VitalSigns, OutcomeEvaluation, etc.

### tests/

- **`test_action_parser.py`** — Tests action string parsing: base actions, parameterized actions, edge cases.
- **`test_case_schema.py`** — 13 tests: validates the example case loads, has unique IDs, all flag/node references are valid, timer stages are sorted.
- **`test_condition_evaluator.py`** — Tests OR-of-ANDs activation logic, reveal rule evaluation, flag/node conditions.
- **`test_effect_executor.py`** — Tests all 9 effect types: set/clear flags, activate/deactivate nodes, modify timers, lock/unlock actions, override vitals, end case.
- **`test_engine_determinism.py`** — 33 tests: initialization, determinism (same input → same output), time advancement, node reveals, flag propagation, timer mechanics, pending reveals, intervention effects, vitals, end conditions.
- **`test_patient_condition.py`** — Tests patient condition derivation from vitals and flags (stable/compensating/decompensating/critical/dead/recovered).
- **`test_state_checkers.py`** — Tests auto-reveals, action-triggered reveals, intervention matching, activation cascades, vitals recomputation, end condition evaluation.
- **`test_timer_manager.py`** — Tests timer countdown, stage progression, pause conditions, acceleration, expiration, pending reveal advancement.
- **`test_vitals_computer.py`** — Tests "worst wins" vital computation from baseline + active timer stages.

## packages/anamnesis/

The LLM-powered case generation pipeline. Enforces Boundary 1 (the freeze line): every file saved to `cases/generated/` has been fully validated against `CaseDefinition` before being written to disk.

- **`pyproject.toml`** — Package config: Python ≥3.11. Depends on pydantic, pyyaml, satori, llm-client. Optional extras: `openai`, `anthropic`, `all`. Dev extras: pytest, ruff, mypy.
- **`README.md`** — What Anamnesis does: two seed modes, validation at Boundary 1, retry/repair strategy, CLI usage.

### src/anamnesis/

- **`__init__.py`** — Public API: exports `CreativeSeed`, `GenerationResult`, `CaseGenerationPipeline`, `validate_case_dict`, `load_seed_file`, `build_creative_prompt`, `build_repair_prompt`.
- **`__main__.py`** — CLI entry point. `python -m anamnesis --diagnosis X --difficulty Y --dramatic-tone Z [--seed path.yaml] [--output-dir path] [--max-retries N] [--provider mock|openai|anthropic] [--verbose]`.
- **`seed.py`** — `CreativeSeed` frozen dataclass with all `CaseSeed` fields plus Mode 2 narrative fields (`dramatic_hook`, `red_herrings`, `character_notes`, etc.). `load_seed_file(path)` parses YAML seed files. `to_case_seed()` extracts the llm-client-compatible subset.
- **`validator.py`** — `validate_case_dict(raw_dict)` runs two-phase validation: (1) Pydantic schema check via `CaseDefinition.model_validate()`, (2) structural consistency checks (unique node IDs, action refs exist in action_costs, timer stages sorted ascending). Returns `(CaseDefinition | None, list[str])`.
- **`result.py`** — `GenerationResult` frozen dataclass. Fields: `success`, `case`, `raw_dict`, `case_path`, `attempts`, `errors`, `seed`. `__post_init__` enforces invariants. Helper constructors `_make_success()`, `_make_failure()`, and `_with_path()` for immutable updates.
- **`prompts.py`** — `build_creative_prompt(seed)` assembles a three-section prompt from all `CreativeSeed` fields (medical requirements, creative direction, structural constraints). `build_repair_prompt(raw_dict, errors)` builds an error-feedback prompt for repair retries.
- **`pipeline.py`** — `CaseGenerationPipeline(config, output_dir)` orchestrates seed → LLM → validate → retry/repair → save. `generate(seed, max_retries=3)` returns `GenerationResult`. `save(result)` writes validated case JSON to `cases/generated/case-{diagnosis}-{uuid8}.json`. `generate_and_save()` convenience wrapper.

### tests/

- **`conftest.py`** — Shared fixtures: minimal valid case dict, example `CreativeSeed`, output temp dir.
- **`test_seed.py`** — 26 tests: `CreativeSeed` construction, `to_case_seed()`, `has_creative_fields()`, `load_seed_file()` happy path and all error branches.
- **`test_validator.py`** — 14 tests: schema errors, structural errors (duplicate IDs, bad action refs, unsorted timers), multi-error collection, non-dict input, success returns empty errors.
- **`test_prompts.py`** — 18 tests: all `CreativeSeed` fields appear in `build_creative_prompt()`, repair prompt includes prior output and errors, unserializable dict fallback.
- **`test_result.py`** — 9 tests: `GenerationResult` invariants, `_make_success/failure/_with_path` helpers, `__post_init__` enforcement.
- **`test_pipeline_mock.py`** — 18 tests: `Provider.MOCK` full pipeline, `generate()`, `save()`, `generate_and_save()`, failure path (no file written), default output dir constant.
- **`test_retry_logic.py`** — 16 tests: success on first attempt, success on retry, repair attempt triggered, all attempts fail, `max_retries=0` edge case; uses `_CountingGenerator` injection.
- **`test_cli.py`** — 11 tests: required args, optional flags (`--verbose`, `--max-retries`, `--seed`, `--provider`), failed generation → exit 1, `--max-retries` forwarded correctly.
- **`test_integration_live.py`** — 7 tests marked `live_llm` (skipped without API keys): real OpenAI/Anthropic end-to-end generation and validation.
- **`test_placeholder.py`** — Original scaffold placeholder (kept).

## packages/llm-client/

The provider-agnostic LLM abstraction layer. Enforces Boundary 4 (the provider line). All LLM calls — case generation, narration, action interpretation — go through interfaces defined here. The rest of the system never imports `openai` or `anthropic` directly.

- **`pyproject.toml`** — Package config: Python ≥3.11, zero required dependencies. Optional deps: `openai`, `anthropic`, `all`. Dev deps include pytest, ruff, mypy, jsonschema.
- **`README.md`** — What LLM Client does: unified interface for OpenAI/Anthropic/mock, handles auth, request formatting, response parsing.
- **`src/llm_client/py.typed`** — PEP 561 marker enabling mypy strict type-checking for packages that import llm-client.

### src/llm_client/

- **`__init__.py`** — Public API: re-exports all interfaces, boundary types, config, factories, exceptions, and mock implementations.
- **`interfaces.py`** — Three abstract base classes (`CaseGenerator`, `Narrator`, `ActionInterpreter`) + five frozen dataclass boundary types (`CaseSeed`, `NarrationEvent`, `NarrationContext`, `ExplanationContext`, `ParsedAction`). These types are owned by llm-client, not satori.
- **`config.py`** — `Provider` enum (OPENAI, ANTHROPIC, MOCK), `ModelConfig` frozen dataclass, and three factory functions (`create_case_generator`, `create_narrator`, `create_action_interpreter`). Factories return the right provider implementation based on config.
- **`exceptions.py`** — Exception hierarchy: `LLMClientError` (base) → `LLMProviderError` (API failures), `LLMResponseError` (unparseable responses), `LLMTimeoutError` (deadlines).
- **`mock.py`** — `MockCaseGenerator` (loads example case JSON), `MockNarrator` (templated strings), `MockActionInterpreter` (simple string matching). No API calls, no dependencies. Used for development and testing.
- **`openai_generator.py`** — `OpenAICaseGenerator`: builds system+user prompts from JSON schema + `CaseSeed`, calls OpenAI chat completions with `response_format={"type": "json_object"}`, parses JSON response. Uses late import of `openai` package.
- **`anthropic_generator.py`** — `AnthropicCaseGenerator`: same prompt strategy as OpenAI, adapted for Anthropic's SDK (separate system param, content blocks response shape). Uses late import of `anthropic` package.

### tests/

- **`conftest.py`** — Shared pytest fixtures for test configuration.
- **`test_boundary_types_comprehensive.py`** — 13 tests: construction of all boundary types, default values, frozen immutability, optional field handling.
- **`test_config.py`** — Tests for `ModelConfig`, `Provider` enum values, factory function routing.
- **`test_error_handling.py`** — 8 tests: exception hierarchy, provider/api_key/schema_path validation errors, exception wrapping.
- **`test_factory_comprehensive.py`** — 10 tests: all three factories with mock/openai/anthropic providers, validates Phase 1 raises for unimplemented live narrators/interpreters.
- **`test_integration.py`** — Integration tests (marked, skipped without API keys): real OpenAI/Anthropic API calls.
- **`test_interfaces.py`** — ABC enforcement: can't instantiate abstract classes directly.
- **`test_mock.py`** — Mock implementation tests: case dict structure, narrator output, action interpreter matching.
- **`test_placeholder.py`** — Original scaffold placeholder.
- **`test_providers.py`** — Provider-specific tests: OpenAI/Anthropic constructor validation, schema loading, prompt building.
- **`test_schema_conformance.py`** — 11 tests: validates mock case output against the actual JSON schema, checks required keys and structure.

## packages/satori-api/

FastAPI bridge server. Exposes the Satori engine and MockNarrator over HTTP. Enforces Boundary 2 (the truth line) and Boundary 3 (the narration line): the frontend never imports Python code directly; all interaction is through HTTP responses.

- **`pyproject.toml`** — Package config: Python ≥3.11, depends on fastapi, uvicorn, pydantic, satori, llm-client. Dev extras: pytest, httpx.
- **`README.md`** — What satori-api does: FastAPI bridge, in-memory sessions, stateless-shaped responses, server-side narration.

### src/satori_api/

- **`__init__.py`** — Package version.
- **`main.py`** — FastAPI application. Four endpoints: POST /api/sessions, GET /api/sessions/{id}, POST /api/sessions/{id}/actions, GET /api/sessions/{id}/nodes/{node_id}. CORS configured for SvelteKit dev server.
- **`models.py`** — Pydantic request/response models: CreateSessionRequest, ExecuteActionRequest, SessionResponse, ActionResponse, GameStateResponse, EventResponse, PatientContextResponse, VitalSignsResponse, NodeContentResponse, ErrorResponse.
- **`session_manager.py`** — In-memory session store. create_session(case_path), get_engine(session_id), delete_session(session_id), session_count(). Isolated so Phase 2 session evolution only touches this module (F-008).
- **`narrator_bridge.py`** — Server-side narration via MockNarrator. narrate_events(events, engine) → list[str]. Builds NarrationEvent + NarrationContext from each event and engine state, calls narrator.narrate() for each.
- **`serialisation.py`** — Domain object → API response converters. Handles frozenset → sorted list, VitalSigns → VitalSignsResponse, GameState → GameStateResponse, PatientContext → PatientContextResponse, Event → EventResponse, build_session_response().

### tests/

- **`test_api.py`** — End-to-end API tests using FastAPI TestClient: session lifecycle, response shapes, determinism, error handling, node content endpoint. ~30 tests.
- **`test_serialisation.py`** — Unit tests for serialisation helpers: frozensets become sorted lists, case_id is str, VitalSigns fields all nullable-safe. ~10 tests.
- **`test_narrator_bridge.py`** — Tests narrate_events(): empty list, parallel length, non-empty strings, MockNarrator output includes patient name. ~4 tests.

---

## packages/internal-affairs/

The SvelteKit web frontend. Ho 05 implementation: fully playable single-page game UI.

- **`package.json`** — npm config: SvelteKit 2.x, Svelte 5.x, Vite 7.x, TypeScript 5.x.
- **`README.md`** — What the frontend does: investigative UI, communicates with satori-api, renders the experience.
- **`svelte.config.js`** — SvelteKit config using adapter-auto.
- **`tsconfig.json`** — TypeScript strict mode config.
- **`vite.config.ts`** — Vite build config with SvelteKit plugin + dev proxy: /api → http://localhost:8000.
- **`.gitignore`** — SvelteKit-specific ignores.
- **`.npmrc`** — Enforces engine-strict for version matching.
- **`static/robots.txt`** — Allows all crawlers.
- **`src/app.html`** — HTML shell with SvelteKit placeholders.
- **`src/app.d.ts`** — TypeScript ambient declarations.
- **`src/lib/index.ts`** — Barrel file for $lib imports.
- **`src/lib/types.ts`** — All TypeScript types mirroring satori-api response models: VitalSigns, PatientContext, GameState, GameEvent, SessionResponse, ActionResponse, PatientCondition, EventLogEntry, AppView.
- **`src/lib/api.ts`** — Typed HTTP client: createSession, getSession, executeAction, getNodeContent, deleteSession. All calls use Vite proxy /api path. Exports ApiError.
- **`src/lib/assets/favicon.svg`** — Default Svelte logo.
- **`src/lib/stores/gameStore.svelte.ts`** — Svelte 5 runes game store. Holds full reactive state (sessionId, gameState, patient, patientCondition, availableActions, eventLog, view, isLoading, error). Methods: startSession, performAction, reset.
- **`src/lib/components/PatientHeader.svelte`** — Patient identity: name, age/sex/setting, chief complaint, appearance, triage note.
- **`src/lib/components/VitalsPanel.svelte`** — Vital signs grid with colour-coded status (normal/warn/critical) and patient condition badge.
- **`src/lib/components/ActionMenu.svelte`** — Available actions as grouped buttons. Action keys humanised (order_labs:cbc → "Order Labs: CBC").
- **`src/lib/components/EventLog.svelte`** — Turn-by-turn feed (newest first). Each entry shows narrated text for significant events plus expandable raw event data.
- **`src/lib/components/OutcomeScreen.svelte`** — Case resolution screen: outcome tier badge (OPTIMAL/GOOD/PARTIAL/FAILURE with colour), end reason, Play Again button.
- **`src/routes/+layout.svelte`** — Root layout: sets favicon, renders child routes.
- **`src/routes/+page.svelte`** — Single page application: start view → play view → outcome view, driven entirely by game store.
