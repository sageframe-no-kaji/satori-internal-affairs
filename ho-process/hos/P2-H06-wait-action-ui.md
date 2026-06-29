# P2-H06: Wait Action UI

**Status:** READY (depends on P2-H01, P2-H02, P2-H05)
**Phase:** 2
**Ho:** 06
**Depends on:** P2-H01 (engine wait action), P2-H02 (action bar exists), P2-H05 (emergency mode locks investigation actions; wait is locked alongside them)

---

## Objective

Add the wait/observe action to the dashboard's action bar as a visible, first-class control. Players choose a duration (15 / 30 / 60 minutes) and the game advances by that much without any clinical effect. The action is disabled during emergencies.

This makes the engine's built-in `wait:N` action (from P2-H01) reachable from the UI.

---

## Context

P2-H01 added the engine's wait handling: `wait:15`, `wait:30`, `wait:60` advance the clock by their respective durations, run the standard tick (timers, pending reveals, vitals), and emit a `Waited` event. The engine accepts these regardless of `state.available_actions`.

P2-H02 created the action bar (`ActionBar.svelte`) with grouped category dropdowns for clinical actions. P2-H05 added emergency-mode rendering, which locks investigation actions visibly.

This ho adds wait to the action bar — sibling to (not nested inside) the clinical categories.

---

## Design Decisions

### Visual prominence

Same visual weight as other action categories. Wait is a legitimate clinical choice — not punished, not hidden. It's a category-level entry in the action bar, not buried in a sub-menu.

### Duration picker

The user picks the duration when choosing wait. Options:

- **A. Dropdown:** Click "Wait/Observe" → menu opens with "15 min / 30 min / 60 min" → click sends `wait:N`. Matches the pattern used by other categorised actions (e.g. `order_labs` → dropdown with `cbc`, `metabolic_panel`).
- **B. Three buttons:** Three sibling buttons in the action bar — "Wait 15", "Wait 30", "Wait 60". Faster but takes more horizontal space.

**Decision: A (dropdown).** Matches the existing action-category pattern from P2-H02. The three durations live in a small inline menu under the Wait button.

### Emergency lock

During emergency mode (P2-H05), wait is locked alongside investigation actions. The reason: you cannot watch the clock while the patient is seizing. Visually it appears greyed out with the same locked-action treatment P2-H05 establishes, with a tooltip / inline note indicating it's locked because of the active emergency.

### Naming

Label the action category "Wait / Observe" in the UI. Internally it submits `wait:N`. The dual word "wait/observe" frames it as a clinical decision (observing the patient over time) not as a meta button (skipping turns).

### Narration

