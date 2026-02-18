# TASK: ANAMNESIS — CASE GENERATION PIPELINE

## GOAL

Build the `packages/anamnesis/` package — the case generation pipeline that enforces Boundary 1 (the freeze line). Anamnesis accepts creative seeds, calls an LLM through llm-client, validates the returned JSON against satori's `CaseDefinition` model, retries on failure, and saves validated cases as frozen artifacts.

Two seed modes:

| Mode | Input | Use Case |
|---|---|---|
| **Mode 1: Automated** | CLI flags (`--diagnosis`, `--difficulty`, `--tone`) | Quick generation, testing |
| **Mode 2: Creative seed** | YAML file with rich narrative direction | Hand-crafted creative briefs, House-style cases |

When this task is complete:
- A `CaseSeed` or `CreativeSeed` → pipeline → validated, playable case JSON on disk
- Mock mode runs the full pipeline without API keys
- Real LLM mode generates a case that passes `CaseDefinition` validation and loads in `SatoriEngine`
- Creative seed files support dramatic hooks, red herrings, character notes, narrative inspiration, key twists, emotional core, and forbidden tropes
- CLI works for both modes

## CONTEXT

This is Ho 04 / Milestone 4 of the Phase 1 gameplan.

**Upstream:**
- **Ho 01 (case schema):** JSON schema at `schemas/case-definition.schema.json` (743 lines). Pydantic models in `satori.models.case_definition`. `CaseDefinition.model_validate()` is the validation gate. `extra="ignore"` silently drops unknown fields.
- **Ho 02 (Satori engine):** `SatoriEngine(case: CaseDefinition)` loads and plays a case. Does its own structural validation at load time (action refs, timer sorting).
- **Ho 03 (llm-client):** `create_case_generator(config) -> CaseGenerator`. `generate_case(seed: CaseSeed) -> dict[str, Any]`. Returns raw parsed JSON — validation is Anamnesis's job. `MockCaseGenerator` loads from `cases/example-neurocysticercosis.json`. Schema is already included in LLM provider prompts.

**Downstream consumers:**
- **Internal Affairs (Ho 05):** Will load generated cases from `cases/generated/` and pass them to `SatoriEngine`.
- **Future F-003 (Case Builder GUI):** Will call `CaseGenerationPipeline.generate()` programmatically. Must expose a clean API, not just a CLI script.

**Boundary 1 (the freeze line):** Anamnesis produces a case definition. That definition crosses the boundary as a validated, schema-conformant artifact. Once it crosses, it's frozen. Satori never asks Anamnesis for more information during play.

**Critical constraint:** Anamnesis depends on both `llm-client` (for generation) and `satori` (for `CaseDefinition` validation). The dependency on satori is **model-layer only** — never import the engine, game state, or events.

---

## DO NOT CHANGE

- `schemas/` — the case definition schema (frozen from Ho 01)
- `packages/satori/` — the engine package (frozen from Ho 02/03)
- `packages/llm-client/` — the LLM abstraction layer (frozen from Ho 03)
- `packages/internal-affairs/` — SvelteKit scaffold
- Root project files (`README.md`, `Makefile`, etc.) — except `.gitignore` for `cases/generated/`

---

## DESIGN DECISIONS (MADE)

These are binding. Do not revisit.

### Decision 1: Two Seed Modes

**Mode 1 (Automated):** Minimal CLI flags produce a `CaseSeed` directly. The LLM invents all creative content from its training data.

**Mode 2 (Creative seed file):** YAML files with rich narrative direction fields. These are creative briefs for the LLM — dramatic hooks, character notes, red herrings, narrative inspiration. Creative fields are **prompt context only** — they guide generation but never appear in the output case JSON.

Mode 3 (condition database with pre-built medical reference profiles) is deferred to a future phase.

### Decision 2: CreativeSeed Extends CaseSeed Conceptually

