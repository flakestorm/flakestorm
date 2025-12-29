"""
flakestorm Integrations Module

Features for integrating with external services:
- HuggingFace model downloading
- Local embeddings for semantic similarity
"""

# Import guards for optional dependencies

__all__ = [
    "HuggingFaceModelProvider",
    "LocalEmbedder",
]


def __getattr__(name: str):
    """Lazy loading of integration modules."""
    if name == "HuggingFaceModelProvider":
        from flakestorm.integrations.huggingface import HuggingFaceModelProvider

        return HuggingFaceModelProvider
    elif name == "LocalEmbedder":
        from flakestorm.assertions.semantic import LocalEmbedder

        return LocalEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
