# Per-Ho Documents (Kamae 5)

This directory contains the per-ho documents for each working session. Each one is the bounded scope and execution spec for a single ho.

This project uses Ri-stage compression — the Kamae 5 framing (goal, scope, boundaries) and the dandori execution spec (acceptance criteria, verification, commit format) live together in one document per ho.

Each per-ho document defines:
- Goal and context
- In scope / out of scope
- Required features and implementation guidance
- Acceptance criteria and verification stack
- Commit message template

Naming: `P<phase>-H<ho>-[DONE-]<slug>.md`. The `DONE-` marker is added once the ho closes. Closed hos stay closed (forward-only) — corrections live in a new ho, not retroactive edits.

If a single ho decomposes into multiple bounded agent tasks, those live as siblings in `../agent-tasks/` named `Ho-NN-AT-MM.md`.