`CreativeSeed` is a separate frozen dataclass that contains all `CaseSeed` fields plus creative fields. It has a `to_case_seed()` method that extracts the llm-client-compatible subset. Creative fields are converted to prompt text, not passed through the `CaseGenerator` interface.

### Decision 3: Retry Strategy — Simple Then Repair

1. Up to `max_retries` (default 3) simple retries — just call the LLM again
2. If simple retries exhausted: **one** error-feedback attempt — build a repair prompt containing the Pydantic validation errors, call the LLM again
3. If all attempts fail: return `GenerationResult` with `success=False` and error details

Simple retries handle random LLM variance. Error-feedback handles systematic structural errors. This avoids wasting tokens on repair prompts when a simple retry would work.

### Decision 4: Pipeline Owns Config

`CaseGenerationPipeline(config: ModelConfig)` calls `create_case_generator(config)` internally. Tests use `Provider.MOCK` in the config. No dependency injection of generators — the factory pattern from Ho 03 handles this.

### Decision 5: GenerationResult Over Exceptions

The pipeline returns a `GenerationResult` object (success/failure, case, attempts, errors) instead of raising on validation failure. Callers inspect the result without try/catch. `LLMProviderError` and `LLMResponseError` from llm-client still propagate for truly unexpected failures (network down, bad API key).

### Decision 6: Structural Validation Before Save

Anamnesis runs the same structural checks the engine does (action refs exist, timer stages sorted, node IDs unique) **before** saving. Invalid cases are caught at generation time, not when someone tries to play them.

### Decision 7: Storage — Configurable With Default

Output defaults to `cases/generated/`. CLI has `--output-dir` flag. Generated cases are `.gitignore`d — they're artifacts, not source.

### Decision 8: YAML Seed Files

Creative seed files use YAML format — human-friendly for multiline narrative content, supports comments. JSON is for machine output (case definitions), YAML is for human input (creative briefs).

---

## REQUIRED COMPONENTS

All source files go in `packages/anamnesis/src/anamnesis/`. All test files go in `packages/anamnesis/tests/`. Seed files go in `seeds/` at the repo root.

### seed.py

Creative seed model and YAML loader.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_client import CaseSeed


@dataclass(frozen=True)
class CreativeSeed:
    """Extended seed with narrative direction fields.

    Contains all CaseSeed fields plus creative fields that guide
    the LLM's narrative output. Creative fields are prompt context
    only — they never appear in the output case JSON.
    """
    # === CaseSeed fields (required) ===
    diagnosis: str
    difficulty: str
    dramatic_tone: str

    # === CaseSeed fields (optional) ===
    patient_age_range: tuple[int, int] | None = None
    patient_sex: str | None = None
    setting: str | None = None
    complications: list[str] | None = None
    learning_objectives: list[str] | None = None
    content_boundaries: list[str] | None = None

    # === Creative fields (Mode 2 — all optional) ===
    dramatic_hook: str | None = None        # Opening scene / first impression
    red_herrings: list[str] | None = None   # Misleading clues to embed
    character_notes: str | None = None      # Personality, backstory, relationships
    narrative_inspiration: str | None = None # Free text reference ("House S2E13")
    key_twists: list[str] | None = None     # Dramatic turns in the case
    emotional_core: str | None = None       # The human story beyond the medicine
    forbidden_tropes: list[str] | None = None # Things to avoid in generation

    def to_case_seed(self) -> CaseSeed:
        """Extract the llm-client CaseSeed subset."""
        ...
```

`load_seed_file(path: Path) -> CreativeSeed` — loads YAML, validates required fields (`diagnosis`, `difficulty`, `dramatic_tone`), returns `CreativeSeed`. Raise `ValueError` on missing required fields or unreadable file.

### prompts.py

Prompt construction for creative enrichment and repair.

```python
def build_creative_prompt(seed: CreativeSeed) -> str:
    """Build enriched user prompt from all seed fields.

    Structure:
    1. Medical requirements (diagnosis, difficulty, setting, etc.)
    2. Creative direction (dramatic hook, character notes, etc.)
    3. Structural constraints (unique node IDs, sorted stages, etc.)

    Returns prompt text to append/replace the default user prompt.
    """
    ...


