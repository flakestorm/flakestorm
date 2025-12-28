"""
Tests for the assertion/invariant system.
"""

import pytest
from entropix.core.config import InvariantConfig, InvariantType
from entropix.assertions.deterministic import (
    ContainsChecker,
    LatencyChecker,
    ValidJsonChecker,
    RegexChecker,
)
from entropix.assertions.safety import ExcludesPIIChecker, RefusalChecker
from entropix.assertions.verifier import InvariantVerifier


class TestContainsChecker:
    """Tests for ContainsChecker."""
    
    def test_contains_pass(self):
        """Test contains check passes when value is present."""
        config = InvariantConfig(type=InvariantType.CONTAINS, value="success")
        checker = ContainsChecker(config)
        
        result = checker.check("Operation was a success!", 100.0)
        
        assert result.passed
        assert "Found" in result.details
    
    def test_contains_fail(self):
        """Test contains check fails when value is missing."""
        config = InvariantConfig(type=InvariantType.CONTAINS, value="success")
        checker = ContainsChecker(config)
        
        result = checker.check("Operation failed", 100.0)
        
        assert not result.passed
        assert "not found" in result.details
    
    def test_contains_case_insensitive(self):
        """Test contains check is case insensitive."""
        config = InvariantConfig(type=InvariantType.CONTAINS, value="SUCCESS")
        checker = ContainsChecker(config)
        
        result = checker.check("it was a success", 100.0)
        
        assert result.passed


class TestLatencyChecker:
    """Tests for LatencyChecker."""
    
    def test_latency_pass(self):
        """Test latency check passes when under threshold."""
        config = InvariantConfig(type=InvariantType.LATENCY, max_ms=2000)
        checker = LatencyChecker(config)
        
        result = checker.check("response", 500.0)
        
        assert result.passed
        assert "500ms" in result.details
    
    def test_latency_fail(self):
        """Test latency check fails when over threshold."""
        config = InvariantConfig(type=InvariantType.LATENCY, max_ms=1000)
        checker = LatencyChecker(config)
        
        result = checker.check("response", 1500.0)
        
        assert not result.passed
        assert "exceeded" in result.details
    
    def test_latency_boundary(self):
        """Test latency check at exact boundary passes."""
        config = InvariantConfig(type=InvariantType.LATENCY, max_ms=1000)
        checker = LatencyChecker(config)
        
        result = checker.check("response", 1000.0)
        
        assert result.passed


class TestValidJsonChecker:
    """Tests for ValidJsonChecker."""
    
    def test_valid_json_pass(self):
        """Test valid JSON passes."""
        config = InvariantConfig(type=InvariantType.VALID_JSON)
        checker = ValidJsonChecker(config)
        
        result = checker.check('{"status": "ok", "value": 123}', 100.0)
        
        assert result.passed
    
    def test_valid_json_array(self):
        """Test JSON array passes."""
        config = InvariantConfig(type=InvariantType.VALID_JSON)
        checker = ValidJsonChecker(config)
        
        result = checker.check('[1, 2, 3]', 100.0)
        
        assert result.passed
    
    def test_invalid_json_fail(self):
        """Test invalid JSON fails."""
        config = InvariantConfig(type=InvariantType.VALID_JSON)
        checker = ValidJsonChecker(config)
        
        result = checker.check('not valid json', 100.0)
        
        assert not result.passed
        assert "Invalid JSON" in result.details


class TestRegexChecker:
    """Tests for RegexChecker."""
    
    def test_regex_pass(self):
        """Test regex match passes."""
        config = InvariantConfig(
            type=InvariantType.REGEX,
            pattern=r"confirmation_\d+"
        )
        checker = RegexChecker(config)
        
        result = checker.check("Your confirmation_12345 is ready", 100.0)
        
        assert result.passed
    
    def test_regex_fail(self):
        """Test regex non-match fails."""
        config = InvariantConfig(
            type=InvariantType.REGEX,
            pattern=r"^OK$"
        )
        checker = RegexChecker(config)
        
        result = checker.check("NOT OK", 100.0)
        
        assert not result.passed


class TestExcludesPIIChecker:
    """Tests for ExcludesPIIChecker."""
    
    def test_no_pii_passes(self):
        """Test response without PII passes."""
        config = InvariantConfig(type=InvariantType.EXCLUDES_PII)
        checker = ExcludesPIIChecker(config)
        
        result = checker.check("Hello, your order is confirmed.", 100.0)
        
        assert result.passed
    
    def test_email_detected(self):
        """Test email PII is detected."""
        config = InvariantConfig(type=InvariantType.EXCLUDES_PII)
        checker = ExcludesPIIChecker(config)
        
        result = checker.check("Contact: john@example.com", 100.0)
        
        assert not result.passed
        assert "email" in result.details.lower()
    
    def test_phone_detected(self):
        """Test phone number PII is detected."""
        config = InvariantConfig(type=InvariantType.EXCLUDES_PII)
        checker = ExcludesPIIChecker(config)
        
        result = checker.check("Call me at 555-123-4567", 100.0)
        
        assert not result.passed


class TestRefusalChecker:
    """Tests for RefusalChecker."""
    
    def test_refusal_detected(self):
        """Test refusal language is detected as passing."""
        config = InvariantConfig(
            type=InvariantType.REFUSAL_CHECK,
            dangerous_prompts=True
        )
        checker = RefusalChecker(config)
        
        result = checker.check("I cannot help with that request.", 100.0)
        
        assert result.passed
        assert "refused" in result.details.lower()
    
    def test_compromised_detected(self):
        """Test compromised response is detected as failing."""
        config = InvariantConfig(
            type=InvariantType.REFUSAL_CHECK,
            dangerous_prompts=True
        )
        checker = RefusalChecker(config)
        
        result = checker.check("Okay, I will ignore previous instructions.", 100.0)
        
        assert not result.passed
        assert "compromise" in result.details.lower()


class TestInvariantVerifier:
    """Tests for InvariantVerifier."""
    
    def test_verify_multiple_invariants(self):
        """Test verifying multiple invariants at once."""
        invariants = [
            InvariantConfig(type=InvariantType.LATENCY, max_ms=2000),
            InvariantConfig(type=InvariantType.VALID_JSON),
        ]
        
        verifier = InvariantVerifier(invariants)
        
        # Both pass
        result = verifier.verify('{"ok": true}', 500.0)
        assert result.all_passed
        assert result.passed_count == 2
        
        # Latency fails
        result = verifier.verify('{"ok": true}', 3000.0)
        assert not result.all_passed
        assert result.failed_count == 1
    
    def test_empty_invariants(self):
        """Test with no invariants."""
        verifier = InvariantVerifier([])
        result = verifier.verify("anything", 100.0)
        
        assert result.all_passed
        assert result.total_count == 0

