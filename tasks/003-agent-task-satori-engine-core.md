# TASK: SATORI ENGINE CORE

## GOAL

Build the deterministic core engine at `packages/satori/src/satori/` that can:

- Load a validated case definition (via existing `validate_case()`)
- Initialize game state (time, vitals, known information, available actions)
- Accept player actions — including parameterized actions (see Design Decisions) — and validate them
- Advance simulated time deterministically
- Manage a pending-reveal queue for delayed results (labs, imaging)
- Reveal information nodes when conditions are met, including auto-reveal nodes
- Evaluate and trigger node activations using OR-of-ANDs logic
- Process intervention effects when treatment actions match node `on_intervene` rules
- Compute current vitals using "worst wins" algorithm, including timer-stage vitals
- Apply all nine effect types defined in the schema
- Evaluate end conditions and determine outcome tier
- Emit typed, structured events for every state change
- Be **fully deterministic**: same case + same actions = same outcome, every time

A test harness at `packages/satori/tests/test_engine_determinism.py` proves determinism by running the Maria Santos case through multiple action sequences and verifying identical outcomes.

## CONTEXT

This is Milestone 2 / Ho 02 of the Phase 1 gameplan. It is the **deterministic core** of the entire system — a state machine interpreter that reads frozen case definitions and produces deterministic sequences of state transitions.

**Upstream dependency:** The case schema and Pydantic models from Ho 01 (task-002) are frozen. The `CaseDefinition` model and all sub-models live in `packages/satori/src/satori/models/case_definition.py`. The example case is at `cases/example-neurocysticercosis.json`.

**Downstream consumers:**
- **Ho 03 (LLM Abstraction):** Will call `narrate(event, state)` — needs typed events with enough context for narration
- **Ho 05 (Internal Affairs frontend):** Will send actions and display `GameState` — needs a clear public API
- **Ho 06 (Vertical Slice):** Full end-to-end integration

**Critical Architectural Constraint:** Satori NEVER calls the LLM. It NEVER generates text. It reads structure and produces events. All randomness belongs in case generation, not execution.

---

## DESIGN DECISIONS (MADE)

These decisions were made during task review. They are binding for implementation.

### Decision 1: Condition-Based Evaluation (not State Enum)

Patient condition is **not** tracked as an explicit state enum (stable → decompensating → critical). Instead, condition is **emergent** from the combination of active nodes, flags, timers, and computed vitals.

**Why:** The case schema already encodes progression through timer stages, flag gates, and vital-sign effects. Adding a parallel state enum would create a second source of truth that could drift from the node graph. The schema is the instruction set; the engine is the interpreter.

**Computed property for consumers:** A utility function `compute_patient_condition(state, case) → PatientCondition` derives a human-readable label (stable / compensating / decompensating / critical / dead / recovered) from current vitals, flags, and active nodes **on demand**. This is a read-only convenience for the frontend and narration layer — it is never stored in `GameState` and never affects engine logic.

### Decision 2: Action Parameter Convention (Split on Colon)

Player actions use the format `base_action:parameter` (e.g., `history_focused:dietary`, `order_labs:cbc`, `start_treatment:albendazole`).

- **Base action** (before colon): Used for time-cost lookup in `case.action_costs`
- **Parameter** (after colon): Matched against `RevealRule.subcategory` and `InterventionEffect.treatment` to determine which nodes are revealed or which interventions are triggered

Actions without parameters (e.g., `history_general`) are also valid — the parameter is `None`.

**Parsing:** `parse_action(action: str) → tuple[str, str | None]` splits on the first colon.

### Decision 3: Pending Reveal Queue (for Delayed Results)

When a player orders labs or imaging with `result_delay_minutes > 0`, the node is **not** immediately revealed. Instead:

1. The action's `action_minutes` cost is paid immediately
2. The node enters a `pending_reveals: dict[str, int]` queue mapping `node_id → minutes_remaining`
3. Each time advancement ticks down all pending reveals
4. When a pending reveal reaches 0, the reveal fires: the node enters `revealed_nodes`, `on_reveal` effects execute, and a `NodeRevealedEvent` is emitted

This is separate from node timers. Timers track node-internal countdowns (progression, crisis). Pending reveals track the delay between ordering a test and getting results.

### Decision 4: Typed Event Subclasses

Each `EventType` has its own frozen dataclass with explicit, named fields. This gives downstream consumers (narration, frontend) a strongly-typed contract.

---

## DO NOT CHANGE

- The case schema or Pydantic models in `packages/satori/src/satori/models/` (frozen from task-002)
- Any package structure outside of `packages/satori/`
- The README or documentation (this task only creates engine code and tests)

---

## REQUIRED COMPONENTS

### 1. Events (packages/satori/src/satori/events.py)

Typed event hierarchy. Every state change the engine produces is one of these.

```python
from enum import StrEnum
from dataclasses import dataclass

class EventType(StrEnum):
    """Types of events the engine emits."""
    TIME_ADVANCED = "time_advanced"
    NODE_ACTIVATED = "node_activated"
    NODE_REVEALED = "node_revealed"
    NODE_EXPIRED = "node_expired"
    TIMER_STAGE = "timer_stage"
    FLAG_SET = "flag_set"
    FLAG_CLEARED = "flag_cleared"
    VITALS_CHANGED = "vitals_changed"
    ACTION_UNLOCKED = "action_unlocked"
    ACTION_LOCKED = "action_locked"
    PENDING_REVEAL_STARTED = "pending_reveal_started"
    CASE_ENDED = "case_ended"

@dataclass(frozen=True)
class Event:
    """Base event — all events have a type and timestamp."""
    type: EventType
    timestamp_minutes: int

@dataclass(frozen=True)
class TimeAdvancedEvent(Event):
    """Clock moved forward."""
    old_time: int
    new_time: int
    cause: str  # the action that caused time to advance

@dataclass(frozen=True)
class NodeActivatedEvent(Event):
    """A node became active in the simulation."""
    node_id: str
    node_type: str  # NodeType value

@dataclass(frozen=True)
class NodeRevealedEvent(Event):
    """A node's content became visible to the player."""
    node_id: str
    node_type: str
    content_text: str       # NodeContent.narrative_text
    structured_data: dict | None  # NodeContent.structured_data

@dataclass(frozen=True)
class NodeExpiredEvent(Event):
    """A node's timer reached zero."""
    node_id: str

@dataclass(frozen=True)
class TimerStageEvent(Event):
    """A timer crossed a stage boundary."""
    node_id: str
    stage_index: int
    stage_at_minutes: int
    vital_signs_changed: bool  # whether this stage carries new vitals

@dataclass(frozen=True)
class FlagSetEvent(Event):
    """A flag was set."""
    flag: str

@dataclass(frozen=True)
class FlagClearedEvent(Event):
    """A flag was cleared."""
    flag: str

@dataclass(frozen=True)
class VitalsChangedEvent(Event):
    """Patient vitals changed."""
    old_vitals: dict  # serialized VitalSigns
    new_vitals: dict

@dataclass(frozen=True)
class ActionUnlockedEvent(Event):
    """An action became available."""
    action: str

@dataclass(frozen=True)
class ActionLockedEvent(Event):
    """An action became unavailable."""
    action: str

@dataclass(frozen=True)
class PendingRevealStartedEvent(Event):
    """A delayed result was ordered (e.g., labs sent)."""
    node_id: str
    delay_minutes: int

@dataclass(frozen=True)
class CaseEndedEvent(Event):
    """The case resolved."""
    outcome_tier: str  # OutcomeTierLevel value
    end_reason: str    # description of what triggered the end
```

