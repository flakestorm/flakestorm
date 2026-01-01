"""
Tests for the mutation engine.
"""

import pytest

from flakestorm.mutations.templates import MutationTemplates
from flakestorm.mutations.types import Mutation, MutationType


class TestMutationType:
    """Tests for MutationType enum."""

    def test_mutation_type_values(self):
        """Test mutation type string values."""
        assert MutationType.PARAPHRASE.value == "paraphrase"
        assert MutationType.NOISE.value == "noise"
        assert MutationType.TONE_SHIFT.value == "tone_shift"
        assert MutationType.PROMPT_INJECTION.value == "prompt_injection"
        assert MutationType.ENCODING_ATTACKS.value == "encoding_attacks"
        assert MutationType.CONTEXT_MANIPULATION.value == "context_manipulation"
        assert MutationType.LENGTH_EXTREMES.value == "length_extremes"
        assert MutationType.CUSTOM.value == "custom"

    def test_display_name(self):
        """Test display name generation."""
        assert MutationType.PARAPHRASE.display_name == "Paraphrase"
        assert MutationType.TONE_SHIFT.display_name == "Tone Shift"
        assert MutationType.PROMPT_INJECTION.display_name == "Prompt Injection"
        assert MutationType.ENCODING_ATTACKS.display_name == "Encoding Attacks"
        assert MutationType.CONTEXT_MANIPULATION.display_name == "Context Manipulation"
        assert MutationType.LENGTH_EXTREMES.display_name == "Length Extremes"

    def test_default_weights(self):
        """Test default weights are assigned."""
        assert MutationType.PARAPHRASE.default_weight == 1.0
        assert MutationType.PROMPT_INJECTION.default_weight == 1.5
        assert MutationType.NOISE.default_weight == 0.8
        assert MutationType.ENCODING_ATTACKS.default_weight == 1.3
        assert MutationType.CONTEXT_MANIPULATION.default_weight == 1.1
        assert MutationType.LENGTH_EXTREMES.default_weight == 1.2


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
        """Test that all mutation types have templates."""
        templates = MutationTemplates()

        # Test all 8 mutation types
        expected_types = [
            MutationType.PARAPHRASE,
            MutationType.NOISE,
            MutationType.TONE_SHIFT,
            MutationType.PROMPT_INJECTION,
            MutationType.ENCODING_ATTACKS,
            MutationType.CONTEXT_MANIPULATION,
            MutationType.LENGTH_EXTREMES,
            MutationType.CUSTOM,
        ]

        for mutation_type in expected_types:
            template = templates.get(mutation_type)
            assert template is not None
            assert "{prompt}" in template

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
