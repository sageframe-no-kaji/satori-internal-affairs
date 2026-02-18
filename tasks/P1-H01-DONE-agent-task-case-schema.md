# TASK: CASE DEFINITION JSON SCHEMA

## GOAL

A complete JSON Schema exists at `schemas/case-definition.schema.json` that
defines the contract between Anamnesis (case generation) and Satori (case
execution). A case conforming to this schema contains everything Satori needs
to run a deterministic game and everything Internal Affairs needs to present
the experience. A corresponding Pydantic model exists at
`packages/satori/src/satori/models/case_definition.py` that validates
Python objects against the same contract.

Additionally, the hand-written example case (Maria Santos / neurocysticercosis)
exists as a validated JSON file at `cases/example-neurocysticercosis.json`.

## CONTEXT

This schema implements a **node-graph architecture** for medical cases.
A case is a graph of independent nodes, each with its own lifecycle,
connected by flag-based dependencies and independent timers. This is
a concurrent state machine pattern with discrete event simulation.

Read the full architecture description:
`docs/architecture/example-case-node-architecture.md`

The schema has two layers in a single file:
- **Structure layer:** nodes, flags, timers, vitals, conditions, outcomes.
  Consumed by Satori. This is the mechanical truth.
- **Narrative layer:** patient identity, node content text, dialogue,
  descriptions. Consumed by Internal Affairs. Keyed to node IDs.

In Phase 1, both layers are frozen at case creation time. In future phases,
the narrative layer may be dynamically generated during play (see F-001 in
future-features.md). The schema must support this by keeping the two layers
cleanly separated within the case definition.

## DO NOT CHANGE

- Any existing package structure or configuration
- The README or other documentation (this task creates new files only)
- Any existing test files

## REQUIRED SCHEMA STRUCTURE (EXACT)

The JSON Schema and Pydantic model must implement the following structure.
Field names, types, and nesting must match exactly. Descriptions can be
expanded but not altered in meaning.

### Top Level

```
CaseDefinition:
  id: string (UUID)
  version: string (semver, e.g. "1.0.0")
  metadata: Metadata
  patient: PatientContext
  ground_truth: GroundTruth
  action_costs: dict[ActionType, TimeCost]
  nodes: list[Node]
  outcome_evaluation: OutcomeEvaluation
```

### Metadata

```
Metadata:
  difficulty: enum ["tutorial", "beginner", "intermediate", "advanced", "expert"]
  estimated_duration_minutes: int
  simulated_duration_minutes: int
  learning_objectives: list[string]
  dramatic_tone: enum ["medical_mystery", "trauma", "ethical_dilemma",
                        "relational", "procedural"]
  content_boundaries: list[string]
  tags: list[string]
```

### PatientContext

This is the narrative layer for patient identity. Satori reads `age` and
`sex` (medically relevant). Internal Affairs reads everything.

```
PatientContext:
  name: string
  age: int
  sex: enum ["male", "female", "intersex"]
  setting: string (e.g. "Emergency Department", "Outpatient Clinic")
  chief_complaint: string
  appearance: string
  backstory: string (brief context — NOT revealed to player directly)
  arriving_vitals: VitalSigns
  triage_note: string
```

### VitalSigns

Used for both baseline vitals and node-level vital declarations.

```
VitalSigns:
  heart_rate: Optional[int]
  blood_pressure_systolic: Optional[int]
  blood_pressure_diastolic: Optional[int]
  temperature: Optional[float]
  respiratory_rate: Optional[int]
  o2_saturation: Optional[int]
```

All fields optional because nodes only declare vitals they affect.
Satori computes current vitals as: for each vital, take the most severe
value across all active nodes and baseline. "Most severe" direction is
defined per vital:
- heart_rate: HIGHER is worse (except bradycardia — use separate node)
- blood_pressure_systolic: CONTEXT-DEPENDENT (hypertensive vs. shock)
- blood_pressure_diastolic: CONTEXT-DEPENDENT
- temperature: HIGHER is worse (except hypothermia — use separate node)
- respiratory_rate: HIGHER is worse
- o2_saturation: LOWER is worse

The severity direction ambiguity for BP means nodes must declare explicit
values, not directions. Satori evaluates severity based on deviation from
baseline in either direction and takes the most deviant.

### GroundTruth

Never revealed to the player during play. Used by Satori for outcome
evaluation and by the teaching layer for debriefs.