### 2. GameState (packages/satori/src/satori/game_state.py)

The current state of a running case. Immutable — all updates return new instances.

```python
from dataclasses import dataclass, field
from uuid import UUID
from satori.models.case_definition import VitalSigns

@dataclass(frozen=True)
class GameState:
    """Immutable game state snapshot."""

    # Identity
    case_id: UUID

    # Time
    current_time_minutes: int

    # Flags (set/cleared by effects)
    flags: frozenset[str]

    # Node lifecycle states
    active_nodes: frozenset[str]    # node IDs currently live in simulation
    revealed_nodes: frozenset[str]  # node IDs whose content is visible to player
    expired_nodes: frozenset[str]   # node IDs whose timers have expired

    # Pending reveals: {node_id: minutes_remaining}
    # For labs/imaging with result_delay_minutes
    pending_reveals: dict[str, int]

    # Timers: {node_id: remaining_minutes}
    # Tracks countdown timers for progression/crisis nodes
    timers: dict[str, int]

    # Current timer stages: {node_id: highest_stage_index_reached}
    # Tracks which timer stage each timed node is currently at
    timer_stages: dict[str, int]

    # Current vitals (computed from baseline + active nodes + timer stages)
    current_vitals: VitalSigns

    # Available actions (initialized from action_costs keys, modified by effects)
    available_actions: frozenset[str]

    # Case resolution
    case_ended: bool = False
    outcome_tier: str | None = None
    end_reason: str | None = None
```

**Key principles:**
- Immutable (`frozen=True` dataclass)
- All updates create a new `GameState` via `dataclasses.replace()`
- No hidden state — everything affecting outcomes is visible here
- Fully serializable for save/replay
- `pending_reveals` and `timers` use `dict` (not `frozenset`) because they carry integer values; treat them as immutable by convention (copy-on-write in updates)

### 3. Action Parser (packages/satori/src/satori/action_parser.py)

Parses compound action strings.

```python
def parse_action(action: str) -> tuple[str, str | None]:
    """
    Parse a player action into (base_action, parameter).

    Examples:
        "history_general" → ("history_general", None)
        "history_focused:dietary" → ("history_focused", "dietary")
        "order_labs:cbc" → ("order_labs", "cbc")
        "start_treatment:albendazole" → ("start_treatment", "albendazole")
    """
    if ":" in action:
        base, param = action.split(":", 1)
        return base, param
    return action, None
```

### 4. ConditionEvaluator (packages/satori/src/satori/condition_evaluator.py)

Evaluates conditions from the schema against current game state.

```python
from satori.models.case_definition import (
    ActivationRule, RevealRule, Condition, ConditionType,
    Comparator, VitalSigns
)
from satori.game_state import GameState

class ConditionEvaluator:
    """Evaluates activation, reveal, and end conditions."""

    def evaluate_activation_rule(
        self,
        rule: ActivationRule,
        state: GameState
    ) -> bool:
        """
        Evaluate if activation rule is satisfied.

        OR-of-ANDs logic:
        - Rule satisfied if ANY path is satisfied
        - Path satisfied if ALL conditions in path are true
        - If rule.paths is None and starts_active is False, never activates by path
        - If rule.starts_active is True, this is only called for re-evaluation
          (node was already activated at init)
        """
        if rule.paths is None:
            return False
        return any(
            all(
                self._evaluate_condition(cond, state)
                for cond in path.conditions
            )
            for path in rule.paths
        )

    def evaluate_reveal_rule(
        self,
        rule: RevealRule,
        state: GameState,
        base_action: str | None,
        action_param: str | None
    ) -> bool:
        """
        Evaluate if reveal rule is satisfied by the given action.

        Matching logic:
        1. If rule.auto_reveal is True → always True (handled separately, but
           this returns True for consistency)
        2. If rule.action is not None:
           - base_action must match rule.action
           - If rule.subcategory is not None, action_param must match rule.subcategory
        3. If rule.conditions is not None, all must be satisfied
        """
        if rule.auto_reveal:
            return True

        # Action matching
        if rule.action is not None:
            if base_action != rule.action:
                return False
            if rule.subcategory is not None and action_param != rule.subcategory:
                return False

        # Additional conditions
        if rule.conditions:
            if not all(self._evaluate_condition(c, state) for c in rule.conditions):
                return False

        return True

    def _evaluate_condition(
        self,
        condition: Condition,
        state: GameState
    ) -> bool:
        """Evaluate a single condition against current state."""
        match condition.type:
            case ConditionType.FLAG_SET:
                return condition.target in state.flags
            case ConditionType.FLAG_NOT_SET:
                return condition.target not in state.flags
            case ConditionType.NODE_ACTIVE:
                return condition.target in state.active_nodes
            case ConditionType.NODE_REVEALED:
                return condition.target in state.revealed_nodes
            case ConditionType.NODE_EXPIRED:
                return condition.target in state.expired_nodes
            case ConditionType.TIME_ELAPSED:
                return self._compare(
                    state.current_time_minutes,
                    condition.value,
                    condition.comparator or Comparator.GTE
                )
            case ConditionType.VITAL_THRESHOLD:
                return self._evaluate_vital_threshold(condition, state)
            case _:
                raise ValueError(f"Unknown condition type: {condition.type}")

    def _compare(self, actual: float, threshold: float, comp: Comparator) -> bool:
        """Apply comparator to two values."""
        match comp:
            case Comparator.GT:
                return actual > threshold
            case Comparator.LT:
                return actual < threshold
            case Comparator.GTE:
                return actual >= threshold
            case Comparator.LTE:
                return actual <= threshold
            case Comparator.EQ:
                return actual == threshold

    def _evaluate_vital_threshold(
        self,
        condition: Condition,
        state: GameState
    ) -> bool:
        """
        Evaluate a vital threshold condition.

        condition.target = vital name (e.g., "heart_rate", "o2_saturation")
        condition.value = threshold value
        condition.comparator = comparison operator
        """
        vital_value = getattr(state.current_vitals, condition.target, None)
        if vital_value is None:
            return False
        return self._compare(
            vital_value,
            condition.value,
            condition.comparator or Comparator.GTE
        )
```