def build_repair_prompt(raw_dict: dict, validation_errors: list[str]) -> str:
    """Build error-feedback prompt for repair attempt.

    Includes the previous (invalid) output and the specific validation
    errors so the LLM can fix them targeted.
    """
    ...
```

**Important:** The creative prompt is injected into the user prompt sent to the LLM. The llm-client `CaseGenerator.generate_case(seed)` constructs its own system prompt (with schema) and user prompt (from `CaseSeed` fields). Anamnesis needs a way to pass creative context through.

**Implementation approach:** The pipeline calls `generator.generate_case(case_seed)` which uses llm-client's built-in prompt construction (system prompt with schema + user prompt from CaseSeed fields). For Mode 2 creative enrichment with real providers, the pipeline should set appropriate CaseSeed optional fields where they map (e.g., `complications`, `learning_objectives`, `content_boundaries`). For fields that don't map to CaseSeed (dramatic_hook, etc.), log them for now — full creative prompt injection requires a minor llm-client extension in a future iteration.

**For Phase 1:** The mock provider ignores prompts entirely (returns hardcoded case). Real providers get CaseSeed fields in their prompts. Creative fields that don't map to CaseSeed are noted in the generation result but don't block the pipeline.

### validator.py

Validation wrapper that catches Pydantic errors and runs structural checks.

```python
from satori.models import CaseDefinition


def validate_case_dict(raw_dict: dict) -> tuple[CaseDefinition | None, list[str]]:
    """Validate a raw dict against CaseDefinition.

    Runs:
    1. CaseDefinition.model_validate(raw_dict) — Pydantic validation
    2. Structural checks:
       - All reveal rule action refs exist in action_costs
       - Timer stages sorted by at_minutes ascending
       - Node IDs unique
       - All nodes have at least id, type, content, activation

    Returns:
        (case_definition, []) on success
        (None, [error_messages]) on failure
    """
    ...
```

### result.py

Generation result type.

```python
@dataclass(frozen=True)
class GenerationResult:
    """Result of a case generation attempt."""
    success: bool
    case: CaseDefinition | None  # None if failed
    raw_dict: dict | None        # Raw LLM output (even if invalid)
    case_path: Path | None       # Where the case was saved (None if not saved)
    attempts: int                 # Total attempts made
    errors: list[str]            # Validation errors from last failed attempt
    seed: CreativeSeed           # The seed that was used
```

### pipeline.py

The core pipeline class.

```python
class CaseGenerationPipeline:
    """Orchestrates seed → LLM → validate → save.

    Usage:
        config = ModelConfig(provider=Provider.MOCK, model="mock")
        pipeline = CaseGenerationPipeline(config)
        result = pipeline.generate(seed)
        if result.success:
            path = pipeline.save(result)
    """

    def __init__(self, config: ModelConfig, output_dir: Path | None = None):
        """Initialize pipeline.

        Args:
            config: LLM provider configuration
            output_dir: Where to save cases. Defaults to cases/generated/.
        """
        ...

    def generate(self, seed: CreativeSeed, max_retries: int = 3) -> GenerationResult:
        """Generate a validated case from a seed.

        Steps:
        1. Extract CaseSeed from CreativeSeed
        2. Call generator.generate_case(case_seed) → dict
        3. Validate with validate_case_dict()
        4. On failure: simple retry (up to max_retries)
        5. If retries exhausted: one error-feedback attempt
        6. Return GenerationResult
        """
        ...

    def save(self, result: GenerationResult) -> Path:
        """Save a successful generation result to disk.

        Filename: case-{diagnosis}-{short_uuid}.json
        Raises ValueError if result.success is False.
        """
        ...
```

### __main__.py

CLI entry point using `argparse`.

```
Usage:
  python -m anamnesis generate --diagnosis pneumothorax --difficulty beginner --tone clinical
  python -m anamnesis generate --seed-file seeds/example-pneumothorax.yaml
  python -m anamnesis generate --seed-file seeds/rich-case.yaml --provider openai --model gpt-4

