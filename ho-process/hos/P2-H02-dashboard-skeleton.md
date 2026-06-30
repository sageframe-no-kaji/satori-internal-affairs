# P2-H02: Dashboard Skeleton

**Status:** READY
**Phase:** 2
**Ho:** 02
**Depends on:** P2-H01 (visible_timers available; not used yet but the API field exists)

---

## Objective

Restructure the SvelteKit frontend from Phase 1's single-page-flow layout to the mission-control dashboard committed in the system design. Land the layout grid, the component shells, the data wiring, and a design-token foundation that makes future visual iteration cheap.

**This ho ships the scaffold, not the final visual design.** A full design pass comes later. H02's job is to establish:

- The three-column dashboard grid (Active Concerns | Narrative Feed | Pending Results) with vitals strip above and action bar below
- A small set of shared design tokens (CSS custom properties) that all panels read from
- Component shells for each panel with correct data wiring (panels read from the game store and render placeholder content where the rich per-panel logic lives in H03/H04/H05/H06)
- Universal Design defaults baked into the token system so the dashboard is comfortably usable by a player with motor coordination limits

---

## Context

Phase 1's frontend (P1-H05/H06) used a vertical single-page flow: start screen → patient header → vitals → event log → action menu → outcome screen. It worked but it didn't surface what the engine actually simulates (concurrent timers, parallel pending results, accumulating evidence).

The dashboard layout — from `docs/architecture/game-design-pitch.md` — is the committed Phase 2 surface:

```
┌──────────────────────────────────────────────────────────┐
│  PATIENT HEADER  (identity, chief complaint, triage)     │
├──────────────────────────────────────────────────────────┤
│  VITALS STRIP (always visible, updates every turn)       │
├──────────────┬───────────────────────┬───────────────────┤
│              │                       │                   │
│  ACTIVE      │    NARRATIVE FEED     │   PENDING         │
│  CONCERNS    │  (story / dialogue /  │   RESULTS         │
│  (evidence   │   exam descriptions)  │   (countdowns)    │
│   board)     │                       │                   │
│              │                       │                   │
├──────────────┴───────────────────────┴───────────────────┤
│  ACTION BAR  [grouped, dropdown subcategories]           │
│              [Wait/Observe]              Clock: T+75     │
└──────────────────────────────────────────────────────────┘
```

The OutcomeScreen overlays this when the case ends; the dashboard remains visible underneath.

---

## Design Decisions

### Design tokens — the foundation

