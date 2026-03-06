"""
Resilience matrix: aggregate contract × chaos results and compute weighted score.

Formula (addendum §6.3):
  score = (Σ(passed_critical×3) + Σ(passed_high×2) + Σ(passed_medium×1))
        / (Σ(total_critical×3) + Σ(total_high×2) + Σ(total_medium×1)) × 100
  Automatic FAIL if any critical invariant fails in any scenario.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_WEIGHT = {"critical": 3, "high": 2, "medium": 1, "low": 1}


@dataclass
class CellResult:
    """Single (invariant, scenario) cell result."""

    invariant_id: str
    scenario_name: str
    severity: str
    passed: bool


@dataclass
class ResilienceMatrix:
    """Aggregated contract × chaos matrix with resilience score."""

    cell_results: list[CellResult] = field(default_factory=list)
    overall_passed: bool = True
    critical_failed: bool = False

    @property
    def resilience_score(self) -> float:
        """Weighted score 0–100. Fails if any critical failed."""
        if not self.cell_results:
            return 100.0
        try:
            from flakestorm.core.performance import (
                calculate_resilience_matrix_score,
                is_rust_available,
            )
            if is_rust_available():
                severities = [c.severity for c in self.cell_results]
                passed = [c.passed for c in self.cell_results]
                score, _, _ = calculate_resilience_matrix_score(severities, passed)
                return score
        except Exception:
            pass
        weighted_pass = 0.0
        weighted_total = 0.0
        for c in self.cell_results:
            w = SEVERITY_WEIGHT.get(c.severity.lower(), 1)
            weighted_total += w
            if c.passed:
                weighted_pass += w
        if weighted_total == 0:
            return 100.0
        score = (weighted_pass / weighted_total) * 100.0
        return round(score, 2)

    def add_result(self, invariant_id: str, scenario_name: str, severity: str, passed: bool) -> None:
        self.cell_results.append(
            CellResult(
                invariant_id=invariant_id,
                scenario_name=scenario_name,
                severity=severity,
                passed=passed,
            )
        )
        if severity.lower() == "critical" and not passed:
            self.critical_failed = True
            self.overall_passed = False

    @property
    def passed(self) -> bool:
        """Overall pass: no critical failure and score reflects all checks."""
        return self.overall_passed and not self.critical_failed
