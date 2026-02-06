"""LLM configuration for Saqal."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    provider: str
    api_key: str
    default_model: str
    default_temperature: float = 0.7
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "openrouter")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

        base_url = None
        if provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"

        return cls(
            provider=provider,
            api_key=api_key,
            default_model=default_model,
            default_temperature=default_temperature,
            base_url=base_url,
        )

    def get_model_name(self, model: Optional[str] = None) -> str:
        """Get the full model name for the provider."""
        model = model or self.default_model
        if self.provider == "openrouter" and "/" not in model:
            # OpenRouter requires provider/model format for some models
            return model
        return model
