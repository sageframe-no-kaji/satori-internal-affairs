# LLM Abstraction Layer — How We Talk to AI Models

**Package:** `packages/llm-client/`
**Milestone:** Ho 03
**What it enforces:** Boundary 4 (the provider line)

---

## Why This Exists

Our game has three places where we need an LLM:

1. **Case generation** — Ask an AI to create a complete medical case (a JSON file describing a patient, their condition, clues, tests, treatments, outcomes)
2. **Narration** — Ask an AI to turn dry game events ("node revealed: lab result") into readable prose ("The lab tech calls you over. The CSF sample shows elevated protein...")
3. **Action interpretation** — Ask an AI to parse what the player typed ("I want to check their reflexes") into a structured game action (`examine:neuro`)

The llm-client package is a wall between the rest of our code and whichever AI company we're using. OpenAI, Anthropic, a local model — the rest of the system doesn't know or care. It asks for a case, narration, or action parse, and gets back a result. That's the "provider line."

---

## The Big Picture

```
┌───────────────────────────────────────────────────────────────┐
│ YOUR CODE (Anamnesis, Satori, Internal Affairs)               │
│                                                               │
│   "Generate me a case about pneumonia"                        │
│   "Narrate this event for the player"                         │
│   "What action did the player mean?"                          │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│ llm-client (Boundary 4)                                       │
│                                                               │
│   CaseGenerator  ─── interface (abstract class)               │
│   Narrator       ─── interface (abstract class)               │
│   ActionInterpreter ── interface (abstract class)             │
│                                                               │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│   │   Mock   │  │  OpenAI  │  │ Anthropic│                   │
│   │ (tests)  │  │ (GPT-4)  │  │ (Claude) │                   │
│   └──────────┘  └──────────┘  └──────────┘                   │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│ THE INTERNET                                                  │
│   (HTTP calls to OpenAI / Anthropic APIs)                     │
└───────────────────────────────────────────────────────────────┘
```

Your code only ever sees the interfaces. It never imports `openai` or `anthropic` directly. It never constructs API calls. It never parses API responses. All of that is hidden behind the wall.

---

## Core Concepts

### 1. Interfaces (What You Ask For)

An **interface** is a contract: "any class that claims to be a CaseGenerator must have a `generate_case()` method that takes a seed and returns a dict." The interface doesn't say *how* it does it — just what goes in and what comes out.

We have three interfaces in `interfaces.py`:

| Interface | Method | Input | Output |
|-----------|--------|-------|--------|
| `CaseGenerator` | `generate_case(seed)` | `CaseSeed` | `dict` (raw JSON) |
| `Narrator` | `narrate(event, context)` | `NarrationEvent` + `NarrationContext` | `str` (prose) |
| `Narrator` | `explain(context)` | `ExplanationContext` | `str` (teaching text) |
| `ActionInterpreter` | `parse(raw_input, available_actions)` | `str` + `list[str]` | `ParsedAction` |

In Python, these are **abstract base classes** (ABCs). You can't instantiate them directly — you must create a concrete class that implements every `@abstractmethod`.

```python
from abc import ABC, abstractmethod

class CaseGenerator(ABC):
    @abstractmethod
    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        ...
```

This means if someone writes `class MyCaseGenerator(CaseGenerator)` but forgets to implement `generate_case()`, Python will raise an error at instantiation time. The interface enforces the contract.

### 2. Boundary Types (What Crosses the Wall)

The data that flows in and out of llm-client is defined as **frozen dataclasses**. These are the "boundary types" — they belong to llm-client, not to satori or anamnesis.

```python
@dataclass(frozen=True)
class CaseSeed:
    diagnosis: str
    difficulty: str
    dramatic_tone: str
    patient_age_range: tuple[int, int] | None = None
    patient_sex: str | None = None
    setting: str | None = None
    complications: list[str] | None = None
    learning_objectives: list[str] | None = None
    content_boundaries: list[str] | None = None
```

Why frozen? Because once you create a `CaseSeed`, nobody can change it. This makes them safe to pass around — no function can accidentally mutate your input.

