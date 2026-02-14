"""Case definition data models for Satori game engine.

These Pydantic models define the structure of medical mystery cases,
implementing the contract between Anamnesis (case generation) and Satori
(case execution).
"""

import json
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Difficulty(StrEnum):
    """Case difficulty levels."""

    TUTORIAL = "tutorial"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DramaticTone(StrEnum):
    """Primary narrative tone and focus of a case."""

    MEDICAL_MYSTERY = "medical_mystery"
    TRAUMA = "trauma"
    ETHICAL_DILEMMA = "ethical_dilemma"
    RELATIONAL = "relational"
    PROCEDURAL = "procedural"


class Sex(StrEnum):
    """Biological sex categories."""

    MALE = "male"
    FEMALE = "female"
    INTERSEX = "intersex"


class NodeType(StrEnum):
    """Categories of nodes in the case graph."""

    MEDICAL_FINDING = "medical_finding"
    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    HISTORY = "history"
    RELATIONAL = "relational"
    EMOTIONAL = "emotional"
    BEHAVIORAL = "behavioral"
    PROGRESSION = "progression"
    INTERVENTION_RESPONSE = "intervention_response"
    OUTCOME = "outcome"


class ConditionType(StrEnum):
    """Types of conditions that can be evaluated."""

    FLAG_SET = "flag_set"
    FLAG_NOT_SET = "flag_not_set"
    NODE_ACTIVE = "node_active"
    NODE_REVEALED = "node_revealed"
    NODE_EXPIRED = "node_expired"
    TIME_ELAPSED = "time_elapsed"
    VITAL_THRESHOLD = "vital_threshold"


class Comparator(StrEnum):
    """Comparison operators for threshold conditions."""

    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"


class EffectType(StrEnum):
    """Types of effects that modify game state."""

    SET_FLAG = "set_flag"
    CLEAR_FLAG = "clear_flag"
    ACTIVATE_NODE = "activate_node"
    DEACTIVATE_NODE = "deactivate_node"
    MODIFY_TIMER = "modify_timer"
    UNLOCK_ACTION = "unlock_action"
    LOCK_ACTION = "lock_action"
    OVERRIDE_VITALS = "override_vitals"
    END_CASE = "end_case"


class NarrativeHookType(StrEnum):
    """Categories of narrative hooks."""

    MISLEADING_ASSUMPTION = "misleading_assumption"
    HIDDEN_CONNECTION = "hidden_connection"
    ETHICAL_TENSION = "ethical_tension"
    RELATIONAL_GATE = "relational_gate"
    RED_HERRING = "red_herring"


class OutcomeCategory(StrEnum):
    """Categories for outcome scoring."""

    MEDICAL = "medical"
    RELATIONAL = "relational"
    ETHICAL = "ethical"


class OutcomeImpact(StrEnum):
    """Impact levels for outcome weights."""

    CRITICAL = "critical"
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class OutcomeTierLevel(StrEnum):
    """Outcome tier levels."""

    OPTIMAL = "optimal"
    GOOD = "good"
    PARTIAL = "partial"
    FAILURE = "failure"


class EndConditionType(StrEnum):
    """Types of conditions that end a case."""

    NODE_ACTIVATED = "node_activated"
    TIME_ELAPSED = "time_elapsed"
    FLAG_SET = "flag_set"
    ALL_CRITICAL_RESOLVED = "all_critical_resolved"


class VitalSigns(BaseModel):
    """Patient vital signs.

    All fields optional - nodes only declare vitals they affect.
    Satori computes current vitals as worst value across active nodes and baseline.
    """

    heart_rate: int | None = Field(None, ge=0, le=300, description="Heart rate in BPM")
    blood_pressure_systolic: int | None = Field(None, ge=0, le=300, description="Systolic BP in mmHg")
    blood_pressure_diastolic: int | None = Field(None, ge=0, le=200, description="Diastolic BP in mmHg")
    temperature: float | None = Field(None, ge=80.0, le=115.0, description="Temperature in Fahrenheit")
    respiratory_rate: int | None = Field(None, ge=0, le=100, description="Respiratory rate in breaths/min")
    o2_saturation: int | None = Field(None, ge=0, le=100, description="Oxygen saturation percentage")


class Metadata(BaseModel):
    """Case metadata including difficulty, learning objectives, and content boundaries."""

    difficulty: Difficulty = Field(..., description="Difficulty level of the case")
    estimated_duration_minutes: int = Field(..., ge=1, description="Expected real-world completion time")
    simulated_duration_minutes: int = Field(..., ge=1, description="Total simulated time span in game minutes")
    learning_objectives: list[str] = Field(..., min_length=1, description="Educational goals")
    dramatic_tone: DramaticTone = Field(..., description="Primary narrative tone")
    content_boundaries: list[str] | None = Field(None, description="Content warnings or boundaries")
    tags: list[str] | None = Field(None, description="Searchable tags")


