# Phase 2 — Ho Overview

**Kamae 4 artifact** — sequences the Phase 2 build
**Phase release tag:** `v0.7` at phase completion
**Date:** 2026-06-29

---

## What This Document Is

The build sequence for Phase 2. It takes the Phase 2 commitments locked in [`satori-internal-affairs-system-design.md`](satori-internal-affairs-system-design.md) and turns them into an ordered sequence of bounded sessions. Each ho is one working session; each section here is what gets framed before that session begins.

This document is intentionally lighter than per-ho documents. Each ho's K5 doc lives under [`hos/`](hos/) and is written at session start using the same workflow used through Phase 1.

---

## Phase 2 — Gameplay Surface + Narrative Voice

**Release:** `v0.7`

**What this phase produces.** The engine already simulates the design; Phase 1's UI surfaced almost none of it. Phase 2 closes that gap and adds the narrative voice the seed promises. At phase completion, the Maria Santos case is playable *as designed* — concurrent timers visible (the ones the character would know), the patient deteriorating off-screen but legible through vitals and emerging symptoms, emergencies that visibly take over the screen, the option to wait when waiting is the right move, and patient/family dialogue generated live by an LLM in the *Grey's Anatomy* register. The mechanical surface and the narrative voice are entangled by design — both ship together because the design can only be evaluated when both are present.

**What's true at the end of Phase 2 that wasn't true at the start.** The dashboard exists; pending results display countdowns; concerns accumulate visibly; emergencies render distinctly; the player can wait; treatment scoring rewards diagnostic rigor; the narrator speaks in the project's voice. The game is playable for one user, on one case, with the felt experience the design calls for. Whether that experience is *good* — whether the design lands — is the question Phase 2 makes answerable.

**What this phase does not do.** No new cases. No teaching/debrief depth. No hosting, mobile polish, or atmosphere work beyond what the dashboard layout naturally needs. The narrator is wired and voiced; tuning across many event types and personality variants is Phase 3+ work.

---

### P2-H01 — Engine Surface Prep

**Narrative.** A small, foundational engine ho that adds the surface primitives Phase 2 needs in one cohesive change. Three things land together: a `diegetic: bool` flag on `NodeTimer` (default `false`); a `visible_timers` field on `GameState` derived from `pending_reveals` plus active timers whose nodes are revealed and whose `timer.diegetic` is true; and a built-in `wait` action with subcategory durations that advances the clock without other effects. The example case (Maria Santos) is updated to mark lab and imaging timers as diegetic.

**Dependencies.** None beyond Phase 1 completion.

**In scope.** Schema field, Pydantic model, GameState derivation, wait action handling in `engine.py` and `action_parser.py`, case update, tests. API serialiser surfaces `visible_timers` on `GameStateResponse`.

**Out of scope.** UI rendering of any of this. Emergency mode (separate ho). Diagnostic scoring (separate ho).

**Decisions this ho resolves.**
- *Exact wait durations.* Recommended: `wait:15`, `wait:30`, `wait:60`. Cases may not author these; they are built-in.
- *Whether `visible_timers` lives on `GameState` or is computed at API serialisation time.* Recommended: on `GameState` so engine tests can assert it directly.
- *Shape of `VisibleTimer`.* Recommended: a frozen dataclass with `label: str`, `remaining_minutes: int`, `source: Literal["pending_reveal", "active_timer"]`. Labels are derived from node `display_name`, not authored separately.

---

### P2-H02 — Dashboard Skeleton

**Narrative.** Restructure the SvelteKit frontend from the current single-page-flow layout to the mission-control dashboard. New layout: a top vitals strip, a three-column body (Active Concerns | Narrative Feed | Pending Results), and a bottom action bar. Component shells are created for each panel but most of them render placeholder content; the goal is to land the layout and the data wiring without yet implementing panel-specific logic. The existing `OutcomeScreen` continues to handle case end.

**Dependencies.** P2-H01 (so `visible_timers` is available to wire even if not yet rendered richly).

**In scope.** Route restructure of `+page.svelte`; new components `VitalsStrip.svelte`, `ActiveConcernsPanel.svelte`, `NarrativeFeedPanel.svelte`, `PendingResultsPanel.svelte`, `ActionBar.svelte`; game store wiring; CSS scaffolding for the three-column grid; responsive baseline (graceful collapse on narrow viewports — full mobile polish deferred to Phase 6).

**Out of scope.** Active Concerns logic (next ho). Pending Results countdowns (later ho). Emergency mode rendering. Real narration content. Visual atmosphere or theme work.

**Decisions this ho resolves.**
- *Component decomposition.* Whether `ActionBar` is one component or composes per-category dropdowns. Recommended: one `ActionBar` that composes a `CategoryDropdown` subcomponent.
- *Whether the Phase 1 `PatientHeader` survives.* Recommended: yes, sits above the vitals strip; demographic context belongs there.
- *CSS approach.* Recommended: Tailwind utilities consistent with what `internal-affairs` already uses. No new design system this ho.

---

### P2-H03 — Active Concerns Panel

**Narrative.** The Active Concerns panel is the player's evidence board — every revealed clinical finding accumulates here as a card. Cards group by category (history, exam, labs, imaging, vitals/secrets) and persist for the whole case. This is the diagnostic whiteboard; it's what makes the player's reasoning visible to themselves. The panel reads from `state.revealed_nodes` and renders structured node data (not narration).

**Dependencies.** P2-H02.

**In scope.** Card component for revealed findings; grouping logic by node category or `node_type`; styling that supports skim-reading; empty state (case start); behavior when many cards accumulate (scroll vs. collapse — decided in this ho).

**Out of scope.** Player annotations on cards (Phase 5). Cards that link to teaching notes (Phase 5). Re-ordering or pinning by the player (deferred).

**Decisions this ho resolves.**
- *Grouping taxonomy.* Whether to group by node category (`history`, `exam`, `labs`, …) or by a new `concern_category` field. Recommended: existing node category; no new schema field.
- *Card content.* What data goes on the card. Recommended: node `display_name`, the structured finding (lab value, exam finding, history quote), the timestamp it was revealed at.
- *Behaviour when the case ends.* Recommended: panel stays populated; outcome screen overlays it rather than replacing it.

---

### P2-H04 — Pending Results Panel

**Narrative.** The Pending Results panel renders the diegetic countdowns from `state.visible_timers`. Each item shows what was ordered, an approximate remaining time (intentionally imprecise — "~30 min" not "27 min" — to preserve uncertainty), and clears when the result arrives and the corresponding node reveals. Consult ETAs, lab turnaround, imaging queues all live here. This is the only place in the UI (apart from emergencies) where a clock is shown.

**Dependencies.** P2-H01 (visible_timers), P2-H02 (panel exists).

**In scope.** Countdown rendering with intentional approximation; per-item label; auto-removal when the corresponding node reveals; empty state.

**Out of scope.** Hidden (non-diegetic) timer rendering. Anything resembling the deterioration clock — that stays hidden by design.

**Decisions this ho resolves.**
- *Approximation strategy.* Recommended: round to nearest 5 minutes for values >10, nearest 1 minute below.
- *How a result transitioning into "ready" is presented.* Recommended: brief highlight + auto-removal once the corresponding node card appears in Active Concerns.

---

### P2-H05 — Emergency Mode

**Narrative.** When a crisis node fires, the dashboard visibly takes over. The screen enters emergency rendering: red border, locked investigation actions visibly disabled (with the lock reason as a tooltip or inline note), only emergency-relevant actions surfaced in the action bar, and the triggering timer becomes visible — the one circumstance where a non-diegetic timer is shown, because the emergency itself is visible to the character. The narrative feed gets a dedicated emergency event style. When the emergency resolves (via successful intervention or case end), the dashboard returns to normal rendering.

**Dependencies.** P2-H01 (visible_timers exists; emergency timer surfaces through the same channel), P2-H02 (dashboard exists), P2-H04 (countdowns render).

**In scope.** Engine: derive `emergency_active: bool` on `GameState` from the appropriate signal; expose through API. Frontend: emergency rendering mode triggered by `state.emergency_active`; locked-action presentation; emergency event styling in the narrative feed.

