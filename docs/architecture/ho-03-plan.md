# Ho 03 Plan — LLM Abstraction Layer

Planning document for Ho 03. Captures design decisions and architectural reasoning.
The agent task spec is in `tasks/004-agent-task-ho-3-llm-abstraction-layer.md`.

---

## Architecture: Three Interfaces, Three Concerns

| Interface | Purpose | Phase 1 Scope | Model Class | Example Models |
|---|---|---|---|---|
| `CaseGenerator` | Produce structured case JSON from a seed | **Fully implemented + tested** | Reasoning | GPT-4o, Claude Sonnet |
| `Narrator` | Generate flavor text during play, explain for teaching | **Interface + mock only** | Creative | GPT-5, Claude Opus/Sonnet 4.5 |
| `ActionInterpreter` | Parse natural language player input → structured action | **Interface stub + mock only** | Fast/cheap | GPT-4o-mini, Claude Haiku |

**Why separate:** Different models, different temperatures, different providers, different reliability requirements. Case generation needs correctness; narration needs richness; intent parsing needs speed. Forcing these through one abstraction hides essential differences.

**Phase 1 gameplay is structured multiple-choice.** No LLM calls during play. All narrative is frozen text from the case definition. `ActionInterpreter` is stubbed to keep the door open for F-002 (Infocom Expert Mode, Phase 3+). `Narrator` stubs preserve the path for F-001 (Play-Time Narrative Generation, Phase 3).

---

## Decisions Made

1. **Three separate interfaces** — `CaseGenerator`, `Narrator`, `ActionInterpreter` — not one unified `LLMClient`. Different concerns, different models, different configs.
2. **JSON mode + Pydantic post-validation** for structured output — uniform across providers. Validation and retry logic belongs in Anamnesis (Ho 04), not in `llm-client`.
3. **`generate_case` returns `dict[str, Any]`** — raw parsed JSON, not domain types. `llm-client` has zero imports from `satori`. Fully independent.
4. **Sync interface** for Phase 1. Async can be added as a separate protocol later.
5. **Both OpenAI and Anthropic** implementations for `CaseGenerator`. Proves the abstraction works.
6. **Per-interface model configuration** — each interface gets its own `ModelConfig` (provider, model name, temperature, max_tokens). Narration can use a creative model while generation uses a reasoning model.
7. **`Narrator` and `ActionInterpreter` are interface + mock only in Phase 1.** No live provider implementations until their respective features are built.

---

## Key Design Rationale

- **Three interfaces, not one:** Case generation, narration, and intent parsing have fundamentally different model requirements. Forcing them through one abstraction hides essential architectural differences. Different models (reasoning vs creative vs fast), different temperatures, potentially different providers.
- **`dict[str, Any]` return, not `CaseDefinition`:** Keeps `llm-client` fully independent. Validation is Anamnesis's job. The retry-validate-repair loop belongs in the domain layer (Ho 04), not the communication layer.
- **JSON mode + validation over Structured Outputs:** Uniform across providers. Structured Outputs is OpenAI-only and would break the provider abstraction. Can be added as an internal optimization later if needed.
- **Sync over async:** Matches Satori. Phase 1 is single-player, single-case. Async is a future concern that doesn't affect the interface design.
- **Stub `ActionInterpreter`:** May or may not be desirable (F-002). Stubbing it costs nothing and keeps the door open. If it's never built, the stub is harmless.

---

## Downstream Consumers

- **Anamnesis (Ho 04):** calls `CaseGenerator.generate_case()`, validates returned dict against Pydantic models, retries on validation failure
- **Internal Affairs (Ho 05):** will eventually call `Narrator.narrate()` — Phase 1 uses frozen text instead
- **Internal Affairs (future F-002):** will eventually call `ActionInterpreter.parse()` — Phase 1 uses structured menus
