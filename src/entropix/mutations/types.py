"""
Mutation Type Definitions

Defines the types of adversarial mutations and the Mutation data structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MutationType(str, Enum):
    """Types of adversarial mutations."""
    
    PARAPHRASE = "paraphrase"
    """Semantically equivalent rewrites that preserve intent."""
    
    NOISE = "noise"
    """Typos, spelling errors, and character-level noise."""
    
    TONE_SHIFT = "tone_shift"
    """Changes in tone: aggressive, impatient, casual, etc."""
    
    PROMPT_INJECTION = "prompt_injection"
    """Adversarial attacks attempting to manipulate the agent."""
    
    @property
    def display_name(self) -> str:
        """Human-readable name for display."""
        return self.value.replace("_", " ").title()
    
    @property
    def description(self) -> str:
        """Description of what this mutation type does."""
        descriptions = {
            MutationType.PARAPHRASE: "Rewrite using different words while preserving meaning",
            MutationType.NOISE: "Add typos and spelling errors",
            MutationType.TONE_SHIFT: "Change tone to aggressive/impatient",
            MutationType.PROMPT_INJECTION: "Add adversarial injection attacks",
        }
        return descriptions.get(self, "Unknown mutation type")
    
    @property
    def default_weight(self) -> float:
        """Default scoring weight for this mutation type."""
        weights = {
            MutationType.PARAPHRASE: 1.0,
            MutationType.NOISE: 0.8,
            MutationType.TONE_SHIFT: 0.9,
            MutationType.PROMPT_INJECTION: 1.5,
        }
        return weights.get(self, 1.0)


@dataclass
class Mutation:
    """
    Represents a single adversarial mutation.
    
    Contains the original prompt, the mutated version,
    metadata about the mutation, and validation info.
    """
    
    original: str
    """The original golden prompt."""
    
    mutated: str
    """The mutated/adversarial version."""
    
    type: MutationType
    """Type of mutation applied."""
    
    weight: float = 1.0
    """Scoring weight for this mutation."""
    
    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when this mutation was created."""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the mutation."""
    
    @property
    def id(self) -> str:
        """Generate a unique ID for this mutation."""
        import hashlib
        content = f"{self.original}:{self.mutated}:{self.type.value}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    @property
    def character_diff(self) -> int:
        """Calculate character-level difference from original."""
        return abs(len(self.mutated) - len(self.original))
    
    @property
    def word_count_diff(self) -> int:
        """Calculate word count difference from original."""
        original_words = len(self.original.split())
        mutated_words = len(self.mutated.split())
        return abs(mutated_words - original_words)
    
    def is_valid(self) -> bool:
        """
        Check if this mutation is valid.
        
        A valid mutation:
        - Has non-empty mutated text
        - Is different from the original
        - Doesn't exceed reasonable length bounds
        """
        if not self.mutated or not self.mutated.strip():
            return False
        
        if self.mutated.strip() == self.original.strip():
            return False
        
        # Mutation shouldn't be more than 3x the original length
        if len(self.mutated) > len(self.original) * 3:
            return False
        
        return True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "original": self.original,
            "mutated": self.mutated,
            "type": self.type.value,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mutation":
        """Create from dictionary."""
        return cls(
            original=data["original"],
            mutated=data["mutated"],
            type=MutationType(data["type"]),
            weight=data.get("weight", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) 
                if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )

