# How the Case Generation Pipeline Works (Ho 04)

This document explains the ideas behind `packages/anamnesis/` — the package that generates case files. It is written to be understood, not just referenced. It covers why each piece is designed the way it is, with short code examples to make the concepts concrete.

---

## The Problem We're Solving

Satori needs case files. Case files are complex JSON documents: they encode nodes, timers, conditions, flags, and action costs in a way the engine can deterministically execute. Hand-authoring every case would be prohibitively slow. So we use an LLM to write them.

But an LLM cannot be trusted to produce valid output every time. A case file with a mistyped action reference, an unsorted timer, or a missing required field will crash the engine at load time. That crash happens during a player's session — the worst possible moment.

**The central job of Anamnesis is this: accept creative input, call the LLM, and refuse to save anything that doesn't fully validate.**

This is what the project calls **Boundary 1** — the freeze line. Once a case file crosses into `cases/generated/`, it has been validated. The engine can trust it. Anamnesis is the gatekeeper at that line.

---

## The Shape of the Pipeline

The full flow from start to finish:

```
CreativeSeed          → tells the LLM what kind of case to build
    ↓
CaseGenerationPipeline.generate()
    ↓
llm-client (CaseGenerator)  → calls the LLM, returns raw JSON dict
    ↓
validate_case_dict()        → checks the dict against CaseDefinition model
    ↓
  success? → _make_success() → pipeline.save() → frozen .json file
  failure? → retry loop    → repair prompt  → _make_failure()
```

Five modules, five jobs:

| Module | Job |
|---|---|
| `seed.py` | What do you want the LLM to build? |
| `validator.py` | Is what the LLM returned valid? |
| `result.py` | What happened (success or failure, with details)? |
| `prompts.py` | What do you say to the LLM when it fails? |
| `pipeline.py` | Orchestrates everything above |

---

## Seeds: Describing What You Want

### The basic idea

Before calling the LLM you have to describe the case you want. That description is a **seed**. The seed is a plain data object — it has no methods that do work, it just holds information.

The llm-client package (Ho 03) already defines a `CaseSeed` type with the fields it understands: diagnosis, difficulty, dramatic tone, complications, etc. Those field values get embedded into the LLM prompt.

### Why we didn't stop there

`CaseSeed` covers the medical specification side: *what disease, how hard, what complications*. But when a human author sits down to brief a case, they think in narrative terms: *what's the opening scene, what misleads the player, what's the emotional core of this story*.

These narrative fields are real and important. We want to capture them. But they don't belong in `CaseSeed` — that's an llm-client type, and it only knows about the fields that the LLM prompt template uses. Poluting it with narrative metadata would create coupling between the generation tool and the prompt engine.

So we created `CreativeSeed`:

```python
@dataclass(frozen=True)
class CreativeSeed:
    # Medical requirements — these map 1:1 to CaseSeed fields
    diagnosis: str
    difficulty: str
    dramatic_tone: str
    patient_age_range: tuple[int, int] | None = None
    complications: list[str] | None = None
    # ... etc

    # Narrative direction — these are prompt context only
    dramatic_hook: str | None = None      # opening scene
    red_herrings: list[str] | None = None # misleading clues
    character_notes: str | None = None    # patient personality
    key_twists: list[str] | None = None   # dramatic turns
    emotional_core: str | None = None     # the human story
    forbidden_tropes: list[str] | None = None  # things to avoid
```

When the pipeline needs to talk to the LLM via llm-client, it does this:

```python
case_seed = seed.to_case_seed()  # strips the creative fields, returns a CaseSeed
raw_dict = self._generator.generate_case(case_seed)
```

The creative fields never leave the anamnesis layer. They're there for the prompt builder — and for a human reading a YAML seed file to understand the authorial intent.

### The `has_creative_fields()` check

```python
if seed.has_creative_fields():
    logger.info("Seed has creative fields (Mode 2). Creative-only fields are noted ...")
```

This is how the pipeline knows whether it's in "Mode 1" (automated, just medical spec) or "Mode 2" (human-authored narrative brief). There's no separate type, no branch on class identity — just a predicate. Adding a Mode 3 later just means adding fields to `CreativeSeed` and updating this predicate if needed.

### YAML for seed files

Human authors write seeds in YAML. YAML supports multiline strings natively (block scalars), which is important for fields like `dramatic_hook` and `emotional_core` that are paragraphs of prose. YAML also supports inline comments, which make seed files self-documenting.

