# Medical Mystery Simulator — Project Overview

## What I Am Building

I am building an **interactive medical mystery simulator** designed for emotionally and intellectually advanced teenagers—especially those who love _Grey’s Anatomy_, _House_, and high-stakes medical drama.

This is **not a chatbot** and not a quiz app.
It is a **clinical reasoning game** where the player steps into the role of a clinician and makes real decisions over time:

- what questions to ask
- what exams to perform
- what tests to order
- when to call consults
- when to wait
- when waiting is dangerous

The experience is dramatic, tense, emotional, and sometimes tragic—**without being gratuitous**—and always grounded in real medical logic.

The goal is not to “guess the diagnosis.”
The goal is to **learn how doctors think**.

---

## Who This Is For

I am building this primarily for:

- Teenagers (roughly 15–18)
- Emotionally mature
- Comfortable with ambiguity and complexity
- Drawn to:
  - trauma
  - romance
  - secrets
  - ethical dilemmas
  - violence, abuse, and death _in the way medical dramas portray them_
- Fans of _Grey’s Anatomy_ who want:
  - stakes
  - mystery
  - consequence
  - emotional realism

This is **not sanitized**.
It is **age-appropriate, but not dumbed down**.

---

## Purpose

This project exists to do three things at once:

### 1. Teach Medical Reasoning

- Pattern recognition
- Hypothesis testing
- Managing uncertainty
- Understanding timing and deterioration
- Recognizing dangerous assumptions

### 2. Teach Medicine as a Human System

- Patients lie, minimize, or hide information
- Relationships affect care
- Consent matters
- Fear, shame, power, and bias influence outcomes
- Doctors disagree and make mistakes

### 3. Preserve What Makes Medical Drama Fun

- Emotional tension
- Ethical discomfort
- Mystery and reveal
- Consequences, including death
- “Oh no” moments that force decisions

---

## Core Design Insight

The key architectural decision is:

> **I separate case generation from case play.**

The system **does not invent facts during gameplay**.

Instead:

- Cases are generated **ahead of time** from structured seeds
- Each case is frozen into a deterministic structure
- Gameplay reveals information gradually through player choices

This prevents chaos while preserving infinite replayability.

---

## System Architecture Overview

### 1. Front End (Player Experience)

The front end is a **guided, turn-based experience**.

The player does not type free-form actions.
They choose from **structured clinical actions**, such as:

- Get history
- Perform physical exam
- Order labs
- Order imaging
- Call a consult
- Start treatment
- Observe / wait
- Escalate care
- Discharge

Each action:

- reveals specific information
- may advance time
- may trigger deterioration or stabilization
- has consequences

The UI emphasizes:

- tension
- pacing
- clarity
- emotional tone
- dramatic beats

Tooltips and side panels explain _why_ actions matter.

---

### 2. Back End (Case Engine)

The backend is a **deterministic logic engine**, not an AI.

It:

- tracks what the player knows
- controls what actions are available
- advances time
- applies consequences
- triggers deterioration, collapse, or recovery
- determines win / loss / partial outcomes

The backend is the **source of truth**.

The LLM never decides outcomes.

---

### 3. Backend Seed Engine (Case Generation)

This is where replayability comes from.

I seed the system with structured inputs such as:

- medical core (diagnosis or syndrome)
- difficulty level
- learning objectives
- dramatic tone (Grey’s-style, trauma-heavy, ethical, etc.)
- human complications (secrets, abuse, romance, power dynamics)
- content boundaries

The LLM uses these seeds to generate a **fully structured case file** (JSON/YAML), including:

- ground truth diagnosis
- initial presentation
- what information is revealed by which actions
- lab values and trends
- imaging findings
- time-based progression
- failure states

Once generated, the case is **frozen** and validated.

No hallucination during play.

---

### 4. Front-End Builder (Case Designer)

I am also envisioning a **case builder interface**.

This can be:

- backend-only (for me)
- or a protected frontend tool

The builder allows me to:

- select medical themes
- select dramatic tone
- choose ethical complications
- tune difficulty
- generate and preview cases
- approve or reject generated cases

This makes the system:

- expandable
- curatable
- safe
- sustainable

Kids never directly generate cases themselves.

---

## Teaching Layer

Teaching is embedded, not bolted on.

Every action can surface:

- tooltips (“Why this matters”)
- short explanations
- ethical context
- optional deeper dives
- post-case debriefs

