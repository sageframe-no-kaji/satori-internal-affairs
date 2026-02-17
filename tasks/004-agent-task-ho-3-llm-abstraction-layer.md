# TASK: LLM ABSTRACTION LAYER

## GOAL

Build the `packages/llm-client/` package — the provider-agnostic LLM abstraction layer that enforces Boundary 4 (the provider line).

Three distinct interfaces for three distinct LLM concerns:

| Interface | Phase 1 Scope | Return Type |
|---|---|---|
| `CaseGenerator` | **Fully implemented** — OpenAI + Anthropic providers | `dict[str, Any]` |
| `Narrator` | **Interface + mock only** | `str` |
| `ActionInterpreter` | **Interface stub + mock only** | `ParsedAction` |

When this task is complete:
- `CaseGenerator` works against live OpenAI and Anthropic APIs
- `Narrator` and `ActionInterpreter` exist as abstract interfaces with mock implementations
- Every mock passes tests without network calls or API keys
- No file in `llm-client` imports anything from `satori`

## CONTEXT

This is Ho 03 / Milestone 3 of the Phase 1 gameplan.

**Upstream:** Ho 00 (scaffolding), Ho 01 (case schema), Ho 02 (Satori engine) are complete. The scaffolded `packages/llm-client/` directory exists with an empty `__init__.py` and placeholder test.

**Downstream consumers:**
- **Anamnesis (Ho 04):** Calls `CaseGenerator.generate_case(seed)`. Receives a raw `dict[str, Any]`, validates it against `CaseDefinition` Pydantic models, and owns the retry-validate-repair loop. Validation does NOT happen in `llm-client`.
- **Internal Affairs (Ho 05):** Will eventually call `Narrator.narrate()` — Phase 1 uses frozen text from the case definition instead.
- **Future F-002 (Infocom Expert Mode):** Will eventually call `ActionInterpreter.parse()` — Phase 1 uses structured menus.

**Schema reference:** The JSON schema at `schemas/case-definition.schema.json` is included in `generate_case` prompts so the LLM knows the target structure. The generator loads this file at construction time.

**Critical constraint:** `llm-client` has **zero dependency on `satori`**. It never imports `CaseDefinition`, `GameState`, `Event`, or any satori type. It defines its own boundary types. Conversion between satori types and llm-client types happens at the call site in Anamnesis or Internal Affairs — never here.

---

## DO NOT CHANGE

- `schemas/` — the case definition schema (frozen from Ho 01)
- `packages/satori/` — the engine package (frozen from Ho 02)
- `packages/anamnesis/` — scaffolded, not yet implemented
- `packages/internal-affairs/` — SvelteKit scaffold
- Root project files (`README.md`, `Makefile`, etc.)

---

## DESIGN DECISIONS (MADE)

These are binding. Do not revisit.

### Decision 1: Three Separate Interfaces

`CaseGenerator`, `Narrator`, and `ActionInterpreter` are separate abstract base classes — NOT methods on a single `LLMClient`. Each serves a different LLM concern with different model requirements:
- **Case generation:** Reasoning models (GPT-4o, Claude Sonnet), moderate temperature, structured JSON output
- **Narration:** Creative models (GPT-5, Claude Opus), higher temperature, prose output
- **Intent parsing:** Fast/cheap models (GPT-4o-mini, Claude Haiku), low temperature, structured output

### Decision 2: JSON Mode + Post-Validation

Structured output from `generate_case` uses JSON mode (both OpenAI and Anthropic support this). The LLM returns a JSON string. `llm-client` parses it to `dict[str, Any]` and returns it. Schema validation against `CaseDefinition` happens in Anamnesis (Ho 04), NOT here. This keeps `llm-client` fully independent of `satori`.

### Decision 3: `generate_case` Returns `dict[str, Any]`

Never domain types. Never `CaseDefinition`. The `llm-client` package does not know what a valid case looks like — it just talks to LLMs and returns parsed JSON. Domain validation is Anamnesis's job.

### Decision 4: Sync Interface

All methods are synchronous. Matches Satori's patterns. Async can be added as a separate protocol layer in a future phase without changing the interface.

### Decision 5: Both OpenAI and Anthropic for CaseGenerator