### 5. VitalsComputer (packages/satori/src/satori/vitals_computer.py)

Computes current vitals from baseline, active nodes, and current timer stages using "worst wins."

```python
from satori.models.case_definition import VitalSigns, Node, TimerStage
from satori.game_state import GameState

class VitalsComputer:
    """Computes current vitals from active nodes using worst-wins algorithm."""

    # Normal ranges for determining "worst"
    NORMAL_RANGES = {
        "heart_rate": (60, 100),
        "blood_pressure_systolic": (90, 140),
        "blood_pressure_diastolic": (60, 90),
        "temperature": (97.0, 99.5),
        "respiratory_rate": (12, 20),
        "o2_saturation": (95, 100),
    }

    def compute_vitals(
        self,
        baseline: VitalSigns,
        active_nodes: list[Node],
        state: GameState
    ) -> VitalSigns:
        """
        Compute current vitals using "worst wins" algorithm.

        Sources of vitals (in addition to baseline):
        1. node.vital_signs — base vitals for each active node
        2. Timer stage vitals — from the highest reached stage of each
           active node's timer (state.timer_stages tracks this)

        For each vital field:
        1. Start with baseline value
        2. Collect values from all active nodes' vital_signs
        3. Collect values from current timer stage vital_signs
           (looked up via state.timer_stages[node_id])
        4. Take the "worst" (most dangerous) value

        "Worst" means furthest from normal range:
        - heart_rate: furthest from 60-100
        - blood_pressure_systolic: highest (hypertensive crisis is acute risk)
        - blood_pressure_diastolic: highest
        - temperature: furthest from 97.0-99.5
        - respiratory_rate: furthest from 12-20
        - o2_saturation: lowest (desaturation is acute risk)
        """
        ...

    def _collect_vital_values(
        self,
        vital_name: str,
        baseline: VitalSigns,
        active_nodes: list[Node],
        state: GameState
    ) -> list[float]:
        """
        Collect all candidate values for a vital from baseline,
        active node vitals, and current timer stage vitals.
        """
        values = []
        baseline_val = getattr(baseline, vital_name, None)
        if baseline_val is not None:
            values.append(baseline_val)

        for node in active_nodes:
            # Node-level vitals
            if node.vital_signs:
                val = getattr(node.vital_signs, vital_name, None)
                if val is not None:
                    values.append(val)

            # Timer-stage vitals (if node has a timer and has reached stages)
            if node.timer and node.timer.stages and node.id in state.timer_stages:
                current_stage_idx = state.timer_stages[node.id]
                # Find the stage with the highest index <= current_stage_idx
                for stage in node.timer.stages:
                    if stage.at_minutes <= self._minutes_elapsed_for_stage(
                        node, current_stage_idx, state
                    ):
                        if stage.vital_signs:
                            val = getattr(stage.vital_signs, vital_name, None)
                            if val is not None:
                                values.append(val)
        return values

    def _worst_value(
        self,
        vital_name: str,
        values: list[float]
    ) -> float | None:
        """
        Determine worst value for a specific vital.

        Strategy per vital:
        - o2_saturation: lowest wins (desaturation)
        - blood_pressure_systolic, blood_pressure_diastolic: highest wins
        - heart_rate, respiratory_rate, temperature: furthest from normal midpoint
        """
        if not values:
            return None
        ...
```

### 6. TimerManager (packages/satori/src/satori/timer_manager.py)

Manages node timers, stage transitions, and pending reveals.

```python
from satori.models.case_definition import CaseDefinition, Condition
from satori.game_state import GameState
from satori.events import (
    Event, TimerStageEvent, NodeExpiredEvent, NodeRevealedEvent,
    PendingRevealStartedEvent
)
from satori.condition_evaluator import ConditionEvaluator

class TimerManager:
    """Manages node timers, stage transitions, and pending reveals."""

    def __init__(self, condition_evaluator: ConditionEvaluator):
        self.condition_eval = condition_evaluator

    def advance_timers(
        self,
        state: GameState,
        minutes_elapsed: int,
        case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """
        Advance all active node timers by minutes_elapsed.

        For each timer (node_id in state.timers):
        1. Check pause conditions — if ALL pause conditions met, skip
        2. Subtract minutes_elapsed from remaining time
        3. Check if timer crossed any stage boundaries (at_minutes thresholds)
           - For each crossed stage: emit TimerStageEvent, apply stage effects,
             update timer_stages tracking
        4. Check if timer expired (remaining <= 0)
           - Emit NodeExpiredEvent
           - Apply on_expire effects from the NodeTimer
           - Apply on_expire effects from NodeEffects (if present)
           - Move node_id to expired_nodes

        Returns updated state and list of events.

        IMPORTANT: Stage boundaries are checked by comparing the timer's
        elapsed time (duration_minutes - remaining) against stage.at_minutes.
        A stage at_minutes=60 triggers when 60 minutes have elapsed since
        the timer started, NOT when 60 minutes remain.
        """
        ...

    def advance_pending_reveals(
        self,
        state: GameState,
        minutes_elapsed: int,
        case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """
        Tick down all pending reveals by minutes_elapsed.

        For each pending reveal whose remaining time reaches 0:
        1. Move node_id to revealed_nodes
        2. Look up the Node to get content for the event
        3. Apply on_reveal effects (from node.effects, if present)
        4. Emit NodeRevealedEvent with content

        Returns updated state and list of events.
        """
        ...

    def _check_pause_conditions(
        self,
        pause_conditions: list[Condition] | None,
        state: GameState
    ) -> bool:
        """
        Check if timer is currently paused.
        Timer pauses when ALL pause conditions are satisfied.
        Returns True if paused.
        """
        if not pause_conditions:
            return False
        return all(
            self.condition_eval._evaluate_condition(c, state)
            for c in pause_conditions
        )
```

### 7. EffectExecutor (packages/satori/src/satori/effect_executor.py)

Applies ALL nine effect types to game state.

