"""
Deterministic Invariant Checkers

Simple, rule-based checks that verify exact conditions:
- String containment
- Latency thresholds
- Valid JSON format
- Regex pattern matching
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entropix.core.config import InvariantConfig, InvariantType


@dataclass
class CheckResult:
    """Result of a single invariant check."""
    
    type: "InvariantType"
    passed: bool
    details: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "passed": self.passed,
            "details": self.details,
        }


class BaseChecker(ABC):
    """Base class for invariant checkers."""
    
    def __init__(self, config: "InvariantConfig"):
        """
        Initialize the checker with configuration.
        
        Args:
            config: The invariant configuration
        """
        self.config = config
        self.type = config.type
    
    @abstractmethod
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """
        Perform the invariant check.
        
        Args:
            response: The agent's response text
            latency_ms: Response latency in milliseconds
            
        Returns:
            CheckResult with pass/fail and details
        """
        ...


class ContainsChecker(BaseChecker):
    """
    Check if response contains a specific string.
    
    Example config:
        type: contains
        value: "confirmation_code"
    """
    
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """Check if response contains the required value."""
        from entropix.core.config import InvariantType
        
        value = self.config.value or ""
        passed = value.lower() in response.lower()
        
        if passed:
            details = f"Found '{value}' in response"
        else:
            details = f"'{value}' not found in response"
        
        return CheckResult(
            type=InvariantType.CONTAINS,
            passed=passed,
            details=details,
        )


class LatencyChecker(BaseChecker):
    """
    Check if response latency is within threshold.
    
    Example config:
        type: latency
        max_ms: 2000
    """
    
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """Check if latency is within threshold."""
        from entropix.core.config import InvariantType
        
        max_ms = self.config.max_ms or 5000
        passed = latency_ms <= max_ms
        
        if passed:
            details = f"Latency {latency_ms:.0f}ms <= {max_ms}ms threshold"
        else:
            details = f"Latency {latency_ms:.0f}ms exceeded {max_ms}ms threshold"
        
        return CheckResult(
            type=InvariantType.LATENCY,
            passed=passed,
            details=details,
        )


class ValidJsonChecker(BaseChecker):
    """
    Check if response is valid JSON.
    
    Example config:
        type: valid_json
    """
    
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """Check if response is valid JSON."""
        from entropix.core.config import InvariantType
        
        try:
            json.loads(response)
            return CheckResult(
                type=InvariantType.VALID_JSON,
                passed=True,
                details="Response is valid JSON",
            )
        except json.JSONDecodeError as e:
            return CheckResult(
                type=InvariantType.VALID_JSON,
                passed=False,
                details=f"Invalid JSON: {e.msg} at position {e.pos}",
            )


class RegexChecker(BaseChecker):
    """
    Check if response matches a regex pattern.
    
    Example config:
        type: regex
        pattern: "^\\{.*\\}$"
    """
    
    def check(self, response: str, latency_ms: float) -> CheckResult:
        """Check if response matches the regex pattern."""
        from entropix.core.config import InvariantType
        
        pattern = self.config.pattern or ".*"
        
        try:
            match = re.search(pattern, response, re.DOTALL)
            passed = match is not None
            
            if passed:
                details = f"Response matches pattern '{pattern}'"
            else:
                details = f"Response does not match pattern '{pattern}'"
            
            return CheckResult(
                type=InvariantType.REGEX,
                passed=passed,
                details=details,
            )
            
        except re.error as e:
            return CheckResult(
                type=InvariantType.REGEX,
                passed=False,
                details=f"Invalid regex pattern: {e}",
            )