Two provider implementations prove the abstraction works. OpenAI is primary. Anthropic is proof-of-concept that the interface can be swapped.

### Decision 6: Per-Interface Model Configuration

Each interface gets its own `ModelConfig`. A `CaseGenerator` can use `gpt-4o` while a `Narrator` (future) uses a creative model. Config is per-instance, not global.

### Decision 7: Narrator and ActionInterpreter Are Stubs

No live provider implementations for `Narrator` or `ActionInterpreter` in Phase 1. Interface definition + `MockNarrator` + `MockActionInterpreter` only. Provider implementations are built when their features are built (F-001, F-002).

---

## REQUIRED COMPONENTS

All source files go in `packages/llm-client/src/llm_client/`. All test files go in `packages/llm-client/tests/`.

### interfaces.py

Three abstract base classes and their boundary types.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseSeed:
    """Input for case generation. Owned by llm-client, not satori."""
    diagnosis: str
    difficulty: str  # matches Difficulty enum values
    dramatic_tone: str  # matches DramaticTone enum values
    patient_age_range: tuple[int, int] | None = None
    patient_sex: str | None = None
    setting: str | None = None
    complications: list[str] | None = None
    learning_objectives: list[str] | None = None
    content_boundaries: list[str] | None = None


@dataclass(frozen=True)
class NarrationEvent:
    """Lightweight event data for narration. Owned by llm-client."""
    event_type: str
    description: str
    structured_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class NarrationContext:
    """Current game context for narration. Owned by llm-client."""
    patient_name: str
    patient_age: int
    patient_sex: str
    setting: str
    current_vitals: dict[str, Any]
    elapsed_minutes: int


@dataclass(frozen=True)
class ExplanationContext:
    """Context for teaching explanations. Owned by llm-client."""
    topic: str
    patient_context: str
    detail_level: str = "intermediate"


@dataclass(frozen=True)
class ParsedAction:
    """Result of natural language intent parsing. Owned by llm-client."""
    action_type: str
    parameter: str | None = None
    confidence: float = 1.0
    raw_input: str = ""


class CaseGenerator(ABC):
    """Generate structured case definitions from seeds."""

    @abstractmethod
    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        """Generate a case definition as raw parsed JSON.

        Returns a dict — NOT a CaseDefinition. Validation is the caller's job.

        Raises:
            LLMProviderError: API call failed
            LLMResponseError: Response was not valid JSON
        """
        ...


class Narrator(ABC):
    """Generate narrative text from game events."""

    @abstractmethod
    def narrate(self, event: NarrationEvent, context: NarrationContext) -> str:
        """Generate narrative text for a game event."""
        ...

    @abstractmethod
    def explain(self, context: ExplanationContext) -> str:
        """Generate a teaching explanation."""
        ...


class ActionInterpreter(ABC):
    """Parse natural language input into structured actions."""

    @abstractmethod
    def parse(self, raw_input: str, available_actions: list[str]) -> ParsedAction:
        """Parse free-text player input into a structured action."""
        ...
```

### config.py

```python
from dataclasses import dataclass, field
from enum import StrEnum


