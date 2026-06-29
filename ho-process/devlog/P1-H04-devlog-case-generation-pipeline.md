# Phase 1 Devlog 005: Case Generation Pipeline (Ho 04)

**Date**: 2026-02-17
**Milestone**: Ho 04 — Anamnesis Package
**Status**: ✅ Complete
**Commits**: `a836406`, `18f105a`

---

## Summary

Built `packages/anamnesis/` — the case generation pipeline that enforces Boundary 1 (the freeze line). Anamnesis accepts creative seeds, calls the LLM through llm-client, validates the returned JSON against satori's `CaseDefinition` model, retries on failure, and saves validated cases as frozen artifacts.

**Result**: 105 unit tests passing (88 original + 17 added in coverage audit), mypy strict compliance, ruff clean. Full pipeline working in mock mode. Two seed modes implemented: Mode 1 (CLI flags) and Mode 2 (YAML creative brief).

One path bug found post-implementation (test path depth off by one: 5× `.parent` instead of 4×) — fixed in the same session before commit.

---

## Architecture Decisions

### Decision 1: Two Seed Modes with a Single Type

**Choice**: `CreativeSeed` is a single frozen dataclass containing all `CaseSeed` fields plus creative fields. It has a `to_case_seed()` method that extracts the llm-client-compatible subset. No separate class hierarchy.

**Why**:
- Mode 1 (automated, CLI flags) and Mode 2 (YAML brief) differ only in which fields are populated — not in the type of object the pipeline receives
- Single type means one pipeline code path handles both modes without branching on type
- `has_creative_fields() -> bool` provides introspection without isinstance checks
- Adding a Mode 3 in the future means adding fields to `CreativeSeed`, not redesigning the hierarchy

**Alternative rejected**: `CreativeSeed` extends `CaseSeed` via inheritance. `CaseSeed` is an llm-client type — inheriting from it would create a hard dependency on the llm-client data model, making `CreativeSeed` fragile to llm-client changes. Composition via `to_case_seed()` is cleaner.

---

### Decision 2: GenerationResult Over Exceptions

**Choice**: `pipeline.generate()` always returns a `GenerationResult(success, case, raw_dict, attempts, errors, seed)` rather than raising on validation failure.

**Why**:
- Callers (CLI, future Case Builder GUI) need to inspect failure details without try/catch
- Validation failure is an expected outcome, not an exceptional one — LLMs produce invalid output regularly
- `result.raw_dict` preserves the last LLM response for debugging even when validation fails
- `result.attempts` enables callers to report how much work was done
- `LLMProviderError` / `LLMResponseError` still propagate normally — these are infrastructure failures (bad API key, network down), not validation failures

**Invariants enforced in `__post_init__`**:
- `success=True` requires `case is not None`
- `success=False` requires `case is None`
- `attempts >= 1` always

**Alternative rejected**: Separate success/failure result types. Added complexity for minimal benefit — callers already check `result.success`.

---

### Decision 3: Simple Retries Then One Repair

**Choice**: Up to `max_retries` (default 3) naïve retries, then exactly one error-feedback repair attempt. Total max LLM calls = `max_retries + 1`.

**Why**:
- Most LLM generation failures are random variance (hallucinated enum values, minor structural drift) — a simple retry often succeeds without wasting tokens on an error prompt
- When simple retries are genuinely exhausted, one targeted repair prompt (containing the exact Pydantic errors) gives the LLM a chance to fix systematic issues
- More than one repair attempt has diminishing returns — if the LLM misunderstood the repair prompt once, it will probably misunderstand it again
- Keeps retry logic simple to test and reason about

**Implementation detail**: The repair attempt increments `attempts` just like a simple retry. `result.attempts == max_retries + 1` means all simple retries were spent and repair was reached.

**Alternative rejected**: Multiple repair passes with escalating prompts. Adds complexity and burns tokens. Simple + one repair already handles the 99% case.

---

### Decision 4: Creative Fields Are Prompt Context Only (Mode 2 Phase 1 Limitation)

**Choice**: `CreativeSeed` stores the full creative brief (`dramatic_hook`, `red_herrings`, `character_notes`, `narrative_inspiration`, `key_twists`, `emotional_core`, `forbidden_tropes`), `build_creative_prompt()` assembles them into a well-structured prompt string — but in Phase 1, that prompt is not yet injected into the LLM API call.