```python
from satori.models.case_definition import (
    CaseDefinition, Effect, EffectType, VitalSigns
)
from satori.game_state import GameState
from satori.events import (
    Event, FlagSetEvent, FlagClearedEvent, NodeActivatedEvent,
    ActionUnlockedEvent, ActionLockedEvent, CaseEndedEvent
)

class EffectExecutor:
    """Executes effects that modify game state."""

    def apply_effects(
        self,
        effects: list[Effect] | None,
        state: GameState,
        case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """
        Apply list of effects to state. Null-safe — if effects is None,
        returns state unchanged.

        Returns updated state and events generated by effects.
        """
        if not effects:
            return state, []

        new_state = state
        events = []

        for effect in effects:
            new_state, effect_events = self._apply_single_effect(
                effect, new_state, case
            )
            events.extend(effect_events)

        return new_state, events

    def _apply_single_effect(
        self,
        effect: Effect,
        state: GameState,
        case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """Apply single effect. Handles ALL nine EffectType values."""
        match effect.type:
            case EffectType.SET_FLAG:
                return self._set_flag(effect.target, state)
            case EffectType.CLEAR_FLAG:
                return self._clear_flag(effect.target, state)
            case EffectType.ACTIVATE_NODE:
                return self._activate_node(effect.target, state, case)
            case EffectType.DEACTIVATE_NODE:
                return self._deactivate_node(effect.target, state)
            case EffectType.MODIFY_TIMER:
                return self._modify_timer(
                    effect.target, effect.value, state
                )
            case EffectType.UNLOCK_ACTION:
                return self._unlock_action(effect.target, state)
            case EffectType.LOCK_ACTION:
                return self._lock_action(effect.target, state)
            case EffectType.OVERRIDE_VITALS:
                return self._override_vitals(effect, state)
            case EffectType.END_CASE:
                return self._end_case(effect.target, state, case)
            case _:
                raise ValueError(f"Unknown effect type: {effect.type}")

    def _set_flag(self, flag: str, state: GameState) -> tuple[GameState, list[Event]]:
        """Add flag to state.flags. Emit FlagSetEvent."""
        ...

    def _clear_flag(self, flag: str, state: GameState) -> tuple[GameState, list[Event]]:
        """Remove flag from state.flags. Emit FlagClearedEvent."""
        ...

    def _activate_node(
        self, node_id: str, state: GameState, case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """
        Add node_id to active_nodes. If the node has a timer,
        initialize it in state.timers. Apply on_activate effects
        (from node.activation.on_activate). Emit NodeActivatedEvent.

        Must look up the Node from case.nodes to get timer config.
        Null-safe: check node.activation.on_activate is not None.
        """
        ...

    def _deactivate_node(
        self, node_id: str, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """Remove node_id from active_nodes. Clean up its timer if present."""
        ...

    def _modify_timer(
        self, node_id: str, value: int, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Add value to the timer for node_id.
        Positive value = extend timer (more time).
        Negative value = accelerate timer (less time, approaching expiry).

        Example: node_08's on_expire does modify_timer on node_06 with value=-60,
        meaning steroids accelerate the headache progression by 60 minutes.
        """
        ...

    def _unlock_action(
        self, action: str, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """Add action to available_actions. Emit ActionUnlockedEvent."""
        ...

    def _lock_action(
        self, action: str, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """Remove action from available_actions. Emit ActionLockedEvent."""
        ...

    def _override_vitals(
        self, effect: Effect, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Override specific vital signs directly.
        effect.target = vital name (e.g., "heart_rate")
        effect.value = new value
        Sets the vital directly on current_vitals, bypassing worst-wins.
        """
        ...

    def _end_case(
        self, outcome_tier: str, state: GameState, case: CaseDefinition
    ) -> tuple[GameState, list[Event]]:
        """
        End the case with the given outcome tier.
        Set case_ended=True, outcome_tier, and emit CaseEndedEvent.
        """
        ...
```

### 8. Patient Condition Utility (packages/satori/src/satori/patient_condition.py)

Computed property for downstream consumers. Not stored in GameState.

```python
from enum import StrEnum
from satori.game_state import GameState
from satori.models.case_definition import CaseDefinition

class PatientCondition(StrEnum):
    """Derived patient condition for display and narration."""
    STABLE = "stable"
    COMPENSATING = "compensating"
    DECOMPENSATING = "decompensating"
    CRITICAL = "critical"
    DEAD = "dead"
    RECOVERED = "recovered"

def compute_patient_condition(
    state: GameState,
    case: CaseDefinition
) -> PatientCondition:
    """
    Derive patient condition from current state.

    This is a READ-ONLY convenience for frontend and narration.
    It does not affect engine logic.

    Heuristics:
    - DEAD: "patient_death" flag set or death outcome node active
    - RECOVERED: "correct_treatment_started" flag set and case ended with optimal/good
    - CRITICAL: any vital in critical range (O2 < 88, HR > 150 or < 40, etc.)
    - DECOMPENSATING: any progression node timer past 50% elapsed
    - COMPENSATING: any progression node timer active but < 50% elapsed
    - STABLE: default when no danger signals present

    The thresholds here are heuristic defaults for Phase 1. In future
    phases, cases may define their own condition-mapping rules.
    """
    ...
```

### 9. Main Engine (packages/satori/src/satori/engine.py)

Orchestrates all components. This is the **public API** of the Satori package.

