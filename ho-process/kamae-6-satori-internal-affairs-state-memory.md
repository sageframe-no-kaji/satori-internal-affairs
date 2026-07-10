---
created: 2026-07-09
type: state-memory
project: satori-internal-affairs
kamae: 6
status: living
---

# Satori Internal Affairs — State Memory

This file is the build's living cross-session memory: hot, mutable, and non-canonical. It is the first thing a fresh agent session reads to reconstitute build state without re-reading the full chain. The cold record wins: git history, per-ho devlogs, and the ho-overview are authoritative where this file and they disagree.

---

**STATE-SUMMARY**

- **COMPLETED** — P2-H09 (crisis mechanic and scoring): survivable seizure crisis, post-crisis re-arm via node_20/node_21, fallthrough failure tier, `emergency_timer` visibility channel, OPTIMAL window widened to 150 min, `family_alienated` made mechanical — all six locked decisions executed and committed (`480254b`). Audit close-out also complete (`b351389`); all five audit tasks resolved.

- **NEXT** — P2-H05 (Emergency Mode): engine `emergency_active` derivation and API surface are determined and locked; visual decisions (emergency signature, locked-action treatment) are the remaining open questions requiring practitioner input before implementation. The ho document is at `ho-process/hos/P2-H05-emergency-mode.md` with status IN PROGRESS. After H05: P2-H03 (Active Concerns Panel) and P2-H08 (Real LLM Narrator) are the remaining Phase 2 hos before `v0.7` release.

- **ACTION ITEMS / BLOCKS** — P2-H05 visual decisions (emergency screen signature and locked-action presentation) are pending practitioner ruling before implementation can proceed. P2-H03 (Active Concerns Panel) has no ho document yet under `hos/` — it appears in the ho-overview but was not scaffolded. P2-H08 (Real LLM Narrator) similarly has no per-ho doc. No test regressions known; the verification stack enforces pre-commit. Untracked working files at `audit/fable-close-out-prompt-2026-07-04.md` and `ho-process/hos/P2-H05-emergency-mode.md` — the H05 doc exists but is not yet committed.

- **PROJECT LIFECYCLE** — dev

_Seeded 2026-07-09 from git history and repo docs by a fleet pass; verify on next session._