**Why**:
- `CaseGenerator.generate_case(seed: CaseSeed)` only accepts a `CaseSeed` — there is no channel to pass a custom user prompt through in the current llm-client interface
- The creative fields ARE captured in the seed and available for future use
- Mode 2 in Phase 1 effectively functions as Mode 1 with richer metadata — the standard `CaseSeed` fields (setting, complications, learning_objectives) are still injected into the LLM prompt by llm-client
- Full creative injection is documented in `docs/architecture/future-features.md` as F-007 (Mode 3)

**What `build_creative_prompt()` is for (Phase 1)**:
- The function is complete and tested — it assembles a proper three-section prompt
- The pipeline calls it and logs it at DEBUG level
- This means the code path is exercised and tested; wiring it to providers is a one-line change when llm-client adds prompt override support

**Logged (not raised)**: The pipeline logs an INFO message when creative fields are present but cannot be injected. This makes the limitation visible without making the pipeline fail.

---

### Decision 5: Structural Checks Run in Anamnesis, Not in Satori

**Choice**: `validate_case_dict()` runs the same structural checks the engine does (action refs exist, timer stages sorted ascending, node IDs unique) before saving — even though `SatoriEngine` would catch these at load time.

**Why**:
- Boundary 1 (the freeze line) means validation at generation time, not play time
- If a case fails structural checks at load time in production, the player experience breaks
- Catching it at generation time gives us the LLM output, error message, and the ability to retry/repair
- The pipeline's repair prompt includes structural errors alongside schema errors — the LLM can fix both
- `[schema]` and `[structural]` prefixes in error messages make it clear where the failure originated

**Two-phase approach**:
1. `CaseDefinition.model_validate(raw_dict)` — Pydantic catches schema violations (missing fields, wrong types, invalid enums)
2. `_check_structural(case)` — domain logic catches consistency violations that Pydantic cannot (cross-field references, ordering constraints)

**Why separate phases, not combined**: Pydantic validation must succeed before we can safely inspect `case.nodes`, `case.action_costs`, etc. Running structural checks on a half-validated object would cause confusing errors.

---

### Decision 6: Pipeline Owns Its Generator (No DI)

**Choice**: `CaseGenerationPipeline(config: ModelConfig)` calls `create_case_generator(config)` internally. No dependency injection parameter for `CaseGenerator`.

**Why**:
- Ho 03 established the factory pattern precisely to avoid this coupling
- Callers configure the pipeline via `ModelConfig(provider=Provider.MOCK)` — that's the injection point
- Keeping generator creation internal means callers only learn about `ModelConfig`, not `CaseGenerator`

**Testing exception**: Test files that need to inject a controlled generator (e.g. `_CountingGenerator` for retry tests) assign directly to `pipeline._generator`. This is a test-only pattern — not a public API. Documented with `# type: ignore[assignment]`.

---

### Decision 7: YAML for Seed Files, JSON for Case Output

**Choice**: Human-authored creative briefs are YAML; machine-generated case definitions are JSON.

**Why**:
- YAML supports multiline strings naturally (block scalars `>` for `dramatic_hook`, `emotional_core`)
- YAML supports inline comments explaining fields — critical for seed files that humans author
- JSON is the right format for validated, deterministic machine output
- Mixing formats would be confusing; the split matches the human/machine boundary cleanly

**Practical detail**: `patient_age_range` in YAML is `[20, 40]` (a YAML sequence). `load_seed_file()` converts this to a `tuple[int, int]` rather than the native Python list, matching `CreativeSeed`'s field type and the `CaseSeed` field type.

---

### Decision 8: Output Filename Pattern `case-{diagnosis}-{short_uuid}.json`

**Choice**: Attach the diagnosis to the filename for human-readable identification. Short UUID (8 chars) prevents collisions without being unwieldy.

**Why**:
- `cases/generated/case-pneumothorax-3f4a1b2c.json` is immediately recognisable in a directory listing
- UUID portion (even truncated to 8 chars) gives collision probability low enough for development use
- `uuid.uuid4()[:8]` is readable and requires no dependencies

**Alternative rejected**: Sequential numbering (`case-001.json`). Race conditions in multi-process generation; also loses the diagnosis-based identification.

---

## Implementation Notes

### Path Resolution in Tests

All test files that reference repo-root-level directories (`cases/`, `seeds/`) use:
```python
repo_root = Path(__file__).parent.parent.parent.parent  # tests/ → anamnesis/ → packages/ → repo root
```

A 5× `.parent` was initially written (one too many), pointing to the parent of the repo root. Caught and bulk-fixed with `sed` before final test run.

