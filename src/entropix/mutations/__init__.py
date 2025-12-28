"""
Entropix Mutation Engine

Generates adversarial mutations from golden prompts using local LLMs.
Supports paraphrasing, noise injection, tone shifting, and prompt injection.
"""

from entropix.mutations.engine import MutationEngine
from entropix.mutations.types import MutationType, Mutation
from entropix.mutations.templates import MutationTemplates, MUTATION_TEMPLATES

__all__ = [
    "MutationEngine",
    "MutationType",
    "Mutation",
    "MutationTemplates",
    "MUTATION_TEMPLATES",
]

