# satori-internal-affairs — close out as much of Phase 2 as possible

## Your role

You are executing multiple Ho System hos autonomously to advance the satori-internal-affairs project from its current mid-Phase-2 state toward `v0.7`. You have authority to author, implement, verify, and commit — EXCEPT at named visual decision points, where you present options and stop for the practitioner's choice before proceeding.

Working dir: `/Users/atmarcus/Vaults/sageframe-no-kaji-dev/satori-internal-affairs`.

## The project in one paragraph

Satori Internal Affairs is an interactive medical mystery simulator — a clinical reasoning game where a teenage player takes the role of a clinician diagnosing patients under time pressure. Deterministic engine (`packages/satori`) over case JSON graphs (nodes/flags/timers/effects). LLM (`packages/anamnesis`) generates cases at design time; play is deterministic. FastAPI bridge (`packages/satori-api`) between engine and SvelteKit UI (`packages/internal-affairs`). Phase 1 complete; Phase 2 (Gameplay Surface + Narrative Voice → v0.7) is mid-flight.

## Entry points — read in this order

1. `README.md`
2. `ho-process/satori-internal-affairs-seed.md` — Kamae 1
3. `ho-process/satori-internal-affairs-system-design.md` — Kamae 2 (canonical architectural reference)
4. `ho-process/ho-overview.md` — Kamae 4 (Phase 2 build sequence)
5. `docs/architecture/game-design-pitch.md`, `case-data-structure.md`, `satori-engine-api.md`
6. `ho-process/hos/P1-H06-DONE-vertical-slice.md` and `ho-process/hos/P2-H01-engine-surface-prep.md` — model per-ho doc format
7. `audit/emergency-mode-decision-memo.md` — your own spike output (you wrote this in an earlier session)
8. `cases/example-neurocysticercosis.json` — the one existing case; read node_09/13/14/16/17 and the `outcome_evaluation` block carefully

## Current state (2026-07-03)

Phase 2 hos done: H01 (engine surface prep), H02 (dashboard skeleton + design tokens), H04 (Pending Results panel), H06 (Wait Action UI), H07 (diagnostic rigor scoring).

Phase 2 hos remaining: **a new case-authoring ho (unwritten)**, H03 (Active Concerns panel), H05 (Emergency Mode), H08 (Real LLM Narrator).

Recent audit (commit `e55e7b1`) closed out: mypy clean, verification stack gates, determinism hardened, steroid rebound gated correctly, narrator failure isolated, accessibility fix on outcome button. The verification stack is now: `ruff check && ruff format --check`, `mypy --strict`, `pytest`, `npm run check`. Coverage floor 90%. Pre-commit hooks enforce.

**Known infrastructure debt: uv migration (audit item C-4).** Not started; can happen anytime.

## Decisions locked — apply these, do not re-litigate

1. **Survivable crisis mechanism.** `emergency_intervention` action deactivates `node_14_seizure_crisis`, sets `crisis_managed`, clears `crisis_active`, unlocks the four investigation actions node_14 locked.

2. **Post-crisis re-arm.** `crisis_managed` activates a new post-crisis progression node with a ~90-minute non-diegetic timer expiring into a **distinct second seizure crisis node** (not reactivation of node_14). The second crisis also takes `emergency_intervention` rescue — the mechanic must not lie the second time.

3. **Timeout fallthrough tier.** T+360 with no treatment and no death currently matches no tier. Add a failure-register fallthrough tier.

4. **`emergency_timer` visibility channel.** Add `emergency_timer: VisibleTimer | None` field on `GameState` (and the API response). Populated only when `emergency_active` is true; carries the currently-active crisis node's timer. `visible_timers` stays semantically clean (diegetic-only).

5. **OPTIMAL window: 150 minutes.** In `outcome_evaluation.tiers.optimal.time_constraints`, `before_minutes: 120` → `150`.

6. **`family_alienated`: mechanical, excludes GOOD.** Add `family_alienated` to GOOD's `excluded_flags`. Keep node_13's `on_expire` and the flag as authored. Retouch PARTIAL's narrative (one sentence) to cover both the late-diagnosis route and the relational-failure route. Document Diego's tick-quantized arrival.

## Execute in this order

### Ho A — Case-authoring bundle (**fully autonomous**)

