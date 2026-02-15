# Case Definition Data Structure

## Purpose

This document explains the data structure that powers deterministic medical mystery gameplay in Satori Internal Affairs. It's the answer to a hard question: **how do you encode a branching, time-sensitive, emotionally complex medical case into a static JSON file that a deterministic engine can execute?**

The case definition schema is the contract between Anamnesis (case generation) and Satori (case execution). It separates what's possible (the structure) from what happens (the content). It's a declarative specification of a concurrent state machine where dozens of independent timers, flags, and conditional reveals orchestrate a medical mystery that can end in recovery, complications, or death — all determined by player choices and timing.

---

## The Core Problem

A medical case isn't linear. It's a graph of concurrent possibilities:

- A patient deteriorates on one timeline while test results arrive on another
- Information reveals conditionally based on what the player already knows
- Treatments have delayed effects that interact with ongoing processes
- Multiple outcomes are possible depending on actions taken and time elapsed
- The same evidence can lead to different conclusions based on interpretation

Traditional branching narrative models (choice trees, dialogue graphs) don't capture this. They assume one thing happens at a time and choices lock you into paths. Medical reality is concurrent: timers tick independently, conditions evolve simultaneously, and the player's knowledge state is separate from the patient's medical state.

The case definition schema solves this through **node-graph architecture with discrete event simulation**.

---

## Architecture: Node-Graph with Discrete Event Simulation

### The Mental Model

Think of a case as a **garden ecosystem with growing conditions**:

- **Nodes** are plants and organisms — each has its own lifecycle (dormant seeds, sprouting, blooming, fruiting, withering)
- **Flags** are nutrients in the soil — when one plant produces them, others can consume them to grow
- **Timers** are growth cycles — some plants mature on their own schedule regardless of whether you're watching
- **Your actions** are like directing sunlight — you illuminate different parts of the garden, revealing what's there

The garden is planted at the start (case generation). During gameplay, different plants grow based on what nutrients are in the soil and how you direct your attention. The garden's development is deterministic: same seeds, same conditions, same outcome. But the growth path varies enormously based on which plants you tend to first.

### The Maria Santos Case as Ecosystem

When Maria Santos arrives in your ER, you're stepping into a garden that's already growing:

**The Chief Complaint (NODE 01)** is a flowering plant in full view — you can't miss it. It's right there when you arrive. The moment you examine it (take general history), it drops seeds into the soil: `headaches_two_weeks` and `seizure_with_aphasia` flags. These nutrients enable other plants to sprout.

**The Headache Progression (NODE 06)** is a parasitic vine. The moment `headaches_two_weeks` nutrient appears in the soil, this vine activates. You never see it directly — it's growing under the surface. But every season that passes (every 60 minutes), it affects the garden's vital signs. At T+60, the leaves wilt slightly (BP rises). At T+120, more wilting. At T+180, the vine strangles a critical root system and triggers the seizure crisis (NODE 07). This vine has **its own growth cycle**. It doesn't care whether you've ordered a CT scan or talked to the family. It's growing on biological time.

**The Dietary History (NODE 05)** is a shy wildflower. It's been there the whole time, waiting for the right conditions. You could shine light on it at any point (ask about diet), but most gardeners don't think to look for it unless other plants signal something's wrong. When you discover the eosinophilia (NODE 04 — a plant with distinctive red leaves) or see the brain lesion (NODE 03 — a large, ominous growth), experienced gardeners start looking for this wildflower. When you finally illuminate it, it produces a critical nutrient: `undercooked_pork_exposure`. This nutrient, combined with others, unlocks the confirmatory X-ray path.

**The Thigh X-Ray (NODE 09)** is a late-season fruit that only appears after specific nutrients accumulate. It won't grow until either `neurocysticercosis_suspected` OR (`undercooked_pork_exposure` + `lesion_found`) are in the soil. You can't force it to fruit. The conditions must be right first.

**The Steroids Treatment (NODE 08)** is pesticide. When you apply it (start steroids), the garden looks healthier immediately! The wilting stops. Maria's headache improves. The visible distress fades. But this pesticide kills beneficial soil bacteria — it suppresses her immune response, allowing the parasite to flourish. After 60 minutes, the false improvement reverses catastrophically. The pesticide **accelerates** the parasitic vine (NODE 06), bringing the crisis 60 minutes sooner. What looked like healing was actually making everything worse.