```yaml
# seeds/example-neurocysticercosis-rich.yaml
diagnosis: Neurocysticercosis
difficulty: hard
dramatic_tone: tense

dramatic_hook: >
  A 34-year-old woman arrives mid-seizure, her husband sprinting
  behind the gurney shouting "she's never had one before!"

red_herrings:
  - Recent international travel making dengue plausible
  - Slightly elevated liver enzymes suggesting alcoholic etiology

forbidden_tropes:
  - Do not make the diagnosis obvious from the chief complaint
  - Avoid the "exotic disease tourist" framing
```

JSON for output (the validated case file) — JSON is machine-readable, deterministic, and the right format for what the engine consumes.

---

## Validation: The Gatekeeper at Boundary 1

### Why two phases?

Schema validation (does this dict have the right shape?) and structural validation (are the cross-references inside it consistent?) are different problems requiring different tools.

**Phase 1 — Pydantic schema validation:**

Pydantic checks field types, required fields, enum values, and nested structure in one call:

```python
try:
    case = CaseDefinition.model_validate(raw_dict)
except ValidationError as e:
    errors = [f"[schema] {_format_pydantic_error(err)}" for err in e.errors()]
    return None, errors
```

If `case.nodes[0].reveal.action` refers to a field that must be a string, but the LLM put a number there, Pydantic catches it here.

**Phase 2 — Structural checks:**

After Pydantic succeeds we have a proper `CaseDefinition` object, not a raw dict. Now we can walk it and check things Pydantic cannot:

```python
def _check_structural(case: CaseDefinition) -> list[str]:
    errors: list[str] = []
    known_actions = set(case.action_costs.keys())

    # Duplicate node IDs
    seen: set[str] = set()
    for node in case.nodes:
        if node.id in seen:
            errors.append(f"[structural] Duplicate node id: '{node.id}'")
        seen.add(node.id)

    for node in case.nodes:
        # Action references that don't exist
        if node.reveal and node.reveal.action:
            if node.reveal.action not in known_actions:
                errors.append(
                    f"[structural] Node '{node.id}' reveal.action '{node.reveal.action}' "
                    f"not found in action_costs"
                )

        # Timer stages must be ascending
        if node.timer and node.timer.stages:
            for i in range(1, len(node.timer.stages)):
                if node.timer.stages[i].at_minutes <= node.timer.stages[i-1].at_minutes:
                    errors.append(f"[structural] Node '{node.id}' timer stages not ascending")

    return errors
```

**Why not combine them both into phase 1?**

Because phase 2 requires a schema-valid object. If Pydantic fails, `case.nodes` doesn't exist yet — we can't walk it safely. The phases are sequential by necessity.

**Why not put structural checks inside Pydantic validators?**

Pydantic validators run per-field, during construction. Cross-node checks (is *this* node's action reference in *that other node's* action_costs?) require seeing the whole case at once. Pydantic validators don't see sibling fields cleanly. And mixing Pydantic concerns with game-engine concerns in one place makes both harder to read and test independently.

### The `[schema]` and `[structural]` prefixes

Every error message is prefixed with either `[schema]` or `[structural]`. This matters when errors get sent back to the LLM in the repair prompt — the model can see *what kind* of problem it made, not just a flat error list. It also makes test assertions cleaner:

```python
_, errors = validate_case_dict(bad_dict)
assert any("[structural]" in e for e in errors)
```

---

## Result: No Exceptions for Expected Failures

### The core idea

LLM output failing validation is not exceptional — it's routine. LLMs sometimes produce invalid JSON, miss required fields, or write action references that don't exist. This happens on probably 10–30% of calls with a less-capable model.

If `pipeline.generate()` raised an exception on validation failure, every caller would need to wrap it in `try/except`. The CLI, the future Case Builder GUI, a batch script — all would need to catch and inspect the exception to find out what went wrong and whether to retry. That's the wrong tool for an expected condition.

Instead, `generate()` always returns a `GenerationResult`:

```python
@dataclass(frozen=True)
class GenerationResult:
    success: bool
    case: CaseDefinition | None  # None on failure
    raw_dict: dict[str, object] | None  # the last LLM response, even if invalid
    case_path: Path | None  # set after save()
    attempts: int  # how many LLM calls were made
    errors: list[str]  # empty on success
    seed: CreativeSeed
```

