"""Narration prompt templates (P2-H08 plumbing).

STRUCTURE ONLY. The base system prompt below is a functional PLACEHOLDER:
neutral, honest about the boundaries, and deliberately voiceless. The
narrator's actual voice is the practitioner's work — it lands in
docs/architecture/narrator-voice.md, and that document's approved base
system prompt replaces PLACEHOLDER_SYSTEM_PROMPT verbatim once it reads
``status: READY``. Do not tune the placeholder; replace it.

Per-event-type guidance lives in EVENT_GUIDANCE so Phase 3+ voice tuning
has a single documented home. The voice document's event-type treatment
table fills these slots.
"""

from llm_client.interfaces import NarrationContext, NarrationEvent

# --- VOICE PENDING ---------------------------------------------------------
# Replaced verbatim by docs/architecture/narrator-voice.md §9 when READY.
PLACEHOLDER_SYSTEM_PROMPT = """\
You narrate moments in a medical simulation for a teenage player who is
playing the clinician. You are given one event and the current patient
context. Respond with one or two plain, present-tense sentences describing
what just happened.

Hard rules — never break these:
- Text only. Never mention game mechanics, state, timers, or scores.
- Never diagnose, conclude, or hint at anything the player has not
  uncovered. You know only what is in the event you are given.
- Never foreshadow what will happen next.
- Plain language a teenager reads easily; medical terms only when the
  event itself contains them.
"""

# Per-event-type guidance slots. Keys are engine EventType values (see
# satori_api.narrator_bridge._describe_event). Empty string = no extra
# guidance; the voice document decides full-voice / light-touch / silent
# treatment per type.
EVENT_GUIDANCE: dict[str, str] = {
    "node_revealed": "",
    "node_activated": "",
    "node_expired": "",
    "timer_stage": "",
    "vitals_changed": "",
    "waited": "",
    "time_advanced": "",
    "flag_set": "",
    "flag_cleared": "",
    "action_unlocked": "",
    "action_locked": "",
    "pending_reveal_started": "",
    "case_ended": "",
}


def build_system_prompt() -> str:
    """The narrator's system prompt. One assembly point for H08's voice drop."""
    return PLACEHOLDER_SYSTEM_PROMPT


def build_user_prompt(event: NarrationEvent, context: NarrationContext) -> str:
    """Assemble the per-event user prompt from event + context facts.

    Everything the narrator may know is here — nothing else reaches it
    (Truth Line: it cannot leak what it was never given).
    """
    lines = [
        f"Patient: {context.patient_name}, {context.patient_age}, {context.patient_sex}, "
        f"in the {context.setting}.",
        f"Elapsed time: {context.elapsed_minutes} minutes.",
    ]
    if context.current_vitals:
        vitals = ", ".join(f"{k}={v}" for k, v in sorted(context.current_vitals.items()))
        lines.append(f"Current vitals: {vitals}.")
    lines.append(f"Event ({event.event_type}): {event.description}")
    if event.structured_data:
        data = ", ".join(f"{k}={v}" for k, v in sorted(event.structured_data.items()))
        lines.append(f"Event data: {data}")
    guidance = EVENT_GUIDANCE.get(event.event_type, "")
    if guidance:
        lines.append(guidance)
    lines.append("Narrate this moment.")
    return "\n".join(lines)