```
GroundTruth:
  diagnosis: string
  differential: list[string]
  mechanism: string
  key_insight: string
  optimal_path: list[OptimalStep]
  critical_time_minutes: Optional[int]
  narrative_hooks: list[NarrativeHook]

OptimalStep:
  action: string
  description: string
  time_minutes: int (cumulative from case start)

NarrativeHook:
  type: enum ["misleading_assumption", "hidden_connection",
              "ethical_tension", "relational_gate", "red_herring"]
  description: string
  structural_role: string (how this hook connects to the node graph)
```

### ActionType and TimeCost

```
ActionType: enum [
  "history_general",
  "history_focused",
  "physical_exam_general",
  "physical_exam_focused",
  "order_labs",
  "order_imaging",
  "start_treatment",
  "consult",
  "wait_observe",
  "emergency_intervention",
  "escalate_care",
  "discharge"
]

TimeCost:
  action_minutes: int (time to perform the action)
  result_delay_minutes: Optional[int] (time until results arrive, if applicable)
```

### Node

The atomic unit of the simulation. Every piece of case reality is a node.

```
Node:
  id: string (unique within case, e.g. "node_01", "chief_complaint")
  type: enum [
    "medical_finding",
    "lab_result",
    "imaging",
    "history",
    "relational",
    "emotional",
    "behavioral",
    "progression",
    "intervention_response",
    "outcome"
  ]

  # --- Narrative Layer ---
  content: NodeContent

  # --- Structure Layer ---
  activation: ActivationRule
  reveal: Optional[RevealRule]      # None for auto-revealed nodes (progressions, outcomes)
  timer: Optional[NodeTimer]
  vital_signs: Optional[VitalSigns] # What this node wants vitals to be when active
  effects: NodeEffects
  outcome_weight: Optional[OutcomeWeight]
  teaching_note: Optional[string]   # Empty in Phase 1, used for F-005
```

### NodeContent

The narrative payload. In Phase 1, this is frozen text. In future phases
(F-001), the `narrative_text` field may be dynamically generated while
`structured_data` remains frozen.

```
NodeContent:
  narrative_text: string            # What the player reads when this node reveals
  structured_data: Optional[dict]   # Machine-readable medical data (lab values, etc.)
  stage_narratives: Optional[list[StageNarrative]]  # For progression nodes with stages

StageNarrative:
  stage_index: int
  narrative_text: string
  structured_data: Optional[dict]
```

### ActivationRule

When does this node become live in the simulation?

```
ActivationRule:
  # A node activates when ANY path is satisfied (OR between paths).
  # Each path requires ALL its conditions to be met (AND within path).
  paths: list[ConditionPath]
  on_activate: Optional[list[Effect]]  # Effects that fire on activation
  starts_active: bool (default: false) # True for starting nodes

ConditionPath:
  conditions: list[Condition]

Condition:
  type: enum ["flag_set", "flag_not_set", "node_active", "node_revealed",
              "node_expired", "time_elapsed", "vital_threshold"]
  target: string              # flag name, node ID, or vital name
  value: Optional[any]        # threshold for time/vital conditions
  comparator: Optional[enum ["gt", "lt", "gte", "lte", "eq"]]
```

This gives us: OR between paths, AND within each path. Covers all cases
from the example without needing a full expression parser.

### RevealRule

How does the player discover this node?

```
RevealRule:
  action: ActionType
  subcategory: Optional[string]     # e.g. "dietary", "neuro", "cardiac", "family"
  conditions: Optional[list[Condition]]  # Additional conditions beyond the action
  auto_reveal: bool (default: false)     # True = reveals automatically when active
  delay_minutes: Optional[int]           # Time between action and reveal (lab results)
```

### NodeTimer

Countdown from activation. Drives time pressure.

```
NodeTimer:
  duration_minutes: int
  pause_conditions: Optional[list[Condition]]
  stages: Optional[list[TimerStage]]   # For progressive effects
  on_expire: list[Effect]

TimerStage:
  at_minutes: int                      # Minutes after activation
  effects: list[Effect]
  vital_signs: Optional[VitalSigns]    # Vitals at this stage
```

### Effects System

What happens when nodes activate, reveal, expire, or get intervened on.

```
NodeEffects:
  on_reveal: Optional[list[Effect]]
  on_expire: Optional[list[Effect]]     # If timer runs out
  on_intervene: Optional[InterventionEffect]

InterventionEffect:
  treatment: string                     # What treatment addresses this node
  effects: list[Effect]

Effect:
  type: enum [
    "set_flag",
    "clear_flag",
    "activate_node",
    "deactivate_node",
    "modify_timer",         # Accelerate or delay another node's timer
    "unlock_action",        # Make a new action available
    "lock_action",          # Remove an action (e.g. during crisis)
    "override_vitals",      # Emergency vital sign override
    "end_case"              # Trigger case resolution
  ]
  target: string            # Flag name, node ID, action type, etc.
  value: Optional[any]      # For modify_timer: minutes to add/subtract
                            # For set_flag: always true (presence = set)
```