Create a small `tokens.css` (or similar — match the project's CSS conventions, but if there are none yet, put it in `src/app.css` or `src/lib/styles/tokens.css`). Define every value the dashboard uses as a CSS custom property. The tokens listed below are the **complete starting set** — add only if a value is genuinely shared.

```css
:root {
  /* Colors — clinical hospital palette, restrained */
  --color-bg-app:        #0e1218;   /* page background, near-black */
  --color-bg-panel:      #161b24;   /* panel background */
  --color-bg-panel-alt:  #1c2230;   /* alternating row / hover */
  --color-border:        #2a3142;   /* default panel border */
  --color-border-strong: #3d4458;   /* emphasised border */

  --color-text:          #e8ecf2;   /* default text */
  --color-text-muted:    #a0a8b8;   /* secondary text */
  --color-text-dim:      #6b7280;   /* tertiary / placeholder */

  /* State colors — used sparingly, only when something IS in that state */
  --color-state-normal:   #5ec585;   /* green — vitals in range */
  --color-state-warning:  #e0a83a;   /* amber — vitals trending */
  --color-state-critical: #d65555;   /* red — vitals out of range, emergencies */
  --color-state-info:     #6ba3d6;   /* blue — neutral state info */

  /* Accent — interactive elements */
  --color-accent:         #7ab0ff;   /* default interactive */
  --color-accent-hover:   #a6c8ff;
  --color-accent-active:  #c5dbff;

  /* Spacing — generous defaults for Universal Design */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  /* Typography — large base for readability */
  --font-size-sm:   16px;
  --font-size-base: 18px;
  --font-size-lg:   22px;
  --font-size-xl:   28px;
  --font-size-2xl:  36px;
  --line-height:    1.55;
  --font-stack:     'Inter', system-ui, -apple-system, sans-serif;

  /* Interactive sizing — Universal Design floor */
  --touch-target-min:    60px;   /* minimum hit-target size (well above 44px WCAG floor) */
  --touch-target-pref:   72px;   /* preferred button height */
  --touch-target-gap:    var(--space-4);   /* minimum spacing between hit targets */

  /* Layout */
  --radius-sm: 4px;
  --radius:    8px;
  --radius-lg: 12px;
  --shadow-panel: 0 2px 8px rgba(0, 0, 0, 0.25);
  --border-width: 1px;
}
```

Every component reads from these tokens. No hex codes, no magic numbers in component styles.

**Why this is load-bearing:** the practitioner will run a full design pass later and wants to tweak this all out. Tokens make that a one-file change instead of a global find-replace.

### Universal Design — baked in

The player has motor coordination limits (ataxia). The design must not require precision. Concretely:

- **Touch targets ≥ 60px tall.** Apply `min-height: var(--touch-target-pref)` to all buttons. Action bar buttons get `var(--touch-target-pref)` (72px) since they're the primary interactions.
- **Gap between interactive elements ≥ `--space-4` (16px).** No clusters of small adjacent buttons that risk mis-clicks.
- **Base font size 18px.** Default body text is large enough to read at arm's length without leaning in.
- **No hover-only behaviors.** Anything that appears on `:hover` must also appear on `:focus` and on touch. Use `:focus-visible` rings on all interactive elements.
- **Keyboard navigation works end-to-end.** Tab through actions, Enter to activate, Esc to close dropdowns. Don't rely on click-only interactions.
- **High contrast.** WCAG AA minimum (4.5:1) for body text, 3:1 for large text and UI components. The clinical palette is naturally high-contrast — verify visually.

### Component decomposition

Build these as separate Svelte 5 components under `src/lib/components/`:

- `VitalsStrip.svelte` (replaces the existing `VitalsPanel.svelte` — keep `VitalsPanel.svelte` for now but the dashboard uses `VitalsStrip`; remove `VitalsPanel.svelte` if it's no longer referenced)
- `ActiveConcernsPanel.svelte` (shell — H03 fills it)
- `NarrativeFeedPanel.svelte` (replaces the existing `EventLog.svelte` — same handling)
- `PendingResultsPanel.svelte` (shell — H04 fills it)
- `ActionBar.svelte` (replaces the existing `ActionMenu.svelte` — same handling)
- `CategoryDropdown.svelte` (subcomponent used by `ActionBar` for each category — Order Labs ▾, History ▾, etc. The Wait/Observe category will use this same component in H06.)

`PatientHeader.svelte` is kept as-is and sits above the vitals strip.

The shells render the panel's chrome (title, borders, empty state) and accept props for the data they'll show. The per-panel logic (rendering findings as cards, rendering countdowns) lives in the H03/H04 ho documents.

### Layout grid

Use CSS Grid for the main dashboard layout. The three-column body is a `grid-template-columns: 1fr 2fr 1fr` (narrative gets twice the width — it's the primary reading surface) with a generous gap. The header strip, vitals strip, and action bar each span the full width.

The dashboard is responsive in a basic way: below ~1100px wide, columns stack vertically. Mobile polish is Phase 6; H02 only does the desktop-first layout plus graceful collapse.

```css
.dashboard {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  grid-template-areas:
    "header"
    "vitals"
    "body"
    "actions";
  min-height: 100vh;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-app);
}

.dashboard-body {
  grid-area: body;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: var(--space-4);
  min-height: 0;   /* allow children to scroll */
}

@media (max-width: 1100px) {
  .dashboard-body { grid-template-columns: 1fr; }
}
```

### Existing components that go

After H02 is in place:
- `VitalsPanel.svelte` → replaced by `VitalsStrip.svelte`
- `EventLog.svelte` → replaced by `NarrativeFeedPanel.svelte`
- `ActionMenu.svelte` → replaced by `ActionBar.svelte` + `CategoryDropdown.svelte`

Delete the replaced ones. The current `+page.svelte` flow (start → play → outcome) is restructured: start screen still exists; play view IS the dashboard; outcome screen overlays the dashboard when `case_ended`.

The `OutcomeScreen.svelte` keeps its current behavior plus the H07 narrative rendering already in place. It overlays the dashboard via fixed positioning rather than replacing it — the player can see the world they ended in.

---

## Deliverables

### 1. `packages/internal-affairs/src/lib/styles/tokens.css` (new)

Contains the full token set above. Imported at the app root (in `src/routes/+layout.svelte` or `src/app.css`, whichever the project uses for global styles).

### 2. `packages/internal-affairs/src/lib/components/VitalsStrip.svelte` (new, replaces VitalsPanel)

Horizontal strip showing all five vitals (HR, BP, Temp, RR, O₂ Sat) in a single row. Each vital is a labelled cell with the value, the unit, and a state indicator (color from `--color-state-*` tokens). The state indicator is what makes a critical vital read as critical — color is the only signal, no motion.

Behavior is the same as Phase 1's VitalsPanel (read from game state, color by threshold). Visual treatment is the new layout: horizontal strip, not vertical card.

### 3. `packages/internal-affairs/src/lib/components/ActiveConcernsPanel.svelte` (new shell)

Renders the panel chrome (title "Active Concerns", border, scroll container) and an empty state ("No findings yet"). Accepts a `findings` prop that's not yet populated — H03 fills the actual rendering. For H02, pass `[]` from the game store and render the empty state.

### 4. `packages/internal-affairs/src/lib/components/NarrativeFeedPanel.svelte` (new, replaces EventLog)

Renders the panel chrome (title "Narrative", border, scroll container) and the event log entries. This panel is the primary reading surface. Accept the event log array from the game store (already in the store from Phase 1). Render entries in reverse-chronological order (newest at top) with each entry as a paragraph block. Match the visual treatment to the clinical aesthetic: muted background, generous line-height, comfortable reading font size.

### 5. `packages/internal-affairs/src/lib/components/PendingResultsPanel.svelte` (new shell)

Renders the panel chrome (title "Pending Results", border) and an empty state ("No pending results"). Accepts a `timers` prop typed as `VisibleTimer[]`. For H02, pass `[]` — H04 wires the real data.

### 6. `packages/internal-affairs/src/lib/components/ActionBar.svelte` (new, replaces ActionMenu)

Bottom bar. Composes `CategoryDropdown.svelte` for each action category. Categories are derived from the `playable_actions` array by grouping on the base key (same grouping logic as Phase 1's `ActionMenu`, preserved). Each `CategoryDropdown` represents one category. The action bar also shows the current game clock on the right ("Clock: T+75 min").

The Wait/Observe category is **not added in this ho** — that's H06. H02 leaves a comment / TODO marker where it will go.

### 7. `packages/internal-affairs/src/lib/components/CategoryDropdown.svelte` (new subcomponent)

A single category button that expands to show its subcategory options.

- Closed state: shows the category label + a "▾" affordance.
- Open state: shows the category label + a list of selectable subcategories below.
- Click/Enter on the category toggles open/closed. Esc closes.
- Click/Enter on a subcategory submits the action and closes the dropdown.
- Focus moves to the first subcategory option when opened.
- All interactive elements meet the touch-target minimum (`var(--touch-target-pref)`).

Props: `categoryLabel: string`, `actions: Array<{ key: string; label: string }>`, `disabled?: boolean`, `disabledReason?: string`, `onAction: (key: string) => void`.

### 8. `packages/internal-affairs/src/routes/+page.svelte` (restructured)

Three views: start, play (= dashboard), outcome (overlay). Same view-state logic as Phase 1; the structural difference is that the play view renders the dashboard composition instead of the linear flow.

Sketch:

```svelte
<script lang="ts">
  import { gameStore } from '$lib/stores/gameStore.svelte';
  import PatientHeader from '$lib/components/PatientHeader.svelte';
  import VitalsStrip from '$lib/components/VitalsStrip.svelte';
  import ActiveConcernsPanel from '$lib/components/ActiveConcernsPanel.svelte';
  import NarrativeFeedPanel from '$lib/components/NarrativeFeedPanel.svelte';
  import PendingResultsPanel from '$lib/components/PendingResultsPanel.svelte';
  import ActionBar from '$lib/components/ActionBar.svelte';
  import OutcomeScreen from '$lib/components/OutcomeScreen.svelte';
  // start screen logic unchanged
</script>

{#if view === 'start'}
  <!-- existing start view -->
{:else if view === 'play' || view === 'outcome'}
  <main class="dashboard">
    <div class="header"><PatientHeader {...patientProps} /></div>
    <div class="vitals"><VitalsStrip {...vitalsProps} /></div>
    <div class="body">
      <ActiveConcernsPanel findings={[]} />
      <NarrativeFeedPanel events={gameStore.eventLog} />
      <PendingResultsPanel timers={[]} />
    </div>
    <div class="actions"><ActionBar actions={gameStore.availableActions} /></div>
  </main>
  {#if view === 'outcome'}
    <OutcomeScreen {...outcomeProps} />
  {/if}
{/if}
```

### 9. Delete replaced components

After verifying nothing references them:
- `packages/internal-affairs/src/lib/components/VitalsPanel.svelte`
- `packages/internal-affairs/src/lib/components/EventLog.svelte`
- `packages/internal-affairs/src/lib/components/ActionMenu.svelte`

### 10. Update `index.ts` barrel if it exports any of the deleted components

---

## Tests

This is a frontend-only ho. The project's existing Phase 1 frontend convention is `npm run check` (svelte-check) as the test gate; no Svelte unit tests exist yet. Don't add a test framework in this ho.

**Manual smoke checks:**

1. `npm run dev` — start the dev server, confirm the dashboard renders without console errors.
2. Start a fresh session with Maria Santos. Confirm:
   - Patient header shows demographics
   - Vitals strip shows all five vitals with color states
   - Active Concerns panel shows "No findings yet"
   - Narrative Feed shows the initial events
   - Pending Results shows "No pending results"
   - Action Bar shows categories with subcategory dropdowns
3. Click an action category, confirm it expands; click an action, confirm it submits and the dropdown closes.
4. Tab through the action bar with the keyboard — every interactive element is reachable; focus is visible.
5. Resize the window narrow — columns collapse into a single stack below ~1100px.
6. Run the case to its end (treatment + family + before time limit) — confirm OutcomeScreen overlays the dashboard.

**Type-check:** `cd packages/internal-affairs && npm run check` must remain clean.

---

## Acceptance Criteria

1. `npm run check` clean.
2. The dashboard renders with the layout above.
3. All interactive elements meet the touch-target minimum (visible-verify: buttons feel large; spec-verify: computed `min-height` is ≥ 60px in dev tools).
4. All color values in component styles reference `--color-*` tokens. Grep `packages/internal-affairs/src/lib/components` for `#` — should match only token definitions, not component-local hex codes.
5. All spacing values in component styles reference `--space-*` tokens. Same grep discipline.
6. Existing case flow (start → play through Maria Santos → outcome) works as before, plus all the new layout.
7. The replaced components (`VitalsPanel.svelte`, `EventLog.svelte`, `ActionMenu.svelte`) are deleted and nothing references them.

---

## Out of Scope

- Per-panel content logic (H03 = Active Concerns, H04 = Pending Results)
- Emergency mode visual treatment (H05)
- Wait/Observe action in the action bar (H06)
- Real LLM narration in the Narrative Feed (H08)
- Full design pass (later — H02 ships a clinical-baseline scaffold designed to be tweaked)
- Mobile-specific polish (Phase 6; H02 does graceful collapse only)
- Animation, motion, transitions beyond simple `:hover`/`:focus` states
- Theme switching (light mode, custom palettes — Phase 6+)
- Backend changes — this ho is pure frontend

If you encounter a structural problem that requires backend changes, **stop and escalate** — engine and API are P2-H01 territory.

---

## Verification Stack

1. `cd packages/internal-affairs && npm run check`
2. `cd packages/internal-affairs && npm run lint` (if the script exists)
3. Manual smoke checks (steps 1–6 above) — `npm run dev` and click through Maria Santos
4. Grep discipline: no hex codes or magic numbers outside `tokens.css` (`grep -rE "#[0-9a-fA-F]{3,6}|^\s*\d+px" packages/internal-affairs/src/lib/components | grep -v tokens.css`)
5. `git status` — only `packages/internal-affairs/` files modified

---

## Commit Message Template

```
feat(P2-H02): dashboard skeleton — mission-control layout + design tokens

- Layout: three-column dashboard grid (Active Concerns | Narrative Feed |
  Pending Results) with patient header, vitals strip, action bar.
  Collapses to single column below 1100px.
- Tokens: src/lib/styles/tokens.css — colors (clinical palette), spacing,
  typography, touch-target sizing. Every component reads from tokens;
  no hex codes or magic numbers in component styles.
- Universal Design baked in: 60px+ touch targets, 16px gaps between
  interactive elements, 18px base font, keyboard navigation, no
  hover-only behaviors, high-contrast palette.
- New components: VitalsStrip, ActiveConcernsPanel (shell — H03 fills),
  NarrativeFeedPanel, PendingResultsPanel (shell — H04 fills), ActionBar,
  CategoryDropdown.
- Replaced and deleted: VitalsPanel, EventLog, ActionMenu.
- OutcomeScreen overlays the dashboard at case end (preserving H07
  narrative rendering).

Scaffold only — full design pass comes later. Tokens make tweaks cheap.
```
