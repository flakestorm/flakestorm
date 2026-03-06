"""
Report Data Models

Data structures for representing test results and statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flakestorm.core.config import FlakeStormConfig
    from flakestorm.mutations.types import Mutation


@dataclass
class CheckResult:
    """Result of a single invariant check."""

    check_type: str
    """Type of the check (e.g., 'latency', 'contains')."""

    passed: bool
    """Whether the check passed."""

    details: str
    """Human-readable details about the check result."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "check_type": self.check_type,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass
class TypeStatistics:
    """Statistics for a specific mutation type."""

    mutation_type: str
    """Name of the mutation type."""

    total: int
    """Total number of tests of this type."""

    passed: int
    """Number of tests that passed."""

    pass_rate: float
    """Pass rate as a decimal (0.0 to 1.0)."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mutation_type": self.mutation_type,
            "total": self.total,
            "passed": self.passed,
            "failed": self.total - self.passed,
            "pass_rate": self.pass_rate,
        }


@dataclass
class TestStatistics:
    """Aggregate statistics for a test run."""

    total_mutations: int
    """Total number of mutations tested."""

    passed_mutations: int
    """Number of mutations that passed all checks."""

    failed_mutations: int
    """Number of mutations that failed one or more checks."""

    robustness_score: float
    """Weighted robustness score (0.0 to 1.0)."""

    avg_latency_ms: float
    """Average response latency in milliseconds."""

    p50_latency_ms: float
    """50th percentile (median) latency."""

    p95_latency_ms: float
    """95th percentile latency."""

    p99_latency_ms: float
    """99th percentile latency."""

    by_type: list[TypeStatistics] = field(default_factory=list)
    """Statistics broken down by mutation type."""

    duration_seconds: float = 0.0
    """Total test duration in seconds."""

    @property
    def pass_rate(self) -> float:
        """Simple pass rate (passed / total)."""
        if self.total_mutations == 0:
            return 0.0
        return self.passed_mutations / self.total_mutations

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_mutations": self.total_mutations,
            "passed_mutations": self.passed_mutations,
            "failed_mutations": self.failed_mutations,
            "robustness_score": self.robustness_score,
            "pass_rate": self.pass_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "duration_seconds": self.duration_seconds,
            "by_type": [t.to_dict() for t in self.by_type],
        }


@dataclass
class MutationResult:
    """Result of testing a single mutation."""

    original_prompt: str
    """The original golden prompt."""

    mutation: Mutation
    """The mutation that was tested."""

    response: str
    """The agent's response."""

    latency_ms: float
    """Response latency in milliseconds."""

    passed: bool
    """Whether all invariant checks passed."""

    checks: list[CheckResult] = field(default_factory=list)
    """Individual check results."""

    error: str | None = None
    """Error message if the agent call failed."""

    @property
    def failed_checks(self) -> list[CheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_prompt": self.original_prompt,
            "mutation": self.mutation.to_dict(),
            "response": self.response,
            "latency_ms": self.latency_ms,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "error": self.error,
        }


@dataclass
class TestResults:
    """Complete results from a test run."""

    config: FlakeStormConfig
    """Configuration used for the test."""

    started_at: datetime
    """When the test started."""

    completed_at: datetime
    """When the test completed."""

    mutations: list[MutationResult]
    """Results for each mutation."""

    statistics: TestStatistics
    """Aggregate statistics."""

    resilience_scores: dict[str, float] | None = field(default=None)
    """V2: mutation_robustness, chaos_resilience, contract_compliance, replay_regression, overall."""

    @property
    def duration(self) -> float:
        """Test duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def passed_mutations(self) -> list[MutationResult]:
        """Get mutations that passed."""
        return [m for m in self.mutations if m.passed]

    @property
    def failed_mutations(self) -> list[MutationResult]:
        """Get mutations that failed."""
        return [m for m in self.mutations if not m.passed]

    def get_by_type(self, mutation_type: str) -> list[MutationResult]:
        """Get mutations of a specific type."""
        return [m for m in self.mutations if m.mutation.type.value == mutation_type]

    def get_by_prompt(self, prompt: str) -> list[MutationResult]:
        """Get mutations for a specific golden prompt."""
        return [m for m in self.mutations if m.original_prompt == prompt]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        out: dict[str, Any] = {
            "version": "1.0",
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration,
            "statistics": self.statistics.to_dict(),
            "mutations": [m.to_dict() for m in self.mutations],
            "golden_prompts": self.config.golden_prompts,
        }
        if self.resilience_scores:
            out["resilience_scores"] = self.resilience_scores
        return out

    def to_replay_session(self, failure_index: int = 0) -> dict[str, Any] | None:
        """Export a failed mutation as a replay session dict (v2). Returns None if no failure."""
        failed = self.failed_mutations
        if not failed or failure_index >= len(failed):
            return None
        m = failed[failure_index]
        return {
            "id": f"export-{self.started_at.strftime('%Y%m%d-%H%M%S')}-{failure_index}",
            "name": f"Exported failure: {m.mutation.type.value}",
            "source": "flakestorm_export",
            "input": m.original_prompt,
            "tool_responses": [],
            "expected_failure": m.error or "One or more invariants failed",
            "contract": "default",
        }