Why does llm-client own these types instead of satori? Because llm-client defines what it needs. If satori owned `CaseSeed`, then satori would be dictating the LLM interface — and that's a boundary violation. The provider line exists so the LLM layer can evolve independently.

Key boundary types:

| Type | Purpose | Direction |
|------|---------|-----------|
| `CaseSeed` | What kind of case to generate | In → CaseGenerator |
| `NarrationEvent` | A game event to narrate | In → Narrator |
| `NarrationContext` | Current game state for narration | In → Narrator |
| `ExplanationContext` | What to explain to the learner | In → Narrator |
| `ParsedAction` | Structured result of parsing player input | Out ← ActionInterpreter |

### 3. Providers (Who Does the Work)

A **provider** is a concrete implementation of an interface. Each provider talks to a specific AI service (or fakes it for testing).

| Provider | Class | What It Does |
|----------|-------|--------------|
| Mock | `MockCaseGenerator` | Returns a hardcoded example case. No API calls. |
| Mock | `MockNarrator` | Returns templated strings like `[Mock Narration] ...` |
| Mock | `MockActionInterpreter` | Simple string matching, no AI |
| OpenAI | `OpenAICaseGenerator` | Sends prompts to GPT-4, parses JSON response |
| Anthropic | `AnthropicCaseGenerator` | Sends prompts to Claude, parses JSON response |

### 4. The Factory Pattern (How You Get a Provider)

You never directly construct an `OpenAICaseGenerator`. Instead, you use a **factory function**:

```python
from llm_client import ModelConfig, Provider, create_case_generator

config = ModelConfig(
    provider=Provider.OPENAI,
    model="gpt-4",
    api_key="sk-...",
    schema_path="schemas/case-definition.schema.json",
)

generator = create_case_generator(config)  # Returns an OpenAICaseGenerator
case = generator.generate_case(seed)       # You don't know or care what's behind this
```

The factory reads `config.provider` and returns the right class. Your calling code only sees `CaseGenerator` — it doesn't know if it got Mock, OpenAI, or Anthropic. This is the core of the abstraction.

To switch providers, you change one line (the `Provider` enum), not your entire codebase.

---

## How the OpenAI Provider Works (Step by Step)

This is the actual flow when you call `generate_case()` with OpenAI:

### Step 1: Construction

```python
config = ModelConfig(
    provider=Provider.OPENAI,
    model="gpt-4",
    api_key="sk-...",
    schema_path="schemas/case-definition.schema.json",
)
generator = create_case_generator(config)
```

Inside `OpenAICaseGenerator.__init__()`:
1. Load the JSON schema from disk into `self.schema_text`
2. Create an OpenAI client: `self.client = openai.OpenAI(api_key=...)`

The schema is loaded once at construction, not on every call. This avoids re-reading the file repeatedly.

### Step 2: Build the Prompts

When you call `generator.generate_case(seed)`, it builds two prompts:

**System prompt** (tells the AI what role it plays):
```
You are a medical case generator. Generate a complete, valid JSON object
conforming to the following schema. Return ONLY the JSON, no surrounding
text or explanation.

Schema:
{the entire JSON schema pasted here}

Key requirements:
- All node IDs must be unique
- All flag references must be set somewhere in the case
- All action references must exist in action_costs
- Timer stages must be sorted by at_minutes ascending
- The case must be medically plausible and educationally valuable
```

**User prompt** (tells it what specific case to create):
```
Generate a medical mystery case with the following specifications:
- Diagnosis: neurocysticercosis
- Difficulty: intermediate
- Dramatic tone: clinical
- Patient age range: 15-25 years
```

The system prompt includes our entire JSON schema. This teaches the AI the exact structure we need — every field, every type, every constraint. The user prompt provides the creative parameters.

### Step 3: Make the API Call

```python
response = self.client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.7,
    max_tokens=16384,
    response_format={"type": "json_object"},  # OpenAI-specific: force JSON output
)
```

