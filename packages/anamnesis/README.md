# Anamnesis

**LLM-powered medical case generation pipeline.**

Anamnesis orchestrates the structured generation of medical mystery cases using LLM prompts. It invokes the LLM client, validates outputs against JSON schemas, and produces frozen case artifacts for Satori to consume. Anamnesis does NOT manage game state, handle player interactions, or expose APIs — it is purely the case creation layer that runs offline or on-demand.