class PatientContext(BaseModel):
    """Patient identity and presentation information.

    Narrative layer for Internal Affairs display, with age/sex medically relevant for Satori.
    """

    name: str = Field(..., description="Patient's full name")
    age: int = Field(..., ge=0, le=150, description="Patient's age in years")
    sex: Sex = Field(..., description="Biological sex")
    setting: str = Field(..., description="Clinical setting")
    chief_complaint: str = Field(..., description="Why the patient is seeking care")
    appearance: str = Field(..., description="Physical appearance and presentation")
    backstory: str | None = Field(None, description="Background context (not directly revealed)")
    arriving_vitals: VitalSigns = Field(..., description="Baseline vital signs on arrival")
    triage_note: str | None = Field(None, description="Initial triage assessment")


class OptimalStep(BaseModel):
    """A step in the optimal solution path."""

    action: str = Field(..., description="The action to perform")
    description: str = Field(..., description="Why this action is part of the optimal path")
    time_minutes: int = Field(..., ge=0, description="Cumulative time from case start")


class NarrativeHook(BaseModel):
    """A dramatic or teaching element embedded in the case."""

    type: NarrativeHookType = Field(..., description="Category of narrative hook")
    description: str = Field(..., description="What this hook adds to the case")
    structural_role: str = Field(..., description="How this hook connects to the node graph")


class GroundTruth(BaseModel):
    """Clinical truth about the case.

    Never revealed to player during gameplay, used for outcome evaluation and teaching debrief.
    """

    diagnosis: str = Field(..., description="The correct diagnosis")
    differential: list[str] = Field(..., description="Alternative diagnoses to consider")
    mechanism: str = Field(..., description="Pathophysiological mechanism")
    key_insight: str = Field(..., description="Critical reasoning needed for diagnosis")
    optimal_path: list[OptimalStep] = Field(..., description="Ideal action sequence")
    critical_time_minutes: int | None = Field(None, ge=0, description="Time limit before irreversible harm")
    narrative_hooks: list[NarrativeHook] = Field(..., description="Dramatic and teaching elements")


class TimeCost(BaseModel):
    """Time cost for performing an action."""

    action_minutes: int = Field(..., ge=0, description="Time to perform the action itself")
    result_delay_minutes: int | None = Field(None, ge=0, description="Time until results available")


class StageNarrative(BaseModel):
    """Narrative for a specific timer stage in a progression node."""

    stage_index: int = Field(..., ge=0, description="Which stage this narrative belongs to")
    narrative_text: str = Field(..., description="Narrative text for this stage")
    structured_data: dict[str, Any] | None = Field(None, description="Machine-readable data for this stage")


class NodeContent(BaseModel):
    """Narrative payload of a node.

    In Phase 1, text is frozen. In future phases, narrative_text may be dynamically generated
    while structured_data remains frozen.
    """

    narrative_text: str = Field(..., description="What the player reads when this node reveals")
    structured_data: dict[str, Any] | None = Field(None, description="Machine-readable medical data")
    stage_narratives: list[StageNarrative] | None = Field(None, description="Narratives for progression stages")


class Condition(BaseModel):
    """A single condition that can be evaluated true or false."""

    type: ConditionType = Field(..., description="Type of condition to evaluate")
    target: str = Field(..., description="What to check: flag name, node ID, vital name, etc.")
    value: Any | None = Field(None, description="Threshold value for comparisons")
    comparator: Comparator | None = Field(None, description="Comparison operator")


class Effect(BaseModel):
    """A single effect that modifies game state."""

    type: EffectType = Field(..., description="Type of effect to apply")
    target: str = Field(..., description="What to affect: flag name, node ID, action type, etc.")
    value: Any | None = Field(None, description="Value for the effect")


class ConditionPath(BaseModel):
    """A single path of conditions that must all be met (AND logic)."""

    conditions: list[Condition] = Field(..., min_length=1, description="All must be true")


class ActivationRule(BaseModel):
    """Defines when a node becomes live.

    OR between paths, AND within each path.
    """

    paths: list[ConditionPath] | None = Field(None, min_length=1, description="Node activates when ANY path satisfied")
    on_activate: list[Effect] | None = Field(None, description="Effects that fire on activation")
    starts_active: bool = Field(False, description="If true, node is active from case start")


class RevealRule(BaseModel):
    """How the player discovers this node."""

    action: str | None = Field(None, description="Action type that reveals this node")
    subcategory: str | None = Field(None, description="Subcategory of action")
    conditions: list[Condition] | None = Field(None, description="Additional conditions required")
    auto_reveal: bool = Field(False, description="If true, reveals automatically when active")
    delay_minutes: int | None = Field(None, ge=0, description="Time between action and reveal")


class TimerStage(BaseModel):
    """Effects that occur at a specific point during a timer countdown."""

    at_minutes: int = Field(..., ge=0, description="Minutes after activation when this stage triggers")
    effects: list[Effect] = Field(..., description="Effects to apply at this stage")
    vital_signs: VitalSigns | None = Field(None, description="Vital signs at this stage")


