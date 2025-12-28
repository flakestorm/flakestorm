"""
Local Embeddings Integration

Provides local embedding models for semantic similarity checks.
Re-exports the LocalEmbedder from assertions.semantic for convenience.
"""

from __future__ import annotations

# Re-export from semantic module
from entropix.assertions.semantic import LocalEmbedder

__all__ = ["LocalEmbedder"]