When the wait completes, any events that fired during the elapsed interval narrate normally (handled by P2-H08's real narrator; pre-narrator, the MockNarrator handles it adequately). The wait itself produces a brief narration like "30 minutes pass." — this comes from narrating the `Waited` event added in P2-H01. For this ho, if no narration is happening yet for `Waited`, the existing event log can render a plain "30 minutes pass" line directly from the event data.

---

## Deliverables

### 1. `ActionBar.svelte` (or a new sibling component)

Add a Wait / Observe category alongside the existing clinical-action categories. Inside the category, render three menu entries for the three durations.

Match whatever component pattern P2-H02 established. If P2-H02 uses a `CategoryDropdown` subcomponent, instantiate it for wait with `[{key: "wait:15", label: "15 minutes"}, {key: "wait:30", label: "30 minutes"}, {key: "wait:60", label: "60 minutes"}]` and label the category "Wait / Observe".

```svelte
<!-- conceptual sketch; match the actual pattern -->
<CategoryDropdown
  categoryLabel="Wait / Observe"
  actions={[
    { key: 'wait:15', label: '15 minutes' },
    { key: 'wait:30', label: '30 minutes' },
    { key: 'wait:60', label: '60 minutes' },
  ]}
  disabled={emergencyActive}
  disabledReason="Emergency in progress"
  onAction={submitAction}
/>
```

The submit handler in the action bar / game store dispatches `executeAction("wait:15")` etc. — same path used by clinical actions. No special path needed.

### 2. Game store / API client

If the action-submit path already handles arbitrary action strings (which it does after P2-H01 + P2-H02), no changes needed. Verify by inspecting the relevant function in `stores/gameStore.svelte.ts` and `lib/api.ts`.

If for some reason the frontend validates actions client-side against `playable_actions`, `available_actions`, or any allow-list — relax that check for `wait:*` strings, since wait is intentionally built-in and not in either list.

### 3. Narration of `Waited` event in the event log

If the existing event log doesn't already render the `Waited` event (P2-H01 added the event type), add a case for it:

```ts
// In whatever event-to-text function the EventLog/NarrativeFeed uses
case 'Waited':
  return `${event.duration_minutes} minutes pass.`;
```

If P2-H08 has already shipped real narration that handles `Waited`, defer to that instead. For pre-P2-H08, the templated string above is fine.

### 4. Emergency lock

Use the same `state.emergency_active` signal (from P2-H05) that locks other investigation actions. Pass the disabled flag into the wait category dropdown.

If P2-H05 established a shared lock-rendering pattern (e.g., a CSS class, a wrapper component, a prop on the action bar's child components), apply it here. Don't reinvent.

---

## Tests

### Engine

No engine changes in this ho. The engine's wait handling was tested in P2-H01.

### Frontend type-check

`npm run check` — must remain clean.

### Smoke test

1. Start a fresh session with Maria Santos
2. Confirm Wait / Observe appears in the action bar with the three duration choices
3. Click Wait → 30 minutes → confirm:
   - Game clock advances 30 minutes
   - Event log shows "30 minutes pass."
   - Any pending result that was due in <30 min now appears as a finding in Active Concerns
   - Vitals may have changed (deterioration progressed)
4. Trigger an emergency (e.g., let the seizure timer fire) → confirm:
   - Wait / Observe is visibly disabled
   - Hovering or focusing shows the "Emergency in progress" reason
   - Clicking it does nothing (or shows a brief visible cue)
5. After emergency resolves → confirm wait is re-enabled

---

## Acceptance Criteria

1. `cd packages/internal-affairs && npm run check` is clean.
2. Wait / Observe category appears in the action bar, with three duration choices.
3. Choosing a duration submits `wait:N` to the API and advances the game correctly.
4. Wait is locked during emergencies using the same pattern P2-H05 established.
5. The event log narrates the elapsed time ("N minutes pass.") for the `Waited` event.
6. No backend changes were made (engine-side wait was complete in P2-H01).

---

## Out of Scope

- New wait durations beyond 15/30/60 (engine doesn't accept them; would require a P2-H01 amendment)
- Adaptive duration suggestions ("the CBC is due in 30 min — wait until then?")
- A free-form duration picker
- Animating the clock advance
- Narration tone tuning for the Waited event (P2-H08's narrator work)
- Anything backend

If the action submit path doesn't accept `wait:*` cleanly for any reason, **stop and escalate** — the wait engine work landed in P2-H01 and should already accept these strings.

---

## Verification Stack

1. `cd packages/internal-affairs && npm run check`
2. `cd packages/internal-affairs && npm run lint` (if applicable)
3. Manual smoke test (run `npm run dev`, follow the smoke test steps above)
4. `git status` — only `packages/internal-affairs/` files modified

---

## Commit Message Template

```
feat(P2-H06): wait/observe action in the action bar

- ActionBar: Wait / Observe category with 15 / 30 / 60 minute durations
- Submits wait:15, wait:30, wait:60 via the existing action path
- Locked during emergencies via P2-H05's shared disable pattern
- Event log narrates "N minutes pass." for Waited events
- No backend changes (engine handling shipped in P2-H01)
```