### OutcomeWeight

How this node contributes to final scoring.

```
OutcomeWeight:
  category: enum ["medical", "relational", "ethical"]
  impact: enum ["critical", "major", "moderate", "minor"]
  scoring_notes: Optional[string]
```

### OutcomeEvaluation

How the case is scored at resolution.

```
OutcomeEvaluation:
  tiers: list[OutcomeTier]
  harmful_actions: Optional[list[HarmfulAction]]
  end_conditions: list[EndCondition]

OutcomeTier:
  tier: enum ["optimal", "good", "partial", "failure"]
  required_flags: Optional[list[string]]
  excluded_flags: Optional[list[string]]
  time_constraints: Optional[list[TimeConstraint]]
  narrative: string   # End-of-case narrative for this tier

TimeConstraint:
  flag: string
  before_minutes: int   # This flag must be set before this time

HarmfulAction:
  description: string
  flag: string          # Flag that indicates this harmful action was taken
  penalty_note: string

EndCondition:
  type: enum ["node_activated", "time_elapsed", "flag_set", "all_critical_resolved"]
  target: Optional[string]
  value: Optional[any]
  description: string
```

## IMPLEMENTATION REQUIREMENTS

### 1. JSON Schema file: `schemas/case-definition.schema.json`

- Valid JSON Schema Draft 2020-12
- Every field must have a `description` property explaining its purpose
- All enums must be defined with clear value descriptions
- Required vs optional fields must match the spec above exactly
- Use `$defs` for reusable sub-schemas (Condition, Effect, VitalSigns, etc.)

### 2. Pydantic model: `packages/satori/src/satori/models/case_definition.py`

- Pydantic v2 (use `BaseModel`, not v1 style)
- Must mirror the JSON Schema exactly — same field names, same types, same nesting
- Use `Literal` for enums where appropriate, or define proper `Enum` classes
- Include docstrings on all model classes
- Include a `validate_case(filepath: str) -> CaseDefinition` function that loads
  and validates a JSON file
- Include a `model_json_schema()` export that produces schema equivalent to
  the hand-written JSON Schema

### 3. Example case: `cases/example-neurocysticercosis.json`

- Implements the Maria Santos case from `docs/architecture/example-case-node-architecture.md`
- Must validate against both the JSON Schema and the Pydantic model
- All 12 nodes from the example document, translated into the formal structure
- Include a brief comment (in a `_comment` field at top level) noting this is
  a hand-written example for schema validation

### 4. Validation test: `packages/satori/tests/test_case_schema.py`

- Test that loads `cases/example-neurocysticercosis.json` and validates it
  against the Pydantic model
- Test that verifies all node IDs are unique
- Test that verifies all flag references in conditions point to flags that
  are actually set by some node's effects
- Test that verifies all node ID references in conditions/effects point to
  nodes that exist
- Test that verifies at least one node has `starts_active: true`
- Test that verifies at least one end condition exists

## INVARIANTS TO PRESERVE

1. The schema must cleanly separate structure (what Satori reads) from
   narrative (what Internal Affairs reads). `NodeContent.narrative_text`
   is narrative. Everything else on a node is structure.
2. Every `Condition` must reference a valid target (flag name or node ID).
   The validation tests must verify referential integrity.
3. `VitalSigns` fields are all optional — nodes only declare vitals they
   affect. The "worst wins" computation is Satori's job, not the schema's.
4. `ActivationRule.paths` implements OR-of-ANDs logic. Multiple paths = OR.
   Multiple conditions within a path = AND.
5. The example case JSON must be manually written to match the example case
   document — NOT generated by an LLM. This is the reference artifact.

## ACCEPTANCE CHECKS (MANDATORY)

- `python -m pytest packages/satori/tests/test_case_schema.py` passes
- The example case JSON loads without validation errors
- The JSON Schema file is valid JSON Schema (test with a schema validator)
- The Pydantic model's `model_json_schema()` output is structurally
  compatible with the hand-written JSON Schema
- `ruff check packages/satori/` passes
- `mypy packages/satori/` passes

## QUALITY

- All Python code must pass ruff and mypy
- Pydantic models must have docstrings
- JSON Schema must have descriptions on all fields
- The example case must be well-formatted and readable

## COMMIT

```
feat(schema): case definition schema and example case

- JSON Schema at schemas/case-definition.schema.json
- Pydantic models at packages/satori/src/satori/models/
- Hand-written example case (neurocysticercosis)
- Schema validation tests with referential integrity checks
```
