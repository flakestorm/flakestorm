"""
Tests for the mutation engine.
"""

import pytest

from flakestorm.mutations.templates import MutationTemplates
from flakestorm.mutations.types import Mutation, MutationType


class TestMutationType:
    """Tests for MutationType enum."""

    def test_mutation_type_values(self):
        """Test mutation type string values for all 24 types."""
        # Core prompt-level attacks (8)
        assert MutationType.PARAPHRASE.value == "paraphrase"
        assert MutationType.NOISE.value == "noise"
        assert MutationType.TONE_SHIFT.value == "tone_shift"
        assert MutationType.PROMPT_INJECTION.value == "prompt_injection"
        assert MutationType.ENCODING_ATTACKS.value == "encoding_attacks"
        assert MutationType.CONTEXT_MANIPULATION.value == "context_manipulation"
        assert MutationType.LENGTH_EXTREMES.value == "length_extremes"
        assert MutationType.CUSTOM.value == "custom"

        # Advanced prompt-level attacks (7)
        assert MutationType.MULTI_TURN_ATTACK.value == "multi_turn_attack"
        assert MutationType.ADVANCED_JAILBREAK.value == "advanced_jailbreak"
        assert (
            MutationType.SEMANTIC_SIMILARITY_ATTACK.value
            == "semantic_similarity_attack"
        )
        assert MutationType.FORMAT_POISONING.value == "format_poisoning"
        assert MutationType.LANGUAGE_MIXING.value == "language_mixing"
        assert MutationType.TOKEN_MANIPULATION.value == "token_manipulation"
        assert MutationType.TEMPORAL_ATTACK.value == "temporal_attack"

        # System/Network-level attacks (9)
        assert MutationType.HTTP_HEADER_INJECTION.value == "http_header_injection"
        assert MutationType.PAYLOAD_SIZE_ATTACK.value == "payload_size_attack"
        assert MutationType.CONTENT_TYPE_CONFUSION.value == "content_type_confusion"
        assert (
            MutationType.QUERY_PARAMETER_POISONING.value == "query_parameter_poisoning"
        )
        assert MutationType.REQUEST_METHOD_ATTACK.value == "request_method_attack"
        assert MutationType.PROTOCOL_LEVEL_ATTACK.value == "protocol_level_attack"
        assert MutationType.RESOURCE_EXHAUSTION.value == "resource_exhaustion"
        assert (
            MutationType.CONCURRENT_REQUEST_PATTERN.value
            == "concurrent_request_pattern"
        )
        assert MutationType.TIMEOUT_MANIPULATION.value == "timeout_manipulation"

    def test_display_name(self):
        """Test display name generation for all mutation types."""
        # Core types
        assert MutationType.PARAPHRASE.display_name == "Paraphrase"
        assert MutationType.TONE_SHIFT.display_name == "Tone Shift"
        assert MutationType.PROMPT_INJECTION.display_name == "Prompt Injection"
        assert MutationType.ENCODING_ATTACKS.display_name == "Encoding Attacks"
        assert MutationType.CONTEXT_MANIPULATION.display_name == "Context Manipulation"
        assert MutationType.LENGTH_EXTREMES.display_name == "Length Extremes"

        # Advanced types
        assert MutationType.MULTI_TURN_ATTACK.display_name == "Multi Turn Attack"
        assert MutationType.ADVANCED_JAILBREAK.display_name == "Advanced Jailbreak"
        assert (
            MutationType.SEMANTIC_SIMILARITY_ATTACK.display_name
            == "Semantic Similarity Attack"
        )
        assert MutationType.FORMAT_POISONING.display_name == "Format Poisoning"
        assert MutationType.LANGUAGE_MIXING.display_name == "Language Mixing"
        assert MutationType.TOKEN_MANIPULATION.display_name == "Token Manipulation"
        assert MutationType.TEMPORAL_ATTACK.display_name == "Temporal Attack"

        # System/Network types
        assert (
            MutationType.HTTP_HEADER_INJECTION.display_name == "Http Header Injection"
        )
        assert MutationType.PAYLOAD_SIZE_ATTACK.display_name == "Payload Size Attack"
        assert (
            MutationType.CONTENT_TYPE_CONFUSION.display_name == "Content Type Confusion"
        )
        assert (
            MutationType.QUERY_PARAMETER_POISONING.display_name
            == "Query Parameter Poisoning"
        )
        assert (
            MutationType.REQUEST_METHOD_ATTACK.display_name == "Request Method Attack"
        )
        assert (
            MutationType.PROTOCOL_LEVEL_ATTACK.display_name == "Protocol Level Attack"
        )
        assert MutationType.RESOURCE_EXHAUSTION.display_name == "Resource Exhaustion"
        assert (
            MutationType.CONCURRENT_REQUEST_PATTERN.display_name
            == "Concurrent Request Pattern"
        )
        assert MutationType.TIMEOUT_MANIPULATION.display_name == "Timeout Manipulation"

    def test_default_weights(self):
        """Test default weights are assigned for all mutation types."""
        # Core types
        assert MutationType.PARAPHRASE.default_weight == 1.0
        assert MutationType.PROMPT_INJECTION.default_weight == 1.5
        assert MutationType.NOISE.default_weight == 0.8
        assert MutationType.ENCODING_ATTACKS.default_weight == 1.3
        assert MutationType.CONTEXT_MANIPULATION.default_weight == 1.1
        assert MutationType.LENGTH_EXTREMES.default_weight == 1.2
        assert MutationType.TONE_SHIFT.default_weight == 0.9
        assert MutationType.CUSTOM.default_weight == 1.0

        # Advanced types
        assert MutationType.MULTI_TURN_ATTACK.default_weight == 1.4
        assert MutationType.ADVANCED_JAILBREAK.default_weight == 2.0
        assert MutationType.SEMANTIC_SIMILARITY_ATTACK.default_weight == 1.3
        assert MutationType.FORMAT_POISONING.default_weight == 1.6
        assert MutationType.LANGUAGE_MIXING.default_weight == 1.2
        assert MutationType.TOKEN_MANIPULATION.default_weight == 1.5
        assert MutationType.TEMPORAL_ATTACK.default_weight == 1.1

        # System/Network types
        assert MutationType.HTTP_HEADER_INJECTION.default_weight == 1.7
        assert MutationType.PAYLOAD_SIZE_ATTACK.default_weight == 1.4
        assert MutationType.CONTENT_TYPE_CONFUSION.default_weight == 1.5
        assert MutationType.QUERY_PARAMETER_POISONING.default_weight == 1.6
        assert MutationType.REQUEST_METHOD_ATTACK.default_weight == 1.3
        assert MutationType.PROTOCOL_LEVEL_ATTACK.default_weight == 1.8
        assert MutationType.RESOURCE_EXHAUSTION.default_weight == 1.5
        assert MutationType.CONCURRENT_REQUEST_PATTERN.default_weight == 1.4
        assert MutationType.TIMEOUT_MANIPULATION.default_weight == 1.3