Author `ho-process/hos/P2-H0X-crisis-mechanic-and-scoring.md` (pick the next available P2-H## number after H07) as the per-ho doc bundling decisions 1–6. Match the format of `ho-process/hos/P2-H01-engine-surface-prep.md`. Under Design Decisions, paste your own two design notes from the memo verbatim — they're paste-ready and the reasoning matters for future readers.

Then execute the ho. Commit atomically. Full verification stack. No visual work in this ho — pure case JSON + small engine addition (`emergency_timer`) + tests.

### Ho B — H05 Emergency Mode (**visual decision points — STOP and offer options**)

Author `ho-process/hos/P2-H05-emergency-mode.md` first, without committing to visual specifics. Include the engine and API work in full detail (they're determined by decision 4 above: `emergency_active: bool` derived as `has crisis flag AND NOT case_ended`, both `emergency_active` and `emergency_timer` on `GameStateResponse`, closing the `TODO(P2-H05)` in `ActionBar.svelte` to wire wait's disabled state).

Then, **BEFORE writing any visual UI code**, produce a visual decision moment.

#### VISUAL DECISION 1 — Emergency state signature

*How does the screen say "EMERGENCY"?* Present three options. For each: a one-sentence description, a small ASCII mockup showing layout, and a note on the UD implication.

Suggested starting palette (adapt if you have a better read):

- **Option A — Screen-edge red border.** Non-emergency layout stays; a 6–8px `--color-state-critical` border wraps the viewport. Vitals strip shifts to a warning register. Panels remain visible; investigation actions gray out inline. Least disruptive; ataxia-friendly (no layout shift under pressure).
- **Option B — Top-anchored emergency banner.** Full-width crimson banner slides down from the top with the crisis label ("SEIZURE — INTERVENE") and the `emergency_timer` countdown large and centered. Investigation panels dim to ~60% opacity. Ataxia note: no layout collapse, but the eye is forced upward — verify the intervention button remains reachable without scrolling.
- **Option C — Central emergency panel.** Investigation UI dims to background; a centered emergency panel takes visual command with the crisis name, timer, and the `emergency_intervention` button rendered at 96×96px. Highest theatrical weight; strongest reading for a player in a moment of pressure. Ataxia note: single large target dominates — probably best for motor-limits.

STOP. Present the options. Wait for the practitioner's choice or a redirect.

#### VISUAL DECISION 2 — Locked action treatment

Once decision 1 is chosen, present:

*How do investigation actions render when they're locked during a crisis?*

- **Option A — Grayed inline with reason.** Actions stay in place, opacity ~35%, tooltip on focus/hover reads "Locked: patient is seizing." Preserves spatial memory (buttons in the same place before and after). Ataxia note: strong — no need to re-locate anything after the emergency.
- **Option B — Emergency-only action bar.** During crisis, the action bar replaces its category dropdowns entirely with just the emergency actions (`emergency_intervention` and any other crisis-relevant options). Investigation returns after intervention. Ataxia note: fewer choices means faster action, but requires the player to accept the layout shift.
- **Option C — Sidebar-relegated.** Locked actions collapse to a small sidebar list with a lock icon; emergency actions take the main position. Middle path. Ataxia note: acceptable, but two visual regions is more scanning.

STOP. Present. Wait.

Then implement whichever combination you chose, using tokens throughout. Commit.

Escalate only if the engine's emergency signal doesn't cleanly derive from flag state — do not invent new engine mechanisms.

### Ho C — H03 Active Concerns panel (**visual decision point — STOP and offer options**)

Author `ho-process/hos/P2-H03-active-concerns-panel.md`. Include the data-wiring and component-shape work in full detail. Then, **BEFORE writing the card styling**, produce a visual decision moment.

#### VISUAL DECISION 1 — Card language and grouping

*How do findings look as they accumulate, and how are they organized?*

- **Option A — Bordered cards, section headers per category.** Each finding is a bordered card with subtle background. Cards are grouped under category headers (History, Exam, Labs, Imaging) with a rule between sections. Traditional; scan-friendly; clinician's-chart-adjacent. Ataxia note: category grouping means the player looks in the right region when new evidence arrives.

  ```
  History
  ┌────────────────────┐
  │ Chief complaint    │
  │ Seizure + speech.. │
  └────────────────────┘
  ┌────────────────────┐
  │ Dietary            │
  │ Undercooked pork.. │
  └────────────────────┘

  Labs
  ┌────────────────────┐
  │ CBC                │
  │ Eosinophilia 12%   │
  └────────────────────┘
  ```

- **Option B — Borderless list with divider lines, flat chronological.** No card borders; findings are text blocks separated by thin horizontal rules. A small category tag ("HISTORY", "LABS") on each entry. Ordered by reveal time (newest at top or bottom — pick). Feels closer to a running clinical note. Ataxia note: dense — verify tap targets on each finding remain ≥ 60px if any interaction is added later.

  ```
  ─────────────────────
  LABS · t=45
  CBC — Eosinophilia 12%
  ─────────────────────
  HISTORY · t=15
  Dietary — Undercooked pork
  ─────────────────────
  HISTORY · t=0
  Chief complaint — Seizure + speech
  ```

- **Option C — Tabbed by category.** A row of tabs (History, Exam, Labs, Imaging) atop the panel; each tab shows the findings within that category. Only one category visible at a time. Denser info hiding. Ataxia note: tabs are extra hit-targets and hide state — probably NOT the right call for this player. Included for completeness.

  ```
  [History] [Exam] [Labs] [Imaging]
  ┌─────────────────────────────────┐
  │ Dietary — Undercooked pork      │
  │ Chief complaint — Seizure...    │
  │                                 │
  └─────────────────────────────────┘
  ```

STOP. Present. Wait for choice.

Then implement using tokens throughout. Commit.

### Ho D — uv migration (**fully autonomous, infrastructure**)

Author `ho-process/hos/P2-H0X-uv-migration.md` and execute. Migrate the four Python packages (satori, anamnesis, llm-client, satori-api) from their current pip/setup pattern to `uv`-managed workflows. Preserve all existing verification. Do not do this before Hos A, B, C — infrastructure changes during active feature work risk conflicts.

### **H08 Real LLM Narrator — DO NOT execute**

Draft the per-ho document at `ho-process/hos/P2-H08-real-llm-narrator.md` describing the technical plumbing only (provider swap, cache, env-var config, fallback path, prompt-template *structure* — not content). Leave the ho doc marked `STATUS: DRAFT — VOICE WORK PENDING PRACTITIONER`. Do NOT write actual prompt content. Do NOT execute.

## How to present a visual decision point

When you reach a **STOP** marker, format the moment like this in your response to the practitioner:

```
🛑 VISUAL DECISION [n] — [name]

[One-line question restated.]

▸ Option A — [name]
  [Description, 1–2 sentences.]
  [ASCII mockup if useful.]
  Ataxia read: [one-line implication]

▸ Option B — [name]
  ...

▸ Option C — [name]
  ...

Which — A, B, C, or a redirect? (If none of these is right, describe what you want and I'll adjust before implementing.)
```

Then WAIT. Do not proceed until the practitioner responds. Do not implement a compromise between options unless explicitly told to. If the practitioner redirects with a different idea, produce the implementation of that instead.

## Hard constraints (practitioner discipline — non-negotiable)

1. **Verification stack.** Every commit passes `ruff check && ruff format --check`, `mypy --strict`, `pytest`, `npm run check`. Coverage floor 90%. Pre-commit hooks enforce; if a hook fails, fix the cause — never `--no-verify`.

2. **Never sign commits.** Do NOT add `Co-Authored-By: Claude`, do NOT add `🤖 Generated with Claude Code`, do NOT identify the AI anywhere. Categorical, no exceptions. Strip such tags from any template.

3. **The four architectural boundaries hold.** Freeze Line (no LLM calls at play time). Truth Line (frontend never computes medical logic). Narration Line (narrator returns text only, never state). Provider Line (openai/anthropic import only in `packages/llm-client/`).

4. **Universal Design is load-bearing.** Player has severe ataxia. 60px+ touch targets, 16px+ gaps between interactives, 18px base font, no hover-only behaviors, keyboard nav, WCAG AA contrast.

5. **Design tokens.** No hex codes or magic-number `px` in component-local styles. Everything reads from `packages/internal-affairs/src/lib/styles/tokens.css`. Extend tokens if you need new ones.

6. **Type errors get explanatory comments.** No silent `# type: ignore`.

7. **Closed hos stay closed (forward-only).** Do not edit `P1-H##-DONE-*.md`, closed devlogs, or older audit artifacts.

8. **Determinism.** Same case + same actions = same outcome. No `time.time()`, no `random`, no `datetime.now()`, no set-iteration ordering assumptions in engine code.

## When to escalate (stop and report — do not invent)

- The case's activation graph doesn't cleanly support the second-crisis re-arm and needs a schema change
- The `emergency_timer` field would require breaking API changes (it should be additive)
- A test failure surfaces a genuine architectural problem rather than a mechanical fix
- H05's emergency signal derivation requires a new engine mechanism beyond flag-check
- Anything that would require modifying the Kamae chain (system design, ho overview)

## Commit discipline

- One atomic commit per ho, using each per-ho doc's Commit Message Template
- Commit messages describe the change, not the AI's process
- If a pre-commit hook fails: fix the cause, re-stage, create a NEW commit (never amend across hook failures — you may destroy prior work)

## Deliverable

Work through Ho A → B (with 2 visual stops) → C (with 1 visual stop) → D → H08 draft in order. For each ho:

1. Write the per-ho doc
2. Execute (except H08 — draft only)
3. At visual decision points: STOP, present options as specified, wait for practitioner choice
4. Verify (full stack)
5. Commit atomically

At the end, write a single summary report at `audit/close-out-report-2026-07-04.md` covering:

- Each ho's commit SHA and verification results
- Visual decisions taken and the practitioner's choice at each
- Any deviations from the decisions locked above with rationale
- Any escalations that stopped work
- What remains after your close-out

Then STOP. Do not continue past what's listed here.

Begin.
