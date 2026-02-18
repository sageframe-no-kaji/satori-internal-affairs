# Seed Files for Anamnesis Case Generation

Seed files provide creative direction for LLM-powered case generation.
They are YAML documents consumed by `python -m anamnesis generate --seed-file`.

---

## Two Modes

### Mode 1 — Automated (minimal seed)

Provide just the required fields. The LLM invents all creative content.

```yaml
diagnosis: pneumothorax
difficulty: beginner
dramatic_tone: clinical
```

Run with:
```bash
python -m anamnesis generate --seed-file seeds/example-pneumothorax.yaml
```

Or equivalently with CLI flags (no seed file needed):
```bash
python -m anamnesis generate --diagnosis pneumothorax --difficulty beginner --tone clinical
```

### Mode 2 — Creative seed (rich narrative brief)

Provide additional creative fields to guide the LLM's narrative choices.
Creative fields are **prompt context only** — they never appear in the output JSON.

See `seeds/example-neurocysticercosis-rich.yaml` for a full Mode 2 example.

---

## Required Fields

| Field | Type | Description |
|---|---|---|
| `diagnosis` | string | The medical diagnosis (e.g., `pneumothorax`, `neurocysticercosis`) |
| `difficulty` | string | `beginner` \| `intermediate` \| `advanced` |
| `dramatic_tone` | string | `clinical` \| `medical_mystery` \| `urgent` \| `educational` |

## Optional Medical Fields

| Field | Type | Description |
|---|---|---|
| `setting` | string | Clinical setting (e.g., `Emergency Department`, `ICU`) |
| `patient_sex` | string | `male` \| `female` \| `nonbinary` |
| `patient_age_range` | `[min, max]` | Age range as list of two integers |
| `complications` | list of strings | Medical complications to embed in the case |
| `learning_objectives` | list of strings | What the learner should take away |
| `content_boundaries` | list of strings | Content restrictions (audience, sensitivity) |

## Creative Fields (Mode 2)

These fields guide the LLM's narrative choices. They are **prompt hints only** —
they have no effect on the output JSON schema.

| Field | Type | Description |
|---|---|---|
| `dramatic_hook` | string | Opening scene / first impression for the player |
| `red_herrings` | list of strings | Misleading clues to weave into the case |
| `character_notes` | string | Patient personality, backstory, family dynamics |
| `narrative_inspiration` | string | Free-text reference (e.g., "House S2E13 tone") |
| `key_twists` | list of strings | Dramatic turns you want the case to include |
| `emotional_core` | string | The human story at the heart of the medical mystery |
| `forbidden_tropes` | list of strings | Narrative patterns to explicitly avoid |

---

## Examples

- `example-pneumothorax.yaml` — minimal Mode 1 seed
- `example-neurocysticercosis-rich.yaml` — full Mode 2 creative brief
