# Example Case: Node Graph Architecture Validation

## Purpose

This document describes a complete case using the node-graph architecture discussed in Ho 01 planning. It is NOT JSON. It is the case described in plain language using the node model, so we can verify the architecture captures the kind of case we want before formalizing the schema.

The case is inspired by the House MD pilot but adapted and simplified to ~10 nodes for validation purposes.

---

## Patient Context (Static)

```
patient:
  name: Maria Santos
  age: 28
  sex: Female
  setting: Emergency Department
  chief_complaint: "Sudden speech difficulty and seizure at work"
  appearance: "Young woman, alert but frightened, slightly disheveled,
               wearing a waitress uniform. Wedding ring on left hand."
  arriving_vitals:
    hr: 92
    bp: 138/88
    temp: 99.1
    rr: 18
    o2_sat: 97%
  triage_note: "Patient seized at restaurant where she works. Coworkers
                called 911. Speech was slurred on arrival. No prior
                seizure history per coworker."
```

## Metadata

```
metadata:
  difficulty: beginner-intermediate
  estimated_duration: 20-30 minutes (simulated time: ~6 hours)
  learning_objectives:
    - Don't anchor on the first imaging finding
    - Environmental and dietary history matters
    - Patient assumptions (cultural, religious) can mislead
    - A wrong treatment can cause real harm
  dramatic_tone: medical_mystery
  content_boundaries:
    - No graphic content
    - Death is possible but not gratuitous
```

## Ground Truth

```
ground_truth:
  diagnosis: Neurocysticercosis (tapeworm larvae in brain)
  mechanism: Patient consumed undercooked pork. Tapeworm eggs
             entered bloodstream and lodged in brain tissue.
             Dying larvae triggered immune response causing
             edema, seizures, and progressive neurological decline.
  key_insight: Initial imaging shows a lesion that looks like a tumor.
               The correct diagnosis depends on discovering dietary
               exposure to undercooked pork — which is only findable
               through environmental history or a very specific
               dietary history question.
  optimal_path:
    - History (general) → learn chief complaint details
    - Physical exam (neuro) → confirm focal deficits
    - Labs (CBC with diff) → notice eosinophil elevation
    - History (dietary/environmental) → learn about pork consumption
    - Consider neurocysticercosis
    - Imaging (X-ray of thigh) → confirm larvae in muscle
    - Treat with albendazole
  critical_time: 180 minutes. After 180 min without correct treatment,
                 patient enters irreversible decline.
```

---

## Action Time Costs

```
action_costs:
  history_general: 15 min
  history_focused: 10 min  (substance, dietary, sexual, family, etc.)
  physical_exam_general: 15 min
  physical_exam_focused: 10 min  (neuro, cardiac, abdominal, etc.)
  order_labs: 2 min to order, 45 min for results
  order_imaging_xray: 2 min to order, 20 min for results
  order_imaging_ct: 2 min to order, 45 min for results
  order_imaging_mri: 2 min to order, 90 min for results
  start_treatment: 5 min
  consult: 5 min to call, 60 min for consult to arrive
  wait_observe: player chooses duration (15/30/60 min increments)
  emergency_intervention: 2 min
```

---

## Nodes

### NODE 01: Chief Complaint Details

**Type:** history **Content:** "Patient reports she was taking an order when words 'stopped making sense.' She felt confused, then her right arm went stiff, then she doesn't remember anything until the ambulance. She's had headaches for about two weeks — bad ones, worse than usual. She assumed it was stress."

**Activation:** Always active (starting node) **Reveal:** action = history_general **Timer:** None **Effects on reveal:**

- Set flag: `headaches_two_weeks`
- Set flag: `seizure_with_aphasia`
- Activate NODE 06 (Headache Progression)

---

### NODE 02: Neurological Exam Findings

**Type:** medical_finding **Content:** "Right-sided weakness — grip strength 3/5 on right, 5/5 on left. Mild expressive aphasia — she searches for words, occasionally substitutes wrong ones. Pupils equal and reactive. No neck stiffness. Babinski positive on right."

**Activation:** Always active (starting node) **Reveal:** action = physical_exam_focused:neuro **Timer:** None **Effects on reveal:**

