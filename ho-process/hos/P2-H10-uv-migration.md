# P2-H10: uv Migration — Reproducible Environment

**Status:** IN PROGRESS
**Phase:** 2 (infrastructure; audit C-4)
**Ho:** 10
**Depends on:** none (scheduled after H03/H05/H09 feature work to avoid conflicts during active development)

---

## Objective

A fresh checkout runs the full verification stack from one committed lockfile. The four Python packages become a uv workspace with a single `uv.lock`; the frontend's `package-lock.json` is un-ignored and committed; Makefile and pre-commit hooks run through the pinned environment instead of whatever toolchain is ambient.

---

## Context

Audit C-4 (HIGH): no venv, no Python lockfile, JS lockfiles actively gitignored — `make setup` installs into ambient `pip` while claiming to create venvs. This violates the operating discipline's pinned-dependencies rule directly. The pre-commit config has carried a "until the uv migration (audit C-4)" note since S1. Deferred from the audit as "a half-day of its own; schedule as the next infrastructure ho" — this is that ho.

---

## Design Decisions

### Workspace, not per-package environments

One repo, four interdependent packages (`satori-api` → `satori` + `llm-client`; `anamnesis` → `llm-client`), one test invocation from the root. A uv **workspace** with a virtual root (`pyproject.toml` carrying only `[tool.uv.workspace]`) gives a single `.venv` and a single `uv.lock`, with all members installed editable and cross-package dependencies resolved via `[tool.uv.sources] … = { workspace = true }`. Per-package environments would re-introduce four drift surfaces for zero isolation benefit — the packages are developed and verified together.

### Latent undeclared dependency, fixed in passing

`anamnesis` imports `llm_client` but does not declare it — it works only because the ambient environment happens to contain everything. The workspace makes this a resolution error, so it gets declared properly here.

### Existing per-package extras stay

`[project.optional-dependencies] dev` blocks remain as authored (they are correct package metadata); the workspace installs them via `uv sync --all-packages --all-extras`. No dependency version changes in this ho — the lockfile pins what the constraints already allow. Build backend (hatchling) unchanged.

### Python pinned at 3.12

`.python-version` committed at the root. `requires-python >=3.11` stays in package metadata (library floor); the pin is the development/verification interpreter.

### Hooks and Makefile run through the environment

Every pre-commit entry and Makefile verification target becomes `uv run --no-sync <tool>` — the committed lockfile's tools, not ambient ones. `--no-sync` keeps hooks from mutating the environment mid-commit; `make setup` owns syncing. The S1-era "ambient toolchain until uv migration" comment comes out.

### JS lockfile committed

`.gitignore` stops ignoring `package-lock.json` (yarn/pnpm lockfiles stay ignored — npm is the package manager here); the lockfile is generated and committed. `make setup` uses `npm install` (not `ci`) locally; CI would use `npm ci` when CI exists.

---

## Deliverables

1. Root `pyproject.toml` — virtual uv workspace declaring the four members
2. `.python-version` — 3.12
3. `packages/satori-api/pyproject.toml` — `[tool.uv.sources]` for `satori`, `llm-client`
4. `packages/anamnesis/pyproject.toml` — declare `llm-client` dependency + workspace source
5. `uv.lock` — committed
6. `.gitignore` — un-ignore `package-lock.json`
7. `packages/internal-affairs/package-lock.json` — committed
8. `Makefile` — `setup` via `uv sync --all-packages --all-extras`; lint/typecheck/test/dev-api via `uv run --no-sync`
9. `.pre-commit-config.yaml` — all hook entries via `uv run --no-sync`; stale comment removed

---

## Out of Scope

- Dependency upgrades (lockfile pins current constraint solutions only)
- CI configuration (none exists; noted for the hosting phase)
- llm-client coverage floor (P2-H08)
- Frontend package manager changes (npm stays)

---

## Verification Stack

1. `uv sync --all-packages --all-extras` from a clean `.venv` — succeeds
2. `uv run --no-sync ruff check packages/ && uv run --no-sync ruff format --check packages/`
3. `uv run --no-sync mypy packages/satori/src packages/anamnesis/src packages/llm-client/src packages/satori-api/src`
4. `uv run --no-sync pytest packages/ -q` — all suites, coverage floors intact
5. `cd packages/internal-affairs && npm run check`
6. Pre-commit hooks green through the new entries (exercised by the commit itself)

---

## Commit Message Template

```
chore(P2-H10): uv workspace migration — reproducible environment (audit C-4)

- root virtual workspace over the four Python packages; single committed
  uv.lock; .python-version pinned 3.12
- anamnesis: declare the llm-client dependency it already imports
- satori-api/anamnesis: workspace sources for in-repo dependencies
- package-lock.json un-ignored and committed
- Makefile + pre-commit hooks run via uv run --no-sync (pinned toolchain,
  not ambient); stale S1-era comment removed
```