Debriefs focus on:

- what assumptions were made
- what signals were missed
- why outcomes occurred
- how real clinicians struggle with the same issues

---

## Handling Trauma, Sex, Abuse, and Death

This system includes:

- sexual relationships
- pregnancy ambiguity
- domestic violence clues
- coercion and power imbalance
- violence
- death as a possible outcome

But:

- no graphic content
- no fetishization
- no shock-for-shock’s-sake

Death is:

- causal
- explained
- emotionally grounded
- framed as learning, not punishment

This mirrors medical dramas _and_ real medicine.

---

## Why This Works

Medicine has:

- a finite number of core pathologies
- infinite surface variation

By generating **variants**, not static cases, the player learns:

- patterns, not answers
- reasoning, not memorization
- judgment under uncertainty

This keeps the experience fresh and deep.

---

## Technology Stack & System Layers

The system is intentionally designed as a **layered stack**, with each layer serving a distinct purpose and audience. This separation keeps the experience dramatic and human-facing on the front end, while preserving rigor, determinism, and clarity in the underlying logic.

---

### Frontend Experience — **Internal Affairs**

**Internal Affairs** is the user-facing application.

This layer is:

- narrative-driven
- emotionally grounded
- relational and ethical in tone
- inspired by medical dramas like _Grey’s Anatomy_

The frontend presents cases as unfolding stories in which the player:

- steps into a clinician role
- makes decisions from structured action menus
- experiences consequences over time
- engages with characters, conflict, and uncertainty

Key responsibilities:

- Case presentation and pacing
- Action selection UI (history, exam, labs, imaging, consults, etc.)
- Narrative delivery (via LLM)
- Tooltips, teaching moments, and optional deep dives
- Outcome summaries and reflective debriefs

The frontend never determines medical truth—it **reveals** it.

---

### Backend Engine — **Satori**

**Satori** is the deterministic case engine and system of record.

This layer:

- enforces medical logic
- tracks state and time
- applies consequences
- controls progression, deterioration, stabilization, or collapse

Satori is responsible for:

- validating player actions
- determining what information can be revealed
- advancing simulated time
- triggering state transitions (e.g., compensation → decompensation)
- enforcing win, loss, or partial-success conditions

Satori does **not** generate narrative or text.
It decides **what happens**, not **how it is described**.

This separation ensures:

- consistency
- replayability
- safety
- educational integrity

---

### Case Generation System — **Anamnesis**

**Anamnesis** is the structured case generator.

This layer operates in design-time rather than play-time and is used to:

- generate complete, self-contained case files
- encode ground truth diagnoses and paths
- define how and when information is revealed
- embed human, ethical, and relational complications

Anamnesis takes **seed inputs** such as:

- medical core condition
- difficulty level
- learning objectives
- dramatic tone
- human and ethical complications
- content boundaries

From these seeds, it produces:

- validated JSON/YAML case definitions
- deterministic progression logic
- predefined failure and success states

Once generated, cases are frozen and handed off to **Satori** for execution.

Anamnesis is never directly exposed to players.

---

### Optional Builder Interface

A protected **Case Builder** interface may sit above Anamnesis.

This tool allows:

- selecting seeds and constraints
- generating preview cases
- reviewing and curating content
- approving cases for inclusion
- tuning difficulty and tone

This ensures scalability without sacrificing control or safety.

---

### LLM Role (Across the Stack)

The LLM is intentionally constrained.

It is used to:

- narrate patient responses
- describe exam findings
- communicate test results
- deliver teaching explanations
- generate reflective debriefs

It is explicitly **not allowed** to:

- invent facts
- alter diagnoses
- override Satori logic
- change case outcomes

This keeps the system dramatic, flexible, and human—without being unpredictable.

---

### Why This Stack Works

This architecture:

- preserves drama without chaos
- enables infinite replayability through variation
- keeps learning intentional and grounded
- cleanly separates experience, logic, and creation

Each layer does one job well:

- **Internal Affairs** tells the story
- **Satori** enforces truth
- **Anamnesis** creates the world

## Together, they form a robust, scalable, and emotionally resonant system.

## What This Ultimately Is

This is a **serious, narrative medical reasoning simulator** for advanced teens.

It teaches:

- how to think
- how to notice
- how to sit with uncertainty
- how consequences unfold

It respects intelligence.
It preserves drama.
It teaches something real.

And it’s something I genuinely want to build.

---