Options:
  --diagnosis        Diagnosis name (Mode 1, required without --seed-file)
  --difficulty       Difficulty level (Mode 1, default: intermediate)
  --tone             Dramatic tone (Mode 1, default: medical_mystery)
  --seed-file        Path to YAML seed file (Mode 2)
  --provider         mock | openai | anthropic (default: mock)
  --model            Model name (default: provider-specific)
  --api-key          API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)
  --schema-path      Path to JSON schema (required for non-mock providers)
  --output-dir       Output directory (default: cases/generated/)
  --max-retries      Max retry attempts (default: 3)
  --no-save          Generate but don't save to disk
```

Print result summary: success/failure, path to saved case, attempt count, validation errors if any.

### __init__.py

Export the public API:

```python
from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.result import GenerationResult
from anamnesis.seed import CreativeSeed, load_seed_file
from anamnesis.validator import validate_case_dict

# Convenience re-exports from llm-client
from llm_client import CaseSeed, ModelConfig, Provider
```

### pyproject.toml updates

```toml
[project]
name = "anamnesis"
version = "0.1.0"
description = "LLM-powered medical case generation pipeline"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
]
openai = [
    "openai>=1.0.0",
]
anthropic = [
    "anthropic>=0.20.0",
]
all = [
    "openai>=1.0.0",
    "anthropic>=0.20.0",
]
```

Note: `llm-client` and `satori` are sibling packages in the monorepo. Install them as editable path dependencies during development (`pip install -e ../llm-client -e ../satori`). Do NOT list them in `pyproject.toml` dependencies — they're development dependencies managed by the workspace, not published package dependencies.

### Seed files

Create `seeds/` directory at repo root.

**`seeds/README.md`** — explains seed file format, all available fields, Mode 1 vs Mode 2.

**`seeds/example-pneumothorax.yaml`** — minimal Mode 1 seed:
```yaml
# Minimal seed — LLM invents all creative content
diagnosis: pneumothorax
difficulty: beginner
dramatic_tone: clinical
setting: Emergency Department
```

**`seeds/example-neurocysticercosis-rich.yaml`** — Mode 2 creative seed based on the existing example case:
```yaml
# Rich creative seed with narrative direction
diagnosis: neurocysticercosis
difficulty: intermediate
dramatic_tone: medical_mystery

patient_age_range: [25, 35]
patient_sex: female
setting: Emergency Department

complications:
  - language barrier (husband translates)
  - dietary history hidden due to cultural sensitivity

learning_objectives:
  - Recognize seizure with focal features as requiring neuroimaging
  - Consider parasitic causes in appropriate epidemiological context
  - Understand why steroids alone worsen neurocysticercosis

dramatic_hook: >
  Young woman brought in by her frantic husband after collapsing
  mid-sentence at a family dinner. She was speaking normally one
  moment, then her words became garbled before she seized.

red_herrings:
  - Recent stress from starting a new job
  - Family history of epilepsy (uncle)
  - Mild anemia on CBC (incidental)

character_notes: >
  Maria is proud and independent. Her husband Carlos is protective
  and anxious — he translates but sometimes filters what Maria says,
  trying to minimize her symptoms. Maria's mother is calling the
  hospital repeatedly (background tension).

narrative_inspiration: >
  House S1E09 (DNR) — the patient whose family dynamics
  complicate the diagnostic process. The medical mystery is
  intertwined with the family story.

key_twists:
  - Steroids (obvious treatment for brain lesion) actually make it worse
  - The husband holds the critical dietary clue but won't volunteer it
  - CT shows a lesion that looks like a tumor initially

emotional_core: >
  A young couple navigating a terrifying medical crisis in a
  language and culture that isn't fully their own. The fear of
  the unknown diagnosis is amplified by being far from family
  support systems.

forbidden_tropes:
  - No immigration status as a plot point
  - No stereotyping based on ethnicity
  - No blaming the patient for dietary choices

