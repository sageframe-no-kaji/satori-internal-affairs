---
created: 2026-07-03
type: agent-task
status: ready
parent: audit/FABLE-REVIEW-2026-07-03.md
project: satori-internal-affairs
---

# S4 — Ataxia-critical frontend fixes + narrator failure guard

**Goal**

Close the two HIGH Universal Design findings and the one failing contrast token (UD-1, UD-2, CON-1), and isolate narration failure from the gameplay response path (C-5) so P2-H08's live narrator lands on a safe substrate.

**Context**

The player has severe ataxia; the P2-H02 UD constraints (≥60px touch floor, visible focus, WCAG AA) are non-negotiable. The review found the sole case-end control below the floor with no focus indicator, and one token failing AA at the sizes it's used. Separately, `narrate_events` runs outside the API's try/except *after* engine state has committed — a raising live narrator would 500 with the action already applied. H08's spec already commits to templated-string fallback; this task lands the guard early.

**Files**

- Modify: `packages/internal-affairs/src/lib/components/OutcomeScreen.svelte` (UD-1, UD-2)
- Modify: `packages/internal-affairs/src/lib/styles/tokens.css` (CON-1 — locate exact path; tokens.css is the single source)
- Modify: `packages/satori-api/src/satori_api/main.py` and/or `packages/satori-api/src/satori_api/narrator_bridge.py` (C-5)
- Create/Modify: satori-api tests (narration-failure fallback)

**Required Changes**

1. **UD-1:** `.reset-btn` gets `min-height: var(--touch-target-pref)`. Do not otherwise restyle OutcomeScreen — its Phase-1 hex/px debt stays deferred as documented.
2. **UD-2:** add a `:focus-visible` outline to `.reset-btn` consistent with the rings on `.category-trigger`/`.start-btn`.
3. **CON-1:** lighten `--color-text-dim` from `#6b7280` to a value ≥4.5:1 against both `--color-bg-panel` and `--color-bg-app` (review computed ~`#868e9e` reaches ~4.5:1 on panel; verify and pick the final value with contrast math in the commit message). One token change; no component edits.
4. **Narrator guard (C-5):** wrap the narration call so any exception from the narrator degrades to a short neutral templated string per event (the same fallback shape H08 specifies) and logs the failure; the action response returns 200 with correct state regardless of narrator health. Test: a stub narrator that raises → response 200, state advanced, fallback narration strings present.

**Do Not**

- Do not implement UD-3–UD-6 (dropdown focus management, modal trap) — batched into P2-H03 per report §7.
- Do not start any live-provider narrator work — that is P2-H08. The guard is provider-agnostic.
- Do not touch `VitalsStrip` thresholds or other Truth-line smells — separate decision.

**Acceptance**

- [ ] `.reset-btn` computes ≥ the 60px floor (via `--touch-target-pref`) and shows a visible focus ring on keyboard focus.
- [ ] New `--color-text-dim` value documented ≥4.5:1 on both backgrounds.
- [ ] `npm run check` clean.
- [ ] Narration-failure test passes: raising narrator → 200, advanced state, fallback strings; existing satori-api suite passes.
- [ ] ruff/mypy/pre-commit clean.

**Verification**

```bash
cd packages/internal-affairs && npm run check
pytest packages/satori-api -q
pre-commit run --all-files
```

**Commit**

Two commits:

```
fix(a11y): outcome button touch target + focus ring; text-dim token to AA (audit UD-1/UD-2/CON-1)
fix(api): isolate narrator failure from gameplay response — templated fallback (audit C-5)
```
