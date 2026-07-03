---
created: 2026-07-03
type: agent-task
status: complete
parent: audit/FABLE-REVIEW-2026-07-03.md
project: satori-internal-affairs
---

# SP — Emergency-mode design reconnaissance (spike, time-boxed ~1h)

**Goal**

Produce a decision memo — `audit/emergency-mode-decision-memo.md` — that gives the practitioner everything needed to make the case-design decisions blocking P2-H05: what a survivable seizure crisis requires, what `crisis_active` flag semantics the `emergency_active` derivation needs, and whether/how the OPTIMAL tier window should widen. **No code or case changes.** This is a read-only exploration whose output feeds a thinking conversation.

**Context**

The review (C-9) found the H05 premise doesn't exist in the case: once `node_14_seizure_crisis` fires, death is unavoidable — `node_17` clears `crisis_active` but doesn't stop node_14's 5-minute death timer, and the `emergency_intervention` action is declared but referenced by nothing. H05's UI ("only emergency-relevant actions surfaced") has no emergency-relevant actions to surface. Separately, OPTIMAL currently requires landing treatment at t=114 against a 120-minute constraint via delay-overlap micro-optimization, and the `family_alienated` penalty flag is inert.

**Files**

- Create: `audit/emergency-mode-decision-memo.md`
- Read-only: `cases/example-neurocysticercosis.json`, `packages/satori/src/satori/` (activation/timer/intervention semantics), `ho-process/ho-overview.md` §P2-H05, `ho-process/satori-internal-affairs-system-design.md`, `schemas/`

**Required Changes**

1. **Survivable-crisis options.** Trace the engine's intervention machinery (`check_interventions`, timer `pause_conditions`, deactivation effects) and lay out 2–3 concrete mechanisms by which `emergency_intervention` during the crisis could avert death (pause node_14's timer, deactivate node_14, timer modification), each with: what case-JSON authoring it needs, whether the current schema expresses it, and what it implies for H05's locked-action design. State plainly if any option requires an engine or schema change (that escalates to the Kamae chain).
2. **`emergency_active` semantics.** H05 recommends deriving `GameState.emergency_active` from reserved `crisis_active:*` flag patterns. Verify against the actual case: node_14 sets `crisis_active`, node_17 clears it. Confirm the derivation works for crisis start, resolution, and death; name edge cases (crisis + case-end same tick; emergency during a wait).
3. **OPTIMAL window analysis.** Present the timeline math (confirmed path lands t=114 vs `before_minutes: 120`) and 2–3 tuning options (widen to 135/150; move the constraint; score rigor without a clock) with the felt-experience tradeoff of each.
4. **`family_alienated`.** One short section: wire it into a tier vs. cut the Diego-leaves timer — the report's position is an inert punishment is worse than none; present both.
5. Every recommendation labeled by decision authority: *case-authoring* (practitioner can decide in a ho) vs *Kamae-chain* (needs a thinking conversation touching the system design).

**Do Not**

- Do not modify any case, engine, schema, or frontend file. Memo only.
- Do not pre-decide — present options with tradeoffs and a recommendation each, clearly marked as recommendation.

**Stop Condition**

This is a time-boxed spike (~1h). If the intervention machinery turns out to be deeper than expected, stop at the box and record what remains unknown in the memo rather than extending.

**Acceptance**

- [ ] `audit/emergency-mode-decision-memo.md` exists, covering all four sections with engine-code citations (file:line).
- [ ] Every option marked case-authoring vs Kamae-chain.
- [ ] `git status` shows no modified files — only the new memo.

**Verification**

```bash
ls audit/emergency-mode-decision-memo.md
git status --porcelain   # only the new memo (and ledger update) appear
```

**Commit**

```
docs(audit): emergency-mode design decision memo — feeds P2-H05
```
