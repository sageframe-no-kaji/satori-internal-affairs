---
created: 2026-07-09
updated: 2026-07-10
type: state-memory
project: satori-internal-affairs
kamae: 6
status: living
---

# Satori Internal Affairs — State Memory

This file is the build's living cross-session memory: hot, mutable, and non-canonical. It is the first thing a fresh agent session reads to reconstitute build state without re-reading the full chain. The cold record wins: git history, per-ho devlogs, and the ho-overview are authoritative where this file and they disagree.

---

**STATE-SUMMARY**

- **COMPLETED** — Phase 2 close-out + first practitioner visual pass (2026-07-10): P2-H05 emergency mode (`0592bb7`); P2-H03 active concerns panel (`241f90c`); P2-H10 uv migration (`db6e507`); P2-H08 plumbing spec drafted, NOT executed (`0bdd987`); close-out report (`36f6a91`, at `audit/close-out-report-2026-07-04.md`); **P2-H11 iPad shell + clinical palette (`038c9f1`)** — practitioner-directed live HMR session: palette Option C (light clinical app, dark monitor vitals inset), viewport-locked shell (pinned header/vitals/actions, panels scroll internally), fold-up dropdowns with click-off close, windowshade concern sections with fresh-evidence green highlight + auto-shade + scroll-to-top, SpO₂ fix, PatientHeader/OutcomeScreen tokenized. Approved on screen.

- **NEXT** — P2-H08 completion is the only thing left before `v0.7`. The plumbing LANDED (`40bcd6c`, practitioner-authorized split): AnthropicNarrator, per-session cache, env wiring (mock default), timeout + fallback, with a clearly-marked PLACEHOLDER system prompt in `llm_client/narration_prompts.py`. **Remaining:** the practitioner's voice session (prompt at `prompts/h08-voice-session.md`, gitignored; output `docs/architecture/narrator-voice.md`) → drop the approved base system prompt into narration_prompts, fill EVENT_GUIDANCE, run the live smoke test behind `live_llm`, restore the llm-client coverage floor, set `SATORI_NARRATOR_PROVIDER=anthropic` in `.env`.

- **ACTION ITEMS / BLOCKS** — (1) H08 voice work as above — the sole blocker for v0.7. (2) Frontend test framework LANDED (P2-H14 `148bc57`: vitest + testing-library, 38 tests, in the pre-commit gate; no coverage floor yet — revisit at v0.7). (3) npm audit advisories in the frontend tree. (4) Emergency-mode dress not yet seen by eye under the new light palette. P2-H12/H13 closed UD-4/5/6 and C-8 earlier today. 649 Python + 38 frontend tests green.

- **PROJECT LIFECYCLE** — dev

_Updated 2026-07-10 after P2-H12/H13 (autonomous audit-debt hos; H11 visual pass earlier same day)._