```python
from satori.models.case_definition import CaseDefinition, validate_case
from satori.game_state import GameState
from satori.events import Event
from satori.condition_evaluator import ConditionEvaluator
from satori.timer_manager import TimerManager
from satori.vitals_computer import VitalsComputer
from satori.effect_executor import EffectExecutor
from satori.action_parser import parse_action

class InvalidActionError(Exception):
    """Raised when a player attempts an unavailable or malformed action."""
    pass

class SatoriEngine:
    """
    Deterministic case execution engine.

    PUBLIC API — this is what Ho 05 (frontend) and Ho 06 (integration) consume.

    Methods:
        __init__(case): Load case and initialize state
        execute_action(action) -> list[Event]: Process a player action
        get_state() -> GameState: Get current immutable state snapshot
        get_available_actions() -> frozenset[str]: Convenience accessor
        get_node_content(node_id) -> NodeContent | None: Get revealed node content
    """

    def __init__(self, case: CaseDefinition):
        self.case = case
        self._node_map: dict[str, Node] = {n.id: n for n in case.nodes}
        self.condition_eval = ConditionEvaluator()
        self.timer_mgr = TimerManager(self.condition_eval)
        self.vitals_comp = VitalsComputer()
        self.effect_exec = EffectExecutor()

        # Initialize game state
        self.state = self._initialize_state()

    def _initialize_state(self) -> GameState:
        """
        Initialize game state from case definition.

        Steps:
        1. Set current_time_minutes = 0
        2. Set flags = frozenset({"case_start"})
        3. Set available_actions from case.action_costs keys
        4. Find all nodes with activation.starts_active == True:
           a. Add to active_nodes
           b. If node has a timer, add to state.timers with duration_minutes
           c. Apply activation.on_activate effects (null-safe)
        5. Evaluate all non-starts_active nodes' activation rules
           (some might activate immediately due to flags/conditions from step 4)
        6. Check for auto-reveal nodes among newly activated nodes
        7. Compute initial vitals from baseline + active nodes
        """
        ...

    def execute_action(self, action: str) -> list[Event]:
        """
        Execute a player action and return events.

        THIS IS THE CORE GAME LOOP.

        1. Parse action into (base_action, parameter)
        2. Validate base_action exists in case.action_costs
        3. Validate action string is in available_actions OR base_action is
           (actions are available at the base level; parameters refine them)
        4. Look up time cost: case.action_costs[base_action].action_minutes
        5. Advance time by action_minutes
        6. Advance all active timers by action_minutes
        7. Advance all pending reveals by action_minutes
        8. Check for auto-reveal nodes (activation met, auto_reveal=True)
        9. Check for action-triggered reveals:
           - For each active, unrevealed node with a reveal rule:
             - If rule matches (base_action, parameter) and conditions met:
               - If reveal has delay_minutes: add to pending_reveals
               - If no delay: reveal immediately
        10. Check for intervention matches:
            - For each active node with effects.on_intervene:
              - If on_intervene.treatment == parameter (or action):
                apply on_intervene.effects
        11. Check for newly activated nodes (cascade — repeat until stable)
        12. Recompute vitals
        13. Check end conditions
        14. If not ended, evaluate outcome tier readiness (for partial tracking)

        Returns list of events in causal order.

        Raises:
            InvalidActionError: if action is not available
        """
        if self.state.case_ended:
            raise InvalidActionError("Case has already ended")

        events: list[Event] = []
        base_action, param = parse_action(action)

        # Validate
        if base_action not in self.case.action_costs:
            raise InvalidActionError(
                f"Unknown action type: {base_action}"
            )
        # Base actions are always available if in action_costs
        # (unless locked by effect)
        if base_action not in self.state.available_actions:
            raise InvalidActionError(
                f"Action {base_action} is currently locked"
            )

        # 1. Time advancement
        time_cost = self.case.action_costs[base_action].action_minutes
        new_state, time_events = self._advance_time(time_cost, action)
        events.extend(time_events)

        # 2. Timer advancement
        new_state, timer_events = self.timer_mgr.advance_timers(
            new_state, time_cost, self.case
        )
        events.extend(timer_events)

        # 3. Pending reveal advancement
        new_state, pending_events = self.timer_mgr.advance_pending_reveals(
            new_state, time_cost, self.case
        )
        events.extend(pending_events)

        # 4. Auto-reveals
        new_state, auto_events = self._check_auto_reveals(new_state)
        events.extend(auto_events)

        # 5. Action-triggered reveals
        new_state, reveal_events = self._check_action_reveals(
            new_state, base_action, param
        )
        events.extend(reveal_events)

        # 6. Intervention matching
        new_state, intervene_events = self._check_interventions(
            new_state, base_action, param
        )
        events.extend(intervene_events)

        # 7. Activation cascade
        new_state, activation_events = self._cascade_activations(new_state)
        events.extend(activation_events)

        # 8. Vitals recomputation
        new_state, vital_events = self._recompute_vitals(new_state)
        events.extend(vital_events)

        # 9. End condition check
        new_state, end_events = self._check_end_conditions(new_state)
        events.extend(end_events)

        self.state = new_state
        return events

    def _advance_time(
        self, minutes: int, cause: str
    ) -> tuple[GameState, list[Event]]:
        """Advance clock. Emit TimeAdvancedEvent."""
        ...

    def _check_auto_reveals(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Check all active, unrevealed nodes for auto_reveal=True.
        If a node is active, has reveal.auto_reveal=True, and hasn't been
        revealed yet, reveal it immediately.
        """
        ...

    def _check_action_reveals(
        self,
        state: GameState,
        base_action: str,
        param: str | None
    ) -> tuple[GameState, list[Event]]:
        """
        Check if the current action reveals any nodes.

        For each active, unrevealed node:
        - If node.reveal is None → skip
        - If node.reveal.auto_reveal → skip (handled by _check_auto_reveals)
        - Evaluate reveal rule against (base_action, param, state)
        - If matched AND reveal.delay_minutes is set:
            → Add to pending_reveals, emit PendingRevealStartedEvent
        - If matched AND no delay:
            → Reveal immediately, apply on_reveal effects, emit NodeRevealedEvent

        Also check case.action_costs[base_action].result_delay_minutes:
        - If present AND the node's own delay_minutes is None, use the action's
          result_delay_minutes as the delay
        - This handles the case where labs are universally delayed but the
          node doesn't specify its own delay
        """
        ...

    def _check_interventions(
        self,
        state: GameState,
        base_action: str,
        param: str | None
    ) -> tuple[GameState, list[Event]]:
        """
        Check if the action triggers any intervention effects.

        For each active node:
        - If node.effects is None → skip
        - If node.effects.on_intervene is None → skip
        - If on_intervene.treatment matches param (or base_action if no param):
            → Apply on_intervene.effects
        """
        ...

    def _cascade_activations(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Check all inactive nodes for activation. Repeat until no new
        activations occur (cascade — one activation may enable another).

        For each node not in active_nodes:
        - Evaluate activation.paths using ConditionEvaluator
        - If satisfied: activate node, start timer if present,
          apply on_activate effects
        - After each round, re-check (new flags/nodes may trigger more)

        Limit cascade depth to prevent infinite loops (e.g., max 10 rounds).
        """
        ...

    def _recompute_vitals(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Recompute vitals from baseline + active nodes + timer stages.
        If vitals changed, emit VitalsChangedEvent.
        """
        ...

    def _check_end_conditions(
        self, state: GameState
    ) -> tuple[GameState, list[Event]]:
        """
        Check all end conditions in case.outcome_evaluation.end_conditions.

        EndConditionType handling:
        - NODE_ACTIVATED: check if target node_id is in active_nodes
        - TIME_ELAPSED: check if current_time_minutes >= value
        - FLAG_SET: check if target flag is in state.flags
        - ALL_CRITICAL_RESOLVED: check if all critical nodes are resolved
          (implementation note: "critical" = outcome_weight.impact == CRITICAL)

        If any end condition is met:
        1. Determine outcome tier by evaluating case.outcome_evaluation.tiers
           in order (optimal first, failure last)
        2. A tier matches if:
           - All required_flags are in state.flags (if specified)
           - No excluded_flags are in state.flags (if specified)
           - All time_constraints are satisfied (flag set before deadline)
        3. First matching tier = the outcome
        4. If no tier matches, default to "failure"
        5. Set case_ended=True, outcome_tier, end_reason
        6. Emit CaseEndedEvent
        """
        ...

    def get_state(self) -> GameState:
        """Get current immutable state snapshot."""
        return self.state

    def get_available_actions(self) -> frozenset[str]:
        """Get currently available base actions."""
        return self.state.available_actions

    def get_node_content(self, node_id: str) -> "NodeContent | None":
        """
        Get content for a revealed node. Returns None if node
        is not revealed or doesn't exist.

        This is how the frontend gets displayable text for revealed
        information. The frontend should call this for each node_id
        in state.revealed_nodes.
        """
        if node_id not in self.state.revealed_nodes:
            return None
        node = self._node_map.get(node_id)
        return node.content if node else None
```

