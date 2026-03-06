"""
LLM client abstraction for mutation generation.

Supports Ollama (default), OpenAI, Anthropic, and Google (Gemini).
API keys must be provided via environment variables only (e.g. api_key: "${OPENAI_API_KEY}").
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flakestorm.core.config import ModelConfig

logger = logging.getLogger(__name__)

# Env var reference pattern for resolving api_key
_ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_api_key(api_key: str | None) -> str | None:
    """Expand ${VAR} to value from environment. Never log the result."""
    if not api_key or not api_key.strip():
        return None
    m = _ENV_REF_PATTERN.match(api_key.strip())
    if not m:
        return None
    return os.environ.get(m.group(1))


class BaseLLMClient(ABC):
    """Abstract base for LLM clients used by the mutation engine."""

    @abstractmethod
    async def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> str:
        """Generate text from the model. Returns the generated text only."""
        ...

    @abstractmethod
    async def verify_connection(self) -> bool:
        """Check that the model is reachable and available."""
        ...


class OllamaLLMClient(BaseLLMClient):
    """Ollama local model client."""

    def __init__(self, name: str, base_url: str = "http://localhost:11434", temperature: float = 0.8):
        self._name = name
        self._base_url = base_url or "http://localhost:11434"
        self._temperature = temperature
        self._client = None

    def _get_client(self):
        from ollama import AsyncClient
        return AsyncClient(host=self._base_url)

    async def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> str:
        client = self._get_client()
        response = await client.generate(
            model=self._name,
            prompt=prompt,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )
        return (response.get("response") or "").strip()

    async def verify_connection(self) -> bool:
        try:
            client = self._get_client()
            response = await client.list()
            models = [m.get("name", "") for m in response.get("models", [])]
            model_available = any(
                self._name in m or m.startswith(self._name.split(":")[0])
                for m in models
            )
            if not model_available:
                logger.warning("Model %s not found. Available: %s", self._name, models)
                return False
            return True
        except Exception as e:
            logger.error("Failed to connect to Ollama: %s", e)
            return False


class OpenAILLMClient(BaseLLMClient):
    """OpenAI API client. Requires optional dependency: pip install flakestorm[openai]."""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.8,
    ):
        self._name = name
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature

    async def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI provider requires the openai package. "
                "Install with: pip install flakestorm[openai]"
            ) from e
        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        resp = await client.chat.completions.create(
            model=self._name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content if resp.choices else ""
        return (content or "").strip()

    async def verify_connection(self) -> bool:
        try:
            await self.generate("Hi", max_tokens=2)
            return True
        except Exception as e:
            logger.error("OpenAI connection check failed: %s", e)
            return False


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic API client. Requires optional dependency: pip install flakestorm[anthropic]."""

    def __init__(self, name: str, api_key: str, temperature: float = 0.8):
        self._name = name
        self._api_key = api_key
        self._temperature = temperature

    async def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> str:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError(
                "Anthropic provider requires the anthropic package. "
                "Install with: pip install flakestorm[anthropic]"
            ) from e
        client = AsyncAnthropic(api_key=self._api_key)
        resp = await client.messages.create(
            model=self._name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text if resp.content else ""
        return text.strip()

    async def verify_connection(self) -> bool:
        try:
            await self.generate("Hi", max_tokens=2)
            return True
        except Exception as e:
            logger.error("Anthropic connection check failed: %s", e)
            return False


class GoogleLLMClient(BaseLLMClient):
    """Google (Gemini) API client. Requires optional dependency: pip install flakestorm[google]."""

    def __init__(self, name: str, api_key: str, temperature: float = 0.8):
        self._name = name
        self._api_key = api_key
        self._temperature = temperature

    def _generate_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig
        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._name)
        config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        resp = model.generate_content(prompt, generation_config=config)
        return (resp.text or "").strip()

    async def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> str:
        try:
            import google.generativeai as genai  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Google provider requires the google-generativeai package. "
                "Install with: pip install flakestorm[google]"
            ) from e
        return await asyncio.to_thread(
            self._generate_sync, prompt, temperature, max_tokens
        )

    async def verify_connection(self) -> bool:
        try:
            await self.generate("Hi", max_tokens=2)
            return True
        except Exception as e:
            logger.error("Google (Gemini) connection check failed: %s", e)
            return False


def get_llm_client(config: ModelConfig) -> BaseLLMClient:
    """
    Factory for LLM clients based on model config.
    Resolves api_key from environment when given as ${VAR}.
    """
    provider = (config.provider.value if hasattr(config.provider, "value") else config.provider) or "ollama"
    name = config.name
    temperature = config.temperature
    base_url = config.base_url if config.base_url else None

    if provider == "ollama":
        return OllamaLLMClient(
            name=name,
            base_url=base_url or "http://localhost:11434",
            temperature=temperature,
        )

    api_key = _resolve_api_key(config.api_key)
    if provider in ("openai", "anthropic", "google") and not api_key and config.api_key:
        # Config had api_key but it didn't resolve (env var not set)
        var_name = _ENV_REF_PATTERN.match(config.api_key.strip())
        if var_name:
            raise ValueError(
                f"API key environment variable {var_name.group(0)} is not set. "
                f"Set it in your environment or in a .env file."
            )

    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI provider requires api_key (e.g. api_key: \"${OPENAI_API_KEY}\").")
        return OpenAILLMClient(
            name=name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
    if provider == "anthropic":
        if not api_key:
            raise ValueError("Anthropic provider requires api_key (e.g. api_key: \"${ANTHROPIC_API_KEY}\").")
        return AnthropicLLMClient(name=name, api_key=api_key, temperature=temperature)
    if provider == "google":
        if not api_key:
            raise ValueError("Google provider requires api_key (e.g. api_key: \"${GOOGLE_API_KEY}\").")
        return GoogleLLMClient(name=name, api_key=api_key, temperature=temperature)

    raise ValueError(f"Unsupported LLM provider: {provider}")