class TestMutation:
    """Tests for Mutation dataclass."""

    def test_mutation_creation(self):
        """Test creating a mutation."""
        mutation = Mutation(
            original="Book a flight",
            mutated="I need to fly somewhere",
            type=MutationType.PARAPHRASE,
            weight=1.0,
        )

        assert mutation.original == "Book a flight"
        assert mutation.mutated == "I need to fly somewhere"
        assert mutation.type == MutationType.PARAPHRASE

    def test_mutation_id_generation(self):
        """Test unique ID generation."""
        m1 = Mutation(
            original="Test",
            mutated="Test 1",
            type=MutationType.NOISE,
        )
        m2 = Mutation(
            original="Test",
            mutated="Test 2",
            type=MutationType.NOISE,
        )

        assert m1.id != m2.id
        assert len(m1.id) == 12

    def test_mutation_validity(self):
        """Test mutation validity checks."""
        # Valid mutation (mutated must be different and <= 3x original length)
        valid = Mutation(
            original="What is the weather today?",
            mutated="Tell me about the weather",
            type=MutationType.PARAPHRASE,
        )
        assert valid.is_valid()

        # Invalid: same as original
        invalid_same = Mutation(
            original="Test prompt",
            mutated="Test prompt",
            type=MutationType.PARAPHRASE,
        )
        assert not invalid_same.is_valid()

        # Invalid: empty mutated (for non-LENGTH_EXTREMES types)
        invalid_empty = Mutation(
            original="Test prompt",
            mutated="",
            type=MutationType.PARAPHRASE,
        )
        assert not invalid_empty.is_valid()

        # Valid: empty mutated for LENGTH_EXTREMES (edge case testing)
        valid_empty = Mutation(
            original="Test prompt",
            mutated="",
            type=MutationType.LENGTH_EXTREMES,
        )
        assert valid_empty.is_valid()

        # Valid: very long mutated for LENGTH_EXTREMES
        very_long = "x" * (len("Test prompt") * 5)
        valid_long = Mutation(
            original="Test prompt",
            mutated=very_long,
            type=MutationType.LENGTH_EXTREMES,
        )
        assert valid_long.is_valid()

    def test_mutation_serialization(self):
        """Test to_dict and from_dict."""
        mutation = Mutation(
            original="Test prompt",
            mutated="Mutated prompt",
            type=MutationType.NOISE,
            weight=0.8,
        )

        data = mutation.to_dict()
        restored = Mutation.from_dict(data)

        assert restored.original == mutation.original
        assert restored.mutated == mutation.mutated
        assert restored.type == mutation.type