### 10. Public API Exports (packages/satori/src/satori/__init__.py)

Update to export the engine's public surface.

```python
"""Satori — Deterministic medical case engine."""

__version__ = "0.1.0"

from satori.engine import SatoriEngine, InvalidActionError
from satori.game_state import GameState
from satori.events import (
    Event, EventType,
    TimeAdvancedEvent, NodeActivatedEvent, NodeRevealedEvent,
    NodeExpiredEvent, TimerStageEvent, FlagSetEvent, FlagClearedEvent,
    VitalsChangedEvent, ActionUnlockedEvent, ActionLockedEvent,
    PendingRevealStartedEvent, CaseEndedEvent,
)
from satori.patient_condition import PatientCondition, compute_patient_condition
from satori.action_parser import parse_action
```

### 11. Error Handling Strategy

The engine has two categories of errors:

**Load-time validation (fail fast):**
When `SatoriEngine.__init__` is called, perform structural validation beyond what Pydantic checks:
- All node IDs referenced in effects/conditions actually exist in the case
- All flags referenced in conditions are set somewhere in the case (or are system flags like `case_start`)
- All action references in reveal rules exist in action_costs
- Timer stages are sorted by `at_minutes` ascending
- No circular activation dependencies (A activates B which activates A)

Raise `CaseValidationError(Exception)` with a descriptive message listing all issues found.

**Runtime errors (player-facing):**
- `InvalidActionError` — action not available or unknown. Include what action was attempted and what actions are available.
- Engine should never crash on valid case data + valid action sequences. Any other exception is a bug.

### 12. Test Harness (packages/satori/tests/test_engine_determinism.py)

Comprehensive tests using the Maria Santos case.

