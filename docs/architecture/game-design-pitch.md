# Satori Internal Affairs — Game Design Overview

**Genre:** Real-time resource management / deduction / crisis triage
**Platform:** Web (SvelteKit), mobile-planned
**Audience:** Teenage girls (15–18), med-curious players, medical drama fans
**Tone:** *Grey's Anatomy* meets *Return of the Obra Dinn*
**Status:** Engine functional, UI in development. Seeking design feedback.

---
## Origin

This project started in a hospital waiting room. My daughter and I were killing time playing a medical mystery with ChatGPT — she'd ask questions, I'd try to steer it, and it kept either collapsing into "You got it!" or going completely off the rails. I found myself writing increasingly strict prompts just to get it to behave like a real case. She did better with multiple choice. I kept wanting the drama of genuine uncertainty. Eventually I realized I was doing all the work anyway — I was essentially authoring the case in real time just to get the LLM to execute it halfway decently. So I asked a different question: what if the structure was airtight and the LLM was only responsible for the voice? That question turned into an engine. The engine turned into a schema. The schema turned into twelve nodes, a flag system, hidden timers, and a 28-year-old woman named Maria Santos with tapeworm larvae in her brain. What I built first was the mechanical truth of the case. What I'm still figuring out is how to make a player feel it.

---

## Elevator Pitch

You are the doctor. A patient arrives. You don't know what's wrong.

Everything you do costs time. Tests take minutes to hours. Consultations take longer. While you're waiting for the CT, the patient's blood pressure is climbing and you don't know why. Her husband arrives in the waiting room screaming. The lab results come back with a number that doesn't fit your theory. You ordered the wrong treatment twenty minutes ago and it's about to make everything worse.

You can't see the clocks that matter. You can only see the ones you set.

**The core loop is triage under uncertainty:** choose what to investigate, when to act, and when to wait — while parallel timers you can't see are running the patient toward crisis or death.

---

## Core Mechanic: Concurrent Hidden Timers + Visible Action Economy

The game runs on a **discrete-event simulation** with player-driven turn structure. Each player action advances a shared game clock by a variable amount (examining a patient: 10 min; ordering a CT: 2 min to order, 45 min until results arrive; emergency intervention: 2 min). Between player actions, all active timers tick forward by the elapsed amount.

The player sees:

- **Diegetic timers** — things their character knows about. "CBC results pending — ~30 minutes." "Radiology called — MRI available in 90 minutes." These are countdowns the player chose to start.
- **Vitals** — heart rate, BP, O₂ sat, temperature. These update after every action. They're the smoke detector. They don't tell you where the fire is.
- **Narrative events** — what happened as a result of their last action, plus anything that triggered in the elapsed time.

The player does NOT see:

- **Biological deterioration timers** — the patient is getting worse on a schedule. The player infers this from worsening vitals and emerging symptoms, but never sees the countdown.
- **NPC behavior timers** — a family member arrives at T+30 and leaves at T+120 if not engaged. A consultant takes 60 minutes to arrive. These are happening in the background.
- **Cascade triggers** — when a hidden timer expires, it can activate new nodes (seizure events, decompensation, death). The player doesn't know the trigger conditions.

**This is the central asymmetry.** The player controls what they spend time on. The game controls what's happening while they spend it. Tension comes from the gap between "what I've ordered" and "what I don't know is happening."

### Closest Mechanical Analogues

| Game | Shared Mechanic | Key Difference |
|------|----------------|----------------|
| **FTL: Faster Than Light** | Multiple concurrent subsystem crises, crew assignment as resource | FTL is real-time with pause; this is turn-based with variable time costs |
| **Pandemic** (board game) | Independent disease tracks advancing between turns, triage decisions | Pandemic tracks are visible; here, deterioration is hidden |
| **XCOM** (tactical layer) | Fog of war, acting on incomplete intel, countdown timers | XCOM is spatial; this is informational |
| **Obra Dinn** | Building a deductive theory from fragments, committing identifications | Obra Dinn is untimed; here, delay kills |
| **Papers, Please** | Time scarcity as core resource, scrutiny vs. throughput tradeoff | Papers Please has throughput pressure; this has parallel process pressure |
| **This War of Mine** | Concurrent survival timers (hunger, morale, injury) advancing independently | TWoM timers are visible; here they're partially hidden |
| **Spirit Island** | Slow powers vs. fast powers, planning around delayed effects | Spirit Island's delay is strategic choice; here delay is environmental |

**What's unusual:** Most deduction games are untimed. Most time-pressure games have visible state. This game hides the state that's killing you and makes you deduce it from indirect signals — while your own actions are creating the timeline.

---

## Information Architecture: What the Player Knows, and When

The game is **not** about having the right answer. It's about the decision to act on an incomplete answer.

### Layer 1: Given Information (Free)

The patient arrives with a chief complaint, an appearance, vitals, and a triage note. This is your starting position. It's designed to suggest one or two obvious theories.

### Layer 2: Revealed Information (Costs Time)