- Set flag: `focal_neuro_deficit`
- Set flag: `right_sided_weakness`

---

### NODE 03: Initial CT Findings — The Misleading Lesion

**Type:** imaging **Content:** "CT head with contrast shows a 2.3cm ring-enhancing lesion in the left parietal lobe with surrounding edema. Radiologist preliminary read: 'Suspicious for primary brain neoplasm vs. abscess. Recommend MRI for further characterization.'"

**Activation:** Always active **Reveal:** action = order_imaging_ct (results arrive at current_time + 45 min) **Timer:** None **Effects on reveal:**

- Set flag: `lesion_found`
- Set flag: `tumor_suspected`
- **This is the anchoring trap.** The CT looks like cancer. Most players will pursue oncology from here. The correct path requires looking past this finding.

---

### NODE 04: Lab Results — The Subtle Clue

**Type:** lab_result **Content:** "CBC: WBC 9.8 (normal), but differential shows eosinophils at 8% (normal: 1-3%). CMP: within normal limits. ESR mildly elevated at 28."

**Activation:** Always active **Reveal:** action = order_labs:cbc (results arrive at current_time + 45 min) **Timer:** None **Effects on reveal:**

- Set flag: `eosinophilia`
- **Teaching moment:** Elevated eosinophils suggest parasitic infection or allergic reaction — NOT cancer. A player who notices this and connects it to the ring-enhancing lesion should reconsider the tumor hypothesis. Most beginners will overlook this.

---

### NODE 05: Dietary History — The Key Unlock

**Type:** history **Content:** "Maria hesitates, then says her mother-in-law makes traditional dishes — including carne de cerdo that's sometimes still pink in the middle. 'She says that's how it's supposed to be. I didn't want to be rude. I've been eating there every Sunday for two years since we got married.'"

**Activation:** Always active **Reveal:** action = history_focused:dietary **Conditions:** None — but most players won't think to ask about diet unless they've noticed the eosinophilia (NODE 04) or have other reason to suspect parasitic infection. **Timer:** None **Effects on reveal:**

- Set flag: `undercooked_pork_exposure`
- Set flag: `dietary_history_taken`
- If `eosinophilia` is also set: Set flag: `neurocysticercosis_suspected`

---

### NODE 06: Headache Progression (Silent Deterioration)

**Type:** progression **Content:** Not directly revealed to player — this node drives the clock.

**Activation:** Activates when `headaches_two_weeks` is set (via NODE 01) **Reveal:** Not directly revealable. Effects are observed through vitals and through NODE 07 if it triggers. **Timer:** 180 minutes from case start

- At T+60: Vitals modifier: HR +5, BP +10/5
- At T+120: Vitals modifier: HR +10, BP +20/10, new symptom: vomiting
- At T+150: Vitals modifier: HR +15, BP +30/15, new symptom: vision changes
- At T+180: Trigger NODE 07 (Seizure Crisis) **Pause condition:** `correct_treatment_started` flag is set **Effects on expire:** Activate NODE 07

---

### NODE 07: Seizure Crisis

**Type:** progression **Content:** "Maria suddenly stops mid-sentence. Her eyes roll back. She seizes — full tonic-clonic, violent. The monitor alarms. HR spikes to 140. BP crashes to 80/50. O2 sat drops to 88%."

**Activation:** Triggered by NODE 06 timer expiry, OR if `wrong_treatment_steroids` flag is set (steroids accelerate the crisis by 60 minutes) **Reveal:** Automatic — plays when activated. Player must respond. **Timer:** 5 minutes. If no emergency intervention, activate NODE 10 (Death). **Pause condition:** action = emergency_intervention (benzodiazepines/airway) **Effects on reveal:**

- Vitals override: HR 140, BP 80/50, O2 88%, RR 6
- Set flag: `crisis_active`
- All non-emergency actions become unavailable until crisis resolved **Effects on intervention:**
- Vitals partially stabilize: HR 110, BP 95/60, O2 94%
- Set flag: `post_crisis`
- Timer on NODE 06 paused (bought time, not cured)
- Clock adds 30 minutes to remaining time before next crisis

---

### NODE 08: The Wrong Treatment — Steroids

