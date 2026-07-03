---
created: 2026-07-03
type: agent-task
status: in-progress
parent: audit/FABLE-REVIEW-2026-07-03.md
project: satori-internal-affairs
---

# S1 — Verification-stack repair

**Goal**

Make the declared verification stack actually execute: mypy runs strict from the repo root, pre-commit gates lint/format/type/test/coverage, the working tree is format- and lint-clean, and the mechanical portion of the 25-error mypy register (23 of 25) is cleared with real fixes, not ignores. Findings C-3, C-7, and §2 of the parent report.

**Context**

`make typecheck` runs mypy from the repo root where no config exists, so the per-package `strict = true` blocks never apply (mypy resolves config from invocation cwd). No `.pre-commit-config.yaml` exists anywhere. Two of the mypy errors are latent runtime crashes (None arithmetic/comparison on authored-case values); the rest are benign annotation gaps, one variance pattern, and 7 dead suppressions. The deeper `Effect.value`/`Condition.value` typing question is a Kamae-chain decision and is **not** resolved here — the None-guards are the bounded fix.

**Files**

- Create: `mypy.ini` (repo root — strict config + llm-client's scoped `ignore_missing_imports` override for `openai`/`anthropic`)
- Create: `.pre-commit-config.yaml` (repo root)
- Modify: `packages/satori/src/satori/events.py` (bare `dict` → `dict[str, Any]`, 3 sites)
- Modify: `packages/satori/src/satori/vitals_computer.py` (split `_worst_value` into typed int/float helpers)
- Modify: `packages/satori/src/satori/effect_executor.py` (6 × `list[Event]` local annotations; None-guard in `_modify_timer`; explicit `VitalSigns` construction at :335)
- Modify: `packages/satori/src/satori/condition_evaluator.py` (None-guards before `_compare`, 2 call sites)
- Modify: `packages/satori-api/src/satori_api/serialisation.py` (delete 7 dead `type: ignore` comments)
- Modify: `packages/satori-api/src/satori_api/narrator_bridge.py` (`dict` → `dict[str, Any]` at :48, drop the now-unneeded ignore)
- Modify: `packages/llm-client/tests/test_schema_conformance.py` (fix E501 at :52)
- Modify: `packages/llm-client/pyproject.toml` (register `integration` marker)
- Modify: `packages/anamnesis/tests/test_placeholder.py` and `packages/llm-client/tests/test_placeholder.py` (rename to unique basenames, e.g. `test_anamnesis_placeholder.py` / `test_llm_client_placeholder.py`)
- Modify: ~12 files under `packages/anamnesis/` and `packages/llm-client/tests/` (mechanical `ruff format`)
- Modify: package `pyproject.toml` files as needed for coverage configuration

**Required Changes**

1. **Root `mypy.ini`.** Strict mode, `python_version = 3.11`, mirroring the per-package `[tool.mypy]` blocks, plus the `openai.*`/`anthropic.*` `ignore_missing_imports` override currently scoped to llm-client. Result: `mypy packages/<pkg>/src` from the repo root runs strict. Drop the unused `openai.*`/`anthropic.*` glob sections mypy reports as unused if they warn.
2. **Type fixes** per the register in §2 of the parent report. All are real fixes; no new `type: ignore` anywhere:
   - `events.py:64,107,108` — parameterize the bare `dict` annotations.
   - `vitals_computer.py` — replace `_worst_value`'s union return with typed helpers (or `@overload`) so int vitals provably produce `int | None`.
   - `effect_executor.py` — annotate the six event-list locals as `list[Event]`; guard `effect.value is None` in `MODIFY_TIMER` handling with a `ValueError` naming the malformed effect; construct `VitalSigns` at the `OVERRIDE_VITALS` site so the value's type is checked before Pydantic.
   - `condition_evaluator.py:112,160` — guard `condition.value is None` with a `ValueError` naming the malformed condition before calling `_compare`.
   - `serialisation.py:43,46-51` — delete the seven dead ignores.
   - `narrator_bridge.py:48` — annotate properly, remove the ignore.
   - Add tests for the two new None-guards (malformed `MODIFY_TIMER` effect, malformed threshold condition → `ValueError`).
3. **Format and lint clean.** `ruff format packages/` (the 12 drifted files); fix the E501 in `test_schema_conformance.py:52` by wrapping.
4. **Pytest hygiene.** Rename the two `test_placeholder.py` files to unique basenames so root-level `pytest packages/...` collects. Register the `integration` marker in llm-client's pyproject (`[tool.pytest.ini_options] markers`).
5. **Coverage configuration.** Add `[tool.coverage.*]` / pytest-cov settings so each package measures line coverage with `fail_under = 90` for satori, satori-api, and anamnesis. llm-client is **exempt from the gate for now** with an explanatory comment referencing the parent report §3 and P2-H08 (provider files are rewritten there; the floor applies from H08 onward).
6. **`.pre-commit-config.yaml`.** Hooks: ruff check, ruff format --check, mypy (strict, via the root config), pytest per package with the coverage gates from (5). Given no committed venv exists yet (C-4 is deferred), local/system-language hooks that call the ambient toolchain are acceptable; note the dependency on the future uv migration in a comment.

**Do Not**

- Do not change `Effect.value` / `Condition.value` schema typing — that is a Kamae-chain decision (parent report C-7). Guards only.
- Do not add or widen any `type: ignore`. The register clears with real fixes.
- Do not touch `state_checkers.py` iteration order (that is S3) or the case JSON (that is S2).
- Do not attempt the uv/lockfile migration (C-4) — deferred to its own task.

**Acceptance**

- [ ] `mypy --strict packages/satori/src packages/satori-api/src packages/anamnesis/src packages/llm-client/src` from repo root: 0 errors.
- [ ] `make typecheck` runs with the root config (no `Config File: Default` behavior) and exits 0.
- [ ] `ruff check packages/` and `ruff format --check packages/`: clean.
- [ ] `pytest packages/satori packages/satori-api packages/anamnesis packages/llm-client -q` from repo root: collects and passes (no basename collision), no unknown-marker warnings.
- [ ] Coverage gate: satori, satori-api, anamnesis each ≥ 90% and enforced; llm-client exemption documented in-file.
- [ ] `pre-commit run --all-files` passes.
- [ ] New None-guard tests pass and fail if the guards are removed.

**Verification**

```bash
mypy --strict packages/satori/src packages/satori-api/src packages/anamnesis/src packages/llm-client/src
make typecheck
ruff check packages/ && ruff format --check packages/
pytest packages/satori packages/satori-api packages/anamnesis packages/llm-client -q
pytest packages/satori/tests --cov=satori --cov-fail-under=90 -q
pre-commit run --all-files
```

**Commit**

Multiple atomic commits, conventional format, no AI attribution:

```
chore(format): apply ruff format to anamnesis + llm-client drift
fix(types): clear the strict-mypy register with real fixes — no new ignores
build(verify): root mypy config, pre-commit gate, coverage floors, pytest hygiene
```