Every clinical action reveals something — but each has a time cost and some have result delays. Taking a history: 10–15 minutes. Ordering labs: 2 minutes to order, 45 minutes until results. Ordering imaging: 2 minutes to order, 20–90 minutes depending on modality. The player is always choosing: "Is this information worth the time it costs?"

### Layer 3: Gated Information (Costs Time + Requires Prior Discovery)

Some nodes only become available after specific flags are set. You can't order a thigh X-ray for cysticercosis until you have reason to suspect it — which requires connecting eosinophilia (from the CBC) to the ring-enhancing lesion (from the CT) to dietary exposure (from a history question most players won't think to ask). The game doesn't tell you what to look for. You have to build the theory yourself.

### Layer 4: Hidden State (Inferred Only)

The patient's biological trajectory. Timer stages. NPC arrivals and departures. Cascade conditions. The player never sees these directly. They see: vitals changing, symptoms appearing, characters arriving or leaving. The challenge is reading the indirect signals.

**Design intent:** This four-layer structure means the player is always operating in partial fog. They're making decisions with 40–70% of the picture, and the thing they're missing is often the thing that's about to kill the patient.

---

## Turn Structure

This is **not** real-time. It's **turn-based with variable-length turns.**

1. **Player reviews current state:** vitals, recent events, pending results, available actions.
2. **Player chooses an action** from a structured menu (not free text). Each action has a type and optional subcategory (e.g., `physical_exam_focused:neuro`, `order_labs:cbc`, `history_focused:dietary`).
3. **The game clock advances** by the action's time cost.
4. **All active timers tick.** Hidden deterioration progresses. Pending results that are now ready get revealed. NPC timers advance. Any nodes whose activation conditions are now met become active.
5. **Events fire.** The player sees: results arriving, symptoms changing, vitals updating, characters appearing, emergencies triggering.
6. **New state is presented.** Available actions may have changed (new actions unlocked, some locked by emergency conditions). The player is back at step 1.

### Emergency Interrupts

When a crisis node fires (e.g., seizure), the game enters an **emergency state:**