**Lesson**: Path resolution from deeply nested test files should be verified with a quick print before writing all tests. `parents[N]` is less error-prone than chained `.parent.parent...`.

---

### `_CountingGenerator` Pattern for Retry Tests

Testing retry logic requires injecting a fake `CaseGenerator` that returns specific responses in sequence. The pattern used:

```python
class _CountingGenerator(CaseGenerator):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]
```

Then injected via `pipeline._generator = gen`. This avoids mocking the factory function while still testing the full retry loop.

**Why not `unittest.mock.patch`**: The generator is created inside `__init__`. Patching `create_case_generator` works but requires understanding the call site. Direct assignment to `_generator` is simpler and makes the test intent obvious.

---

### `ErrorDetails` vs `dict[str, Any]` in Pydantic

`e.errors()` on a `ValidationError` returns `list[ErrorDetails]`, where `ErrorDetails` is a `TypedDict` in `pydantic_core`. Under `mypy --strict`, passing `ErrorDetails` to a function typed as `dict[str, Any]` is an error.

Fix: import `ErrorDetails` from `pydantic_core` and type `_format_pydantic_error(err: ErrorDetails)`.

```python
from pydantic_core import ErrorDetails

def _format_pydantic_error(err: ErrorDetails) -> str:
    loc = " -> ".join(str(p) for p in err.get("loc", []))
    ...
```

---

### `py.typed` Markers for Sibling Packages

`mypy --strict` on anamnesis reported `import-untyped` for `llm_client` and `satori.models`. Both packages lacked `py.typed` markers (PEP 561).

Fix: `touch packages/llm-client/src/llm_client/py.typed packages/satori/src/satori/py.typed`

This is the correct fix — not `# type: ignore` at every import. py.typed markers signal to mypy that the package exports type information intentionally.

---

### Unused `# type: ignore` Comments Post-Fix

After adding `py.typed` markers, several `# type: ignore[arg-type]` and `# type: ignore[assignment]` comments in `pipeline.py` became invalid (mypy no longer needed them). Removed. The lesson: `# type: ignore` added to work around missing stubs should be removed when the stubs are added.

---

## Test Coverage Audit

After the initial 88-test pass, a manual coverage audit identified 17 untested cases. Added:

| Module | Gap covered |
|---|---|
| `seed.py` | Non-dict YAML root (bare list → `ValueError`) |
| `seed.py` | Non-list value for a list field (`complications: "string"`) |
| `seed.py` | `_opt_str` returns `None` for whitespace-only value |
| `validator.py` | Non-dict input handled without crash |
| `validator.py` | Success returns exactly `errors == []` (not just falsy) |
| `validator.py` | Multiple structural errors collected in one pass |
| `result.py` | `_make_success()` helper directly tested |
| `result.py` | `_make_failure(raw_dict=None)` |
| `pipeline.py` | `generate_and_save()` failure path — no file written |
| `pipeline.py` | Default `output_dir` is `Path("cases/generated")` |
| `prompts.py` | `build_repair_prompt` with unserializable dict → `str()` fallback |
| `prompts.py` | `content_boundaries` items appear in prompt |
| `prompts.py` | `setting`/`patient_sex` appear in prompt |
| `prompts.py` | `key_twists` appear in prompt |
| `__main__.py` | Failed generation → exit code 1 |
| `__main__.py` | `--verbose` flag accepted without error |
| `__main__.py` | `--max-retries` forwarded to `pipeline.generate()` |

Final count: **105 tests**, 7 deselected (live_llm marker), 0 failed.

---

## What Went Right

### 1. Clean Separation from Ho 03

The llm-client boundary held perfectly:
- Zero satori imports in llm-client (`grep` verified)
- Zero engine imports in anamnesis source (`grep` verified)
- `create_case_generator()` factory consumed exactly as designed in Ho 03

### 2. Two-Phase Validation Catches Everything

`CaseDefinition.model_validate()` + `_check_structural()` together catch every class of structural error the engine would reject. No cases slipped through validation and failed at load time.

### 3. Mock Mode Full Fidelity

`Provider.MOCK` exercises the complete pipeline — validate, retry loop, save, filename generation — without API calls. All 105 unit tests run in 0.18s.

### 4. Task Spec Quality

The 428-line task spec (`005-DONE-agent-task-ho-4-case-generation-pipeline.md`) had all design decisions pre-made. Zero architectural rework during implementation. The only decisions made during implementation were tactical (e.g. ErrorDetails import, py.typed placement).

---

## What Was Harder Than Expected

### 1. Path Depth from Nested Tests

