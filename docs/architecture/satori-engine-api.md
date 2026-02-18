# Satori Engine — Public API Reference

**Package version:** `0.1.0`
**Source:** `packages/satori/`
**Stability:** Phase 1 — stable within the phase; may expand in Phase 2+

This document is the authoritative reference for every symbol a consumer of
the `satori` package needs to know about. Internal implementation helpers
(`_advance_time`, `_validate_case_structure`, etc.) are omitted.

---

## Contents

1. [SatoriEngine](#1-satoriengine)
2. [GameState](#2-gamestate)
3. [Events](#3-events)
4. [PatientCondition](#4-patientcondition)
5. [parse\_action](#5-parse_action)
6. [CaseDefinition models](#6-casedefinition-models)
7. [LLM Client interfaces](#7-llm-client-interfaces)
8. [LLM Client config & factories](#8-llm-client-config--factories)
9. [Exceptions](#9-exceptions)
10. [Package exports summary](#10-package-exports-summary)

---

## 1. SatoriEngine

```python
from satori import SatoriEngine
```

### `class SatoriEngine`

Deterministic case execution engine. The only entry point an integration
layer needs for running a case.

#### Constructor

```python
SatoriEngine(case: CaseDefinition) -> None
```

Initialise the engine with a validated case definition. Performs
structural validation beyond Pydantic checks (e.g. reveal actions present
in `action_costs`, timer stages sorted). Computes the initial `GameState`,
activating all `starts_active` nodes and cascading their effects.

| Param | Type | Notes |
|---|---|---|
| `case` | `CaseDefinition` | Validated — call `validate_case()` first |

**Raises:** `CaseValidationError` — structural issues with the case.

#### Methods

```python
def execute_action(self, action: str) -> list[Event]
```

Execute a player action and return the resulting event list. This is the
**core game loop method**. Internally: parses action → validates →
advances time → advances timers → processes pending reveals → applies
expired/stage effects → checks auto-reveals → checks action-triggered
reveals → checks interventions → cascades activations → recomputes vitals
→ checks end conditions. Events are returned in causal order.

| Param | Type | Notes |
|---|---|---|
| `action` | `str` | `"base_action"` or `"base_action:parameter"` |

**Returns:** `list[Event]`

**Raises:** `InvalidActionError` — case already ended, unknown action type,
or action currently locked.

---

```python
def get_state(self) -> GameState
```

Return the current immutable state snapshot. Does not advance simulation.

**Returns:** `GameState`

---

```python
def get_available_actions(self) -> frozenset[str]
```

Convenience accessor for currently unlocked base action keys.

**Returns:** `frozenset[str]`

---

```python
def get_node_content(self, node_id: str) -> NodeContent | None
```

Return display content for a revealed node. Returns `None` if the node is
not yet revealed or does not exist. This is the primary way the frontend
gets displayable narrative + structured data for each finding.

| Param | Type | Notes |
|---|---|---|
| `node_id` | `str` | Node ID as defined in the case |

**Returns:** `NodeContent | None`

---

## 2. GameState

```python
from satori import GameState
```

### `@dataclass(frozen=True) class GameState`

Immutable snapshot of all engine state at a given moment. All mutations
produce new instances via `dataclasses.replace()`. The engine never
mutates a state object in place.

| Field | Type | Description |
|---|---|---|
| `case_id` | `UUID` | Case identifier |
| `current_time_minutes` | `int` | Simulation clock in minutes |
| `flags` | `frozenset[str]` | Set of active flag strings |
| `active_nodes` | `frozenset[str]` | Node IDs active in simulation |
| `revealed_nodes` | `frozenset[str]` | Node IDs visible to the player |
| `expired_nodes` | `frozenset[str]` | Node IDs whose timers expired |
| `pending_reveals` | `dict[str, int]` | `{node_id: remaining_minutes}` |
| `timers` | `dict[str, int]` | `{node_id: remaining_minutes}` |
| `timer_stages` | `dict[str, int]` | `{node_id: highest_stage_index_reached}` |
| `current_vitals` | `VitalSigns` | Computed from baseline + active nodes + stages |
| `available_actions` | `frozenset[str]` | Currently unlocked action keys |
| `case_ended` | `bool` | Whether the case has resolved (`False` by default) |
| `outcome_tier` | `str \| None` | `OutcomeTierLevel` value if ended, else `None` |
| `end_reason` | `str \| None` | Human-readable reason for case end |

---

## 3. Events

```python
from satori import (
    Event, EventType,
    TimeAdvancedEvent, NodeActivatedEvent, NodeRevealedEvent, NodeExpiredEvent,
    TimerStageEvent, FlagSetEvent, FlagClearedEvent, VitalsChangedEvent,
    ActionUnlockedEvent, ActionLockedEvent, PendingRevealStartedEvent, CaseEndedEvent,
)
```

All event classes are frozen dataclasses sharing a `type: EventType`
discriminant and `timestamp_minutes: int`.

### `class EventType(StrEnum)`

| Member | Value |
|---|---|
| `TIME_ADVANCED` | `"time_advanced"` |
| `NODE_ACTIVATED` | `"node_activated"` |
| `NODE_REVEALED` | `"node_revealed"` |
| `NODE_EXPIRED` | `"node_expired"` |
| `TIMER_STAGE` | `"timer_stage"` |
| `FLAG_SET` | `"flag_set"` |
| `FLAG_CLEARED` | `"flag_cleared"` |
| `VITALS_CHANGED` | `"vitals_changed"` |
| `ACTION_UNLOCKED` | `"action_unlocked"` |
| `ACTION_LOCKED` | `"action_locked"` |
| `PENDING_REVEAL_STARTED` | `"pending_reveal_started"` |
| `CASE_ENDED` | `"case_ended"` |

### `@dataclass(frozen=True) class Event` (base)

| Field | Type |
|---|---|
| `type` | `EventType` |
| `timestamp_minutes` | `int` |

### `@dataclass(frozen=True) class TimeAdvancedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `TIME_ADVANCED` (init=False) |
| `old_time` | `int` | |
| `new_time` | `int` | |
| `cause` | `str` | The action string that triggered time advancement |

### `@dataclass(frozen=True) class NodeActivatedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `NODE_ACTIVATED` (init=False) |
| `node_id` | `str` | |
| `node_type` | `str` | `NodeType` string value |

### `@dataclass(frozen=True) class NodeRevealedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `NODE_REVEALED` (init=False) |
| `node_id` | `str` | |
| `node_type` | `str` | |
| `content_text` | `str` | `NodeContent.narrative_text` |
| `structured_data` | `dict \| None` | `NodeContent.structured_data` |

### `@dataclass(frozen=True) class NodeExpiredEvent(Event)`

| Field | Type |
|---|---|
| `type` | `EventType` `NODE_EXPIRED` |
| `node_id` | `str` |

### `@dataclass(frozen=True) class TimerStageEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `TIMER_STAGE` (init=False) |
| `node_id` | `str` | |
| `stage_index` | `int` | |
| `stage_at_minutes` | `int` | Timer threshold this stage fired at |
| `vital_signs_changed` | `bool` | Whether new vitals accompany this stage |

### `@dataclass(frozen=True) class FlagSetEvent(Event)`

| Field | Type |
|---|---|
| `type` | `EventType` `FLAG_SET` |
| `flag` | `str` |

### `@dataclass(frozen=True) class FlagClearedEvent(Event)`

| Field | Type |
|---|---|
| `type` | `EventType` `FLAG_CLEARED` |
| `flag` | `str` |

### `@dataclass(frozen=True) class VitalsChangedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `VITALS_CHANGED` (init=False) |
| `old_vitals` | `dict` | Serialised `VitalSigns` |
| `new_vitals` | `dict` | Serialised `VitalSigns` |

### `@dataclass(frozen=True) class ActionUnlockedEvent(Event)`

| Field | Type |
|---|---|
| `type` | `EventType` `ACTION_UNLOCKED` |
| `action` | `str` |

### `@dataclass(frozen=True) class ActionLockedEvent(Event)`

| Field | Type |
|---|---|
| `type` | `EventType` `ACTION_LOCKED` |
| `action` | `str` |

### `@dataclass(frozen=True) class PendingRevealStartedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `PENDING_REVEAL_STARTED` (init=False) |
| `node_id` | `str` | |
| `delay_minutes` | `int` | How many minutes until the reveal fires |

### `@dataclass(frozen=True) class CaseEndedEvent(Event)`

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | `CASE_ENDED` (init=False) |
| `outcome_tier` | `str` | `OutcomeTierLevel` value |
| `end_reason` | `str` | |

---

## 4. PatientCondition

```python
from satori import PatientCondition, compute_patient_condition
```

### `class PatientCondition(StrEnum)`

| Member | Value |
|---|---|
| `STABLE` | `"stable"` |
| `COMPENSATING` | `"compensating"` |
| `DECOMPENSATING` | `"decompensating"` |
| `CRITICAL` | `"critical"` |
| `DEAD` | `"dead"` |
| `RECOVERED` | `"recovered"` |

### `compute_patient_condition(state: GameState, case: CaseDefinition) -> PatientCondition`

Derive patient condition from current state. **Read-only convenience** for
frontend/narration. Does NOT affect engine logic.

Heuristics in priority order:

1. `DEAD` — `"patient_death"` flag set, or a death node is active.
2. `RECOVERED` — case ended with optimal/good tier **and** `"correct_treatment_started"` flag is set.
3. `CRITICAL` — any vital in critical range: O₂ < 88%, HR > 150 or < 40, systolic BP < 90, temp > 104°F or < 95°F.
4. `DECOMPENSATING` — progression node timer is past 50% elapsed.
5. `COMPENSATING` — progression node timer is active but < 50% elapsed.
6. `STABLE` — default.

---

## 5. parse\_action

```python
from satori import parse_action
```

### `parse_action(action: str) -> tuple[str, str | None]`

Parse a player action string into `(base_action, parameter)`. The
`base_action` is used for time-cost lookup; `parameter` for
reveal/intervention matching.

| Input | Returns |
|---|---|
| `"history_general"` | `("history_general", None)` |
| `"history_focused:dietary"` | `("history_focused", "dietary")` |
| `"order_labs:cbc"` | `("order_labs", "cbc")` |
| `"start_treatment:albendazole"` | `("start_treatment", "albendazole")` |

---

## 6. CaseDefinition models

```python
from satori.models import CaseDefinition, validate_case
# Individual types also re-exported from satori.models
```

Only the types most relevant to API consumers are documented here. See
`packages/satori/src/satori/models/case_definition.py` for the full
schema.

### `validate_case(filepath: str | Path) -> CaseDefinition`

Load and fully validate a case definition from a JSON file.

**Raises:** `FileNotFoundError`, `json.JSONDecodeError`, `pydantic.ValidationError`

### Key models

#### `CaseDefinition(BaseModel)`

| Field | Type |
|---|---|
| `id` | `UUID` |
| `version` | `str` — semver pattern |
| `metadata` | `Metadata` |
| `patient` | `PatientContext` |
| `ground_truth` | `GroundTruth` |
| `action_costs` | `dict[str, TimeCost]` |
| `nodes` | `list[Node]` |
| `outcome_evaluation` | `OutcomeEvaluation` |

#### `PatientContext(BaseModel)`

| Field | Type |
|---|---|
| `name` | `str` |
| `age` | `int` |
| `sex` | `Sex` |
| `setting` | `str` |
| `chief_complaint` | `str` |
| `appearance` | `str` |
| `backstory` | `str \| None` |
| `arriving_vitals` | `VitalSigns` |
| `triage_note` | `str \| None` |

#### `VitalSigns(BaseModel)`

All fields optional (`None` = not measured/relevant).

| Field | Type | Constraint |
|---|---|---|
| `heart_rate` | `int \| None` | 0–300 BPM |
| `blood_pressure_systolic` | `int \| None` | 0–300 mmHg |
| `blood_pressure_diastolic` | `int \| None` | 0–200 mmHg |
| `temperature` | `float \| None` | 80.0–115.0 °F |
| `respiratory_rate` | `int \| None` | 0–100 breaths/min |
| `o2_saturation` | `int \| None` | 0–100 % |

#### `NodeContent(BaseModel)`

| Field | Type |
|---|---|
| `narrative_text` | `str` |
| `structured_data` | `dict[str, Any] \| None` |
| `stage_narratives` | `list[StageNarrative] \| None` |

#### Enums quick reference

| Enum | Members |
|---|---|
| `Difficulty` | `TUTORIAL`, `BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `EXPERT` |
| `DramaticTone` | `MEDICAL_MYSTERY`, `TRAUMA`, `ETHICAL_DILEMMA`, `RELATIONAL`, `PROCEDURAL` |
| `Sex` | `MALE`, `FEMALE`, `INTERSEX` |
| `NodeType` | `MEDICAL_FINDING`, `LAB_RESULT`, `IMAGING`, `HISTORY`, `RELATIONAL`, `EMOTIONAL`, `BEHAVIORAL`, `PROGRESSION`, `INTERVENTION_RESPONSE`, `OUTCOME` |
| `OutcomeTierLevel` | `OPTIMAL`, `GOOD`, `PARTIAL`, `FAILURE` |
| `EffectType` | `SET_FLAG`, `CLEAR_FLAG`, `ACTIVATE_NODE`, `DEACTIVATE_NODE`, `MODIFY_TIMER`, `UNLOCK_ACTION`, `LOCK_ACTION`, `OVERRIDE_VITALS`, `END_CASE` |
| `ConditionType` | `FLAG_SET`, `FLAG_NOT_SET`, `NODE_ACTIVE`, `NODE_REVEALED`, `NODE_EXPIRED`, `TIME_ELAPSED`, `VITAL_THRESHOLD` |

---

## 7. LLM Client interfaces

```python
from llm_client import Narrator, NarrationEvent, NarrationContext
from llm_client import CaseGenerator, ActionInterpreter
from llm_client import CaseSeed, ExplanationContext, ParsedAction
```

### `class Narrator(ABC)`

```python
def narrate(self, event: NarrationEvent, context: NarrationContext) -> str
def explain(self, context: ExplanationContext) -> str
```

`narrate()` returns a narrative string for a game event.
`explain()` returns a teaching explanation string.

**MockNarrator** returns:
`"[Mock Narration] {patient_name} experiences {event_type}: {description} (Time: {elapsed_minutes} minutes)"`

### `@dataclass(frozen=True) class NarrationEvent`

| Field | Type |
|---|---|
| `event_type` | `str` |
| `description` | `str` |
| `structured_data` | `dict[str, Any] \| None` |

### `@dataclass(frozen=True) class NarrationContext`

| Field | Type |
|---|---|
| `patient_name` | `str` |
| `patient_age` | `int` |
| `patient_sex` | `str` |
| `setting` | `str` |
| `current_vitals` | `dict[str, Any]` |
| `elapsed_minutes` | `int` |

### `@dataclass(frozen=True) class ExplanationContext`

| Field | Type | Default |
|---|---|---|
| `topic` | `str` | *(required)* |
| `patient_context` | `str` | *(required)* |
| `detail_level` | `str` | `"intermediate"` |

### `@dataclass(frozen=True) class CaseSeed`

| Field | Type | Default |
|---|---|---|
| `diagnosis` | `str` | *(required)* |
| `difficulty` | `str` | *(required)* |
| `dramatic_tone` | `str` | *(required)* |
| `patient_age_range` | `tuple[int, int] \| None` | `None` |
| `patient_sex` | `str \| None` | `None` |
| `setting` | `str \| None` | `None` |
| `complications` | `list[str] \| None` | `None` |
| `learning_objectives` | `list[str] \| None` | `None` |
| `content_boundaries` | `list[str] \| None` | `None` |

### `class CaseGenerator(ABC)`

```python
def generate_case(self, seed: CaseSeed) -> dict[str, Any]
```

Returns raw parsed JSON dict, NOT a `CaseDefinition`. Validation is
caller's responsibility.

---

## 8. LLM Client config & factories

```python
from llm_client import ModelConfig, Provider
from llm_client import create_narrator, create_case_generator, create_action_interpreter
```

### `class Provider(StrEnum)`

| Member | Value |
|---|---|
| `OPENAI` | `"openai"` |
| `ANTHROPIC` | `"anthropic"` |
| `MOCK` | `"mock"` |

### `@dataclass(frozen=True) class ModelConfig`

| Field | Type | Default |
|---|---|---|
| `provider` | `Provider` | *(required)* |
| `model` | `str` | *(required)* |
| `api_key` | `str \| None` | `None` — use `None` for mock |
| `temperature` | `float` | `0.7` |
| `max_tokens` | `int` | `16384` |
| `schema_path` | `str \| None` | `None` |

### Factory functions

```python
create_narrator(config: ModelConfig) -> Narrator
create_case_generator(config: ModelConfig) -> CaseGenerator
create_action_interpreter(config: ModelConfig) -> ActionInterpreter
```

All raise `LLMClientError` if `api_key` is `None` for non-mock providers,
or if no live implementation exists for the given provider in Phase 1.

**Phase 1 mock usage:**

```python
from llm_client import create_narrator, ModelConfig, Provider

narrator = create_narrator(ModelConfig(provider=Provider.MOCK, model="mock"))
```

---

## 9. Exceptions

| Exception | Where raised | Meaning |
|---|---|---|
| `CaseValidationError` | `SatoriEngine.__init__` | Case has structural issues beyond Pydantic |
| `InvalidActionError` | `SatoriEngine.execute_action` | Case ended, action unknown, or action locked |
| `LLMClientError` | `create_narrator` / `create_case_generator` / `create_action_interpreter` | Missing API key or no implementation for provider |
| `LLMProviderError` | `CaseGenerator.generate_case` | LLM API call failed |
| `LLMResponseError` | `CaseGenerator.generate_case` | LLM response is not valid JSON |

---

## 10. Package exports summary

### `satori` top-level exports (`__all__`)

```python
SatoriEngine, InvalidActionError
GameState
Event, EventType,
TimeAdvancedEvent, NodeActivatedEvent, NodeRevealedEvent, NodeExpiredEvent,
TimerStageEvent, FlagSetEvent, FlagClearedEvent, VitalsChangedEvent,
ActionUnlockedEvent, ActionLockedEvent, PendingRevealStartedEvent, CaseEndedEvent
PatientCondition, compute_patient_condition, parse_action
```

### `satori.models` top-level exports (`__all__`)

```python
ActivationRule, CaseDefinition, Comparator, Condition, ConditionPath, ConditionType,
Difficulty, DramaticTone, Effect, EffectType, EndCondition, EndConditionType,
GroundTruth, HarmfulAction, InterventionEffect, Metadata, NarrativeHook,
NarrativeHookType, Node, NodeContent, NodeEffects, NodeTimer, NodeType,
OptimalStep, OutcomeCategory, OutcomeEvaluation, OutcomeImpact, OutcomeTier,
OutcomeTierLevel, OutcomeWeight, PatientContext, RevealRule, Sex, StageNarrative,
TimeCost, TimeConstraint, TimerStage, VitalSigns, validate_case
```

### `llm_client` top-level exports

```python
CaseSeed, NarrationEvent, NarrationContext, ExplanationContext, ParsedAction
CaseGenerator, Narrator, ActionInterpreter
ModelConfig, Provider
create_case_generator, create_narrator, create_action_interpreter
LLMClientError, LLMProviderError, LLMResponseError
```
