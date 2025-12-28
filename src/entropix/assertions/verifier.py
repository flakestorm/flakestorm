"""
Invariant Verifier

Main verification engine that runs all configured invariant checks
against agent responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from entropix.assertions.deterministic import (
    BaseChecker,
    CheckResult,
    ContainsChecker,
    LatencyChecker,
    ValidJsonChecker,
    RegexChecker,
)
from entropix.assertions.semantic import SimilarityChecker
from entropix.assertions.safety import ExcludesPIIChecker, RefusalChecker

if TYPE_CHECKING:
    from entropix.core.config import InvariantConfig, InvariantType


# Registry of checker classes by invariant type
CHECKER_REGISTRY: dict[str, type[BaseChecker]] = {
    "contains": ContainsChecker,
    "latency": LatencyChecker,
    "valid_json": ValidJsonChecker,
    "regex": RegexChecker,
    "similarity": SimilarityChecker,
    "excludes_pii": ExcludesPIIChecker,
    "refusal_check": RefusalChecker,
}


@dataclass
class VerificationResult:
    """
    Result of verifying all invariants against a response.
    
    Contains the overall pass/fail status and individual check results.
    """
    
    all_passed: bool
    """True if all invariant checks passed."""
    
    checks: list[CheckResult] = field(default_factory=list)
    """Individual check results."""
    
    @property
    def passed_count(self) -> int:
        """Number of checks that passed."""
        return sum(1 for c in self.checks if c.passed)
    
    @property
    def failed_count(self) -> int:
        """Number of checks that failed."""
        return sum(1 for c in self.checks if not c.passed)
    
    @property
    def total_count(self) -> int:
        """Total number of checks."""
        return len(self.checks)
    
    def get_failed_checks(self) -> list[CheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed]
    
    def get_passed_checks(self) -> list[CheckResult]:
        """Get list of passed checks."""
        return [c for c in self.checks if c.passed]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "all_passed": self.all_passed,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "checks": [c.to_dict() for c in self.checks],
        }


class InvariantVerifier:
    """
    Main verifier that runs all configured invariant checks.
    
    Instantiates the appropriate checker for each configured invariant
    and runs them against agent responses.
    
    Example:
        >>> verifier = InvariantVerifier(config.invariants)
        >>> result = verifier.verify(response, latency_ms=150.0)
        >>> if result.all_passed:
        ...     print("All checks passed!")
    """
    
    def __init__(self, invariants: list["InvariantConfig"]):
        """
        Initialize the verifier with invariant configurations.
        
        Args:
            invariants: List of invariant configurations to check
        """
        self.invariants = invariants
        self.checkers = self._build_checkers()
    
    def _build_checkers(self) -> list[BaseChecker]:
        """Build checker instances from configurations."""
        checkers = []
        
        for invariant in self.invariants:
            checker_cls = CHECKER_REGISTRY.get(invariant.type.value)
            
            if checker_cls is None:
                raise ValueError(
                    f"Unknown invariant type: {invariant.type}. "
                    f"Available types: {list(CHECKER_REGISTRY.keys())}"
                )
            
            checkers.append(checker_cls(invariant))
        
        return checkers
    
    def verify(self, response: str, latency_ms: float) -> VerificationResult:
        """
        Verify a response against all configured invariants.
        
        Args:
            response: The agent's response text
            latency_ms: Response latency in milliseconds
            
        Returns:
            VerificationResult with all check outcomes
        """
        results = []
        
        for checker in self.checkers:
            result = checker.check(response, latency_ms)
            results.append(result)
        
        all_passed = all(r.passed for r in results)
        
        return VerificationResult(
            all_passed=all_passed,
            checks=results,
        )
    
    def add_checker(self, checker: BaseChecker) -> None:
        """
        Add a custom checker at runtime.
        
        Args:
            checker: A BaseChecker instance
        """
        self.checkers.append(checker)
    
    def remove_checker(self, invariant_type: "InvariantType") -> bool:
        """
        Remove checkers of a specific type.
        
        Args:
            invariant_type: Type of checkers to remove
            
        Returns:
            True if any checkers were removed
        """
        original_count = len(self.checkers)
        self.checkers = [
            c for c in self.checkers 
            if c.type != invariant_type
        ]
        return len(self.checkers) < original_count
    
    @property
    def checker_types(self) -> list[str]:
        """Get list of active checker types."""
        return [c.type.value for c in self.checkers]

