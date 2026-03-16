# Satori Internal Affairs

A patient walks into your ER with chest pain and a story that doesn't add up. You have to decide — right now — what questions to ask, what tests to order, and how long you can afford to wait. If you're wrong, they deteriorate. If you're slow, they deteriorate. If you miss what they're not telling you, they deteriorate.

This is not a quiz. There is no multiple choice. The goal is not to guess the diagnosis.

The goal is to learn how doctors think.

**Development Process:** This project was built using the [Ho System](https://atmarcus.net/work/ho-system), a structured methodology for human-AI collaborative development. The human makes every design decision. The AI implements under direction. There is verification at every step.

---

## Why This Exists

I designed this for my teenage daughter. She loves medical dramas — *Grey's Anatomy*, *House*, the whole genre. She's also spent a lot of time in hospitals and *really* wants to understand the medicine. Not the TV version. The real version. How doctors actually think, what they're weighing, why they order what they order, and what happens when they get it wrong.

I couldn't find anything that gave her that. Quiz apps test memorization. Chatbots hallucinate. Medical dramas are compelling but consequence-free. So I'm building the thing that should exist.

## What This Is

Satori Internal Affairs is an interactive medical mystery simulator — a clinical reasoning game where the player steps into the role of a clinician and makes real decisions under pressure.

Each case is a story. Patients have secrets. Families have conflicts. Test results take time. Conditions worsen. Death is a possible outcome — not as punishment, but as consequence.

The experience is built for emotionally and intellectually advanced teenagers — the ones who love *Grey's Anatomy*, *House*, and high-stakes medical drama. It's age-appropriate but not dumbed down. The medicine is real. The stakes feel real. The reasoning is what actual clinicians do.

## What This Teaches

Medicine has a finite number of core pathologies and infinite surface variation. By generating case *variants* rather than static scenarios, the system teaches:

- **Pattern recognition** — learning to see what matters in noise
- **Hypothesis testing** — forming and revising theories as evidence arrives
- **Managing uncertainty** — acting before you have complete information
- **Timing and deterioration** — understanding that waiting is itself a decision
- **Medicine as a human system** — patients lie, minimize, and hide. Fear, shame, and power dynamics shape outcomes. Doctors disagree and make mistakes.

The player doesn't memorize facts. They develop judgment.

---

## Architecture

### The Core Design Insight

The system **separates case generation from case play.**

An LLM generates rich, medically grounded cases from structured seeds — but once a case is generated, it's frozen. During gameplay, no facts are invented. No diagnoses shift. No outcomes change based on what the LLM feels like saying. The game engine is deterministic: same case, same actions, same result. Every time.

This is the architectural decision everything else follows from. It preserves drama and replayability without sacrificing consistency or safety.

### The Stack

The project is a monorepo with four packages, each with a single responsibility:

**Satori** — the deterministic game engine. Loads frozen cases, validates player actions, advances time, tracks vitals, triggers deterioration or recovery, and determines outcomes. Satori is the source of truth. It does not generate text. It does not call the LLM. It decides *what happens*, not *how it's described*.

**Anamnesis** — the case generation pipeline. Takes structured seeds (diagnosis, difficulty, dramatic tone, ethical complications) and uses the LLM to produce complete case definitions. Output is validated against a JSON Schema and frozen before it ever reaches Satori. Anamnesis runs at design-time, never during gameplay.

**LLM Client** — the provider abstraction layer. A single interface through which all LLM calls flow. Currently backed by the ChatGPT API, but designed so the provider can be swapped — to Anthropic, a local model, or a fine-tuned model — without changing anything upstream.

**Internal Affairs** — the player-facing frontend. A SvelteKit application that presents cases, shows available actions, displays results, and renders the experience. It sends actions to Satori and renders what Satori returns. It never decides what's medically true. It tells the story; Satori enforces the truth.

### Four Boundaries

The architecture is defined by four boundaries that must never leak:

| Boundary | Separates | Why It Matters |
|----------|-----------|----------------|
| **Freeze Line** | Case generation (Anamnesis) → Case execution (Satori) | No facts invented during play. Cases are immutable artifacts. |
| **Truth Line** | Game logic (Satori) → Presentation (Internal Affairs) | The frontend reveals truth; it never determines it. |
| **Narration Line** | Deterministic state (Satori) → LLM text generation | Narrative is cosmetic. Strip it away and the game still works. |
| **Provider Line** | Domain logic (Anamnesis) → LLM implementation (LLM Client) | Swap models without touching case generation logic. |

---

## Project Structure

```
satori-internal-affairs/
├── packages/
│   ├── satori/              # Deterministic game engine (Python)
│   ├── anamnesis/           # Case generation pipeline (Python)
│   ├── llm-client/          # LLM abstraction layer (Python)
│   └── internal-affairs/    # Player frontend (SvelteKit)
├── schemas/                 # Shared JSON Schema — the contract between layers
├── cases/                   # Frozen, validated case artifacts
├── docs/                    # Architecture documentation and devlog
│   ├── architecture/
│   └── devlog/
├── tasks/                   # Agent task specifications
├── Makefile                 # Development convenience commands
└── README.md
```

## Tech Stack

- **Backend:** Python 3.11+ (Pydantic, pytest, ruff, mypy)
- **Frontend:** SvelteKit with TypeScript
- **LLM:** ChatGPT API via provider-agnostic abstraction
- **Case Format:** JSON with JSON Schema validation
- **Architecture:** Monorepo with containerization-ready package boundaries

## Development Setup

### Python Packages

```bash
make setup              # Install all Python packages in dev mode
```

Or individually:

```bash
pip install -e packages/satori
pip install -e packages/anamnesis
pip install -e packages/llm-client
```

### Frontend

```bash
cd packages/internal-affairs
npm install
npm run dev
```

### Dev Commands

```bash
make lint               # Ruff across all Python packages
make typecheck          # Mypy across all Python packages
make test               # Pytest across all Python packages
make dev-frontend       # SvelteKit dev server
```

---

## Current Status

**Phase 1 — Architectural Foundation**

Monorepo structure is established. System boundaries are defined. Currently building: the JSON Schema that serves as the contract between Anamnesis and Satori, followed by the deterministic engine core.

See [Phase 1 Gameplan](docs/architecture/phase-1-gameplan.md) for the full roadmap.

## Documentation

- [Seed Document](docs/satori-internal-affairs-seed.md) — the original architectural vision and design rationale
- [Phase 1 Gameplan](docs/architecture/phase-1-gameplan.md) — milestone breakdown and dependency map

## License

This project is licensed under the [MIT License](LICENSE).