Key parameters:
- **model**: Which AI model to use (GPT-4, GPT-4o, etc.)
- **messages**: The conversation history — system prompt sets behavior, user prompt gives the task
- **temperature**: Randomness (0.0 = deterministic, 1.0 = creative). We use 0.7 for variety while keeping structure.
- **max_tokens**: Maximum length of the response. Cases are big JSON objects, so we need ~16K.
- **response_format**: OpenAI-specific feature that forces the response to be valid JSON. This prevents the AI from wrapping its response in markdown code blocks or adding explanatory text.

### Step 4: Parse the Response

```python
content = response.choices[0].message.content
case_dict = json.loads(content)
return case_dict
```

The AI returns a string. We parse it as JSON and return the raw dict. **We do NOT validate it here.** Validation is the caller's job (anamnesis will validate against the schema before passing to satori). This keeps the LLM layer focused: talk to the API, get JSON back, hand it over.

### Step 5: Error Handling

Three things can go wrong:

| Error | Exception | When |
|-------|-----------|------|
| API is down, bad key, rate limit | `LLMProviderError` | The HTTP call itself failed |
| AI returned non-JSON or empty content | `LLMResponseError` | Got a response, but can't parse it |
| Response timed out | `LLMTimeoutError` | No response within deadline |

All three inherit from `LLMClientError`, so callers can catch broadly (`except LLMClientError`) or specifically (`except LLMProviderError`).

---

## How Anthropic Differs from OpenAI

The Anthropic provider does the same thing but the SDK differs:

| Aspect | OpenAI | Anthropic |
|--------|--------|-----------|
| Client | `openai.OpenAI(api_key=...)` | `anthropic.Anthropic(api_key=...)` |
| System prompt | Part of messages list | Separate `system=` parameter |
| JSON mode | `response_format={"type": "json_object"}` | Not available — we instruct in the prompt instead |
| Response shape | `response.choices[0].message.content` → `str` | `response.content[0].text` → `str` (content is a list of blocks) |
| User messages | `{"role": "system", ...}, {"role": "user", ...}` | Only user messages, system is separate |

The prompt content is identical. The wiring is different. This is exactly why the abstraction layer exists — your calling code doesn't need to know any of this.

---

## Optional Dependencies (How We Avoid Bloat)

Here's a practical problem: if you're running tests with the Mock provider, you don't want to install `openai` and `anthropic` packages. They're big, they pull in their own dependencies, and you don't need them.

Solution: **optional dependency groups** in `pyproject.toml`:

```toml
[project]
dependencies = []  # Zero required dependencies!

[project.optional-dependencies]
openai = ["openai>=1.0.0"]
anthropic = ["anthropic>=0.20.0"]
all = ["openai>=1.0.0", "anthropic>=0.20.0"]
```

Install what you need:
```bash
pip install llm-client              # Mock only, no SDK needed
pip install llm-client[openai]      # Mock + OpenAI
pip install llm-client[anthropic]   # Mock + Anthropic
pip install llm-client[all]         # Everything
```

The provider classes use **late imports** — they only `import openai` inside their `__init__()`, not at module level. This means Python doesn't try to find the openai package unless you actually construct an OpenAI provider:

```python
class OpenAICaseGenerator(CaseGenerator):
    def __init__(self, config):
        # This import only runs when you create an OpenAI generator
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.api_key)
        except ImportError as e:
            raise LLMProviderError(
                "openai package not installed. Install with: pip install llm-client[openai]"
            ) from e
```

If the package isn't installed, you get a clear error message telling you exactly what to install. If you never construct an OpenAI generator (because you're using Mock), the import never runs and you don't need the package.

---

## The Mock Provider (Why It Matters)

The Mock provider isn't just for unit tests — it's how we develop the entire system without spending money on API calls.

**MockCaseGenerator** loads our example case file (`cases/example-neurocysticercosis.json`) and returns it as a dict. Every call returns the same case. This means:
- Satori can be developed and tested against a real case structure
- The frontend can render real case data
- The full pipeline works end-to-end without any API keys
- Tests are fast (no network calls) and deterministic (same input = same output)

