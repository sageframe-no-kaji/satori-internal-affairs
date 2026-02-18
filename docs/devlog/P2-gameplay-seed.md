# P2 — Gameplay Mechanics Seed

## What This Document Is

Homework. Things to think about before writing Ho 06+ task specs. None of this is decided — it's a design space to walk through so the next implementation is intentional, not accidental.

The engine works. The data structure works. What doesn't exist yet is a **designed player experience** — the thing that makes someone lean forward, second-guess themselves, and feel the weight of a decision.

---

## What Already Works (Mechanically)

The engine supports all of the following. They are implemented and tested:

- **Concurrent independent timers** — multiple node timers tick in parallel, each on their own schedule
- **Flag-gated activation** — nodes wake up when conditions in the world change
- **Lock/unlock action chains** — actions become available as the player discovers things
- **Delayed reveals** — labs and imaging take simulated time to return results
- **Timer stages with vitals effects** — patient deteriorates through stages (BP rises, consciousness drops)
- **Timer expiry cascades** — one timer expiring can activate another node (headache progression → seizure crisis → death)
- **Intervention effects** — treatments set flags, modify timers, trigger consequences
- **Multiple end conditions** — correct treatment, patient death, time exhaustion
- **Outcome tier evaluation** — scored based on flags present at case end

**What does NOT work yet:** The player can only send bare base actions (`order_labs`) because the UI doesn't surface subcategories (`order_labs:cbc`). This is a wiring problem — Ho 06 fixes it. Everything below assumes that's done.

---

## The Gap: What Makes It a Game

Right now the player loop is:

> Pick an action from a list → read what happened → pick another → repeat

The intended experience is:

> **Notice something.** Build a theory. Test it. Get results that complicate it. Face a decision before you're ready. Find out if you were right — or what you missed.

The difference between these two is game design. The engine can execute either. The question is what to author *into* the cases and what mechanics to expose *through* the UI.

---

## Your Notes (From the Devlog)

These are your original instincts. They're good. Let's evaluate each one against what exists:

### "Need to make a diagnosis before treatment, even if wrong"

**Status: Not yet implemented.** The engine currently allows `start_treatment:albendazole` the moment `start_treatment` is unlocked. There is no gate that says "you must commit to a diagnosis first."

**Design options:**

- **A. Diagnosis commitment action.** Add a new base action category: `commit_diagnosis`. The player types or selects a diagnosis. This sets a flag (`committed_diagnosis_neurocysticercosis` or `committed_diagnosis_brain_tumor`). Treatment actions only unlock after a diagnosis is committed. Wrong commitments aren't fatal — you can re-commit — but each commitment costs time and affects outcome scoring.

- **B. Soft diagnosis gate via the case.** No engine change. Instead, the case's `node_17_correct_treatment` has an additional activation condition: `neurocysticercosis_suspected` must be set. The player can still *try* steroids without confirming a diagnosis (node_15 starts_active, so `start_treatment:steroids` always works once unlocked) — but reaching albendazole requires having built the hypothesis first. This is already partially true in the current case.

- **C. Diagnosis as scored outcome, not mechanical gate.** The player can treat whenever they want. But the outcome evaluation explicitly scores whether a diagnosis was articulated. "Correct treatment without stated reasoning" gets a lower tier than "correct treatment with reasoning." This preserves the freedom to act but rewards the reasoning process.

**Things to think about:** Option A is the most game-like (it creates a moment of commitment). Option B is achievable now with case authoring alone. Option C requires the outcome evaluation schema to track diagnostic reasoning, which it doesn't currently do.

### "Treatments have consequences"

**Status: Partially implemented.** Steroids set `wrong_treatment_steroids`, trigger a 60-minute rebound timer, and accelerate the crisis. But this is authored per-case. There's no general "treatment consequence" system.

**What's already possible:** Any treatment subcategory can have a node that reveals on it and fires effects. The mechanism is there. The question is authoring: does every treatment option have a consequence node? Should there be a `start_treatment:acetaminophen` that does nothing harmful but wastes time? A `start_treatment:broad_spectrum_antibiotics` that masks symptoms temporarily?

**Things to think about:** Red herring treatments that *feel* productive (symptoms temporarily improve) but don't address the cause are the most interesting design space. The steroids node already does this. More of these = richer gameplay. This is entirely a case authoring question, not an engine question.

### "Emergencies need to be TRIGGERED and CLEAR"

**Status: The engine supports this. The UI does not surface it.**

