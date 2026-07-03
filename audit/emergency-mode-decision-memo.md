# Emergency-mode design decision memo

**Audit SP spike output — feeds P2-H05 and the Kamae chain.**
Date: 2026-07-03. Read-only reconnaissance; no code or case changes.
Engine state examined at post-S3 HEAD (`b19114e`); the S2 case repair (steroid gating, `e9af5e5`) is assumed.

Every recommendation below is labeled by decision authority:
- **[case-authoring]** — the practitioner can decide inside a ho; expressible in the current schema, no engine work.
- **[Kamae-chain]** — touches the system design or a mechanic decision the documents haven't made; belongs in a thinking conversation first.

---

## 1. Survivable crisis — what `emergency_intervention` needs

**Current state.** Once `node_14_seizure_crisis` activates, death is unavoidable: its 5-minute timer activates `node_16_patient_death` (case JSON, node_14 `timer.on_expire`), `node_17`'s `clear_flag crisis_active` does not touch node_14's timer, and the `emergency_intervention` action (declared in `action_costs`) is referenced by **nothing** — it currently spends 2 minutes and does nothing, which is worse than being locked: it *punishes* the correct instinct.

**Engine machinery available (verified, no engine change required for any option):**
- **Intervention matching:** `InterventionEffect` (`case_definition.py:305-309`) carries `treatment: str` + `effects`; `check_interventions` (`state_checkers.py`, `check_interventions`) matches it against the action's param, or the base action when there is no param — so `on_intervene: {treatment: "emergency_intervention", effects: [...]}` on node_14 fires when the player takes the bare `emergency_intervention` action.
- **Timer teardown:** `deactivate_node` (`effect_executor.py`, `_deactivate_node`) removes the node from `active_nodes` AND cleans up its timer and stage tracking.
- **Timer pause:** `NodeTimer.pause_conditions` (`case_definition.py:299`) — checked every tick (`timer_manager.py:81`); a paused timer holds its remaining minutes.
- **Timer extension:** `modify_timer` with positive value.

### Option A — Intervention deactivates the crisis node **[case-authoring]** *(recommended)*
Author on node_14: `on_intervene: {treatment: "emergency_intervention", effects: [deactivate_node node_14, clear_flag crisis_active, set_flag crisis_managed]}`.
- **Mechanics:** death timer removed outright; `crisis_managed` is available for outcome tiers (e.g., a managed-crisis run can still reach PARTIAL/GOOD; an unmanaged one cannot).
- **Felt experience:** benzodiazepines/airway control end the seizure — clinically the right shape (status epilepticus care is exactly this).
- **Caveats:** deactivation also removes node_14's crisis vitals from worst-wins, so vitals visibly recover — desirable. But the patient is "stabilized, still sick": node_09 has already expired, so no second crisis clock exists. See the re-arm question below.
- **H05 implication:** emergency mode ends when `crisis_active` clears — same signal as the treatment path; clean for the `emergency_active` derivation (§2).

### Option B — Intervention pauses the death timer **[case-authoring]**
`pause_conditions: [flag_set crisis_managed]` on node_14's timer + `on_intervene` setting `crisis_managed`.
- **Mechanics:** the timer freezes but the node stays active — crisis vitals persist, the emergency visually continues until albendazole clears it.
- **Felt experience:** "you've bought time, not safety" — dramatically stronger, mechanically murkier (the frozen countdown must be presented carefully in the Pending/Emergency UI; a paused *visible* timer is a new UI state H05 would have to design).
- **Caveat:** if nothing ever unpauses/deactivates, the crisis persists to case end; the emergency-mode UI would run for the rest of the case.

### Option C — Intervention buys minutes (`modify_timer +10`) **[case-authoring]**
Repeatable rescue that extends the window each time.
- **Felt experience:** frantic, repeated intervention — but repeatable actions with flat costs invite degenerate play (spam emergency_intervention forever). Would need a lockout mechanic the schema doesn't have. **Not recommended.**

**Open design question, either A or B [Kamae-chain]:** should a *managed* crisis re-arm? Today node_09 is expired by the time node_14 fires, so after a successful rescue there is no further deterioration clock — the player can idle safely to the 360-minute limit. If the design wants "stabilized but still dying without treatment," that needs a second progression node (case-authoring once decided) — e.g., a post-crisis progression timer activated by `crisis_managed`. This is the one piece with real design weight: it defines what "surviving the crisis" means.

**Sequencing note:** whichever option is chosen should land as a case ho **before or inside P2-H05** — the H05 UI premise ("only emergency-relevant actions surfaced") needs at least one emergency-relevant action to exist.

---

## 2. `emergency_active` semantics for H05

The ho-overview recommends deriving `GameState.emergency_active: bool` from reserved `crisis_active:*` flag patterns. Verified against the actual case:

