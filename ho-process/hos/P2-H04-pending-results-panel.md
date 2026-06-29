# P2-H04: Pending Results Panel

**Status:** READY (depends on P2-H01 and P2-H02 being complete)
**Phase:** 2
**Ho:** 04
**Depends on:** P2-H01 (`visible_timers` exists), P2-H02 (dashboard panel shells exist)

---

## Objective

Implement the Pending Results panel in the mission-control dashboard. The panel renders `state.visible_timers` (already exposed by P2-H01) as countdown items the player can read at a glance. Each item shows what was ordered, an intentionally-approximate remaining time ("~30 min" not "27 min"), and disappears when the corresponding result arrives.

This is the only place in the UI — apart from emergencies (P2-H05) — where a clock is shown to the player. Deterioration timers are hidden by design and stay hidden.

---

## Context

P2-H01 added `visible_timers` to `GameState`: a sorted tuple of `VisibleTimer` records, each with `label`, `remaining_minutes`, `source` (`"pending_reveal"` or `"active_timer"`), and `node_id`. The API serialises this as `visible_timers: VisibleTimerResponse[]` on `GameStateResponse`.

P2-H02 created the dashboard skeleton with a `PendingResultsPanel.svelte` component shell. This ho fills that shell with real content.

---

## Design Decisions

### Approximation strategy

Round remaining minutes for display:
- `remaining_minutes > 10` → round to nearest 5 (e.g., 27 → "~25 min", 23 → "~25 min")
- `remaining_minutes <= 10` → round to nearest 1 (e.g., 7 → "~7 min", 3 → "~3 min")

The exact value is in the data; only the display approximates. This preserves a small uncertainty about exactly when the result will arrive while still being honest about scale.

### Visual treatment

Each item is a card with:
- The label (from `VisibleTimer.label`)
- The approximate remaining time, prefixed with a clock glyph or "~" sign
- A subtle visual hint of the source (`pending_reveal` items might be subtly distinct from `active_timer` items — e.g., a different icon — but they share the same card shape)

Items are listed in the order the engine already provides (sorted by `remaining_minutes` ascending then `node_id`). Don't re-sort in the frontend; trust the engine's order.

When a result transitions to "ready" (it leaves `visible_timers` because the corresponding node reveals), the item disappears from the panel and the corresponding card appears in Active Concerns (P2-H03). Don't animate the handoff in this ho — it's enough that the panel updates correctly.

### Empty state

When `visible_timers` is empty, the panel shows a brief "No pending results" placeholder. Visual weight is minimal — don't draw the player's eye to nothing.

### "Consults" sub-grouping

The pitch's dashboard mockup shows "Pending Results" and "Consults" as distinct sub-sections of the right column. In the current Phase 1 case (Maria Santos), consults exist as nodes (e.g., neurology) but they're modeled as pending reveals with longer delays — not architecturally distinct from labs/imaging. For this ho, **do not** add a separate consults section. Render all `visible_timers` in one list. If the project later wants visual separation, a `category` field can be added to `VisibleTimer` in a future ho.

---

## Deliverables

### 1. `packages/internal-affairs/src/lib/components/PendingResultsPanel.svelte`

Replace the shell content from P2-H02 with the real rendering:

```svelte
<script lang="ts">
  import type { VisibleTimer } from '$lib/types';

  let { timers }: { timers: VisibleTimer[] } = $props();

  function formatRemaining(minutes: number): string {
    if (minutes > 10) {
      const rounded = Math.round(minutes / 5) * 5;
      return `~${rounded} min`;
    }
    return `~${minutes} min`;
  }
</script>

<section class="pending-results-panel">
  <h3 class="panel-title">Pending Results</h3>

  {#if timers.length === 0}
    <div class="empty-state">No pending results</div>
  {:else}
    <ul class="results-list">
      {#each timers as timer (timer.node_id)}
        <li class="result-item">
          <span class="label">{timer.label}</span>
          <span class="remaining">{formatRemaining(timer.remaining_minutes)}</span>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  /* match the project's existing Tailwind/CSS conventions for cards */
</style>
```

