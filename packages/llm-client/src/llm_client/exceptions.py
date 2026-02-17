"""Exceptions for the LLM client package."""


class LLMClientError(Exception):
    """Base exception for llm-client."""


class LLMProviderError(LLMClientError):
    """API call to the provider failed (network, auth, rate limit)."""


class LLMResponseError(LLMClientError):
    """Provider returned a response that could not be parsed as JSON."""


class LLMTimeoutError(LLMClientError):
    """Provider did not respond within the timeout."""
