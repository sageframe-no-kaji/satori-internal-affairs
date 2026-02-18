"""Anamnesis — LLM-powered medical case generation pipeline.

Public API:
    CaseGenerationPipeline  — orchestrates seed → LLM → validate → save
    GenerationResult        — result type returned by the pipeline
    CreativeSeed            — extended seed with narrative direction (Mode 2)
    load_seed_file()        — load a YAML seed file into a CreativeSeed
    validate_case_dict()    — validate a raw dict against CaseDefinition

Re-exported from llm-client for convenience:
    CaseSeed, ModelConfig, Provider
"""

# Convenience re-exports from llm-client
from llm_client import CaseSeed, ModelConfig, Provider

from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.result import GenerationResult
from anamnesis.seed import CreativeSeed, load_seed_file
from anamnesis.validator import validate_case_dict

__version__ = "0.1.0"

__all__ = [
    # Pipeline
    "CaseGenerationPipeline",
    "GenerationResult",
    # Seeds
    "CreativeSeed",
    "load_seed_file",
    # Validation
    "validate_case_dict",
    # llm-client re-exports
    "CaseSeed",
    "ModelConfig",
    "Provider",
]