The seizure crisis (`node_14_seizure_crisis`) auto-reveals and locks several action categories when it fires. Its `on_reveal` effects include locking `history_general`, `history_focused`, `physical_exam_general`, `physical_exam_focused`. The patient is seizing — you can't take a history anymore.

**The problem:** The current UI shows this as just another narration entry in a chronological log. There is no visual distinction between "lab results came back" and "THE PATIENT IS SEIZING." No alarm. No state change in the interface. No forced attention.

**Design options:**

- **A. Emergency state in GameState.** Add a computed field: `emergency_active: bool` (derived from flags like `crisis_active`). The UI enters a different visual mode when this is true — red border, restricted action list, countdown visible.

- **B. Event severity levels.** Events already have types. Add a severity or urgency field to certain events. `NodeRevealedEvent` for the crisis node carries `urgency: "emergency"`. The UI renders emergency events differently.

- **C. Pure UI treatment.** No engine change. The frontend inspects the flags in each response (e.g., `crisis_active`), and when it sees crisis flags, it changes its own rendering. This is fragile (the frontend must know which flags mean "emergency") but requires zero engine changes.

**Things to think about:** Option A is cleanest — it gives the UI a single boolean to check. Option B is most flexible — it works for any event, not just crises. Option C is the quickest to ship but accumulates design debt.

### "There should be COUNTDOWN CLOCKS for situations"

**Status: The engine has timers. The UI does not show them.**

`state.timers` contains `{"node_09_headache_progression": 165, "node_15_steroid_response": 45}` — minutes remaining on each active timer. `state.pending_reveals` contains `{"node_04_cbc_results": 30}` — minutes until a lab result arrives.

**The question is what the player should see:**

- **Show all timers?** That reveals too much structure. The player shouldn't know there's a `headache_progression` timer ticking — they should *feel* the patient getting worse.

- **Show only "known" timers?** Labs have a natural clock: "CBC results pending — estimated 30 minutes." The player ordered the test; they know it takes time. This is fair to show. But the patient's deterioration timer is hidden — you only see its effects through worsening vitals and symptoms.

- **Show pending results as a queue?** A "Pending Results" panel showing items the player has ordered and approximate time remaining. This is the Kanban-adjacent idea from your notes.

**Things to think about:** The distinction between *diegetic* timers (the player's character would know about them — lab turnaround, imaging queue) and *non-diegetic* timers (biological deterioration the character can't see) is crucial. Showing the deterioration timer removes the tension. Showing the lab timer is expected clinical behavior.

### "There should be multiple things happening at once and trackable"

**Status: The engine runs them concurrently. The UI shows a flat chronological log.**

This is perhaps the biggest UI gap. The engine is a concurrent discrete event simulator — multiple timers ticking, multiple nodes activating, multiple pending reveals counting down. The UI flattens all of this into a single timeline.

**Design options for tracking concurrent state:**

- **A. Kanban-style board.** Columns: "Active Concerns" | "Pending Results" | "Resolved." Cards move between columns as the case progresses. This makes parallelism visible.

- **B. Patient dashboard.** Top section: vitals (updating). Side panel: active concerns / hypotheses (accumulating). Center: narrative events (latest at top). Bottom: pending results with ETAs. This is closer to a real clinical tracking board.

- **C. Tabbed investigation view.** Tabs for different investigation threads: "History", "Physical Exam", "Labs/Imaging", "Treatment". Each tab shows findings in that category. The player can see what they've learned in each domain independently.

**Analog from games:** The closest existing game patterns are:

- **Pandemic (board game)** — multiple disease tracks advancing independently, player must triage which to address
- **FTL: Faster Than Light** — multiple ship systems running concurrently, fires and breaches happening in parallel, crew must be assigned
- **This War of Mine** — concurrent survival timers (hunger, sickness, morale), each advancing independently
- **Return of the Obra Dinn** — building a theory from fragments, committing identifications, getting scored on accuracy

None of these are exact matches, but They all share the "multiple independent processes advancing under time pressure" pattern that you're describing.

---

## The Three Design Axes (Expanded)

These aren't mutually exclusive. But one should be dominant — it shapes everything else.

### Axis A — Diagnostic Commitment

The game is fundamentally about **forming and testing a hypothesis**.

- The player must commit to a working diagnosis before unlocking advanced actions
- Wrong diagnosis → wrong treatment path → consequences
- Changing diagnosis costs time
- The central tension: "Am I sure enough to commit?"

**Schema implications:** New action category `commit_diagnosis`. Outcome evaluation scores diagnostic reasoning. Cases must have plausible differentials (not just one obvious answer).

