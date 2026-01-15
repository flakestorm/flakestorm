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
    """
    Types of adversarial mutations.

    Includes 22+ mutation types covering:
    - Prompt-level attacks: semantic, noise, tone, injection, encoding, context, length, custom
    - Advanced prompt attacks: multi-turn, advanced jailbreaks, semantic similarity, format poisoning, language mixing, token manipulation, temporal
    - System/Network-level attacks: HTTP headers, payload size, content-type, query params, request methods, protocol-level, resource exhaustion, concurrent patterns, timeout manipulation
    """

    # Original 8 types
    PARAPHRASE = "paraphrase"
    """Semantically equivalent rewrites that preserve intent."""

    NOISE = "noise"
    """Typos, spelling errors, and character-level noise."""

    TONE_SHIFT = "tone_shift"
    """Changes in tone: aggressive, impatient, casual, etc."""

    PROMPT_INJECTION = "prompt_injection"
    """Basic adversarial attacks attempting to manipulate the agent."""

    ENCODING_ATTACKS = "encoding_attacks"
    """Encoded inputs using Base64, Unicode escapes, or URL encoding."""

    CONTEXT_MANIPULATION = "context_manipulation"
    """Adding, removing, or reordering context information."""

    LENGTH_EXTREMES = "length_extremes"
    """Edge case inputs: empty, minimal, or very long versions."""

    CUSTOM = "custom"
    """User-defined mutation templates for domain-specific testing."""

    # Advanced prompt-level attacks (7 new types)
    MULTI_TURN_ATTACK = "multi_turn_attack"
    """Context persistence and conversation state management attacks."""

    ADVANCED_JAILBREAK = "advanced_jailbreak"
    """Sophisticated prompt injection techniques (DAN, role-playing, hypothetical scenarios)."""

    SEMANTIC_SIMILARITY_ATTACK = "semantic_similarity_attack"
    """Adversarial examples - inputs that look similar but have different meanings."""

    FORMAT_POISONING = "format_poisoning"
    """Structured data parsing and format injection attacks (JSON, XML, markdown)."""

    LANGUAGE_MIXING = "language_mixing"
    """Multilingual inputs, code-switching, and character set handling."""

    TOKEN_MANIPULATION = "token_manipulation"  # nosec B105
    """Tokenizer edge cases, special tokens, and token boundary attacks."""

    TEMPORAL_ATTACK = "temporal_attack"
    """Time-sensitive context, outdated references, and temporal confusion."""

    # System/Network-level attacks (8+ new types)
    HTTP_HEADER_INJECTION = "http_header_injection"
    """HTTP header manipulation and header-based injection attacks."""

    PAYLOAD_SIZE_ATTACK = "payload_size_attack"
    """Extremely large payloads, memory exhaustion, and size-based DoS."""

    CONTENT_TYPE_CONFUSION = "content_type_confusion"
    """Content-Type manipulation and MIME type confusion attacks."""

    QUERY_PARAMETER_POISONING = "query_parameter_poisoning"
    """Malicious query parameters, parameter pollution, and GET request attacks."""

    REQUEST_METHOD_ATTACK = "request_method_attack"
    """HTTP method confusion and method-based attacks."""

    PROTOCOL_LEVEL_ATTACK = "protocol_level_attack"
    """HTTP protocol-level attacks, request smuggling, chunked encoding, protocol confusion."""

    RESOURCE_EXHAUSTION = "resource_exhaustion"
    """CPU/memory exhaustion, infinite loops, and resource-based DoS."""

    CONCURRENT_REQUEST_PATTERN = "concurrent_request_pattern"
    """Race conditions, concurrent request handling, and state management under load."""

    TIMEOUT_MANIPULATION = "timeout_manipulation"
    """Timeout handling, slow request attacks, and hanging request patterns."""

    @property
    def display_name(self) -> str:
        """Human-readable name for display."""
        return self.value.replace("_", " ").title()

    @property
    def description(self) -> str:
        """Description of what this mutation type does."""
        descriptions = {
            # Original 8 types
            MutationType.PARAPHRASE: "Rewrite using different words while preserving meaning",
            MutationType.NOISE: "Add typos and spelling errors",
            MutationType.TONE_SHIFT: "Change tone to aggressive/impatient",
            MutationType.PROMPT_INJECTION: "Add basic adversarial injection attacks",
            MutationType.ENCODING_ATTACKS: "Transform using Base64, Unicode, or URL encoding",
            MutationType.CONTEXT_MANIPULATION: "Add, remove, or reorder context information",
            MutationType.LENGTH_EXTREMES: "Create empty, minimal, or very long versions",
            MutationType.CUSTOM: "Apply user-defined mutation templates",
            # Advanced prompt-level attacks
            MutationType.MULTI_TURN_ATTACK: "Create fake conversation history with contradictory or manipulative prior turns",
            MutationType.ADVANCED_JAILBREAK: "Use advanced jailbreak patterns: role-playing, hypothetical scenarios, developer mode",
            MutationType.SEMANTIC_SIMILARITY_ATTACK: "Generate inputs that are lexically or structurally similar but semantically different",
            MutationType.FORMAT_POISONING: "Inject structured data (JSON, XML, markdown, YAML) with malicious payloads",
            MutationType.LANGUAGE_MIXING: "Mix languages, scripts (Latin, Cyrillic, CJK), emoji, and code-switching patterns",
            MutationType.TOKEN_MANIPULATION: "Insert special tokens, manipulate token boundaries, use tokenizer-breaking sequences",
            MutationType.TEMPORAL_ATTACK: "Add impossible dates, outdated references, conflicting temporal information",
            # System/Network-level attacks
            MutationType.HTTP_HEADER_INJECTION: "Generate prompts with HTTP header-like patterns and injection attempts",
            MutationType.PAYLOAD_SIZE_ATTACK: "Generate prompts designed to create massive payloads when serialized",
            MutationType.CONTENT_TYPE_CONFUSION: "Include content-type manipulation instructions or format confusion patterns",
            MutationType.QUERY_PARAMETER_POISONING: "Include query parameter patterns, parameter pollution attempts, or query-based injection",
            MutationType.REQUEST_METHOD_ATTACK: "Include HTTP method manipulation instructions or method-based attack patterns",
            MutationType.PROTOCOL_LEVEL_ATTACK: "Include protocol-level attack patterns, request smuggling instructions, or protocol manipulation",
            MutationType.RESOURCE_EXHAUSTION: "Generate prompts with patterns designed to exhaust resources: deeply nested JSON, recursive structures",
            MutationType.CONCURRENT_REQUEST_PATTERN: "Generate prompts with patterns designed for concurrent execution and state manipulation",
            MutationType.TIMEOUT_MANIPULATION: "Generate prompts with patterns designed to cause timeouts or slow processing",
        }
        return descriptions.get(self, "Unknown mutation type")

    @property
    def default_weight(self) -> float:
        """Default scoring weight for this mutation type."""
        weights = {
            # Original 8 types
            MutationType.PARAPHRASE: 1.0,
            MutationType.NOISE: 0.8,
            MutationType.TONE_SHIFT: 0.9,
            MutationType.PROMPT_INJECTION: 1.5,
            MutationType.ENCODING_ATTACKS: 1.3,
            MutationType.CONTEXT_MANIPULATION: 1.1,
            MutationType.LENGTH_EXTREMES: 1.2,
            MutationType.CUSTOM: 1.0,
            # Advanced prompt-level attacks
            MutationType.MULTI_TURN_ATTACK: 1.4,
            MutationType.ADVANCED_JAILBREAK: 2.0,
            MutationType.SEMANTIC_SIMILARITY_ATTACK: 1.3,
            MutationType.FORMAT_POISONING: 1.6,
            MutationType.LANGUAGE_MIXING: 1.2,
            MutationType.TOKEN_MANIPULATION: 1.5,
            MutationType.TEMPORAL_ATTACK: 1.1,
            # System/Network-level attacks
            MutationType.HTTP_HEADER_INJECTION: 1.7,
            MutationType.PAYLOAD_SIZE_ATTACK: 1.4,
            MutationType.CONTENT_TYPE_CONFUSION: 1.5,
            MutationType.QUERY_PARAMETER_POISONING: 1.6,
            MutationType.REQUEST_METHOD_ATTACK: 1.3,
            MutationType.PROTOCOL_LEVEL_ATTACK: 1.8,
            MutationType.RESOURCE_EXHAUSTION: 1.5,
            MutationType.CONCURRENT_REQUEST_PATTERN: 1.4,
            MutationType.TIMEOUT_MANIPULATION: 1.3,
        }
        return weights.get(self, 1.0)

    @classmethod
    def open_source_types(cls) -> list[MutationType]:
        """Get mutation types available in Open Source edition (all 22+ types)."""
        return [
            # Original 8 types
            cls.PARAPHRASE,
            cls.NOISE,
            cls.TONE_SHIFT,
            cls.PROMPT_INJECTION,
            cls.ENCODING_ATTACKS,
            cls.CONTEXT_MANIPULATION,
            cls.LENGTH_EXTREMES,
            cls.CUSTOM,
            # Advanced prompt-level attacks
            cls.MULTI_TURN_ATTACK,
            cls.ADVANCED_JAILBREAK,
            cls.SEMANTIC_SIMILARITY_ATTACK,
            cls.FORMAT_POISONING,
            cls.LANGUAGE_MIXING,
            cls.TOKEN_MANIPULATION,
            cls.TEMPORAL_ATTACK,
            # System/Network-level attacks
            cls.HTTP_HEADER_INJECTION,
            cls.PAYLOAD_SIZE_ATTACK,
            cls.CONTENT_TYPE_CONFUSION,
            cls.QUERY_PARAMETER_POISONING,
            cls.REQUEST_METHOD_ATTACK,
            cls.PROTOCOL_LEVEL_ATTACK,
            cls.RESOURCE_EXHAUSTION,
            cls.CONCURRENT_REQUEST_PATTERN,
            cls.TIMEOUT_MANIPULATION,
        ]


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
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]

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
        - Is different from the original (except for LENGTH_EXTREMES which may be empty)
        - Doesn't exceed reasonable length bounds (unless it's LENGTH_EXTREMES testing long inputs)
        """
        # LENGTH_EXTREMES may intentionally create empty strings - these are valid
        if self.type == MutationType.LENGTH_EXTREMES:
            # Empty strings are valid for length extremes testing
            if not self.mutated:
                return True
            # Very long strings are also valid for length extremes
            # Allow up to 10x original length for length extremes testing
            if len(self.mutated) > len(self.original) * 10:
                return True  # Very long is valid for this type

        # For other types, empty strings are invalid
        if not self.mutated or not self.mutated.strip():
            return False

        if self.mutated.strip() == self.original.strip():
            return False

        # Mutation shouldn't be more than 3x the original length (except LENGTH_EXTREMES)
        if self.type != MutationType.LENGTH_EXTREMES:
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
    def from_dict(cls, data: dict[str, Any]) -> Mutation:
        """Create from dictionary."""
        return cls(
            original=data["original"],
            mutated=data["mutated"],
            type=MutationType(data["type"]),
            weight=data.get("weight", 1.0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            metadata=data.get("metadata", {}),
        )
