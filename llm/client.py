"""LLM client using OpenAI SDK for Saqal."""

import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from .config import LLMConfig


@dataclass
class LLMResponse:
    """Response from an LLM completion."""

    text: str
    tokens_used: int
    latency_ms: int
    model: str


class LLMClient:
    """LLM client using OpenAI SDK with support for OpenRouter and OpenAI."""

    def __init__(
        self,
        provider: str,
        api_key: str,
        default_model: str,
        default_temperature: float = 0.7,
        base_url: Optional[str] = None,
    ):
        """Initialize LLM client with provider configuration."""
        self.provider = provider
        self.api_key = api_key
        self.default_model = default_model
        self.default_temperature = default_temperature

        # Set base URL based on provider
        if provider == "openrouter":
            self.base_url = base_url or "https://openrouter.ai/api/v1"
        else:
            self.base_url = base_url  # None for OpenAI default

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        """Create client from config object."""
        return cls(
            provider=config.provider,
            api_key=config.api_key,
            default_model=config.default_model,
            default_temperature=config.default_temperature,
            base_url=config.base_url,
        )

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Execute a completion request.

        Returns LLMResponse with text, tokens, latency.
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            return LLMResponse(
                text=text,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                model=model,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            raise LLMError(f"LLM completion failed: {str(e)}", latency_ms=latency_ms) from e


class LLMError(Exception):
    """Exception raised for LLM errors."""

    def __init__(self, message: str, latency_ms: int = 0):
        super().__init__(message)
        self.latency_ms = latency_ms