**Diego, Maria's Husband (NODE 12)** is a pollinator that arrives on schedule (T+30). If you engage with him before he leaves (90-minute timer), he cross-pollinates your garden with critical information. He mentions the Sunday pork meals — an alternate source of the `undercooked_pork_exposure` nutrient. If you ignore him, he flies away. You lose access to that pollination path permanently.

### Why This Ecosystem Model Works

**1. Independence**: Each organism has its own lifecycle. The parasitic vine (NODE 06 — headache progression) grows whether or not you're examining the brain lesion flower (NODE 03 — CT scan). The deterioration process and the diagnostic process are parallel, not sequential. Maria's condition worsens on a biological timeline while test results arrive on a laboratory timeline.

**2. Composition**: Complex garden behavior emerges from simple growth rules. The dietary history wildflower (NODE 05) has a trivial reveal condition: shine light on it (ask about diet). But the complexity is in the ecosystem: you don't think to look for wildflowers when there's a giant ominous growth (brain lesion) demanding attention. The eosinophilia's red leaves (NODE 04) or Diego's pollination (NODE 12) are what make experienced gardeners search the underbrush.

**3. Time Pressure**: Every action you take is a season passing. Seasons advance the growth cycles. The parasitic vine (NODE 06) ticks through stages — slight wilting at summer (T+60), significant wilting at autumn (T+120), root damage at winter (T+150), strangulation at spring (T+180). You never see the vine directly, but you see the garden's vital signs changing. The BP creeps up. The leaves droop. The soil condition worsens. This creates dramatic tension without you needing to understand the underground mechanism.

**4. Conditional Blooming**: The confirmatory X-ray fruit (NODE 09) only appears when nutrients accumulate: `neurocysticercosis_suspected` OR (`undercooked_pork_exposure` + `lesion_found`). You can't order the thigh X-ray until these flags are in the soil. The diagnostic path unlocks only after evidence accumulates. The garden teaches you when you're ready to see certain truths.

**5. Consequences Cascade**: The steroid pesticide (NODE 08) feels like success — the wilting stops! Maria smiles! The visible symptoms improve! Then the pesticide timer expires. The beneficial bacteria die. The immune suppression lets the parasite (vine) accelerate by 60 minutes. The garden looked healthy briefly, then the underground damage surfaces catastrophically. The false improvement is itself a teaching moment: treating visible symptoms without understanding the soil ecology makes everything worse.

### From Metaphor to Mechanism

The ecosystem metaphor isn't just poetry — it maps directly to the technical architecture:

|Ecosystem Concept|Technical Implementation|Maria Santos Example|
|---|---|---|
|**Plant/organism**|Node with type, content, lifecycle|NODE 06 (parasitic vine) = `type: "progression"`|
|**Nutrient in soil**|Flag (boolean, set by effects)|`headaches_two_weeks` enables vine growth|
|**Growth cycle**|NodeTimer with stages and expiry|180-min timer, stages at T+60/120/150/180|
|**Season passing**|Player action advances game clock|Each action costs time (15 min, 45 min, etc.)|
|**Shining light**|Player action triggers reveal|`action: history_general` reveals NODE 01|
|**Conditional blooming**|ActivationRule with flag conditions|NODE 09 needs `neurocysticercosis_suspected` flag|
|**Pesticide effect**|InterventionEffect with timer modification|Steroids accelerate NODE 06 by 60 minutes|
|**Pollinator**|Relational node with timer and effects|NODE 12 (Diego) arrives T+30, leaves T+120|
|**Garden vital signs**|Computed from active node modifiers|Sum all active nodes' vital_signs declarations|

The ecosystem lives in JSON. The growth rules are declarative. Satori is the gardener who tracks which plants are active, which nutrients are in the soil, and what the current season is.

---

## Structure Hierarchy

```
CaseDefinition
├── Metadata (difficulty, duration, learning goals, tone)
├── PatientContext (demographics, appearance, arriving vitals, triage)
├── GroundTruth (diagnosis, mechanism, optimal path, narrative hooks)
├── ActionCosts (time cost per action type)
├── Nodes[] (the atomic units — medical, relational, progression, intervention)
│   ├── NodeContent (narrative text, structured data)
│   ├── ActivationRule (when does this node become live?)
│   ├── RevealRule (how does the player discover it?)
│   ├── NodeTimer (countdown from activation)
│   ├── VitalSigns (what vitals does this node want when active?)
│   ├── NodeEffects (what happens on reveal, expire, intervene?)
│   └── OutcomeWeight (how does this contribute to final score?)
└── OutcomeEvaluation (tiers, harmful actions, end conditions)
```