**What it feels like:** House M.D. — the whiteboard scene. "What if it's not lupus?"

### Axis B — Resource Scarcity (Time as Currency)

The game is fundamentally about **choosing what to spend attention on**.

- Every action costs time. Time is the only resource.
- Ordering everything is expensive and signals bad reasoning
- The clock is always visible. The patient is always getting worse (or not — and you don't know which).
- The central tension: "What do I check first? Can I afford to wait for these results?"

**Schema implications:** `action_costs` becomes more differentiated (some actions are cheap, some are expensive). Outcome evaluation penalizes over-ordering. Cases must be winnable in tight time budgets with good reasoning, but losable if you scatter your attention.

**What it feels like:** Papers, Please — you have limited time per person, you have to decide what to scrutinize.

### Axis C — Incomplete Information Under Time Pressure

The game is fundamentally about **acting before you're ready**.

- Results arrive asynchronously. The patient is changing while you wait.
- You never have all the information. You always have to decide with 70% confidence.
- The central tension: "Do I treat now based on what I suspect, or wait for confirmation while the patient might get worse?"

**Schema implications:** Longer delays on confirmatory tests. Deterioration timers that are deliberately shorter than result turnaround times. Cases where the "fast but risky" treatment path and the "slow but safe" diagnostic path are in direct conflict.

**What it feels like:** The actual experience of emergency medicine. Also: XCOM — you're making tactical decisions with fog of war and a turn counter.

---

## Your Instinct Points to C (With Elements of A)

Based on your devlog notes, the seed document, and the case-data-structure.md ecosystem metaphor — you consistently describe:

- Things happening in parallel on their own schedules
- The player having to decide when to act vs. when to wait
- Consequences that emerge from timing, not just correctness
- Diagnosis as a pre-commitment before treatment (element of A)

The Maria Santos case is already authored toward C: the headache progression timer (180 min) runs independently, labs take 45 min, the CT takes 45 min, Diego arrives at T+30 and leaves at T+120. The tension is supposed to be: "Do I wait for the MRI to confirm, or do I start albendazole now based on clinical suspicion while her headaches are getting worse?"

That tension doesn't land yet because the UI doesn't surface the concurrent timers or the deterioration. But the engine is already running the right simulation underneath.

---

## Concrete Things to Decide Before Ho 06+

These need answers. They don't need to be final — but they need to be specific enough to implement.

1. **Does the player commit a diagnosis before treatment?** (Yes/No/Optional-but-scored)

2. **What timers are visible to the player?** (All / Only diegetic / None — infer from vitals)

3. **Is the action menu flat (all subcategories shown) or contextual (subcategories appear based on what makes clinical sense)?** Flat is simpler to implement. Contextual is more realistic but requires encoding "what a reasonable clinician would think to order" into the case.

4. **What is the primary feedback loop?** When the player acts, what changes on screen tell them whether they're on the right track? Options: vitals trending, narrative tone shifting, new actions appearing, diagnosis confidence score, or nothing — you only find out at the end.

5. **How are emergencies visually distinct?** Separate UI mode? Red banner? Forced action? Audio cue?

6. **Is there a "waiting" action?** Can the player explicitly choose to wait 15-30 minutes without doing a clinical action? This is clinically realistic (sometimes the correct move is to observe) but it needs to feel like a real choice, not a skip button.

---

## Reference: What Exists in the Engine Today

| Mechanic | Engine support | UI support | Case authoring |
|---|---|---|---|
| Subcategory actions (`order_labs:cbc`) | Yes | **No** (Ho 06) | Yes (18 nodes use them) |
| Lock/unlock action chains | Yes | Partial (buttons appear/disappear) | Yes |
| Countdown timers (deterioration) | Yes | **No** (not displayed) | Yes (node_09: 180 min) |
| Pending results with ETAs | Yes | **No** (not displayed) | Yes (CBC: 45 min) |
| Emergency state changes | Yes (flags + action locks) | **No** (no visual distinction) | Yes (node_14 locks actions) |
| Treatment consequences | Yes (effects on reveal) | Partial (narrated only) | Yes (steroids → rebound) |
| Diagnosis commitment | **No** | **No** | **No** |
| Concurrent event tracking | Yes (engine internals) | **No** (flat log only) | Yes (multiple timers) |
| Outcome scoring | Yes | Yes (tier displayed) | Yes |
| Relational nodes with timers | Yes | Partial (narrated only) | Yes (Diego: T+30 → T+120) |