class TestMutationTemplates:
    """Tests for MutationTemplates."""

    def test_all_types_have_templates(self):
        """Test that all 24 mutation types have templates."""
        templates = MutationTemplates()

        # All 24 mutation types
        expected_types = [
            # Core prompt-level attacks (8)
            MutationType.PARAPHRASE,
            MutationType.NOISE,
            MutationType.TONE_SHIFT,
            MutationType.PROMPT_INJECTION,
            MutationType.ENCODING_ATTACKS,
            MutationType.CONTEXT_MANIPULATION,
            MutationType.LENGTH_EXTREMES,
            MutationType.CUSTOM,
            # Advanced prompt-level attacks (7)
            MutationType.MULTI_TURN_ATTACK,
            MutationType.ADVANCED_JAILBREAK,
            MutationType.SEMANTIC_SIMILARITY_ATTACK,
            MutationType.FORMAT_POISONING,
            MutationType.LANGUAGE_MIXING,
            MutationType.TOKEN_MANIPULATION,
            MutationType.TEMPORAL_ATTACK,
            # System/Network-level attacks (9)
            MutationType.HTTP_HEADER_INJECTION,
            MutationType.PAYLOAD_SIZE_ATTACK,
            MutationType.CONTENT_TYPE_CONFUSION,
            MutationType.QUERY_PARAMETER_POISONING,
            MutationType.REQUEST_METHOD_ATTACK,
            MutationType.PROTOCOL_LEVEL_ATTACK,
            MutationType.RESOURCE_EXHAUSTION,
            MutationType.CONCURRENT_REQUEST_PATTERN,
            MutationType.TIMEOUT_MANIPULATION,
        ]

        assert len(expected_types) == 24, "Should have exactly 24 mutation types"

        for mutation_type in expected_types:
            template = templates.get(mutation_type)
            assert template is not None, f"Template missing for {mutation_type.value}"
            assert (
                "{prompt}" in template
            ), f"Template for {mutation_type.value} missing {{prompt}} placeholder"

    def test_format_template(self):
        """Test formatting a template with a prompt."""
        templates = MutationTemplates()
        formatted = templates.format(MutationType.PARAPHRASE, "Book a flight to Paris")

        assert "Book a flight to Paris" in formatted
        assert "{prompt}" not in formatted

    def test_custom_template(self):
        """Test setting a custom template."""
        templates = MutationTemplates()
        custom = "Custom template for {prompt}"

        templates.set_template(MutationType.NOISE, custom)

        assert templates.get(MutationType.NOISE) == custom

    def test_custom_template_requires_placeholder(self):
        """Test that custom templates must have {prompt} placeholder."""
        templates = MutationTemplates()

        with pytest.raises(ValueError):
            templates.set_template(MutationType.NOISE, "No placeholder here")
