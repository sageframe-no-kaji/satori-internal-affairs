"""Event types emitted by the Satori engine.

Every state change produces a typed event. These events form the contract
between the engine and downstream consumers (narration layer, frontend).
"""

from dataclasses import dataclass, field
from enum import StrEnum


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

    type: EventType = field(init=False, default=EventType.TIME_ADVANCED)
    old_time: int
    new_time: int
    cause: str  # the action that caused time to advance



@dataclass(frozen=True)
class NodeActivatedEvent(Event):
    """A node became active in the simulation."""

    type: EventType = field(init=False, default=EventType.NODE_ACTIVATED)
    node_id: str
    node_type: str  # NodeType value


@dataclass(frozen=True)
class NodeRevealedEvent(Event):
    """A node's content became visible to the player."""

    type: EventType = field(init=False, default=EventType.NODE_REVEALED)
    node_id: str
    node_type: str
    content_text: str  # NodeContent.narrative_text
    structured_data: dict | None  # NodeContent.structured_data


@dataclass(frozen=True)
class NodeExpiredEvent(Event):
    """A node's timer reached zero."""

    type: EventType = field(init=False, default=EventType.NODE_EXPIRED)
    node_id: str


@dataclass(frozen=True)
class TimerStageEvent(Event):
    """A timer crossed a stage boundary."""

    type: EventType = field(init=False, default=EventType.TIMER_STAGE)
    node_id: str
    stage_index: int
    stage_at_minutes: int
    vital_signs_changed: bool  # whether this stage carries new vitals


@dataclass(frozen=True)
class FlagSetEvent(Event):
    """A flag was set."""

    type: EventType = field(init=False, default=EventType.FLAG_SET)
    flag: str


@dataclass(frozen=True)
class FlagClearedEvent(Event):
    """A flag was cleared."""

    type: EventType = field(init=False, default=EventType.FLAG_CLEARED)
    flag: str


@dataclass(frozen=True)
class VitalsChangedEvent(Event):
    """Patient vitals changed."""

    type: EventType = field(init=False, default=EventType.VITALS_CHANGED)
    old_vitals: dict  # serialized VitalSigns
    new_vitals: dict


@dataclass(frozen=True)
class ActionUnlockedEvent(Event):
    """An action became available."""

    type: EventType = field(init=False, default=EventType.ACTION_UNLOCKED)
    action: str


@dataclass(frozen=True)
class ActionLockedEvent(Event):
    """An action became unavailable."""

    type: EventType = field(init=False, default=EventType.ACTION_LOCKED)
    action: str


@dataclass(frozen=True)
class PendingRevealStartedEvent(Event):
    """A delayed result was ordered (e.g., labs sent)."""

    type: EventType = field(init=False, default=EventType.PENDING_REVEAL_STARTED)
    node_id: str
    delay_minutes: int


@dataclass(frozen=True)
class CaseEndedEvent(Event):
    """The case resolved."""

    type: EventType = field(init=False, default=EventType.CASE_ENDED)
    outcome_tier: str  # OutcomeTierLevel value
    end_reason: str  # description of what triggered the end