Match the visual conventions established by P2-H02 (color palette, spacing scale, typography). If P2-H02 introduced shared styling tokens, reuse them. If not, keep the styles local and minimal.

### 2. Type: `packages/internal-affairs/src/lib/types.ts`

Add the `VisibleTimer` TypeScript interface mirroring the API response:

```ts
export interface VisibleTimer {
  label: string;
  remaining_minutes: number;
  source: 'pending_reveal' | 'active_timer';
  node_id: string;
}
```

If P2-H02 already added this, skip. Otherwise add it here.

### 3. Game store: `packages/internal-affairs/src/lib/stores/gameStore.svelte.ts`

Surface `visible_timers` from the latest game state response so the panel can read it via store. Likely already done in P2-H02 as part of the dashboard wiring; this ho only fills the consumer.

If not done in P2-H02, add a derived field or expose it directly: `visibleTimers: VisibleTimer[]`.

### 4. Wire the panel in the dashboard

In `+page.svelte` (or wherever P2-H02 places the panel), pass the store's `visibleTimers` into `<PendingResultsPanel timers={...} />`.

---

## Tests

### Frontend type-check

`npm run check` — must remain clean.

### Smoke test of the rendering

A visual smoke test (no automated test required for Phase 2 frontend, per the project's existing Phase 1 conventions):

1. Start a fresh session with the Maria Santos case
2. Confirm the panel shows "No pending results"
3. Order `order_labs:cbc` — confirm a card appears with "CBC" (or whatever the node's `display_name` is) and an approximate countdown
4. Order `order_imaging:ct_head` — confirm two cards appear, ordered by remaining time
5. Use the wait action (P2-H06) or take other actions until the CBC results arrive — confirm the CBC card disappears from this panel and a finding appears in Active Concerns

(If P2-H03 isn't done when this ho runs, skip step 5's Active Concerns verification — just confirm the panel updates.)

---

## Acceptance Criteria

1. `cd packages/internal-affairs && npm run check` is clean.
2. The dashboard renders with the Pending Results panel populated correctly when timers exist and empty-stated when they don't.
3. Approximation logic produces the expected strings for boundary values (test `formatRemaining(0)`, `(3)`, `(10)`, `(11)`, `(13)`, `(27)`, `(60)` mentally or with a small inline test).
4. The panel doesn't re-sort the timers; it trusts the API's order.
5. No backend changes were made (this is a pure frontend ho).

---

## Out of Scope

- Emergency-state styling on this panel (P2-H05)
- Active Concerns panel content (P2-H03)
- Visual handoff animation when a result becomes ready
- Separating consults from labs/imaging visually
- Adding new fields to `VisibleTimer` (any data model change would have to come back through the engine and API)
- Player annotations or interactions with pending items

If a backend change would be needed, **stop and escalate** — this is a frontend-only ho by design.

---

## Verification Stack

1. `cd packages/internal-affairs && npm run check`
2. `cd packages/internal-affairs && npm run lint` (if the project has a lint command)
3. Manual smoke test in dev (run `npm run dev` and exercise the panel as above)
4. `git status` — only `packages/internal-affairs/` files should be modified

---

## Commit Message Template

```
feat(P2-H04): pending results panel — diegetic countdowns rendered

- PendingResultsPanel.svelte: render visible_timers from game state with
  intentionally-approximate countdowns (~5-min rounding above 10, ~1-min
  below)
- Empty state when no timers active
- Trust engine's sort order (remaining_minutes ascending, then node_id)
- types.ts / gameStore wiring filled in (whatever P2-H02 left as TODO)

Only place in the UI besides emergencies where a clock is shown.
Deterioration stays hidden by design.
```
