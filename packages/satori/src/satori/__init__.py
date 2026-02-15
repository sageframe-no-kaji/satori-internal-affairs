"""Satori — Deterministic medical case engine."""

__version__ = "0.1.0"

from satori.action_parser import parse_action
from satori.engine import InvalidActionError, SatoriEngine
from satori.events import (
    ActionLockedEvent,
    ActionUnlockedEvent,
    CaseEndedEvent,
    Event,
    EventType,
    FlagClearedEvent,
    FlagSetEvent,
    NodeActivatedEvent,
    NodeExpiredEvent,
    NodeRevealedEvent,
    PendingRevealStartedEvent,
    TimeAdvancedEvent,
    TimerStageEvent,
    VitalsChangedEvent,
)
from satori.game_state import GameState
from satori.patient_condition import PatientCondition, compute_patient_condition

__all__ = [
    # Core engine
    "SatoriEngine",
    "InvalidActionError",
    # State
    "GameState",
    # Events
    "Event",
    "EventType",
    "TimeAdvancedEvent",
    "NodeActivatedEvent",
    "NodeRevealedEvent",
    "NodeExpiredEvent",
    "TimerStageEvent",
    "FlagSetEvent",
    "FlagClearedEvent",
    "VitalsChangedEvent",
    "ActionUnlockedEvent",
    "ActionLockedEvent",
    "PendingRevealStartedEvent",
    "CaseEndedEvent",
    # Utilities
    "PatientCondition",
    "compute_patient_condition",
    "parse_action",
]