**MockNarrator** returns templated strings: `"[Mock Narration] Maria experiences node_revealed: Lab results show..."`. Ugly, but functional — the frontend can display it, and you can see the event flow.

**MockActionInterpreter** does simple string matching. If the player types "examine" and "examine:neuro" is an available action, it matches. No AI needed.

In Phase 1, all three interfaces only have Mock implementations fully working. The OpenAI and Anthropic classes exist for CaseGenerator, but they're not wired into the pipeline yet. That happens in Ho 04 (Anamnesis).

---

## How This Connects to the Rest of the System

```
                        ┌──────────────┐
                        │  Anamnesis   │  (Ho 04 — case generation pipeline)
                        │              │
                        │  Uses:       │
                        │  CaseGenerator│
                        │  CaseSeed    │
                        └──────┬───────┘
                               │ calls create_case_generator()
                               │ passes CaseSeed
                               │ gets back dict
                               │ validates against schema
                               │ converts to CaseDefinition
                               ▼
                        ┌──────────────┐
                        │   Satori     │  (Ho 02 — game engine)
                        │              │
                        │  Receives:   │
                        │  CaseDefinition│
                        │  (frozen)    │
                        └──────┬───────┘
                               │ emits Events
                               ▼
                     ┌─────────────────────┐
                     │  Internal Affairs   │  (Ho 05 — frontend)
                     │                     │
                     │  Uses:              │
                     │  Narrator           │
                     │  ActionInterpreter  │
                     │  NarrationEvent     │
                     │  NarrationContext   │
                     │  ParsedAction       │
                     └─────────────────────┘
```

The key insight: **CaseGenerator is used at generation time (before the game starts). Narrator and ActionInterpreter are used at play time (during the game).** These are two completely different moments. Boundary 1 (the freeze line) separates them.

---

## Design Decisions Worth Understanding

### Why `generate_case()` returns `dict`, not `CaseDefinition`

The LLM returns JSON text. We parse it into a Python dict. We do NOT convert it to a `CaseDefinition` (satori's model). Why?

1. **Separation of concerns** — llm-client shouldn't depend on satori. If it imported `CaseDefinition`, changing satori's models would break llm-client.
2. **Validation is the caller's job** — The AI might return invalid JSON. The caller (anamnesis) validates against the schema and decides what to do if it's wrong.
3. **The dict can be logged, inspected, modified** — Before converting to a frozen model, anamnesis might want to patch things, log the raw output, or retry.

### Why three interfaces instead of one big "LLMService"

Each interface has a fundamentally different job:
- CaseGenerator needs a JSON schema and returns structured data
- Narrator needs game context and returns prose
- ActionInterpreter needs available actions and returns parsed structure

A single "LLMService" would mean every implementation must handle all three concerns. With separate interfaces, you can use OpenAI for case generation but Anthropic for narration — or Mock for everything during development.

### Why frozen dataclasses for boundary types instead of Pydantic models

Satori uses Pydantic because it needs complex validation (nested models, custom validators). The boundary types are simple value objects — just data containers. Dataclasses are lighter weight, have no dependencies, and `frozen=True` makes them immutable. They're the right tool for the job.

### Why the factory validates config but doesn't validate output

The factory checks that you have an API key and schema path before constructing a provider. This prevents confusing errors deep in the constructor. But it doesn't validate the LLM's output because:
- The factory doesn't know what "valid" means (that's schema-dependent)
- The caller might want the raw output even if it's invalid (for debugging)
- Validation logic belongs in the consumer, not the producer

---

## File Map