Caller code becomes:

```python
result = pipeline.generate(seed)
if result.success:
    path = pipeline.save(result)
    print(f"Generated: {path}")
else:
    print(f"Failed after {result.attempts} attempts:")
    for e in result.errors:
        print(f"  - {e}")
```

No try/except. The result tells you everything you need to know.

### The invariants

`success=True` requires `case is not None`. `success=False` requires `case is None`. `attempts >= 1` always. These are enforced in `__post_init__` so they can't be violated by accident:

```python
def __post_init__(self) -> None:
    if self.success and self.case is None:
        raise ValueError("success is True but case is None")
    if not self.success and self.case is not None:
        raise ValueError("success is False but case is not None")
    if self.attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {self.attempts}")
```

### But infrastructure failures DO raise

`LLMProviderError` (bad API key, network timeout) and `LLMResponseError` (response wasn't JSON at all) propagate up unchanged. Those are not "generation failed to validate" — they're "we couldn't even attempt generation." The caller needs to handle those differently (retry after delay, alert on credentials). `GenerationResult` is only for cases where the LLM responded and we could evaluate what it said.

### The frozen dataclass and `_with_path`

`GenerationResult` is frozen — you can't mutate it after construction. This is intentional. Results are facts about what happened. Once `generate()` returns a result, that result is immutable.

But there's a problem: `save()` needs to add a `case_path` to the result after the file is written. You can't set a field on a frozen dataclass.

The solution is a helper that constructs a *new* result with all the same values plus the path:

```python
def _with_path(result: GenerationResult, path: Path) -> GenerationResult:
    return GenerationResult(
        success=result.success,
        case=result.case,
        raw_dict=result.raw_dict,
        case_path=path,           # ← the only difference
        attempts=result.attempts,
        errors=result.errors,
        seed=result.seed,
    )
```

The convenience method `generate_and_save()` does both steps and returns the final result with `case_path` set:

```python
def generate_and_save(self, seed: CreativeSeed, max_retries: int = 3) -> GenerationResult:
    result = self.generate(seed, max_retries=max_retries)
    if result.success:
        path = self.save(result)
        return _with_path(result, path)   # new object, path attached
    return result  # failure: no path, returned as-is
```

---

## The Retry Loop: Simple Then Repair

### Why not just retry forever?

Because LLM calls cost money and time. If the LLM is consistently producing invalid output for a particular seed, infinite retries just waste resources. We need a cutoff. The default is 3 simple retries — enough to ride out random failures — plus one repair attempt.

### Simple retries

The first `max_retries` calls are identical: same seed, fresh call, hoping variance produces a valid response.

```python
for attempt in range(1, max_retries + 1):
    raw = self._generator.generate_case(case_seed)
    case_def, errors = validate_case_dict(raw)

    if case_def is not None:
        return _make_success(case_def, raw, attempt, seed)

    last_errors = errors  # save for repair prompt
```

This handles the common case: the LLM got unlucky once (hallucinated an enum value, dropped a required field) but gets it right on the second or third attempt.

### The repair attempt

If all simple retries fail, we know *specifically what's wrong*. Rather than giving up, we give the LLM one more chance with a prompt that contains the invalid output and the exact list of errors:

```python
repair_prompt = build_repair_prompt(
    last_raw,    # the last invalid LLM response
    last_errors  # the validation errors from that response
)
```

The repair prompt looks like:

```
Your previous response was not a valid case definition.
Please fix ALL of the following errors and return corrected JSON:

## Validation Errors

  1. [schema] nodes -> 0 -> reveal -> action: value is not a valid string
  2. [structural] Node 'chest-xray' reveal.action 'order-xray' not found in action_costs
  (known: ['examine-patient', 'get-history', 'order-labs'])

## Your Previous (Invalid) Output

```json
{ ... the invalid JSON ... }
```

Return ONLY the corrected JSON. Do not include any explanation.
```

Giving the LLM its own output back alongside specific error messages is significantly more effective than a fresh retry, because the model can see exactly what to change rather than starting from scratch.

### Total max calls = max_retries + 1

This is deliberate. `attempts` in the result tells you exactly how many calls were made. `attempts == max_retries + 1` means all simple retries were exhausted and the repair path was reached. `attempts < max_retries + 1` means success came during simple retries.

---

## The Pipeline: Putting It All Together

### Generator injection is test-friendly by design

The pipeline creates its own `CaseGenerator` from a `ModelConfig`:

```python
class CaseGenerationPipeline:
    def __init__(self, config: ModelConfig, output_dir: Path | None = None) -> None:
        self._generator = create_case_generator(config)
```

In production you pass `ModelConfig(provider=Provider.OPENAI, model="gpt-4o")`. In tests you pass `ModelConfig(provider=Provider.MOCK, model="mock")`. The mock provider returns a hardcoded valid case — no API call, no latency, always the same output. This means all 105 unit tests run in 0.18 seconds.

Tests that need finer control (counting how many calls are made, returning different values per call) inject a custom generator directly:

```python
class _CountingGenerator(CaseGenerator):
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    def generate_case(self, seed):
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]

# In the test:
pipeline._generator = _CountingGenerator([bad_response, bad_response, valid_response])
result = pipeline.generate(seed, max_retries=3)
assert result.attempts == 3
assert result.success is True
```

This is a test-only pattern — not a public API. The underscore prefix signals that. It works because the generator is just stored on the instance; you can replace it if you need to.

### Saving: filename tells you what's inside

```python
def save(self, result: GenerationResult) -> Path:
    short_id = str(uuid.uuid4())[:8]
    safe_diagnosis = result.seed.diagnosis.lower().replace(" ", "-")
    filename = f"case-{safe_diagnosis}-{short_id}.json"
```

A saved case file named `case-neurocysticercosis-3f4a1b2c.json` tells you the diagnosis at a glance. The short UUID prevents collisions without making the filename unwieldy. Sequential numbering would be simpler but has two problems: it creates race conditions when generating in parallel, and it loses the human-readable diagnosis label.

---

## What "Boundary 1" Actually Means in Code

The boundary concept is architectural — it's a commitment that every file in `cases/generated/` can be trusted. Nothing crosses that boundary without passing validation.

In code it's simple: `save()` raises if `success=False`:

```python
def save(self, result: GenerationResult) -> Path:
    if not result.success or result.case is None:
        raise ValueError("Cannot save a failed GenerationResult (success=False)")
    # ... write to disk
```

And `generate_and_save()` only calls `save()` inside `if result.success`:

```python
def generate_and_save(self, seed, max_retries=3):
    result = self.generate(seed, max_retries=max_retries)
    if result.success:
        path = self.save(result)         # ← only reached on success
        return _with_path(result, path)
    return result                         # ← failure returned, nothing saved
```

It is physically impossible to save an invalid case using this API. You'd have to bypass all these checks and write to disk manually. That's what "enforced boundary" means — not a convention, but a code path that doesn't exist.

---

## Connecting Back to the Larger System

Anamnesis sits between two other packages:

- **llm-client** (Ho 03): defines `CaseSeed`, `CaseGenerator`, `ModelConfig`, the `Provider` enum. Anamnesis calls llm-client. It never touches the LLM directly.
- **satori** (Ho 01 / 02): defines `CaseDefinition` — the model that validated cases are instances of. Satori's engine loads `.json` files that Anamnesis has validated. Anamnesis imports from satori's models package but never touches the engine itself.

The dependency direction is one-way:

```
anamnesis → llm-client  (for calling the LLM)
anamnesis → satori.models  (for validating against CaseDefinition)

satori.engine → [loads case files from disk]
```

The engine has no idea Anamnesis exists. It just loads a JSON file and trusts it's valid. It trusts that because Anamnesis enforced Boundary 1.

---

## Summary of Design Principles Used Here

**1. Expected failures return values; unexpected failures raise exceptions.**
Validation failure is expected → `GenerationResult`. API key failure is unexpected → exception propagates.

**2. Frozen data means immutable facts.**
Results are frozen because they represent what happened, not a work-in-progress. When you need to "update" a frozen object, you construct a new one (`_with_path`).

**3. Separate the what from the how.**
`CreativeSeed` describes what the author wants. `CaseGenerationPipeline` decides how to achieve it. The seed has no methods that touch the LLM.

**4. Boundaries enforced by code, not convention.**
Saving invalid output isn't discouraged — it's impossible through the normal API.

**5. Phases in validation for a reason, not habit.**
Phase 1 (schema) must succeed before phase 2 (structural) can run. This isn't defensive coding, it's a hard prerequisite: you can't check cross-node references on an object that doesn't have nodes yet.