- Most actions are locked (you can't take a dietary history while the patient is seizing)
- Only emergency actions are available (airway management, benzodiazepines, etc.)
- A visible, short countdown starts (e.g., 5 minutes to intervene or the patient dies)
- This is the only time a hidden timer becomes visible — because the emergency itself is visible

The emergency interrupt is the game's equivalent of a boss phase. It forces the player out of their investigation mode and into immediate reaction.

---

## The Dashboard (Proposed UI Concept)

The UI I'm envisioning is less "text adventure" and more **mission control.** Think: a medical strategy dashboard where you're managing parallel workstreams.

### Working Concept Layout

```
┌──────────────────────────────────────────────────────────┐
│  VITALS STRIP (always visible, updates every turn)       │
│  HR: 102↑  BP: 158/98↑  Temp: 99.1  RR: 18  O₂: 97%   │
├──────────────┬───────────────────────┬───────────────────┤
│              │                       │                   │
│  ACTIVE      │    NARRATIVE FEED     │   PENDING         │
│  CONCERNS    │                       │   RESULTS         │
│              │  Latest events,       │                   │
│  • Seizure   │  findings, dialogue   │  ⏱ CBC: ~30 min  │
│    history   │                       │  ⏱ CT: ~15 min   │
│  • R-sided   │  [scrollable]         │                   │
│    weakness  │                       │  CONSULTS         │
│  • Ring      │                       │  ⏱ Neuro: ~45min │
│    lesion    │                       │                   │
│  • Eosino-   │                       │                   │
│    philia    │                       │                   │
│              │                       │                   │
├──────────────┴───────────────────────┴───────────────────┤
│  ACTION BAR                                              │
│  [History ▾] [Exam ▾] [Labs ▾] [Imaging ▾] [Treat ▾]   │
│  [Consult ▾] [Wait/Observe] [Emergency]                 │
│                                              Clock: T+75 │
└──────────────────────────────────────────────────────────┘
```

**Active Concerns** = the player's accumulating evidence board. Every revealed finding appears here as a card. This is the player's "whiteboard" — what they know so far.

**Pending Results** = diegetic timers. Things the player ordered that haven't come back yet. Countdown is approximate ("~30 min" not "27 min") to preserve some uncertainty.

**Narrative Feed** = the story. Patient dialogue, exam descriptions, event narration. This is where the *Grey's Anatomy* lives — emotional texture, character moments, dramatic beats. Generated by an LLM from deterministic game state.

**Action Bar** = structured menus with subcategories. Dropdowns expand to show available options. Locked actions are grayed out or hidden. During emergencies, the bar collapses to emergency-only options.

**Does this dashboard pattern have a name?** I'm calling it "mission control triage" but I don't know if there's an established term for this kind of concurrent-process-management UI in games. It feels adjacent to RTS base management or FTL's ship view, but oriented around information rather than spatial positioning.

---

## Case Architecture (For the Technically Curious)

Each case is a **frozen JSON artifact** — a directed graph of nodes with flag-based edges, independent timers, and effect chains. The game engine is a deterministic interpreter: same case + same actions = same outcome, every time.

- **Nodes** are the atomic units. Each represents one piece of case reality (a finding, a lab result, a patient's secret, a family member's arrival, a biological process, a treatment response).
- **Flags** are the wiring. Nodes set flags when they activate or reveal. Other nodes' activation conditions check for flags. This creates emergent dependency graphs without requiring explicit tree structures.
- **Timers** are the pressure. Each node can have a countdown that ticks with the game clock. Timer stages produce escalating effects. Timer expiry can cascade into new node activations (deterioration → crisis → death).
- **Effects** are the consequences. Revealing a node, expiring a timer, or applying a treatment fires a list of effects: set a flag, activate a node, lock an action, override vitals, end the case.

No AI is involved in game logic. The LLM provides narrative text (patient dialogue, exam descriptions, emotional texture) from deterministic state — it's the voice actor, not the game designer. Cases are generated by AI from medical databases and structured seeds, but once frozen, they're immutable. The AI cannot invent facts, alter outcomes, or change what the player discovers.

**Why this matters for design feedback:** The system is data-driven. Any mechanic that can be expressed as nodes, flags, timers, and effects can be authored into a case without engine changes. If you have a mechanic idea, the question is "can this be expressed as a graph of conditional activations with time-based triggers?" — and the answer is almost always yes.

---

## Outcome Scoring

Cases resolve into tiers: **Optimal, Good, Partial, Failure.** Scoring is based on:

- **Flags present at case end** — did you discover the key findings? Confirm the diagnosis? Start the right treatment?
- **Flags absent** — did you avoid harmful actions? (Steroids in the example case cause a dramatic rebound.)
- **Time constraints** — was the correct treatment started before the critical threshold?
- **Relational outcomes** — did you engage with the family? Were you honest with the patient? These are scored separately from medical outcomes.

There is no single "you win" condition. The same case can end with the patient alive but relationally damaged, or dead but with the diagnosis correctly identified too late. The debrief compares the player's path to the optimal path and explains what real clinicians struggle with in similar cases.

---

## What I'm Looking For

I'm not looking for "cool idea!" — I'm looking for design critique. Specifically:

1. **Does the hidden-timer / visible-action-economy split work?** Or does hiding the deterioration feel unfair rather than tense? Is there a smarter way to create the "I know something bad is happening but I can't see what" feeling?

2. **Is the dashboard layout the right metaphor?** Or should this be more narrative-forward (visual novel with embedded mechanics), more spatial (hospital map you move through), or more abstract (card-based, Slay the Spire style)?

3. **Variable-length turns with concurrent timers** — are there games that do this well that I should study? The closest I've found is FTL and Pandemic, but neither is quite the same pattern. I'm particularly interested in board games or tabletop RPGs that handle "multiple independent countdowns advancing at different rates."

4. **The emergency interrupt mechanic** — does forcing the player out of investigation mode into crisis response feel like a natural escalation, or does it feel like the game yanking the controller? How do other games handle sudden state changes that invalidate the player's current plan?

5. **"Diagnosis commitment" as a mechanic** — should the player have to formally declare a working hypothesis before certain actions unlock? Or does that feel too gamey for a simulation? Is there a way to reward diagnostic reasoning without making it a mechanical gate?

6. **The target audience is teenage girls who love medical drama.** What does that mean for pacing, for feedback loops, for the emotional register of failure? Medical sim games skew toward clinical detachment. I want this to feel like a show they're starring in. How do I keep the drama without the mechanics feeling cold?

7. **Am I reinventing something that already exists?** If there's a game, a system, or a design pattern that already solves what I'm describing, I'd rather learn from it than build from scratch.

---

## Glossary (For Cross-Discipline Clarity)

| Term | Meaning in This System |
|------|----------------------|
| **Node** | Atomic unit of case content — a finding, event, process, or outcome. Equivalent to a "card" in a deckbuilder or an "encounter" in an RPG, but with its own lifecycle and activation rules. |
| **Flag** | Boolean state marker. Set by effects, checked by conditions. The wiring between nodes. Similar to "tags" in Bitsy or "facts" in Ink. |
| **Timer** | Per-node countdown that ticks with the game clock. Can have staged effects at intervals. Expiry triggers consequences. |
| **Action** | Player input, categorized by type and subcategory. `order_labs:cbc`, `history_focused:dietary`, `emergency_intervention`. Each has a fixed time cost. |
| **Diegetic timer** | A countdown the player's character would know about — lab turnaround, imaging queue, consult arrival. Shown to the player. |
| **Non-diegetic timer** | A biological or situational countdown the character can't see — deterioration, NPC patience, cascade triggers. Hidden from the player; inferred from indirect signals. |
| **Freeze line** | Architectural boundary: once a case is generated, it's immutable. No facts invented during play. |
| **Truth line** | Architectural boundary: the UI reveals truth but never determines it. All medical logic lives in the engine. |

---

## Where to Find Me

tyro@sageframe.net / github.com/sageframe-no-kaji / sageframe.substack.com

I'm genuinely looking for people who think about this stuff professionally or obsessively. If you've designed a system that manages concurrent hidden state under player time pressure, I want to hear about it. If you've played a game that does what I'm describing and I haven't found it yet, I want to know.