```python
import pytest
from pathlib import Path
from satori.engine import SatoriEngine, InvalidActionError
from satori.models.case_definition import validate_case
from satori.events import *
from satori.game_state import GameState
from satori.patient_condition import compute_patient_condition, PatientCondition

CASE_PATH = Path(__file__).parent.parent.parent.parent / "cases" / "example-neurocysticercosis.json"

@pytest.fixture
def case():
    return validate_case(CASE_PATH)

@pytest.fixture
def engine(case):
    return SatoriEngine(case)


class TestInitialization:
    """Engine initialization from case definition."""

    def test_loads_all_nodes(self, engine):
        """12 nodes in Maria Santos case."""
        assert len(engine._node_map) == 12

    def test_starts_active_nodes_activated(self, engine):
        """Nodes with starts_active=True are in active_nodes at init."""
        state = engine.get_state()
        # node_01 through node_05 and node_08 have starts_active=True
        for node_id in [
            "node_01_chief_complaint",
            "node_02_neuro_exam",
            "node_03_ct_lesion",
            "node_04_lab_eosinophilia",
            "node_05_dietary_history",
            "node_08_wrong_treatment_steroids",
        ]:
            assert node_id in state.active_nodes, f"{node_id} should be active"

    def test_initial_vitals_are_baseline(self, engine):
        """Initial vitals should be patient's arriving vitals."""
        state = engine.get_state()
        assert state.current_vitals.heart_rate is not None
        assert state.current_vitals.o2_saturation is not None

    def test_initial_time_is_zero(self, engine):
        """Clock starts at 0."""
        assert engine.get_state().current_time_minutes == 0

    def test_case_start_flag_set(self, engine):
        """The system flag 'case_start' is set at init."""
        assert "case_start" in engine.get_state().flags

    def test_available_actions_initialized(self, engine):
        """Available actions come from action_costs keys."""
        state = engine.get_state()
        assert "history_general" in state.available_actions
        assert "order_labs" in state.available_actions
        assert "start_treatment" in state.available_actions

    def test_timers_initialized_for_timed_nodes(self, engine):
        """Nodes with timers that are starts_active should have timers running."""
        state = engine.get_state()
        # node_06 is NOT starts_active, so no timer yet
        # node_08 IS starts_active and HAS a timer
        assert "node_08_wrong_treatment_steroids" in state.timers


class TestDeterminism:
    """Same case + same actions = same outcome."""

    def test_identical_runs_produce_identical_results(self, case):
        """Run the same action sequence twice, verify identical outcomes."""
        actions = [
            "history_general",
            "physical_exam_focused:neuro",
            "order_labs:cbc",
            "history_focused:dietary",
            "order_imaging_xray:extremity",
            "start_treatment:albendazole",
        ]

        engine1 = SatoriEngine(case)
        events1 = []
        for action in actions:
            events1.extend(engine1.execute_action(action))
        state1 = engine1.get_state()

        engine2 = SatoriEngine(case)
        events2 = []
        for action in actions:
            events2.extend(engine2.execute_action(action))
        state2 = engine2.get_state()

        assert len(events1) == len(events2)
        for e1, e2 in zip(events1, events2):
            assert type(e1) == type(e2)
            assert e1.type == e2.type
            assert e1.timestamp_minutes == e2.timestamp_minutes
        assert state1 == state2

    def test_different_actions_produce_different_outcomes(self, case):
        """Wrong path should produce worse outcome than optimal."""
        # Optimal path
        optimal_engine = SatoriEngine(case)
        for action in [
            "history_general",
            "physical_exam_focused:neuro",
            "order_labs:cbc",
            "history_focused:dietary",
            "order_imaging_xray:extremity",
            "start_treatment:albendazole",
        ]:
            optimal_engine.execute_action(action)

        # Wrong path — give steroids instead
        wrong_engine = SatoriEngine(case)
        for action in [
            "history_general",
            "physical_exam_focused:neuro",
            "start_treatment:steroids",
        ]:
            wrong_engine.execute_action(action)

        optimal_state = optimal_engine.get_state()
        wrong_state = wrong_engine.get_state()

        # Wrong path should set the harm flag
        assert "wrong_treatment_steroids" in wrong_state.flags


class TestActionParsing:
    """Action string parsing and validation."""

    def test_simple_action(self, engine):
        """Action without parameter works."""
        events = engine.execute_action("history_general")
        assert len(events) > 0

    def test_parameterized_action(self, engine):
        """Action with parameter works."""
        events = engine.execute_action("physical_exam_focused:neuro")
        assert len(events) > 0

    def test_unknown_action_raises(self, engine):
        """Unknown base action raises InvalidActionError."""
        with pytest.raises(InvalidActionError):
            engine.execute_action("unknown_action")

    def test_action_after_case_ended_raises(self, case):
        """Cannot act after case ends."""
        # This will depend on case resolution logic
        ...


class TestTimeAndTimers:
    """Time advancement and timer mechanics."""

    def test_time_advances_by_action_cost(self, engine):
        """history_general costs 15 action_minutes."""
        engine.execute_action("history_general")
        assert engine.get_state().current_time_minutes == 15

    def test_cumulative_time(self, engine):
        """Multiple actions accumulate time."""
        engine.execute_action("history_general")       # +15 = 15
        engine.execute_action("history_focused:dietary") # +10 = 25
        assert engine.get_state().current_time_minutes == 25

    def test_timer_deterioration(self, engine):
        """Burning time should advance timers on active timed nodes."""
        # Execute enough actions to see progression
        # node_06 has a 180-minute timer — need to burn enough time
        ...


class TestReveals:
    """Node reveal mechanics including delays."""

    def test_immediate_reveal(self, engine):
        """history_general reveals node_01 immediately."""
        events = engine.execute_action("history_general")
        state = engine.get_state()
        assert "node_01_chief_complaint" in state.revealed_nodes

    def test_delayed_reveal(self, engine):
        """order_labs:cbc should start a pending reveal, not reveal immediately."""
        events = engine.execute_action("order_labs:cbc")
        state = engine.get_state()
        # Should be pending, not revealed yet
        assert "node_04_lab_eosinophilia" not in state.revealed_nodes
        # Should emit PendingRevealStartedEvent
        pending_events = [e for e in events if isinstance(e, PendingRevealStartedEvent)]
        assert len(pending_events) > 0

    def test_delayed_reveal_completes(self, engine):
        """After enough time passes, pending reveal resolves."""
        engine.execute_action("order_labs:cbc")  # starts 45-min delay
        # Burn enough time for the results to arrive
        # Each history_general is 15 min, need 3 to reach 45
        engine.execute_action("history_general")  # +15 = 17 total
        engine.execute_action("history_general")  # +15 = 32
        engine.execute_action("history_general")  # +15 = 47
        state = engine.get_state()
        assert "node_04_lab_eosinophilia" in state.revealed_nodes

    def test_subcategory_matching(self, engine):
        """history_focused:dietary reveals node_05, not other history nodes."""
        engine.execute_action("history_focused:dietary")
        state = engine.get_state()
        assert "node_05_dietary_history" in state.revealed_nodes


class TestInterventions:
    """Treatment action mechanics."""

    def test_wrong_treatment_sets_flag(self, engine):
        """start_treatment:steroids should trigger on_intervene and set harm flag."""
        engine.execute_action("start_treatment:steroids")
        state = engine.get_state()
        assert "wrong_treatment_steroids" in state.flags


class TestVitals:
    """Vitals computation."""

    def test_vitals_reflect_baseline(self, engine):
        """Initial vitals come from patient.arriving_vitals."""
        vitals = engine.get_state().current_vitals
        assert vitals is not None

    def test_vitals_worsen_with_progression(self, engine):
        """As timer stages progress, vitals should worsen."""
        # This requires burning enough time for node_06 stages
        ...


class TestEndConditions:
    """Case resolution mechanics."""

    def test_correct_treatment_ends_case(self, case):
        """Starting correct treatment with right preconditions ends case."""
        engine = SatoriEngine(case)
        # Run near-optimal path
        for action in [
            "history_general",
            "physical_exam_focused:neuro",
            "order_labs:cbc",
            "history_focused:dietary",
            "order_imaging_xray:extremity",
            "start_treatment:albendazole",
        ]:
            engine.execute_action(action)

        state = engine.get_state()
        assert "correct_treatment_started" in state.flags

    def test_time_limit_ends_case(self, case):
        """Case ends at 360 minutes."""
        engine = SatoriEngine(case)
        # Burn time with cheap actions
        for _ in range(25):  # 25 * 15 = 375 min
            if engine.get_state().case_ended:
                break
            engine.execute_action("history_general")
        assert engine.get_state().case_ended


class TestPatientCondition:
    """Computed patient condition utility."""

    def test_initial_condition_is_stable(self, engine, case):
        """At start, patient should be stable or compensating."""
        condition = compute_patient_condition(engine.get_state(), case)
        assert condition in (PatientCondition.STABLE, PatientCondition.COMPENSATING)


class TestEventTypes:
    """Events are properly typed."""

    def test_events_are_typed_subclasses(self, engine):
        """Events should be specific subclasses, not generic Event."""
        events = engine.execute_action("history_general")
        for event in events:
            assert not type(event) == Event, "Should be a typed subclass"
            assert isinstance(event, Event)

    def test_time_event_has_fields(self, engine):
        """TimeAdvancedEvent has old_time and new_time."""
        events = engine.execute_action("history_general")
        time_events = [e for e in events if isinstance(e, TimeAdvancedEvent)]
        assert len(time_events) == 1
        assert time_events[0].old_time == 0
        assert time_events[0].new_time == 15

    def test_reveal_event_has_content(self, engine):
        """NodeRevealedEvent carries the node's narrative text."""
        events = engine.execute_action("history_general")
        reveal_events = [e for e in events if isinstance(e, NodeRevealedEvent)]
        if reveal_events:
            assert reveal_events[0].content_text  # non-empty string
```

---

## INVARIANTS TO PRESERVE

1. **Determinism**: Given same case and same action sequence, engine produces identical events and final state
2. **Immutability**: GameState is frozen — all updates create new instances via `dataclasses.replace()`
3. **Event causality**: Events emitted in causal order: time → timers → pending reveals → auto-reveals → action reveals → interventions → activations → vitals → end
4. **No hidden state**: All state visible in GameState — no private variables affecting outcomes
5. **Pure computation**: No randomness, no I/O, no LLM calls in any engine module
6. **Vitals algorithm**: "Worst wins" — most dangerous value from baseline + active nodes + timer stage vitals
7. **OR-of-ANDs**: Activation satisfied if ANY path satisfied, path satisfied if ALL conditions true
8. **Null safety**: All optional fields in the Pydantic models (`effects: NodeEffects | None`, `paths: list | None`, etc.) are null-checked before access
9. **All nine effects**: Every `EffectType` in the schema has a handler in `EffectExecutor`
10. **Comparator respect**: `Condition.comparator` is used for `TIME_ELAPSED` and `VITAL_THRESHOLD` evaluations — never hardcoded to `>=`

---

## FIELD REFERENCE (from frozen Pydantic models)

