# P2-H11: iPad Shell + Clinical Palette

**Status:** DONE — implemented live with the practitioner watching (HMR pass, 2026-07-10); approved "looks great"
**Phase:** 2 (visual quality; practitioner visual-pass feedback, 2026-07-10)
**Ho:** 11
**Depends on:** P2-H05, P2-H03 (their surfaces are what gets re-dressed)

---

## Objective

The dashboard becomes a viewport-locked, iPad-first clinical app: patient header and vitals pinned top, action bar pinned bottom, nothing scrolls except panel contents; and the palette moves from dev-terminal dark to the practitioner-chosen **Option C — light clinical app with a dark monitor inset** (the vitals strip is the one diegetic device on the page).

## Context

First practitioner visual pass (2026-07-10) returned four directives: pin header/vitals top and actions bottom; size for iPad with no page scroll; palette "Grey's Anatomy, not neckbeard"; make it feel like a well-designed iPad app. Palette direction was presented as three rendered HTML mockups (daylight / slate device / light-with-dark-monitor); the practitioner chose C. Also caught in the pass: the vitals strip renders "SPO&SUB2;" (a malformed `&sub2;` entity), and the debug "Raw events" disclosure reads as a desktop-webpage tell.

## Design Decisions

### VISUAL DECISION — palette direction: **DECIDED (practitioner, 2026-07-10): Option C.**
Light clinical chrome (pale cool-grey ground `#eef1f4`, white panels, ink text, scrub-teal interactives) with the vitals strip as a dark monitor inset (`#0d141c`, glowing state colors). Rejected: A (all-light — less character, vitals lose their "device" read), B (still a dark app; the note was that dark-terminal is the wrong register).

### Token strategy
All existing token *names* keep working — values change. Two new scoped groups: `--color-monitor-*` (the dark inset: its own label/unit/state colors, since light-theme state colors fail AA on the dark cell) and `--color-chip-*` (light amber chips — the old `badge-bg-*` tints are now monitor-scoped and would be wrong under cards). The `badge-bg-*` tokens stay dark-valued and are documented as monitor-scoped (the condition badge lives inside the strip). Tier tint borders for the outcome card join as `--color-tint-*`.

All text pairs AA-verified: ink 15.1:1, muted 5.9/5.5, dim 4.9/4.6, teal 5.0/4.6, states 4.6–6.3, chip 5.3, banner white-on-crimson 6.3, monitor label 6.6 / unit 5.3 / green 10.2 / amber 11.3 / red 7.2.

### Legacy hex components tokenized
`PatientHeader` and `OutcomeScreen` predate the token rule and carry hardcoded dark-theme hex; they'd break on any retheme. Both convert fully to tokens in this ho (outcome tiers map to the state tokens: optimal→normal, good→info, partial→warning, failure→critical).

### Viewport lock
`.dashboard` goes `height: 100dvh; overflow: hidden` (was `min-height: 100vh`, which let the page grow and scroll). Panel bodies already scroll internally. Target: iPad landscape (~1180×820); the emergency banner row still enters/leaves without moving the action bar.

### Debug chrome out of the player surface
The narrative feed's "Raw events" disclosure renders only in dev builds (`import.meta.env.DEV`).

### SpO₂
`SpO&sub2;` → the literal `SpO₂` character.

## Deliverables

1. `tokens.css` — Option C values; monitor, chip, tint, fresh-evidence, emergency-hover token groups
2. `VitalsStrip.svelte` — monitor-token restyle; badge colors from monitor group; SpO₂ fix
3. `PatientHeader.svelte`, `OutcomeScreen.svelte` — tokenized, light
4. `+page.svelte` — viewport lock
5. `NarrativeFeedPanel.svelte` — raw-events disclosure opt-in via `VITE_DEBUG_EVENTS` (out of the player surface even in dev)
6. `ActionBar.svelte` — emergency-button hover token (was borrowing a monitor-scoped badge tint)

### Added during the live pass (practitioner-directed, same session)

7. `CategoryDropdown.svelte` — menus fold **up** (the bar is pinned to the viewport bottom; downward menus clipped at the screen edge); closed-state arrow points ▴; click/tap anywhere outside an open menu closes it (which also prevents multiple menus open at once)
8. `ActiveConcernsPanel.svelte` — **windowshade sections**: each category header is a full-width toggle at the 60px floor with the finding count always visible; oversized shade arrow (28px — state must read at arm's length); tightened section spacing to the 16px touch-gap floor
9. `ActiveConcernsPanel.svelte` — **fresh-evidence behavior**: findings arriving on the latest turn tint their card and header light green (`--color-fresh-*`, 5.9:1); other sections auto-shade, the fresh section opens and scrolls to the top of the pane — new evidence is never buried, section order never changes. Self-clearing on the next turn. Deliberate: keyboard focus does NOT move (mid-flow focus theft costs an ataxia player their place in the action bar; during crises focus belongs to the intervention button).

## Out of Scope

- UD-4/5/6 focus work (practitioner declined bundling; still needs its own ho)
- Component behavior changes of any kind — this ho is dress and shell only
- Portrait layout / phone breakpoints (iPad landscape is the target device)

## Verification Stack

Standard full stack (`uv run --no-sync` ruff/mypy/pytest, `npm run check`); contrast table above; practitioner visual pass on the running app (HMR live during the session).

## Commit Message Template

```
feat(P2-H11): iPad shell + clinical palette — light app, dark monitor inset

[completed at commit]
```