**Out of scope.** Audio cues (Phase 6). Multiple concurrent emergencies (the schema allows it but the example case doesn't author it; Phase 2 handles one at a time and notes the limitation).

**Decisions this ho resolves.**
- *Emergency state representation.* Recommended: a derived `GameState.emergency_active: bool` computed from a reserved flag pattern (`crisis_active:*` flags), so cases declare it via flag effects rather than a new schema field. Backward-compatible.
- *Locked-action presentation.* Recommended: visible but greyed out with a reason; don't hide them — the player should see what they *can't* do during a crisis.
- *Whether the emergency timer can be made approximate or must show exact remaining time.* Recommended: exact (this is the one place precision serves the design — the player is racing it).

---

### P2-H06 — Wait Action UI

**Narrative.** The wait/observe action becomes a visible, first-class control in the action bar. It sits alongside the clinical categories and offers durations as subactions. Choosing wait advances the clock without other clinical effects, lets timers tick, lets pending results arrive, and lets the patient's hidden deterioration play out. The narrative feed describes what happens during the wait (anything that triggers during the elapsed time is narrated).

**Dependencies.** P2-H01 (engine wait action), P2-H02 (action bar exists), P2-H05 (so wait correctly disables during emergencies along with other investigation actions).

**In scope.** Action bar wait button with duration menu; correct disabling during emergencies; narrative-feed treatment of elapsed-time events.

**Out of scope.** Adaptive duration suggestions ("you usually have ~30 min before the next result"). The player picks from the fixed set.

**Decisions this ho resolves.**
- *Visual prominence.* Recommended: same visual weight as other action categories — wait is not punished or hidden; it's a legitimate clinical choice.
- *Whether wait is disabled during emergencies.* Recommended: yes — you cannot watch the clock while the patient is seizing.

---

### P2-H07 — Diagnostic Rigor Scoring

**Narrative.** Without changing the engine, extend the Maria Santos case so the outcome evaluation rewards diagnostic confirmation before treatment commitment. The player who orders an MRI and confirms a ring-enhancing lesion before committing to albendazole earns a higher tier than one who treats correctly but on suspicion alone. This is the entire diagnosis-commitment design — no new mechanic, just authoring outcome rules that score the reasoning the engine can already detect via flags.

**Dependencies.** Phase 1 outcome system; no engine work expected.

**In scope.** Add `confirmed_diagnosis_*` flags to the appropriate node effects in the case (set when imaging confirms the lesion, etc.); update outcome rules to check them; ensure the tier separation is visible in the outcome screen.

**Out of scope.** Engine changes. New schema fields. Other cases (one case is the test bed).

**Decisions this ho resolves.**
- *Granularity of "rigor" scoring.* Recommended: binary per-tier modifier — "Optimal" requires diagnostic confirmation; "Good" allows correct-by-suspicion; everything else unchanged.
- *Whether to surface the rigor distinction in the debrief.* Phase 2 outcome screen displays the achieved tier and reason; full debrief explanation is Phase 5. Decided: yes, surface the reason at tier-explain level only.

---

### P2-H08 — Real LLM Narrator

**Narrative.** Replace `MockNarrator` with a live narrator using the `Narrator` interface already defined in `llm-client`. This is the largest ho in the phase by code volume and by design weight — it is the layer that turns a working sim into the felt experience. The work spans three concerns: provider implementation (a concrete `Narrator` against OpenAI or Anthropic), prompt engineering tuned to the *Grey's Anatomy* register, and operational plumbing (env-var provider selection in `satori-api`, per-session narration cache to avoid re-calling for identical events, graceful fallback to a templated string if the LLM is unavailable or times out so the game keeps running). The boundary holds: the narrator returns text only, never state changes.

**Dependencies.** P2-H02 (narrative feed exists), P2-H03 (concerns panel exists for non-narrative content), P2-H05 (emergency events have distinct narration needs).

**In scope.** One provider's `Narrator` implementation; prompt template covering the existing 12 event types with case-context injection; narration cache keyed by `(event_type, node_id, session_id)`; env-var wiring; fallback path; tests including a smoke test against the real provider behind a marker.

**Out of scope.** Tuning the voice across many cases (only one case exists). Multi-provider auto-failover. Streaming responses (Phase 3+).

**Decisions this ho resolves.**
- *Narrator provider.* Open. Decided in this ho. Recommended: Anthropic — the practitioner's default LLM provider for narrative work; the project's `llm-client` already has Anthropic case generation as a sibling implementation.
- *Cache strategy.* Open. Recommended: per-session in-memory dict keyed by `(event_type, node_id)`. Avoids re-calling for the same revealed node mid-session. No cross-session cache in Phase 2.
- *Prompt strategy.* Open. Recommended: one base system prompt establishing voice and constraints; per-event-type user prompt templates assembled from `NarrationEvent` + `NarrationContext`. Document the templates so Phase 3+ tuning is grounded.
- *Fallback behaviour.* Open. Recommended: on timeout or provider error, render a short, neutral templated string (e.g. `"<event description>"`) and log the failure; the game keeps running.

---

## Other Deferred Decisions

None at the Phase level beyond what is rendered inline above. Deferred *features* (cases beyond Maria, teaching depth, hosting, mobile, F-002/003/005/006/007) are catalogued in the System Design and in `future-features.md`; they are not Phase 2 decisions and do not need representation here.

---

## How to Use This Document

When opening a Phase 2 ho, the practitioner reads the relevant section here, then writes the per-ho document under `hos/P2-H##-<slug>.md` using the project's existing Ri-compressed format (K5 framing + dandori execution in one file). The per-ho document inherits the in-scope / out-of-scope bounds from this document and adds the implementation-level acceptance criteria, verification gates, and commit format. If a ho needs to decompose into multiple agent tasks, they live under `agent-tasks/` as `Ho-NN-AT-MM.md`.

The phase ships as `v0.7` when all eight hos are complete and Maria Santos plays end-to-end on the new dashboard with live narration.
