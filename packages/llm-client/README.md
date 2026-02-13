# LLM Client

**Provider-agnostic LLM abstraction layer.**

The LLM Client provides a unified interface for interacting with LLM providers (OpenAI, Anthropic, local models). It handles authentication, request formatting, response parsing, and error handling across different provider APIs. This layer does NOT contain domain logic, generate cases, or manage game state — it is purely the provider line boundary that isolates the rest of the system from LLM-specific implementation details.