---

## Layer Separation: Structure vs. Narrative

The schema has **two layers in a single file**:

### Structure Layer (Consumed by Satori)

Mechanical truth. How the simulation works.

- Activation rules (flags, time, vitals)
- Timers and stages
- Effects (set flag, activate node, modify timer, end case)
- Reveal conditions
- Outcome evaluation logic

**Example**: NODE 06 has a timer of 180 minutes with staged effects at T+60, T+120, T+150, T+180. Each stage modifies vitals. On expiry, it activates NODE 07.

This is pure logic. Satori reads this and executes it. No LLM. No interpretation.

### Narrative Layer (Consumed by Internal Affairs)

What the player reads. How it feels.

- `patient.name`, `patient.appearance`, `patient.backstory`
- `node.content.narrative_text`
- `ground_truth.diagnosis`, `ground_truth.key_insight`
- `outcome_tier.narrative`

**Example**: NODE 07's content is: _"Maria suddenly stops mid-sentence. Her eyes roll back. She seizes — full tonic-clonic, violent..."_

This is presentation. Internal Affairs renders it. In Phase 1, this text is frozen (generated at case creation time). In future phases, this could be dynamically generated by the LLM at play-time while the structure remains frozen.

**Why separate them?**

Because the experience and the truth live at different layers. The structure must be deterministic and verifiable. The narrative can be dramatic and atmospheric. Mixing them would mean either constraining the drama (boring) or destabilizing the logic (dangerous).

The separation is enforced by placement: narrative fields are explicitly named (`narrative_text`, `appearance`, `description`). Everything else is structure.

---

## Key Concepts

### 1. Nodes: Atomic Units of Reality

Every piece of the case is a node. A node is independent, self-contained, and connects to other nodes only through flags and timers.

**Node types**:

- `medical_finding` — exam findings, symptoms, signs
- `lab_result` — test data
- `imaging` — radiology, scans
- `history` — patient backstory, revelations
- `relational` — family dynamics, trust, social context
- `emotional` — patient affect, reactions
- `behavioral` — patient actions independent of player
- `progression` — disease trajectory, deterioration/improvement
- `intervention_response` — treatment effects
- `outcome` — end states (death, recovery, discharge)

**Why this matters**: The schema doesn't privilege medical nodes over relational nodes. NODE 12 (Maria's husband Diego) is structurally identical to NODE 03 (CT scan). Both have activation rules, reveal rules, timers, and effects. The only difference is content.

This design choice enables cases where human dynamics are as mechanically important as medical findings. A player who ignores Diego loses access to diagnostic information (he mentions the Sunday pork meals). The relational failure has medical consequences.

### 2. Activation: When Nodes Become Live

A node is **activated** when it enters the simulation. Activation ≠ reveal. The player doesn't see activated nodes unless they meet reveal conditions.

**Activation rules** define: _under what conditions does this piece of reality become live?_

```python
class ActivationRule:
    paths: list[ConditionPath]  # OR between paths
    on_activate: Optional[list[Effect]]
    starts_active: bool = False
```

Each `ConditionPath` is a list of `Condition` objects (AND within a path). If ANY path is satisfied, the node activates.

**Example**: NODE 06 (headache progression) activates when `headaches_two_weeks` flag is set. This flag is set by NODE 01 (chief complaint). So: player does general history → NODE 01 reveals → flag sets → NODE 06 activates → timer starts ticking.

The player never sees NODE 06 directly. But it's running. At T+60, it modifies vitals (+5 HR, +10/5 BP). At T+180, it triggers NODE 07 (seizure crisis).

**Design principle**: Activation is about the simulation, not the player. Nodes can be active and consequential without ever being revealed.

### 3. Reveal: How Players Discover Nodes

A node is **revealed** when the player sees its content. Reveal requires:

1. The node is active
2. Reveal conditions are met