class Provider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for an LLM provider instance."""
    provider: Provider
    model: str
    api_key: str | None = None  # None for mock
    temperature: float = 0.7
    max_tokens: int = 16384
    # Path to JSON schema file for prompt inclusion (CaseGenerator only)
    schema_path: str | None = None
```

Include factory functions:
- `create_case_generator(config: ModelConfig) -> CaseGenerator`
- `create_narrator(config: ModelConfig) -> Narrator`
- `create_action_interpreter(config: ModelConfig) -> ActionInterpreter`

Factory must:
- Return `MockCaseGenerator`/`MockNarrator`/`MockActionInterpreter` when `provider == Provider.MOCK`
- Raise `LLMClientError` if `api_key` is `None` for non-mock providers
- Raise `LLMClientError` if `schema_path` is `None` when creating a non-mock `CaseGenerator`

### exceptions.py

```python
class LLMClientError(Exception):
    """Base exception for llm-client."""

class LLMProviderError(LLMClientError):
    """API call to the provider failed (network, auth, rate limit)."""

class LLMResponseError(LLMClientError):
    """Provider returned a response that could not be parsed as JSON."""

class LLMTimeoutError(LLMClientError):
    """Provider did not respond within the timeout."""
```

### openai_generator.py

`OpenAICaseGenerator(CaseGenerator)` using the `openai` Python SDK.

Requirements:
- Constructor takes `ModelConfig`. Reads schema from `config.schema_path` at construction time and stores it.
- `generate_case(seed)` builds a system prompt + user prompt, calls the API with `response_format={"type": "json_object"}`, parses the JSON response, and returns `dict[str, Any]`.
- System prompt instructs the LLM to generate a complete medical case conforming to the included JSON schema. Include the full schema text in the system prompt.
- User prompt is constructed from `CaseSeed` fields.
- Wrap OpenAI SDK errors in `LLMProviderError`.
- Wrap JSON parse failures in `LLMResponseError`.
- Default model: `gpt-4o`

### anthropic_generator.py

`AnthropicCaseGenerator(CaseGenerator)` using the `anthropic` Python SDK.

Same pattern as OpenAI but adapted for Anthropic's API:
- Uses Anthropic's message API with JSON-requesting system prompt
- No `response_format` parameter — instruct JSON-only output via system prompt
- Wrap Anthropic SDK errors in `LLMProviderError`
- Default model: `claude-sonnet-4-20250514`

### mock.py

Three mock implementations. **No network calls. No API keys. Deterministic.**

- `MockCaseGenerator`: Returns a hardcoded dict loaded from `cases/example-neurocysticercosis.json` (pass path at construction, or embed a minimal valid case dict). Must return a `dict[str, Any]` that would pass `CaseDefinition` validation.
- `MockNarrator`: `narrate()` returns a templated string incorporating the event type and patient name. `explain()` returns a templated string incorporating the topic.
- `MockActionInterpreter`: `parse()` does simple string matching — splits on whitespace, matches first word against available actions, returns `ParsedAction` with confidence 1.0 if matched, 0.0 if not.

### __init__.py

Export the full public API:

```python
from llm_client.interfaces import (
    CaseGenerator, Narrator, ActionInterpreter,
    CaseSeed, NarrationEvent, NarrationContext,
    ExplanationContext, ParsedAction,
)
from llm_client.config import ModelConfig, Provider, create_case_generator, create_narrator, create_action_interpreter
from llm_client.exceptions import LLMClientError, LLMProviderError, LLMResponseError, LLMTimeoutError
from llm_client.mock import MockCaseGenerator, MockNarrator, MockActionInterpreter
```

### pyproject.toml updates

Replace the existing empty dependencies with optional groups:

```toml
[project]
dependencies = []

[project.optional-dependencies]
openai = ["openai>=1.0"]
anthropic = ["anthropic>=0.20"]
all = ["openai>=1.0", "anthropic>=0.20"]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
]
```

No `pydantic` dependency. No `satori` dependency.

### .env.example

Create at project root (`/` not inside `packages/llm-client/`):

```
# LLM Provider API Keys
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

---

## IMPLEMENTATION GUIDANCE

- **Prompt construction:** Include the full JSON schema text in the system prompt for `generate_case`. The schema is ~300 lines — this is fine for modern context windows. Make the system prompt clear: "Generate a complete, valid JSON object conforming to the following schema. Return ONLY the JSON, no surrounding text."
- **API key loading:** Read from `ModelConfig.api_key` directly. The caller is responsible for loading from environment variables — the config layer doesn't auto-read env vars. This keeps the config pure and testable.
- **Error wrapping:** Catch provider-specific exceptions (`openai.APIError`, `anthropic.APIError`) and re-raise as `LLMProviderError`. Catch `json.JSONDecodeError` and re-raise as `LLMResponseError`. Never let provider-specific exceptions leak through the interface.
- **No streaming:** Simple request/response. One API call, one complete response.
- **No retry logic in llm-client:** Retry-on-validation-failure belongs in Anamnesis. `llm-client` makes one call, returns the parsed dict or raises. Simple.
- **Integration test convention:** Tests that call live APIs must be marked `@pytest.mark.integration` and skipped by default. Define this marker in `conftest.py` or `pyproject.toml`. Running `pytest` without flags runs only unit tests. Running `pytest -m integration` runs API tests.

---

## INVARIANTS TO PRESERVE

1. **Zero satori imports:** No file in `packages/llm-client/` imports from `satori`, `satori.models`, `satori.events`, or any satori module
2. **Return type discipline:** `generate_case` returns `dict[str, Any]` — never a Pydantic model, never a string
3. **No domain validation:** `llm-client` never validates whether a returned dict is a valid case definition
4. **Provider isolation:** No OpenAI or Anthropic types appear in `interfaces.py`, `config.py`, `mock.py`, `exceptions.py`, or `__init__.py`
5. **Mock purity:** Mock implementations make zero network calls and require zero API keys
6. **Sync only:** All interface methods are synchronous
7. **Stubs are stubs:** `Narrator` and `ActionInterpreter` have no live provider implementations — mock only

---

## ACCEPTANCE CHECKS (MANDATORY)

### Interface & Type Safety
1. `CaseGenerator()` raises `TypeError` — it's abstract
2. `Narrator()` raises `TypeError` — it's abstract
3. `ActionInterpreter()` raises `TypeError` — it's abstract
4. `mypy --strict` passes on all `llm-client` source files
5. `ruff` passes on all `llm-client` source and test files

### Mock Implementations
6. `MockCaseGenerator.generate_case(seed)` returns a `dict` with keys `id`, `version`, `metadata`, `patient`, `ground_truth`, `action_costs`, `nodes`, `outcome_evaluation`
7. `MockNarrator.narrate(event, context)` returns a non-empty `str`
8. `MockNarrator.explain(context)` returns a non-empty `str`
9. `MockActionInterpreter.parse(input, actions)` returns a `ParsedAction`
10. All mock tests pass without API keys set

### Config & Factory
11. `create_case_generator(MockConfig)` returns a `MockCaseGenerator`
12. `create_case_generator(OpenAIConfig)` returns an `OpenAICaseGenerator`
13. `create_case_generator(config_with_no_api_key)` raises `LLMClientError`
14. `create_case_generator(config_with_no_schema_path)` raises `LLMClientError` (for non-mock)

### Provider Implementations
15. `OpenAICaseGenerator` is a subclass of `CaseGenerator`
16. `AnthropicCaseGenerator` is a subclass of `CaseGenerator`
17. Both constructors load and store the JSON schema from `schema_path`

### Integration (marked, skipped by default)
18. `OpenAICaseGenerator.generate_case(seed)` returns a `dict` with expected top-level keys
19. `AnthropicCaseGenerator.generate_case(seed)` returns a `dict` with expected top-level keys

### Boundary Enforcement
20. `grep -r "from satori" packages/llm-client/` returns zero matches
21. `grep -r "import satori" packages/llm-client/` returns zero matches
22. `.env.example` exists at project root with `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`

---

## LINE COUNT EXPECTATION

| File | Est. Lines |
|---|---|
| `interfaces.py` | ~90 |
| `config.py` | ~70 |
| `exceptions.py` | ~20 |
| `openai_generator.py` | ~100 |
| `anthropic_generator.py` | ~90 |
| `mock.py` | ~80 |
| `__init__.py` | ~20 |
| **Source total** | **~470** |
| `tests/test_interfaces.py` | ~40 |
| `tests/test_mock.py` | ~80 |
| `tests/test_config.py` | ~60 |
| `tests/test_providers.py` | ~50 |
| `tests/test_integration.py` | ~40 |
| `tests/conftest.py` | ~20 |
| **Test total** | **~290** |

---

## QUALITY

- All code type-checked with `mypy --strict`
- All code linted with `ruff` (line-length 100, selects `E,F,I,N,W,UP`)
- Docstrings on all classes and public methods
- All tests have real assertions — no `assert True` placeholders
- No `# type: ignore` without justification comment
- Integration tests skipped by default (marker-gated)

---

## COMMIT

```
feat(llm-client): LLM abstraction layer with three-interface architecture

- CaseGenerator, Narrator, ActionInterpreter as separate ABCs
- OpenAI and Anthropic implementations of CaseGenerator
- Mock implementations for all three interfaces
- ModelConfig with per-interface provider/model configuration
- Factory functions for client creation
- Zero dependency on satori — fully independent package
- Integration tests gated behind @pytest.mark.integration
- .env.example with API key placeholders

Boundary 4 (provider line) enforced: no provider types leak through interfaces
```