content_boundaries:
  - Age-appropriate for 14+ audience
  - No graphic descriptions of seizure
```

### Filesystem changes

- Create `cases/generated/.gitkeep`
- Add `cases/generated/*.json` to root `.gitignore`

---

## IMPLEMENTATION GUIDANCE

- **Prompt flow for mock:** `MockCaseGenerator` ignores the prompt entirely and returns the hardcoded example case. Creative fields have no effect in mock mode. This is fine — mock mode tests the pipeline mechanics (validate, retry, save), not prompt quality.
- **Prompt flow for real providers:** `CaseSeed` fields are passed through `generate_case()` and become part of the user prompt (this already works from Ho 03). Creative-only fields (dramatic_hook, etc.) don't have a path into the LLM prompt in Phase 1 — they're stored in the `GenerationResult` for future use. This is acceptable because Mode 2's creative enrichment will be fully wired when we add a prompt injection point to llm-client in a future iteration.
- **Validation is strict:** If `CaseDefinition.model_validate()` fails, the case is invalid. Period. No partial results, no "close enough." The freeze line means every case that crosses it must be fully valid.
- **satori imports:** Only import from `satori.models` (specifically `CaseDefinition`, `validate_case`). Never import `SatoriEngine`, `GameState`, `Event`, or any engine module — except in integration tests where we prove the generated case is playable.
- **Output JSON:** When saving, use `CaseDefinition.model_dump(mode="json")` for clean serialization (handles UUID, enums, etc.). Write with `json.dump(indent=2)` for readability.
- **UUID generation:** Use `uuid.uuid4()` if the LLM doesn't provide a valid UUID for the case `id` field.
- **API key loading:** CLI reads from `--api-key` flag or falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` environment variables. The pipeline itself doesn't read env vars — that's the CLI's job.

---

## INVARIANTS TO PRESERVE

1. **satori model imports only:** Anamnesis imports from `satori.models` for validation. Never from `satori.engine`, `satori.game_state`, `satori.events`, etc. (except integration tests)
2. **llm-client interface respected:** Always call through `CaseGenerator.generate_case(seed: CaseSeed)`. Never construct provider-specific classes directly.
3. **Freeze line enforced:** Every saved case passes `CaseDefinition.model_validate()`. No exceptions.
4. **No schema modification:** The JSON schema and Pydantic models are frozen from Ho 01/02.
5. **No llm-client modification:** The LLM abstraction layer is frozen from Ho 03.
6. **Mock purity:** Mock mode makes zero network calls, requires zero API keys, and exercises the full pipeline.
7. **Creative fields are prompt-only:** They never appear in output case JSON. They never modify the schema.
8. **Seed format stability:** `CreativeSeed` fields must be documented and stable — F-003 (Case Builder GUI) will depend on this format.

---

## ACCEPTANCE CHECKS (MANDATORY)

### Seed & Config
1. `CreativeSeed` constructs with required fields only (diagnosis, difficulty, dramatic_tone)
2. `CreativeSeed` constructs with all fields populated
3. `CreativeSeed.to_case_seed()` returns a valid `CaseSeed` with correct field mapping
4. `load_seed_file()` loads a YAML file and returns a `CreativeSeed`
5. `load_seed_file()` raises `ValueError` on missing required fields
6. `load_seed_file()` handles all creative fields correctly

### Validation
7. `validate_case_dict()` returns `(CaseDefinition, [])` for the example neurocysticercosis case dict
8. `validate_case_dict()` returns `(None, [errors])` for an empty dict
9. `validate_case_dict()` returns `(None, [errors])` for a dict with invalid action refs
10. `validate_case_dict()` returns `(None, [errors])` for a dict with unsorted timer stages

### Pipeline — Mock Mode
11. `CaseGenerationPipeline(mock_config).generate(seed)` returns `GenerationResult` with `success=True`
12. `result.case` is a valid `CaseDefinition` instance
13. `result.attempts == 1` (mock produces valid output on first try)
14. `pipeline.save(result)` writes a JSON file to the output directory
15. The saved JSON file can be loaded by `CaseDefinition.model_validate(json.load(f))`

### Pipeline — Retry Logic
16. Pipeline retries when generator returns invalid dict (mock generator that returns bad data)
17. Pipeline attempts error-feedback repair after simple retries are exhausted
18. Pipeline returns `success=False` with error details when all attempts fail
19. `result.attempts` reflects the actual number of calls made

### CLI
20. `python -m anamnesis generate --diagnosis X --difficulty Y --tone Z --provider mock` succeeds
21. `python -m anamnesis generate --seed-file seeds/example-pneumothorax.yaml --provider mock` succeeds
22. CLI prints result summary (success/failure, path, attempts)
23. `--no-save` flag generates but doesn't write to disk

### Integration (marked, skipped by default)
24. With `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set: pipeline generates a case that passes `CaseDefinition` validation
25. The generated case loads in `SatoriEngine(result.case)` without `CaseValidationError`
26. The generated case has `len(nodes) >= 3` (not trivially empty)

### Type Safety & Quality
27. `mypy --strict` passes on all anamnesis source files
28. `ruff` passes on all anamnesis source and test files
29. `grep -r "from satori.engine" packages/anamnesis/src/` returns zero matches
30. `grep -r "from satori.game_state" packages/anamnesis/src/` returns zero matches

### Filesystem
31. `seeds/example-pneumothorax.yaml` exists and is loadable
32. `seeds/example-neurocysticercosis-rich.yaml` exists and is loadable
33. `cases/generated/.gitkeep` exists
34. `cases/generated/*.json` is in `.gitignore`

---

## LINE COUNT EXPECTATION

| File | Est. Lines |
|---|---|
| `seed.py` | ~100 |
| `prompts.py` | ~80 |
| `validator.py` | ~70 |
| `result.py` | ~30 |
| `pipeline.py` | ~120 |
| `__main__.py` | ~100 |
| `__init__.py` | ~20 |
| **Source total** | **~520** |
| `tests/test_seed.py` | ~80 |
| `tests/test_validator.py` | ~70 |
| `tests/test_prompts.py` | ~50 |
| `tests/test_result.py` | ~30 |
| `tests/test_pipeline_mock.py` | ~80 |
| `tests/test_retry_logic.py` | ~80 |
| `tests/test_cli.py` | ~60 |
| `tests/test_integration_live.py` | ~50 |
| `tests/conftest.py` | ~20 |
| **Test total** | **~520** |
| `seeds/example-pneumothorax.yaml` | ~5 |
| `seeds/example-neurocysticercosis-rich.yaml` | ~60 |
| `seeds/README.md` | ~40 |
| **Seed files total** | **~105** |

---

## QUALITY

- All code type-checked with `mypy --strict`
- All code linted with `ruff` (line-length 100, selects `E,F,I,N,W,UP`)
- Docstrings on all classes and public methods
- All tests have real assertions — no `assert True` placeholders
- No `# type: ignore` without justification comment
- Integration tests skipped by default (marker-gated)
- Seed YAML files include comments explaining each field

---

## COMMIT

```
feat(anamnesis): case generation pipeline with creative seed support

- CaseGenerationPipeline: seed → LLM → validate → save
- CreativeSeed with narrative direction fields (Mode 2)
- YAML seed file support with dramatic hooks, character notes, red herrings
- Retry-then-repair validation loop (simple retries + error feedback)
- validate_case_dict() with structural checks (action refs, timer sorting)
- GenerationResult return type for inspection without exceptions
- CLI: python -m anamnesis generate (Mode 1 flags + Mode 2 seed files)
- Example seed files for pneumothorax (minimal) and neurocysticercosis (rich)
- Integration test: real LLM → valid case → playable by SatoriEngine
- Saves validated cases to cases/generated/

Boundary 1 (freeze line) enforced: every saved case passes CaseDefinition validation
```