```python
class RevealRule:
    action: ActionType  # What action triggers reveal
    subcategory: Optional[str]  # Refinement (e.g., "neuro" exam)
    conditions: Optional[list[Condition]]  # Additional gates
    auto_reveal: bool = False  # Reveals automatically when active
    delay_minutes: Optional[int]  # Results delay (labs, imaging)
```

**Example 1 — Action-gated reveal**:  
NODE 02 (neuro exam findings) reveals when `action = physical_exam_focused:neuro`. The player must specifically examine the nervous system. General exam won't reveal it.

**Example 2 — Conditional reveal**:  
NODE 09 (thigh X-ray) requires `neurocysticercosis_suspected` OR (`undercooked_pork_exposure` AND `lesion_found`). The X-ray option doesn't appear in the action menu until these flags accumulate. The player must build a hypothesis before this diagnostic path unlocks.

**Example 3 — Auto-reveal**:  
NODE 07 (seizure crisis) has `auto_reveal: true`. When it activates, it immediately displays. The player has no choice — the patient is seizing, the event is unavoidable.

**Example 4 — Delayed reveal**:  
NODE 03 (CT results) has `delay_minutes: 45`. Player orders the CT at T+0. Results don't arrive until T+45. During that time, the clock is ticking, NODE 06 is progressing, the patient may be deteriorating.

**Design principle**: Reveal is about player knowledge, not simulation state. The simulation can know things the player doesn't.

### 4. Flags: The Wiring Between Nodes

Flags are boolean signals. They're set by effects. They're checked by conditions.

A flag is just a string: `"eosinophilia"`, `"correct_treatment_started"`, `"crisis_active"`.

**Flags serve three purposes**:

**1. Cross-node communication**  
NODE 04 (lab results) sets `eosinophilia`. NODE 05 (dietary history) checks if `eosinophilia` is set and, if so, sets `neurocysticercosis_suspected`. This creates a chain: evidence → hypothesis → diagnostic path unlock.

**2. Gate unlocking**  
NODE 09 (thigh X-ray) only becomes available when `neurocysticercosis_suspected` is set. Flags control what actions the player can take.

**3. Outcome evaluation**  
The OPTIMAL outcome tier requires flags: `diagnosis_confirmed`, `correct_treatment_started`, `family_engaged`. The game scores based on which flags were set by case end.

**Design principle**: Flags are the graph edges. Nodes are the vertices. The case is the graph.

### 5. Timers: Countdown Clocks

Timers create time pressure. They tick down from activation.

```python
class NodeTimer:
    duration_minutes: int
    pause_conditions: Optional[list[Condition]]
    stages: Optional[list[TimerStage]]  # Progressive effects
    on_expire: list[Effect]
```

**Example**: NODE 06 (headache progression) has a 180-minute timer with stages at T+60, T+120, T+150, T+180. Each stage modifies vitals progressively. At expiry (T+180), it triggers NODE 07 (seizure crisis).

**Pause conditions** stop the timer without resetting it. If `correct_treatment_started` flag is set, NODE 06 pauses. The patient stabilizes. The timer doesn't tick anymore. But if treatment fails or rebounds, the timer can resume.

**Design principle**: Timers make inaction costly. The player can't wait forever. The patient deteriorates on a schedule.

### 6. Effects: State Transitions

Effects are **how nodes change the simulation**. They fire on activation, reveal, expiry, or intervention.

```python
class Effect:
    type: Literal[
        "set_flag",
        "clear_flag",
        "activate_node",
        "deactivate_node",
        "modify_timer",
        "unlock_action",
        "lock_action",
        "override_vitals",
        "end_case"
    ]
    target: str  # flag name, node ID, action type, etc.
    value: Optional[Any]
```

**Effect types**:

- `set_flag` / `clear_flag` — Boolean state changes
- `activate_node` / `deactivate_node` — Bring nodes into/out of simulation
- `modify_timer` — Accelerate or delay another node's countdown
- `unlock_action` / `lock_action` — Change what the player can do
- `override_vitals` — Emergency vital sign changes (crisis)
- `end_case` — Terminate the simulation (death, discharge, resolution)

**Example — Cascading effects**:

NODE 08 (steroids) sets `wrong_treatment_steroids` flag. This causes NODE 06's timer to accelerate by 60 minutes (via `modify_timer` effect). The false improvement makes the real crisis arrive sooner. The player's mistake has a mechanical consequence encoded in the effect chain.