**Type:** intervention_response **Content:** "Maria improves dramatically within hours of starting steroids. Her speech clears. Headache subsides. She smiles for the first time since admission. 'See? I'm better. Can I go home?'"

**Activation:** When player starts treatment with steroids (a reasonable but incorrect choice if they believe it's vasculitis or tumor-related edema) **Reveal:** Automatic — plays when steroids are administered. **Timer:** 60 minutes after administration. Then: "Maria's improvement reverses suddenly. The headache returns, worse. She becomes confused. The edema is worsening — the steroids suppressed the immune system, allowing the parasite to flourish." **Effects on activation:**

- Set flag: `wrong_treatment_steroids`
- Immediate vitals: HR -10, BP normalizing (false improvement)
- At timer expiry: NODE 06 timer accelerated by 60 minutes
- Set flag: `steroid_rebound`

---

### NODE 09: Confirmation — Thigh X-Ray

**Type:** imaging **Content:** "X-ray of right thigh shows two small, calcified ovoid densities in the muscle tissue consistent with encysted larvae. Radiologist note: 'Findings consistent with cysticercosis.'"

**Activation:** Requires `neurocysticercosis_suspected` flag OR (`undercooked_pork_exposure` AND `lesion_found`) **Reveal:** action = order_imaging_xray:extremity (results arrive at current_time + 20 min) **Conditions:** Player must specifically order an extremity X-ray, not a head X-ray. This is available as an option only when activation conditions are met. **Timer:** None **Effects on reveal:**

- Set flag: `diagnosis_confirmed`
- Set flag: `cysticercosis_confirmed`

---

### NODE 10: Correct Treatment — Albendazole

**Type:** intervention_response **Content:** "You start Maria on albendazole. You warn her: the side effects can include abdominal pain, nausea, headache, dizziness, and fever. She nods. 'If it gets rid of whatever's in my head, I'll take it.' Over the next 24 hours, her symptoms slowly improve. The aphasia fades. The headaches ease. She asks to call her husband."

**Activation:** Requires `diagnosis_confirmed` OR `neurocysticercosis_suspected` **Reveal:** action = start_treatment:albendazole (available only when activation conditions are met) **Timer:** None **Effects on activation:**

- Set flag: `correct_treatment_started`
- Pauses NODE 06 timer
- Vitals normalize over next 60 simulated minutes
- If `crisis_active`: stabilizes crisis

---

### NODE 11: Patient Death

**Type:** outcome **Content:** "Maria seizes again. This time the interventions don't hold. Intracranial pressure rises beyond what the brain can tolerate. Despite everything your team does, she herniates. Time of death is called. She was 28 years old."

**Activation:** NODE 07 timer expires without intervention, OR third crisis event without correct treatment **Reveal:** Automatic. Case ends. **Effects:** Case terminates. Outcome = FAILURE.

---

### NODE 12: Maria's Husband (Relational)

**Type:** relational **Content:** "A man arrives in the waiting room, agitated, speaking rapid Spanish to the front desk. He's Maria's husband, Diego. He's frightened and angry — he wants to know what's happening. If approached with respect and given honest information, he becomes cooperative. He volunteers: 'My mother cooks for us every Sunday. Maria always eats everything — she doesn't want to offend her.'"

**Activation:** Activates at T+30 (he arrives at the hospital) **Reveal:** action = history_focused:family OR when player interacts with waiting room/family **Timer:** 90 minutes from activation. If not engaged: "Diego becomes increasingly agitated. He's now shouting at the nurses' station. Security is called. He's escorted out. You've lost access to a family informant." **Pause condition:** Player engages with him before timer expires **Effects on reveal:**

- Set flag: `family_engaged`
- Set flag: `sunday_meals_known`
- If NOT `dietary_history_taken`: provides an alternate path to `undercooked_pork_exposure` (Diego mentions the pork)
- Contributes to relational outcome score

---

## Vital Sign Computation

```
baseline_vitals:
  hr: 92
  bp_sys: 138
  bp_dia: 88
  temp: 99.1
  rr: 18
  o2_sat: 97

current_vitals = baseline + sum(active_node_modifiers)

Example at T+120 with no treatment:
  NODE 06 modifier at T+120: HR +10, BP +20/+10
  Current: HR 102, BP 158/98, Temp 99.1, RR 18, O2 97%

Example at T+120 with steroids given at T+60:
  NODE 08 modifier: HR -10, BP normalizing... then reverses
  NODE 06 accelerated: crisis arrives 60 min earlier
  Current: depends on when the rebound hits
```

---

## Outcome Evaluation

```
outcome_tiers:

  OPTIMAL:
    required_flags:
      - diagnosis_confirmed
      - correct_treatment_started
      - family_engaged
    time_constraint: correct_treatment_started before T+120
    description: "Maria recovers fully. The parasitic infection is
      identified and treated early. Diego is informed and involved.
      The family understands what happened and how to prevent it.
      Maria returns to work within weeks."

  GOOD:
    required_flags:
      - correct_treatment_started
    excluded_flags:
      - patient_death
    time_constraint: correct_treatment_started before T+180
    description: "Maria recovers, but the delay caused additional
      neurological damage. She has residual word-finding difficulty
      that may or may not resolve. The parasites are treated."

  PARTIAL:
    conditions:
      - crisis_active was triggered but resolved
      - correct_treatment_started eventually
      - OR: wrong_treatment_steroids caused rebound but recovered
    description: "Maria survives but with significant complications.
      The steroid rebound or delayed diagnosis caused lasting harm.
      She may not return to full function."

  FAILURE:
    conditions:
      - NODE 11 activated (patient_death)
    description: "Maria died. The parasitic infection went undiagnosed
      too long. The brain edema became unsurvivable."

  scoring:
    medical_nodes_resolved: [01, 02, 03, 04, 05, 09, 10] (out of 7)
    relational_nodes_resolved: [12] (out of 1)
    harmful_actions: [08 - steroids] (penalty)
    time_efficiency: how quickly correct treatment started
    crisis_management: was NODE 07 handled if triggered
```

---

## What This Example Validates

1. **The node system works.** Each node is independent with its own lifecycle, but they interact through flags and timers. The graph emerges from the wiring, not from a rigid tree structure.
    
2. **Conditional reveal works.** NODE 05 (dietary history) is always technically available, but players won't think to ask unless other evidence points them there. NODE 09 (thigh X-ray) is gated by flags that require prior discovery.
    
3. **Time pressure works.** NODE 06 is always ticking. The player doesn't see it, but every action they take costs time, and the patient is deteriorating. This creates tension without the player needing to know the exact mechanism.
    
4. **Wrong answers have consequences.** NODE 08 (steroids) feels like success — the patient improves! — then makes everything worse. This is the Grey's Anatomy moment: the gut-punch reversal that teaches why anchoring on first impressions is dangerous.
    
5. **Relational nodes integrate naturally.** NODE 12 (Diego) is both a relational element and an alternative diagnostic pathway. Engaging with the family isn't just "nice" — it's clinically useful. And ignoring them has consequences.
    
6. **Outcomes are proportional.** The same case can end in full recovery, partial recovery, or death — depending entirely on player choices and timing. No single action determines the outcome; it's the pattern.
    
7. **The schema structure is uniform.** Every node — medical, relational, progression, intervention — uses the same anatomy. The complexity is in the content and wiring, not in structural variation.
    

---

## Open Design Questions for Schema Formalization

1. **Flag syntax:** How should conditions be expressed? Simple AND/OR logic? More complex boolean expressions? The example uses informal language — the schema needs a formal condition grammar.
    I dont totally understand what you are asking. here.
    
2. **Vitals modifier stacking:** When multiple nodes modify the same vital, do they simply add? Are there caps? Can a modifier be multiplicative? The example assumes simple addition.
    
3. **Action availability:** How does the schema express that certain actions (like ordering a thigh X-ray for cysticercosis) only become available when certain flags are set? Is this part of the node, or part of a separate action-availability system?
    
4. **Timer precision:** NODE 06 has sub-timer effects (different things at T+60, T+120, T+150, T+180). Is this one node with staged effects, or should it be multiple linked nodes? Staged effects are simpler; linked nodes are more flexible.
    
5. **Narrative text:** Where does the LLM narration fit? The node content fields have static text — is that the fallback, with LLM narration as an enhancement layer? Or does the node only contain structured data, with all text generated by the LLM?