```
packages/llm-client/
├── pyproject.toml              # Package config, optional deps (openai, anthropic)
├── src/llm_client/
│   ├── __init__.py             # Public API — everything importable from here
│   ├── interfaces.py           # ABC interfaces + boundary types (CaseSeed, etc.)
│   ├── config.py               # ModelConfig, Provider enum, factory functions
│   ├── exceptions.py           # LLMClientError hierarchy
│   ├── mock.py                 # MockCaseGenerator, MockNarrator, MockActionInterpreter
│   ├── openai_generator.py     # OpenAICaseGenerator (real API calls)
│   └── anthropic_generator.py  # AnthropicCaseGenerator (real API calls)
└── tests/
    ├── test_boundary_types.py              # CaseSeed, ParsedAction, etc. construction
    ├── test_boundary_types_comprehensive.py # All boundary type fields + defaults
    ├── test_config.py                      # ModelConfig, Provider enum
    ├── test_factory.py                     # create_case_generator factory
    ├── test_factory_comprehensive.py       # All three factories
    ├── test_interfaces.py                  # ABC enforcement (can't instantiate)
    ├── test_mock.py                        # Mock implementations
    ├── test_schema_conformance.py          # Mock output vs JSON schema
    └── test_error_handling.py              # Exception hierarchy + error wrapping
```

---

## Quick Reference: Using llm-client in Your Code

### Generate a case (what Anamnesis will do)

```python
from llm_client import (
    CaseSeed,
    ModelConfig,
    Provider,
    create_case_generator,
)

# For development: use Mock (no API key needed)
config = ModelConfig(provider=Provider.MOCK, model="mock")
generator = create_case_generator(config)

seed = CaseSeed(
    diagnosis="pneumothorax",
    difficulty="intermediate",
    dramatic_tone="clinical",
    patient_age_range=(20, 40),
)

case_dict = generator.generate_case(seed)
# case_dict is a raw Python dict — validate it yourself
```

### Generate a case with a real LLM

```python
# For production: use OpenAI
config = ModelConfig(
    provider=Provider.OPENAI,
    model="gpt-4",
    api_key="sk-...",
    schema_path="schemas/case-definition.schema.json",
)
generator = create_case_generator(config)

try:
    case_dict = generator.generate_case(seed)
except LLMProviderError as e:
    print(f"API error: {e}")  # Network, auth, rate limit
except LLMResponseError as e:
    print(f"Bad response: {e}")  # AI returned garbage
```

### Narrate an event (what Internal Affairs will do)

```python
from llm_client import (
    ModelConfig,
    NarrationContext,
    NarrationEvent,
    Provider,
    create_narrator,
)

config = ModelConfig(provider=Provider.MOCK, model="mock")
narrator = create_narrator(config)

event = NarrationEvent(
    event_type="node_revealed",
    description="CBC results available",
    structured_data={"wbc": 15000, "rbc": 4.5},
)

context = NarrationContext(
    patient_name="Maria",
    patient_age=19,
    patient_sex="female",
    setting="Emergency Department",
    current_vitals={"heart_rate": 95, "temperature": 38.5},
    elapsed_minutes=15,
)

prose = narrator.narrate(event, context)
# "[Mock Narration] Maria experiences node_revealed: CBC results available (Time: 15 minutes)"
```

### Parse player input (what Internal Affairs will do)

```python
from llm_client import ModelConfig, Provider, create_action_interpreter

config = ModelConfig(provider=Provider.MOCK, model="mock")
interpreter = create_action_interpreter(config)

result = interpreter.parse(
    raw_input="I want to examine the patient's neurological status",
    available_actions=["history_general", "examine:neuro", "examine:general", "order:cbc"],
)

# result.action_type = "examine"
# result.parameter = "neuro"
# result.confidence = 1.0
```

---

## What Comes Next

- **Ho 04 (Anamnesis)** will be the first real consumer of `CaseGenerator`. It will call `create_case_generator()`, pass a `CaseSeed`, validate the returned dict against the JSON schema, and convert it to a `CaseDefinition` for Satori.
- **Ho 05 (Internal Affairs)** will use `Narrator` and `ActionInterpreter` to give the player a rich text experience on top of Satori's structured events.
- When we add real Narrator and ActionInterpreter implementations for OpenAI/Anthropic, we'll follow the same pattern: create a class, implement the interface methods, register it in the factory. No other code changes.