- **Start:** node_14's `on_reveal` sets `crisis_active`; node_14 is `auto_reveal`, so the flag lands the same tick the crisis activates. ✓
- **Resolution:** node_17's `on_reveal` clears `crisis_active` (albendazole during crisis) — and Option A's intervention would clear it too. ✓
- **Death:** `crisis_active` is still set when node_16 ends the case. The derivation should therefore be `emergency_active = has crisis flag AND NOT case_ended` — otherwise the outcome screen renders in emergency dress. **[case-authoring/engine-derivation detail — resolve in H05 as planned]**
- **Edge cases to spec in H05:**
  - *Crisis + case-end same tick* (albendazole reveal ends the case and clears the flag in one tick): last-write within the tick is deterministic post-S3; the API surfaces only the final state, so the frontend never sees a half-tick. No special handling needed.
  - *Emergency during a wait:* the crisis can fire mid-`wait:60`; the response returns with `emergency_active` true and the elapsed events. H06 already decided wait is disabled *during* emergencies; a wait that *enters* one is fine and should stay legal.
  - *Exact-precision timer:* H05's decision that the emergency timer shows exact remaining time is served by `visible_timers` only if node_14's timer surfaces there. Node_14 is non-diegetic by design; H05 already plans to surface the triggering timer as the one exception. Note (audit C-10): the `active_timer` branch of `compute_visible_timers` requires `timer.diegetic: true` — H05 either marks node_14's timer diegetic at crisis time (no mechanism — diegetic is static case data) **or** the API/engine surfaces the emergency timer through a separate channel. **[Kamae-chain — small, but it's an engine-surface decision H05's per-ho doc must settle; the ho-overview text implies the same channel, which the current filter does not support.]**

---

## 3. The OPTIMAL window

**The math (post-S2 verified by the regression harness):** fastest rigorous path — CT at t=74, dietary history for the X-ray unlock, thigh X-ray (20-min delay), family visit overlapped into result windows — lands `correct_treatment_started` at **t=116** against `before_minutes: 120`. Four minutes of slack, achievable only with delay-overlap scheduling the case never teaches. A thorough player who sequences naturally (family visit not overlapped, or MRI instead of X-ray) lands t≈130–160 → GOOD.

Options:

- **A. Widen to 150 [case-authoring]** *(recommended)* — keeps time pressure meaningful (still well inside the 180 GOOD bound and the 195 crisis), but rewards *rigor* rather than scheduling micro-optimization. A confirmed + family-engaged run that doesn't dawdle lands OPTIMAL.
- **B. Keep 120 [case-authoring]** — OPTIMAL as a mastery tier for replayers who learn to overlap delays. Defensible if the design wants a "perfect run" concept; the debrief (Phase 5) would need to teach the overlap explicitly or it reads as arbitrary.
- **C. Drop the time constraint from OPTIMAL entirely [Kamae-chain]** — rigor and family engagement alone define OPTIMAL; time pressure lives only in the crisis clock and GOOD's 180. This changes what the tier system expresses (the seed's "timing and deterioration" pillar), so it is not a case-local call.

**Related latent engine limitation (report, low):** tier `time_constraints` compare against case-end time, not flag-set time (`state_checkers.py`, outcome evaluation). Correct today only because `correct_treatment_started` ends the case. Any future tier constraining a non-ending flag scores wrong. Worth a line in whichever ho next touches outcome rules. **[Kamae-chain if the semantics change; engine fix is small once decided]**

---

## 4. `family_alienated`

Diego's timer (`node_13`, 90 minutes from arrival) sets `family_alienated` on expiry if the player never took `history_focused:family`. Nothing reads the flag — the relational-failure branch has zero consequence. An inert punishment is worse than none: the mechanic implies the game noticed, and it didn't.

- **A. Wire it into the tiers [case-authoring]** *(recommended, smallest true fix)* — add `family_alienated` to OPTIMAL's `excluded_flags`. Today it's near-redundant (OPTIMAL already *requires* `family_engaged`, and you can't have engaged Diego *and* let him leave — the reveal sets `family_engaged` before the timer can expire), so the honest version of this option is: **exclude it from GOOD**, making the relational failure cost one tier. That gives the husband thread real mechanical weight, which is what the seed's "medicine as a human system" pillar wants.
- **B. Cut the timer/flag [case-authoring]** — if the design decides relational consequence belongs to Phase 5's debrief rather than the tier system, delete the `on_expire` and the flag, and let Diego's departure be narrative-only. Cheaper, but it walks back an authored mechanic.
- Note the audit's determinism nuance either way: Diego's *arrival* is tick-quantized (activates on the first tick crossing T+30), so his departure time varies with action cadence — acceptable, but worth knowing before wiring consequences to it.

---

## Recommended package for the thinking conversation

1. Survivable crisis: **Option A** (intervention deactivates node_14, sets `crisis_managed`), plus a decision on post-crisis re-arm.
2. `emergency_active`: derive as `crisis-flag AND NOT case_ended`; settle the emergency-timer visibility channel (the one genuine engine-surface question in H05).
3. OPTIMAL window: **widen to 150**.
4. `family_alienated`: **exclude from GOOD** (relational failure costs a tier).

Items 1, 3, 4 are case-authoring once blessed; item 2's timer-channel piece needs a sentence in the H05 per-ho doc before implementation. If all four are accepted, they fit naturally as one small case ho preceding P2-H05.