These are the exact field names the engine must use. Do NOT invent field names.

| Model | Field | Type | Notes |
|---|---|---|---|
| `TimeCost` | `action_minutes` | `int` | NOT `.minutes` — this is the time cost |
| `TimeCost` | `result_delay_minutes` | `int \| None` | Delay before results arrive |
| `RevealRule` | `action` | `str \| None` | Base action type that reveals |
| `RevealRule` | `subcategory` | `str \| None` | Parameter that must match |
| `RevealRule` | `auto_reveal` | `bool` | If True, reveals when active without action |
| `RevealRule` | `delay_minutes` | `int \| None` | Override delay for this specific node |
| `RevealRule` | `conditions` | `list[Condition] \| None` | Additional conditions |
| `ActivationRule` | `paths` | `list[ConditionPath] \| None` | Can be None when starts_active=True |
| `ActivationRule` | `starts_active` | `bool` | Default False |
| `ActivationRule` | `on_activate` | `list[Effect] \| None` | Effects on activation |
| `Node` | `effects` | `NodeEffects \| None` | Can be None — null-check required |
| `NodeEffects` | `on_reveal` | `list[Effect] \| None` | |
| `NodeEffects` | `on_expire` | `list[Effect] \| None` | |
| `NodeEffects` | `on_intervene` | `InterventionEffect \| None` | |
| `InterventionEffect` | `treatment` | `str` | Matched against action parameter |
| `InterventionEffect` | `effects` | `list[Effect]` | |
| `NodeTimer` | `duration_minutes` | `int` | Total countdown duration |
| `NodeTimer` | `pause_conditions` | `list[Condition] \| None` | |
| `NodeTimer` | `stages` | `list[TimerStage] \| None` | |
| `NodeTimer` | `on_expire` | `list[Effect]` | Required, min_length=1 |
| `TimerStage` | `at_minutes` | `int` | Minutes elapsed since activation |
| `TimerStage` | `effects` | `list[Effect]` | |
| `TimerStage` | `vital_signs` | `VitalSigns \| None` | |
| `Condition` | `comparator` | `Comparator \| None` | Use for TIME_ELAPSED, VITAL_THRESHOLD |
| `Effect` | `value` | `Any \| None` | Used by MODIFY_TIMER, OVERRIDE_VITALS |
| `EndCondition` | `type` | `EndConditionType` | |
| `EndCondition` | `target` | `str \| None` | |
| `EndCondition` | `value` | `Any \| None` | |
| `OutcomeTier` | `required_flags` | `list[str] \| None` | |
| `OutcomeTier` | `excluded_flags` | `list[str] \| None` | |
| `OutcomeTier` | `time_constraints` | `list[TimeConstraint] \| None` | |

---

## ACCEPTANCE CHECKS (MANDATORY)

All of these must pass before the task is complete.

### Initialization
1. Load Maria Santos case from JSON → initialize engine → verify 12 nodes in node map
2. Verify nodes with `starts_active=True` are in `active_nodes` at init
3. Verify `case_start` flag is set at init
4. Verify `available_actions` initialized from `action_costs` keys
5. Verify timers initialized for active nodes that have timers

### Action Execution
6. Execute `history_general` → verify time advances by 15 minutes
7. Execute `history_focused:dietary` → verify `node_05_dietary_history` revealed
8. Execute `physical_exam_focused:neuro` → verify `node_02_neuro_exam` revealed
9. Execute unknown action → verify `InvalidActionError` raised

### Delayed Reveals
10. Execute `order_labs:cbc` → verify `node_04_lab_eosinophilia` is NOT in `revealed_nodes`
11. Execute `order_labs:cbc` → verify node IS in `pending_reveals`
12. After 45+ minutes of actions → verify `node_04_lab_eosinophilia` IS revealed

### Determinism
13. Execute optimal path twice → verify identical events and final state
14. Execute different paths → verify different outcomes
15. Execute same path → verify `state1 == state2`

### Timers & Deterioration
16. Burn enough time → verify `node_06_headache_progression` timer advances
17. Verify timer stage events emitted as stages are crossed
18. Verify vitals worsen as timer stages progress

### Interventions
19. Execute `start_treatment:steroids` → verify `wrong_treatment_steroids` flag set
20. Verify steroids modify node_06 timer (accelerate by -60 minutes)

### End Conditions
21. Execute optimal path → verify case ends with appropriate outcome
22. Burn 360+ minutes → verify case ends (time_elapsed end condition)
23. Verify outcome tier evaluation: optimal requires `diagnosis_confirmed`, `correct_treatment_started`, `family_engaged` flags AND treatment before 120 minutes

### Structural
24. Verify no LLM calls or imports anywhere in engine code
25. Verify `GameState` is truly immutable (frozen dataclass)
26. Verify all events are typed subclasses of `Event`
27. Verify all events have timestamps and causal ordering
28. Verify vitals computation uses worst-wins across baseline + active nodes + timer stage vitals

---

## LINE COUNT EXPECTATION

~800–1100 lines total across engine modules:

| File | Est. Lines | Notes |
|---|---|---|
| `events.py` | ~90 | Typed event subclasses |
| `game_state.py` | ~50 | Frozen dataclass |
| `action_parser.py` | ~15 | Simple split |
| `condition_evaluator.py` | ~120 | OR-of-ANDs + comparator logic |
| `vitals_computer.py` | ~120 | Worst-wins with timer stage awareness |
| `timer_manager.py` | ~180 | Timers + pending reveals + stages |
| `effect_executor.py` | ~180 | All 9 effect types |
| `patient_condition.py` | ~60 | Computed property util |
| `engine.py` | ~250 | Orchestrator + public API |

Test file: ~350 lines (comprehensive tests as specified above)

---

## QUALITY

- All code type-checked with mypy (strict mode)
- All code linted with ruff
- Comprehensive docstrings on all classes and public methods
- Unit tests achieve >90% coverage of engine modules
- Integration test proves determinism with real Maria Santos case
- No `# type: ignore` unless absolutely necessary with justification comment

---

## COMMIT

```
feat(satori): deterministic engine core

- Typed event hierarchy (13 event types as frozen dataclasses)
- Immutable GameState with frozen dataclass
- Action parser for base_action:parameter convention
- ConditionEvaluator with OR-of-ANDs logic and Comparator support
- TimerManager with stage transitions, pause conditions, pending reveals
- VitalsComputer with worst-wins across baseline + nodes + timer stages
- EffectExecutor handling all 9 EffectType values
- Patient condition computed property for downstream consumers
- SatoriEngine orchestrating all components with clear public API
- Load-time case validation beyond Pydantic schema checks
- Full determinism test harness with Maria Santos case

Proves: same case + same actions = same outcome
```
