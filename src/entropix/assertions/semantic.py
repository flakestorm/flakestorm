"""
Semantic Invariant Checkers

Checks that use embeddings to verify semantic similarity
between expected and actual responses.

Requires the 'semantic' extra: pip install entropix[semantic]
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from entropix.assertions.deterministic import BaseChecker, CheckResult

if TYPE_CHECKING:
    from entropix.core.config import InvariantConfig

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """
    Local embedding model using sentence-transformers.
    
    Loads a lightweight model for computing semantic similarity
    between texts without requiring external API calls.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern for efficient model reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_model(self):
        """Lazily load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # Use a small, fast model
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded embedding model: all-MiniLM-L6-v2")
                
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for semantic checks. "
                    "Install with: pip install entropix[semantic]"
                )
        return self._model
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        import numpy as np
        
        model = self._load_model()
        
        # Compute embeddings
        embeddings = model.encode([text1, text2])
        
        # Cosine similarity
        emb1, emb2 = embeddings[0], embeddings[1]
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2)
        )
        
        return float(similarity)


class SimilarityChecker(BaseChecker):
    """
    Check if response is semantically similar to expected text.
    
    Uses local embeddings to compare the agent's response
    with an expected response template.
    
    Example config:
        type: similarity
        expected: "Your flight has been booked successfully"
        threshold: 0.8
    """
    
    def __init__(self, config: "InvariantConfig"):
        """Initialize with optional embedder."""
        super().__init__(config)
        self._embedder = None
    
    @property
    def embedder(self) -> LocalEmbedder:
        """Lazily initialize embedder."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder
    
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """Check semantic similarity to expected response."""
        from entropix.core.config import InvariantType
        
        expected = self.config.expected or ""
        threshold = self.config.threshold or 0.8
        
        if not expected:
            return CheckResult(
                type=InvariantType.SIMILARITY,
                passed=False,
                details="No expected text configured for similarity check",
            )
        
        try:
            similarity = self.embedder.similarity(response, expected)
            passed = similarity >= threshold
            
            if passed:
                details = f"Similarity {similarity:.1%} >= {threshold:.1%} threshold"
            else:
                details = f"Similarity {similarity:.1%} < {threshold:.1%} threshold"
            
            return CheckResult(
                type=InvariantType.SIMILARITY,
                passed=passed,
                details=details,
            )
            
        except ImportError as e:
            return CheckResult(
                type=InvariantType.SIMILARITY,
                passed=False,
                details=str(e),
            )
        except Exception as e:
            logger.error(f"Similarity check failed: {e}")
            return CheckResult(
                type=InvariantType.SIMILARITY,
                passed=False,
                details=f"Error computing similarity: {e}",
            )

