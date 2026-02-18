"""Shared pytest fixtures for anamnesis tests."""

import json
from pathlib import Path

import pytest

from anamnesis.seed import CreativeSeed


@pytest.fixture
def minimal_seed() -> CreativeSeed:
    """A minimal Mode 1 CreativeSeed with only required fields."""
    return CreativeSeed(
        diagnosis="pneumothorax",
        difficulty="beginner",
        dramatic_tone="clinical",
    )


@pytest.fixture
def rich_seed() -> CreativeSeed:
    """A full Mode 2 CreativeSeed with all fields populated."""
    return CreativeSeed(
        diagnosis="neurocysticercosis",
        difficulty="intermediate",
        dramatic_tone="medical_mystery",
        patient_age_range=(25, 35),
        patient_sex="female",
        setting="Emergency Department",
        complications=["language barrier", "dietary history withheld"],
        learning_objectives=["Recognize focal seizure", "Consider parasitic causes"],
        content_boundaries=["Age-appropriate for 14+"],
        dramatic_hook="Young woman collapses mid-sentence at a family dinner.",
        red_herrings=["Recent job stress", "Family history of seizures"],
        character_notes="Maria is proud and independent. Carlos is overprotective.",
        narrative_inspiration="House S1E09 tone — family dynamics complicate diagnosis.",
        key_twists=["Steroids alone worsen neurocysticercosis"],
        emotional_core="A young couple navigating a foreign medical system.",
        forbidden_tropes=["No immigration status as plot point"],
    )


@pytest.fixture
def example_case_path() -> Path:
    """Path to the canonical example neurocysticercosis case JSON."""
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / "cases" / "example-neurocysticercosis.json"


@pytest.fixture
def example_case_dict(example_case_path: Path) -> dict:  # type: ignore[type-arg]
    """The example case as a raw dict (as returned by the LLM mock)."""
    with example_case_path.open() as f:
        return json.load(f)