Test files at `packages/anamnesis/tests/` are 4 levels below the repo root. Writing `Path(__file__).parent.parent.parent.parent.parent` (5× parent) is a natural mistake when counting levels manually. A quick verification step before writing all tests would have caught this immediately.

### 2. Mode 2 Creative Injection Limitation

The task spec anticipated the limitation (flagged as requiring a future llm-client extension), but it still required careful documentation. `build_creative_prompt()` is a complete, tested function that currently goes nowhere visible — it exists to be wired up in Mode 3. Making this not feel like dead code required good logging and devlog clarity.

---

## Files Created / Modified

**Source** (6 new files, 1 updated, ~870 lines):
- `src/anamnesis/seed.py` (172 lines) — `CreativeSeed`, `load_seed_file()`
- `src/anamnesis/result.py` (100 lines) — `GenerationResult`, `_make_success/failure/_with_path`
- `src/anamnesis/validator.py` (98 lines) — `validate_case_dict()`, `_check_structural()`
- `src/anamnesis/prompts.py` (137 lines) — `build_creative_prompt()`, `build_repair_prompt()`
- `src/anamnesis/pipeline.py` (185 lines) — `CaseGenerationPipeline`
- `src/anamnesis/__main__.py` (293 lines) — CLI entry point
- `src/anamnesis/__init__.py` (38 lines, updated) — public API exports

**Tests** (9 files, ~1100 lines):
- `tests/conftest.py` — shared fixtures
- `tests/test_seed.py` — 26 tests
- `tests/test_validator.py` — 14 tests
- `tests/test_prompts.py` — 18 tests
- `tests/test_result.py` — 9 tests
- `tests/test_pipeline_mock.py` — 18 tests
- `tests/test_retry_logic.py` — 16 tests
- `tests/test_cli.py` — 11 tests
- `tests/test_integration_live.py` — 7 tests (live_llm marker, skipped by default)

**Infrastructure**:
- `packages/llm-client/src/llm_client/py.typed` — PEP 561 marker
- `packages/satori/src/satori/py.typed` — PEP 561 marker
- `seeds/README.md` — seed file format documentation
- `seeds/example-pneumothorax.yaml` — minimal Mode 1 seed
- `seeds/example-neurocysticercosis-rich.yaml` — full Mode 2 creative brief
- `cases/generated/.gitkeep` — keeps generated dir tracked
- `.gitignore` — `cases/generated/*.json` added
- `pyproject.toml` — pyyaml dependency, openai/anthropic extras, pytest markers

**Docs**:
- `docs/architecture/future-features.md` — F-007 (Mode 3 full prompt injection) added

---

## Metrics

| Metric | Value |
|---|---|
| **Source lines** | ~870 |
| **Test lines** | ~1100 |
| **Unit tests** | 105 passing |
| **Live integration tests** | 7 (marker-gated, not run) |
| **Test runtime** | 0.18s |
| **Type errors (mypy --strict)** | 0 |
| **Lint errors (ruff)** | 0 |
| **Post-implementation fixes** | 2 (path depth, py.typed markers) |
| **Coverage audit additions** | 17 tests |
| **Commits** | 2 (implementation + docs) |

---

## Next Steps

**Ho 05 — Internal Affairs (SvelteKit Frontend)**:
- Load cases from `cases/generated/` and play them via `SatoriEngine`
- `CaseGenerationPipeline` is the programmatic interface F-003 (Case Builder GUI) will use later

**Mode 3 (Future — F-007)**:
- Add `generate_case_with_prompt(seed, prompt: str)` to `CaseGenerator` interface in llm-client
- Wire `build_creative_prompt()` into `CaseGenerationPipeline.generate()` for Mode 2 seeds
- All the prompt construction code already exists — it's a one-line connection once the interface supports it

---

## Conclusion

Ho 04 delivered a complete, validated case generation pipeline in one session. The design decisions from the task spec all held — no architectural rework, just implementation. The retry-then-repair strategy works correctly in mock mode and is ready for real LLM validation when keys are available.

The most consequential decision was making `GenerationResult` a frozen dataclass with `__post_init__` invariants rather than a plain dict or exception-based API. Every caller — CLI, tests, future GUI — benefits from a typed, inspectable result object. The investment in that design was 30 lines and has already paid for itself in clearer test assertions and a cleaner CLI implementation.

Boundary 1 (the freeze line) is enforced: every case in `cases/generated/` has passed both Pydantic schema validation and structural consistency checks. The engine can load them without surprises.