class NodeTimer(BaseModel):
    """Countdown timer from node activation, driving time pressure."""

    duration_minutes: int = Field(..., ge=0, description="Total timer duration from activation")
    pause_conditions: list[Condition] | None = Field(None, description="Conditions that pause the timer")
    stages: list[TimerStage] | None = Field(None, description="Progressive effects at specific time points")
    on_expire: list[Effect] = Field(..., min_length=1, description="Effects when timer reaches zero")


class InterventionEffect(BaseModel):
    """Effect triggered by a specific treatment or intervention."""

    treatment: str = Field(..., description="Name of treatment that triggers this effect")
    effects: list[Effect] = Field(..., description="Effects to apply when this treatment is given")


class NodeEffects(BaseModel):
    """Effects triggered by node lifecycle events."""

    on_reveal: list[Effect] | None = Field(None, description="Effects when node is revealed to player")
    on_expire: list[Effect] | None = Field(None, description="Effects when timer expires")
    on_intervene: InterventionEffect | None = Field(None, description="Effects when specific intervention applied")


class OutcomeWeight(BaseModel):
    """How this node contributes to final case scoring."""

    category: OutcomeCategory = Field(..., description="Category of outcome contribution")
    impact: OutcomeImpact = Field(..., description="Weight in outcome evaluation")
    scoring_notes: str | None = Field(None, description="Notes about how to score this node")


class Node(BaseModel):
    """Atomic unit of simulation.

    Every piece of case reality is a node with its own lifecycle.
    """

    id: str = Field(..., description="Unique identifier for this node within the case")
    type: NodeType = Field(..., description="Category of node determining its role")
    content: NodeContent = Field(..., description="Narrative payload")
    activation: ActivationRule = Field(..., description="When this node becomes live")
    reveal: RevealRule | None = Field(None, description="How the player discovers this node")
    timer: NodeTimer | None = Field(None, description="Countdown from activation")
    vital_signs: VitalSigns | None = Field(None, description="Vital signs this node wants when active")
    effects: NodeEffects | None = Field(None, description="Lifecycle event effects")
    outcome_weight: OutcomeWeight | None = Field(None, description="Contribution to final scoring")
    teaching_note: str | None = Field(None, description="Teaching point for debrief")


class TimeConstraint(BaseModel):
    """A flag must be set before a certain time."""

    flag: str = Field(..., description="Flag that must be set")
    before_minutes: int = Field(..., ge=0, description="Time limit in minutes from case start")


class OutcomeTier(BaseModel):
    """A specific outcome tier (optimal, good, partial, failure)."""

    tier: OutcomeTierLevel = Field(..., description="Tier level")
    required_flags: list[str] | None = Field(None, description="Flags that must be set")
    excluded_flags: list[str] | None = Field(None, description="Flags that must NOT be set")
    time_constraints: list[TimeConstraint] | None = Field(None, description="Time-based requirements")
    narrative: str = Field(..., description="End-of-case narrative for this tier")


class HarmfulAction(BaseModel):
    """An action that harms the patient."""

    description: str = Field(..., description="What the harmful action was")
    flag: str = Field(..., description="Flag indicating this harmful action was taken")
    penalty_note: str = Field(..., description="Explanation of the penalty or harm")


class EndCondition(BaseModel):
    """Condition that triggers case end."""

    type: EndConditionType = Field(..., description="Type of end condition")
    target: str | None = Field(None, description="Target for the condition")
    value: Any | None = Field(None, description="Value for the condition")
    description: str = Field(..., description="What this end condition represents")


class OutcomeEvaluation(BaseModel):
    """How the case is scored at resolution."""

    tiers: list[OutcomeTier] = Field(..., min_length=1, description="Outcome tiers from optimal to failure")
    harmful_actions: list[HarmfulAction] | None = Field(None, description="Actions that harm the patient")
    end_conditions: list[EndCondition] = Field(..., min_length=1, description="Conditions that can end the case")


class CaseDefinition(BaseModel):
    """Complete medical mystery case definition.

    Defines the contract between Anamnesis (case generation) and Satori (case execution).
    """

    id: UUID = Field(..., description="Unique identifier for this case")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Semantic version")
    metadata: Metadata = Field(..., description="Case metadata")
    patient: PatientContext = Field(..., description="Patient identity and presentation")
    ground_truth: GroundTruth = Field(..., description="Clinical truth (never revealed during gameplay)")
    action_costs: dict[str, TimeCost] = Field(..., description="Time costs for each action type")
    nodes: list[Node] = Field(..., min_length=1, description="Atomic units of the simulation")
    outcome_evaluation: OutcomeEvaluation = Field(..., description="How the case is scored")


def validate_case(filepath: str | Path) -> CaseDefinition:
    """Load and validate a case definition from a JSON file.

    Args:
        filepath: Path to the JSON file containing the case definition

    Returns:
        Validated CaseDefinition instance

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
        pydantic.ValidationError: If the case doesn't conform to the schema
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {filepath}")

    with path.open() as f:
        data = json.load(f)

    return CaseDefinition.model_validate(data)
