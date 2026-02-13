# Satori Internal Affairs

**A medical mystery simulator combining deterministic game mechanics with LLM-powered case generation.**

Satori Internal Affairs is an investigative game where players diagnose complex medical cases by interviewing patients, ordering tests, and piecing together clues. The system uses a frozen case model to ensure consistent, reproducible gameplay while leveraging LLMs for dynamic case generation.

## System Architecture

The project is structured as a monorepo with four core packages:

### **Satori** — Deterministic Game Engine (Python)
The mechanical heart of the system. Satori maintains ground truth for medical cases, validates player actions against frozen case schemas, tracks investigation state, and determines outcomes. It enforces rules but does not generate content or interface with LLMs.

### **Anamnesis** — Case Generation Pipeline (Python)
Orchestrates LLM-powered creation of medical mystery cases. Anamnesis uses structured prompts to generate case artifacts, validates them against JSON schemas, and produces frozen case files for Satori to consume. This layer runs offline or on-demand, not during gameplay.

### **LLM Client** — Provider Abstraction Layer (Python)
A provider-agnostic interface for LLM interactions. Handles authentication, request formatting, response parsing, and error handling across different LLM providers (OpenAI, Anthropic, local models). Isolates the rest of the system from provider-specific implementation details.

### **Internal Affairs** — Player Frontend (SvelteKit)
The SvelteKit web application presenting the investigative interface. Communicates with Satori to submit actions and receive state updates. Purely a presentation layer with no game logic, case generation, or LLM interactions.

## Four System Boundaries

The architecture is defined by four critical boundaries:

- **Freeze Line** — Separates case generation (Anamnesis) from case execution (Satori). Cases are generated once, validated, and frozen into immutable JSON artifacts. This ensures reproducibility and consistent gameplay.

- **Truth Line** — Separates ground truth (Satori) from narrative presentation (Internal Affairs). Satori knows the complete medical truth; the frontend only knows what the player has discovered.

- **Narration Line** — Separates deterministic game state (Satori) from dynamic text generation. Future iterations may use LLMs to generate examination descriptions, but core game logic remains deterministic.

- **Provider Line** — Separates domain logic (Anamnesis) from LLM implementation (LLM Client). Allows switching providers without changing case generation logic.

## Directory Structure

```
satori-internal-affairs/
├── packages/
│   ├── satori/              # Deterministic game engine (Python)
│   ├── anamnesis/           # Case generation pipeline (Python)
│   ├── llm-client/          # LLM abstraction layer (Python)
│   └── internal-affairs/    # SvelteKit frontend
├── schemas/                 # Shared JSON Schema case definitions
├── cases/                   # Frozen, validated case artifacts
├── docs/                    # Architecture docs and devlog
├── tasks/                   # Agent task specifications
└── README.md
```

## Tech Stack

- **Backend**: Python 3.11+ with pytest, ruff, mypy
- **Frontend**: SvelteKit with TypeScript
- **LLM Integration**: ChatGPT API (provider-agnostic via abstraction layer)
- **Case Format**: JSON with JSON Schema validation

## Development Setup

### Python Packages

Each Python package can be installed in development mode:

```bash
pip install -e packages/satori
pip install -e packages/anamnesis
pip install -e packages/llm-client
```

Or use the convenience command:

```bash
make setup
```

### Frontend

```bash
cd packages/internal-affairs
npm install
npm run dev
```

### Development Commands

```bash
make lint       # Run ruff across all Python packages
make typecheck  # Run mypy across all Python packages
make test       # Run pytest across all Python packages
make dev-frontend  # Start SvelteKit dev server
```

## Current Status

**Phase 1 — Architectural Foundation**

The monorepo structure is established with skeletal implementations of all four packages. Core architectural boundaries are defined. Next steps include implementing JSON schemas for case definitions and building out the Satori case validation engine.

## Documentation

- [Seed Document](docs/satori-internal-affairs-seed.md) — Original architectural vision
- [Phase 1 Gameplan](docs/architecture/phase-1-gameplan.md) — Current development roadmap
