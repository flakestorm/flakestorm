"""
Mutation Engine

Core engine for generating adversarial mutations using configurable LLM backends.
Supports Ollama (local), OpenAI, Anthropic, and Google (Gemini).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from flakestorm.mutations.llm_client import BaseLLMClient, get_llm_client
from flakestorm.mutations.templates import MutationTemplates
from flakestorm.mutations.types import Mutation, MutationType

if TYPE_CHECKING:
    from flakestorm.core.config import ModelConfig

logger = logging.getLogger(__name__)


class MutationEngine:
    """
    Engine for generating adversarial mutations using configurable LLM backends.

    Uses the configured provider (Ollama, OpenAI, Anthropic, Google) to rewrite
    prompts according to different mutation strategies.

    Example:
        >>> engine = MutationEngine(config.model)
        >>> mutations = await engine.generate_mutations(
        ...     "Book a flight to Paris",
        ...     [MutationType.PARAPHRASE, MutationType.NOISE],
        ...     count=10
        ... )
    """

    def __init__(
        self,
        config: ModelConfig,
        templates: MutationTemplates | None = None,
    ):
        """
        Initialize the mutation engine.

        Args:
            config: Model configuration (provider, name, api_key via env only for non-Ollama)
            templates: Optional custom templates
        """
        self.config = config
        self.model = config.name
        self.temperature = config.temperature
        self.templates = templates or MutationTemplates()
        self._client: BaseLLMClient = get_llm_client(config)

    async def verify_connection(self) -> bool:
        """
        Verify connection to the configured LLM provider and model availability.

        Returns:
            True if connection is successful and model is available
        """
        return await self._client.verify_connection()

    async def generate_mutations(
        self,
        seed_prompt: str,
        types: list[MutationType],
        count: int = 10,
    ) -> list[Mutation]:
        """
        Generate adversarial mutations for a seed prompt.

        Args:
            seed_prompt: The original "golden" prompt
            types: Types of mutations to generate
            count: Total number of mutations to generate

        Returns:
            List of Mutation objects
        """
        mutations: list[Mutation] = []

        # Distribute count across mutation types
        per_type = max(1, count // len(types))
        remainder = count - (per_type * len(types))

        # Generate mutations for each type
        tasks = []
        for i, mutation_type in enumerate(types):
            type_count = per_type + (1 if i < remainder else 0)
            for _ in range(type_count):
                tasks.append(self._generate_single_mutation(seed_prompt, mutation_type))

        # Run all generations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter valid mutations
        for result in results:
            if isinstance(result, Mutation) and result.is_valid():
                mutations.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Mutation generation failed: {result}")

        return mutations

    async def _generate_single_mutation(
        self,
        seed_prompt: str,
        mutation_type: MutationType,
    ) -> Mutation:
        """
        Generate a single mutation using the LLM.

        Args:
            seed_prompt: The original prompt
            mutation_type: Type of mutation to apply

        Returns:
            A Mutation object
        """
        # Format the prompt template
        formatted_prompt = self.templates.format(mutation_type, seed_prompt)

        try:
            mutated = await self._client.generate(
                formatted_prompt,
                temperature=self.temperature,
                max_tokens=256,
            )

            # Clean up the response
            mutated = self._clean_response(mutated, seed_prompt)

            return Mutation(
                original=seed_prompt,
                mutated=mutated,
                type=mutation_type,
                weight=mutation_type.default_weight,
                metadata={
                    "model": self.model,
                    "temperature": self.temperature,
                },
            )

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _clean_response(self, response: str, original: str) -> str:
        """
        Clean up the LLM response.

        Removes common artifacts like quotes, prefixes, etc.
        """
        # Remove common prefixes
        prefixes = [
            "Here's the rewritten prompt:",
            "Rewritten:",
            "Modified:",
            "Result:",
            "Output:",
        ]
        for prefix in prefixes:
            if response.lower().startswith(prefix.lower()):
                response = response[len(prefix) :].strip()

        # Remove surrounding quotes
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]

        # If the response is just the original, try to extract differently
        if response.strip() == original.strip():
            # Sometimes the model prefixes with the prompt
            lines = response.split("\n")
            if len(lines) > 1:
                response = lines[-1].strip()

        return response.strip()

    async def generate_batch(
        self,
        prompts: list[str],
        types: list[MutationType],
        count_per_prompt: int = 10,
    ) -> dict[str, list[Mutation]]:
        """
        Generate mutations for multiple prompts in batch.

        Args:
            prompts: List of seed prompts
            types: Types of mutations to generate
            count_per_prompt: Mutations per prompt

        Returns:
            Dictionary mapping prompts to their mutations
        """
        results: dict[str, list[Mutation]] = {}

        tasks = [
            self.generate_mutations(prompt, types, count_per_prompt)
            for prompt in prompts
        ]

        all_mutations = await asyncio.gather(*tasks)

        for prompt, mutations in zip(prompts, all_mutations, strict=False):
            results[prompt] = mutations

        return results
