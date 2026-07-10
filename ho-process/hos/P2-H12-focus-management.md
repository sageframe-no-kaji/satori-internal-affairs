# P2-H12: Focus Management — Dropdowns and Outcome Modal

**Status:** IN PROGRESS (autonomous; fully specified by audit UD-4/UD-5/UD-6, no open decisions)
**Phase:** 2 (accessibility debt)
**Ho:** 12
**Depends on:** P2-H11 (fold-up dropdowns, click-off close — this ho builds on that interaction model)

---

## Objective

Keyboard focus behaves like the ARIA patterns the markup already claims. Three audit items, all MEDIUM, all mechanical:

- **UD-4:** opening a dropdown moves focus to its first option (a P2-H02 deliverable, spec'd and never implemented).
- **UD-5:** arrow-key navigation between `role="option"` items; closing returns focus to the trigger instead of dropping it to `<body>`.
- **UD-6:** the outcome overlay declares `aria-modal="true"` but neither moves nor traps focus — an announced modal that isn't one.

## Design (per ARIA listbox/dialog patterns — nothing novel)

**CategoryDropdown:**
- Open (click, Enter, Space, or either arrow key on the trigger) → focus first option.
- ArrowUp/ArrowDown cycle options with wrap; Home/End jump to first/last.
- Enter/Space select; selection and Escape close AND return focus to the trigger.
- Click-off close does NOT steal focus back (the player clicked elsewhere on purpose).
- Focus leaving the component (Tab out) closes the menu.

**OutcomeScreen:**
- The Play Again button — the sole interactive on the overlay — receives focus when the case ends.
- Tab is trapped on it (one focusable element; the trap lives on the button itself, so no synthetic key handling on non-interactive elements).
- No Escape-to-dismiss: dismissing the outcome resets the game, which must stay a deliberate press.

## Out of Scope

- Frontend test framework (no component harness exists; verification is svelte-check + the keyboard script below)
- Any visual change

## Verification

`npm run check`; full Python stack untouched but run per discipline. Manual keyboard script: Tab to a dropdown → Enter (focus lands on first option) → arrows cycle with wrap → Esc (focus back on trigger) → reopen, select with Enter (fires action, focus back on trigger) → click elsewhere (menu closes, focus stays where clicked) → finish a case (focus lands on Play Again; Tab does not escape it).

## Commit Message Template

```
fix(P2-H12): focus management — dropdown listbox keys, outcome focus trap (UD-4/5/6)
```
