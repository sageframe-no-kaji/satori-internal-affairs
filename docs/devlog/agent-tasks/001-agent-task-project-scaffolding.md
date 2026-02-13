# Agent Task: Project Scaffolding & README

## Goal

The `satori-internal-affairs` repository has a complete directory structure, a comprehensive README, development environment configuration, and all foundational files committed. A developer cloning the repo understands immediately what this project is, how it's organized, and how to get started.

## Context

This is a medical mystery simulator with three core layers:

- **Satori** — deterministic game engine (Python)
- **Anamnesis** — LLM-powered case generation pipeline (Python)
- **Internal Affairs** — player-facing frontend (SvelteKit)
- **LLM Client** — provider-agnostic LLM abstraction layer (Python)

The backend is Python. The frontend is SvelteKit. This is a monorepo. The architecture is defined in `satori-internal-affairs-seed.md` which should be committed into `docs/`.

The repo already exists. This task sets up the internal structure.

## Features

1. **Directory structure** matching the monorepo layout:
   ```
   satori-internal-affairs/
   ├── packages/
   │   ├── satori/              ← deterministic engine (Python)
   │   │   ├── src/
   │   │   │   └── satori/
   │   │   ├── tests/
   │   │   ├── pyproject.toml
   │   │   └── README.md
   │   ├── anamnesis/           ← case generation pipeline (Python)
   │   │   ├── src/
   │   │   │   └── anamnesis/
   │   │   ├── tests/
   │   │   ├── pyproject.toml
   │   │   └── README.md
   │   ├── llm-client/          ← LLM abstraction layer (Python)
   │   │   ├── src/
   │   │   │   └── llm_client/
   │   │   ├── tests/
   │   │   ├── pyproject.toml
   │   │   └── README.md
   │   └── internal-affairs/    ← SvelteKit frontend
   │       └── (SvelteKit project scaffold)
   ├── schemas/                 ← shared JSON Schema case definitions
   ├── cases/                   ← frozen, validated case artifacts
   ├── docs/
   │   ├── architecture/        ← system design docs
   │   ├── devlog/              ← learning and decision journal
   │   └── satori-internal-affairs-seed.md
   ├── tasks/                   ← agent task specs
   ├── README.md
   ├── .gitignore
   └── Makefile (or justfile)   ← top-level dev commands
   ```

2. **Python package setup** for each backend package:
   - `pyproject.toml` with project metadata, Python >=3.11, and dev dependencies (pytest, ruff, mypy)
   - `src/` layout with proper `__init__.py` files
   - Empty `tests/` directory with a placeholder test
   - Per-package README with one-paragraph description of that layer's responsibility

3. **SvelteKit project scaffold** for `packages/internal-affairs/`:
   - Initialize with `npx sv create` (skeleton project, TypeScript)
   - No additional dependencies yet — just the default scaffold
   - Per-package README describing Internal Affairs' role

4. **Root README.md** containing:
   - Project title and one-paragraph description
   - System architecture overview (the three layers, what each does)
   - The four system boundaries (freeze line, truth line, narration line, provider line) — brief descriptions
   - Directory structure explanation
   - Tech stack summary (Python, SvelteKit, ChatGPT API via abstraction)
   - How to set up the development environment
   - Current status (Phase 1 — architectural foundation)
   - Link to the seed document in `docs/`

5. **Root .gitignore** covering:
   - Python: `__pycache__/`, `.venv/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`
   - Node: `node_modules/`, `.svelte-kit/`, `build/`
   - IDE: `.vscode/`, `.idea/`
   - Environment: `.env`, `.env.local`
   - OS: `.DS_Store`
   - Obsidian: `.obsidian`

6. **Root Makefile** (or justfile) with convenience commands:
   - `make lint` — runs ruff across all Python packages
   - `make typecheck` — runs mypy across all Python packages
   - `make test` — runs pytest across all Python packages
   - `make dev-frontend` — starts SvelteKit dev server
   - `make setup` — installs all dependencies (Python venvs + npm install)

7. **Seed document** committed to `docs/satori-internal-affairs-seed.md`

8. **Phase 1 gameplan** committed to `docs/architecture/phase-1-gameplan.md`

## Implementation Guidance

- Use `src/` layout for Python packages (not flat layout). This keeps imports clean and avoids namespace collisions.
- Each Python package should be installable in dev mode: `pip install -e packages/satori` etc.
- For the SvelteKit scaffold, use the official `sv create` tool with skeleton template and TypeScript. Don't add any UI libraries or components yet.
- The README should be written for a technical reader evaluating this as a portfolio piece. Clear, professional, no fluff. Show that the architecture is intentional.
- Per-package READMEs are short — 3-5 sentences describing that layer's single responsibility and what it does NOT do.

## Commit

```
feat: project scaffolding and architectural foundation

- Monorepo structure with four packages (satori, anamnesis, llm-client, internal-affairs)
- Python dev environment (pyproject.toml, ruff, mypy, pytest)
- SvelteKit skeleton for frontend
- Root README with architecture overview
- Seed document and Phase 1 gameplan in docs/
```