**Design principle**: Effects are the programming language of the case. Nodes are data. Effects are instructions.

### 7. Vitals: Emergent State from Active Nodes

Vital signs are **computed, not stored**.

```python
baseline_vitals = patient.arriving_vitals

current_vitals = baseline + sum(active_node_modifiers)
```

Each active node can declare `vital_signs` — what it wants vitals to be. Satori computes current vitals as:

1. Start with baseline (patient's arriving vitals)
2. For each active node, take its vital modifiers
3. Sum them (or apply "worst wins" logic per vital type)

**Example**:

```
Baseline: HR 92, BP 138/88
NODE 06 active at T+120: HR +10, BP +20/+10
Current vitals: HR 102, BP 158/98
```

If NODE 08 (steroids) activates: HR -10 (temporary improvement). Current vitals: HR 92, BP 138/88. Patient looks stable! Then NODE 08's timer expires, modifier reverses, NODE 06 accelerates. The brief stabilization was a trap.

**Design principle**: Vitals are **emergent from active nodes**. Satori doesn't track "current BP" as a stored variable. It recomputes it every time from the active node set. This prevents state desync and makes the simulation verifiable: you can always reconstruct vitals from the node activation history.

### 8. Conditions: Boolean Logic Without Expression Parsing

Conditions are how nodes check state before activating or revealing.

```python
class Condition:
    type: Literal[
        "flag_set",
        "flag_not_set",
        "node_active",
        "node_revealed",
        "node_expired",
        "time_elapsed",
        "vital_threshold"
    ]
    target: str
    value: Optional[Any]
    comparator: Optional[Literal["gt", "lt", "gte", "lte", "eq"]]
```

**ConditionPath = AND**: All conditions in a path must be true.  
**ActivationRule.paths = OR**: Any path can satisfy activation.

**Example**:

```python
# NODE 09 (thigh X-ray) activation
paths = [
    [Condition(type="flag_set", target="neurocysticercosis_suspected")],
    [
        Condition(type="flag_set", target="undercooked_pork_exposure"),
        Condition(type="flag_set", target="lesion_found")
    ]
]
```

This reads: Activate if `neurocysticercosis_suspected` is set **OR** if both `undercooked_pork_exposure` AND `lesion_found` are set.

**Why not a full expression parser?**

Because OR-of-ANDs is sufficient for every case we've designed. Adding full boolean expressions (`(A AND B) OR (C AND NOT D)`) would complicate the schema and implementation without adding expressive power we need. Simplicity is a design goal.

**Design principle**: Provide just enough logic to express real cases, no more.

### 9. Outcome Evaluation: Multi-Dimensional Scoring

Outcomes are **not binary**. There's no single "win" or "lose". Cases can end in:

- OPTIMAL — everything done right, quickly, with empathy
- GOOD — patient survives, correct treatment, but delays caused harm
- PARTIAL — patient survives but with lasting damage
- FAILURE — patient dies

```python
class OutcomeTier:
    tier: Literal["optimal", "good", "partial", "failure"]
    required_flags: Optional[list[str]]
    excluded_flags: Optional[list[str]]
    time_constraints: Optional[list[TimeConstraint]]
    narrative: str
```

**Example — OPTIMAL tier**:

```python
required_flags: ["diagnosis_confirmed", "correct_treatment_started", "family_engaged"]
time_constraints: [TimeConstraint(flag="correct_treatment_started", before_minutes=120)]
```

To achieve OPTIMAL: player must confirm diagnosis, start correct treatment, engage with family, AND start treatment within 120 minutes of case start.

**Why this matters**: The system rewards thoroughness, speed, and empathy. A player who rushes and gets the diagnosis right but ignores Diego achieves GOOD, not OPTIMAL. A player who takes too long achieves PARTIAL even if everything else is right. The outcome reflects the full pattern of choices, not just medical correctness.

---

## Worked Example: NODE 06 (Headache Progression)

This node demonstrates the full architecture in action.

```json
{
  "id": "node_06",
  "type": "progression",
  "content": {
    "narrative_text": "",
    "structured_data": null
  },
  "activation": {
    "paths": [[
      {"type": "flag_set", "target": "headaches_two_weeks"}
    ]],
    "starts_active": false
  },
  "reveal": null,
  "timer": {
    "duration_minutes": 180,
    "pause_conditions": [
      {"type": "flag_set", "target": "correct_treatment_started"}
    ],
    "stages": [
      {
        "at_minutes": 60,
        "effects": [],
        "vital_signs": {
          "heart_rate": 97,
          "blood_pressure_systolic": 148,
          "blood_pressure_diastolic": 93
        }
      },
      {
        "at_minutes": 120,
        "effects": [],
        "vital_signs": {
          "heart_rate": 102,
          "blood_pressure_systolic": 158,
          "blood_pressure_diastolic": 98
        }
      },
      {
        "at_minutes": 150,
        "effects": [],
        "vital_signs": {
          "heart_rate": 107,
          "blood_pressure_systolic": 168,
          "blood_pressure_diastolic": 103
        }
      }
    ],
    "on_expire": [
      {"type": "activate_node", "target": "node_07"}
    ]
  },
  "vital_signs": null,
  "effects": {},
  "outcome_weight": null
}
```

**How it works**:

1. **Activation**: When player does general history (NODE 01), flag `headaches_two_weeks` is set. NODE 06 activates. Timer starts.
    
2. **Reveal**: `reveal: null` means this node is never revealed to the player. It's invisible. But it's running.
    
3. **Timer stages**:
    
    - At T+60: Vitals shift to HR 97, BP 148/93 (slight deterioration)
    - At T+120: HR 102, BP 158/98 (worsening)
    - At T+150: HR 107, BP 168/103 (significant hypertension)
    - At T+180: Timer expires → activates NODE 07 (seizure)
4. **Pause condition**: If `correct_treatment_started` flag is set (player gives albendazole), timer pauses. Deterioration stops. Patient stabilizes.
    
5. **Emergency override**: If `wrong_treatment_steroids` is set (NODE 08), another node modifies this timer, accelerating it by 60 minutes. Crisis arrives at T+120 instead of T+180.
    

**What this teaches the player**:

- **Time matters**: Every action costs time. Ordering unnecessary tests delays critical treatment. Waiting to see what happens is dangerous.
    
- **Vitals are signals**: The player sees BP creeping up. They might not know why. But the data is telling them: something is worsening.
    
- **Silent progression**: The player never sees "headache is getting worse" as a message. They see vitals. They see time passing. They have to infer the deterioration.
    
- **False improvements are traps**: NODE 08 (steroids) makes vitals improve briefly, then makes NODE 06 accelerate. The lesson: treating symptoms without understanding mechanism makes things worse.
    

**Architectural elegance**: This node is ~20 lines of JSON. It encodes progressive deterioration, pause conditions, crisis triggers, and treatment interaction. The behavior is complex. The structure is simple.

---

## Why This Structure Matters

### 1. Determinism Despite Complexity

The case is a graph of 12 nodes, dozens of flags, multiple timers, conditional reveals, and branching outcomes. Yet it's **deterministic**: same actions, same timing, same result. Every time.

This is possible because:

- State is explicit (flags, active nodes, timers)
- Transitions are declarative (activation rules, effects)
- Time is discrete (player actions advance clock by fixed amounts)
- Computation is pure (vitals computed from active nodes, no hidden state)

Satori doesn't "decide" anything. It evaluates conditions and applies effects. The case definition is the program. Satori is the interpreter.

### 2. Replayability Through Variation

The same structure supports infinite cases. Change the:

- Patient identity and presentation
- Ground truth diagnosis
- Node content (what information, when)
- Flag wiring (what unlocks what)
- Timer durations (how fast things deteriorate)
- Outcome conditions (what constitutes success)

The structure remains the same. The experience changes completely.

A different case might have:

- 8 nodes instead of 12
- No relational nodes
- Faster progression (90-minute crisis instead of 180)
- Different anchoring trap (normal labs that hide the diagnosis)
- Outcome that depends on ethical choices, not just medical correctness

The schema is expressive enough for all of these.

### 3. Clean LLM Integration

The schema separates:

- What Satori needs (structure)
- What the LLM generates (narrative)
- What Internal Affairs renders (presentation)

**Current Phase 1 approach**: LLM generates both structure and narrative at case creation time. Both are frozen.

**Future Phase 3 approach**: LLM generates structure at case creation time (frozen). LLM generates narrative at play-time (dynamic). The schema supports both because narrative fields are isolated.

The boundary is explicit: `content.narrative_text`, `patient.appearance`, `outcome_tier.narrative` are narrative. Everything else is structure.

### 4. Human and Medical Parity

The schema doesn't privilege medical nodes. Relational, emotional, and behavioral nodes are structurally identical.

This design choice has consequences:

- Cases can be **primarily relational** — a domestic violence victim who won't disclose until trust is built, where the medical diagnosis is straightforward but the human barriers are complex.
    
- Cases can be **ethically weighted** — a patient who refuses necessary treatment for religious reasons, where the "correct" medical outcome conflicts with patient autonomy.
    
- Cases can be **emotionally consequential** — a patient who survives but whose family fractures, where the medical success is a human failure.
    

The schema supports all of these because nodes are generic. The medical mystery simulator can teach clinical reasoning AND ethical reasoning AND human systems thinking. The same structure.

### 5. Portfolio Artifact

This schema demonstrates:

**System Design**: Separating concerns (structure/narrative, generation/execution, logic/presentation), defining clear contracts between components, preventing implicit coupling.

**Data Modeling**: Encoding complex behavior in declarative structures, balancing expressiveness and simplicity, choosing the right level of abstraction.

**Deterministic Simulation**: Discrete event systems, concurrent timers, emergent state, condition evaluation, effect propagation.

**Domain Modeling**: Translating real-world complexity (medical cases, human dynamics, time pressure, uncertainty) into executable structures.

**API Design**: Schema as contract, validation as gate, frozen artifacts as immutable inputs, clear layer boundaries.

This is not a toy project. The schema is production-grade. The thinking is architectural. The tradeoffs are explicit.

---

## Open Questions and Future Extensions

### 1. Timer Stage Flexibility

Current design: Stages are fixed points (T+60, T+120, T+150).

Future possibility: Stages trigger on **vital thresholds** instead of time. "When BP > 160/100, activate next stage." This makes progression condition-dependent rather than time-dependent.

Tradeoff: More expressive, but harder to reason about. Time-based stages are predictable. Condition-based stages can create feedback loops (deterioration triggers stage, stage worsens vitals, worse vitals trigger next stage faster).

### 2. Multi-Path Optimization

Current design: One optimal path in `ground_truth.optimal_path`.

Future possibility: Multiple optimal paths of different styles (fast aggressive, slow thorough, relationship-first).

Challenge: Outcome evaluation becomes more complex. "Did the player achieve ANY optimal path?" vs "Did they achieve the FASTEST optimal path?"

### 3. Dynamic Action Availability

Current design: Actions are gated by flags (`neurocysticercosis_suspected` unlocks thigh X-ray).

Future possibility: Actions have **prerequisites** declared in the schema (not just unlocks). "CT requires stable vitals" or "Discharge requires resolved crisis."

Benefit: More medical realism. Players can't order imaging on a crashing patient.

Risk: Over-constraining. If prerequisites are too strict, players feel railroaded.

### 4. Nested Timers

Current design: Timers are flat (one timer per node).

Future possibility: Sub-timers within nodes. "After treatment starts, improvement takes 12 hours with checkpoints at 2h, 6h, 12h."

Use case: Long-running treatments with observable milestones.

Implementation: Add `timer.sub_timers` array, similar to `timer.stages` but with independent durations.

### 5. Probabilistic Elements

Current design: Fully deterministic.

Future possibility: Optional randomness at case generation time (frozen before play). "This case has a 30% chance of spontaneous improvement at T+90."

Why: Models real medical uncertainty. Same diagnosis, different patient trajectories.

Constraint: Randomness must be **seeded and frozen**. Same seed = same case. Replayability preserved.

---

## Conclusion

The case definition schema is a **declarative concurrent state machine** encoded in JSON. It models medical cases as node graphs with activation rules, reveal conditions, timers, effects, and emergent vital signs.

It's deterministic enough to replay identically.  
It's expressive enough to model branching outcomes, time pressure, conditional unlocks, and human dynamics.  
It's simple enough to hand-write (as demonstrated in the example case).  
It's structured enough to generate programmatically.

It separates structure (what Satori executes) from narrative (what Internal Affairs renders), enabling clean LLM integration without sacrificing determinism.

It's the foundation everything else is built on.

And it works.