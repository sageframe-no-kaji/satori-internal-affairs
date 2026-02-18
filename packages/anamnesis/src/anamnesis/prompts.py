"""Prompt construction for creative enrichment and repair attempts.

build_creative_prompt() — constructs a rich user prompt from a CreativeSeed
build_repair_prompt()   — constructs an error-feedback prompt for repair retries

Phase 1 note: Creative fields that don't map to CaseSeed (dramatic_hook, etc.)
are embedded here as prompt text. For mock mode, these prompts are never sent
to an LLM. For real providers, the pipeline uses CaseSeed fields directly via
the llm-client interface; creative-only fields are logged but not yet injected
into the provider's system prompt (that requires a future llm-client extension).
"""

import json
from typing import Any

from anamnesis.seed import CreativeSeed


def build_creative_prompt(seed: CreativeSeed) -> str:
    """Build an enriched user prompt from all CreativeSeed fields.

    The returned text is structured in three sections:
    1. Medical requirements — diagnosis, difficulty, setting, etc.
    2. Creative direction — dramatic hook, character notes, etc. (Mode 2 fields)
    3. Structural constraints reminder

    Args:
        seed: The CreativeSeed with all available fields.

    Returns:
        A formatted prompt string containing all available creative context.
    """
    sections: list[str] = []

    # ── Section 1: Medical Requirements ─────────────────────────────────────
    medical_lines = [
        f"Diagnosis: {seed.diagnosis}",
        f"Difficulty: {seed.difficulty}",
        f"Dramatic tone: {seed.dramatic_tone}",
    ]
    if seed.setting:
        medical_lines.append(f"Setting: {seed.setting}")
    if seed.patient_sex:
        medical_lines.append(f"Patient sex: {seed.patient_sex}")
    if seed.patient_age_range:
        medical_lines.append(
            f"Patient age range: {seed.patient_age_range[0]}–{seed.patient_age_range[1]} years"
        )
    if seed.complications:
        comps = "\n".join(f"  - {c}" for c in seed.complications)
        medical_lines.append(f"Complications to include:\n{comps}")
    if seed.learning_objectives:
        objs = "\n".join(f"  - {o}" for o in seed.learning_objectives)
        medical_lines.append(f"Learning objectives:\n{objs}")
    if seed.content_boundaries:
        bounds = "\n".join(f"  - {b}" for b in seed.content_boundaries)
        medical_lines.append(f"Content boundaries:\n{bounds}")

    sections.append("## Medical Requirements\n\n" + "\n".join(medical_lines))

    # ── Section 2: Creative Direction (Mode 2 fields) ────────────────────────
    creative_lines: list[str] = []

    if seed.dramatic_hook:
        creative_lines.append(f"**Opening / dramatic hook:**\n{seed.dramatic_hook.strip()}")

    if seed.character_notes:
        creative_lines.append(f"**Patient & character notes:**\n{seed.character_notes.strip()}")

    if seed.narrative_inspiration:
        creative_lines.append(
            f"**Narrative inspiration (tone/structure reference):**\n"
            f"{seed.narrative_inspiration.strip()}"
        )

    if seed.emotional_core:
        creative_lines.append(
            f"**Emotional core (the human story):**\n{seed.emotional_core.strip()}"
        )

    if seed.red_herrings:
        herrings = "\n".join(f"  - {r}" for r in seed.red_herrings)
        creative_lines.append(f"**Red herrings to embed:**\n{herrings}")

    if seed.key_twists:
        twists = "\n".join(f"  - {t}" for t in seed.key_twists)
        creative_lines.append(f"**Key dramatic twists:**\n{twists}")

    if seed.forbidden_tropes:
        tropes = "\n".join(f"  - {t}" for t in seed.forbidden_tropes)
        creative_lines.append(f"**Forbidden tropes (do NOT include):**\n{tropes}")

    if creative_lines:
        sections.append("## Creative Direction\n\n" + "\n\n".join(creative_lines))

    # ── Section 3: Structural Constraints ────────────────────────────────────
    sections.append(
        "## Structural Constraints\n\n"
        "- All node IDs must be unique strings within this case.\n"
        "- Timer stages must be sorted ascending by at_minutes.\n"
        "- All reveal.action references must exist in action_costs.\n"
        "- Response must be valid JSON conforming exactly to the case definition schema."
    )

    return "\n\n".join(sections)


def build_repair_prompt(raw_dict: dict[str, Any], validation_errors: list[str]) -> str:
    """Build an error-feedback prompt for a repair retry attempt.

    Includes the previous (invalid) output and the specific validation
    errors so the LLM can make targeted fixes.

    Args:
        raw_dict: The previous LLM output that failed validation.
        validation_errors: List of error messages from validate_case_dict().

    Returns:
        A formatted prompt asking the LLM to fix the specific errors.
    """
    error_block = "\n".join(f"  {i + 1}. {e}" for i, e in enumerate(validation_errors))

    try:
        prev_json = json.dumps(raw_dict, indent=2, default=str)
    except (TypeError, ValueError):
        prev_json = str(raw_dict)

    return (
        "Your previous response was not a valid case definition. "
        "Please fix ALL of the following errors and return corrected JSON:\n\n"
        f"## Validation Errors\n\n{error_block}\n\n"
        "## Your Previous (Invalid) Output\n\n"
        f"```json\n{prev_json}\n```\n\n"
        "Return ONLY the corrected JSON. Do not include any explanation or markdown "
        "outside the JSON object. Fix every error listed above."
    )
