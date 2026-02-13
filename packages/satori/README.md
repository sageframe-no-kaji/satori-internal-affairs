# Satori

**Deterministic game engine for medical mystery simulation.**

Satori is the core game state engine. It maintains the ground truth of the medical case, validates player actions against the case schema, tracks investigation state, and determines outcomes. Satori does NOT generate cases, interface with LLMs, or render UI — it is purely the mechanical layer that enforces rules and manages state.
