"""
Orchestrator for flakestorm Test Runs

Coordinates the entire testing process: mutation generation,
agent invocation, invariant verification, and result aggregation.

Runs tests sequentially with a maximum of 50 mutations per test run.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

# Hardcoded limits for open source edition
MAX_MUTATIONS_PER_RUN = 50
PARALLEL_EXECUTION_ENABLED = False  # Sequential execution only

if TYPE_CHECKING:
    from flakestorm.assertions.verifier import InvariantVerifier
    from flakestorm.core.config import FlakeStormConfig
    from flakestorm.core.protocol import BaseAgentAdapter
    from flakestorm.mutations.engine import MutationEngine
    from flakestorm.mutations.types import Mutation
    from flakestorm.reports.models import MutationResult, TestResults, TestStatistics


@dataclass
class OrchestratorState:
    """State tracking for the orchestrator."""

    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_mutations: int = 0
    completed_mutations: int = 0
    passed_mutations: int = 0
    failed_mutations: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_mutations == 0:
            return 0.0
        return (self.completed_mutations / self.total_mutations) * 100

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()


class Orchestrator:
    """
    Orchestrates the entire flakestorm test run.

    Coordinates between:
    - MutationEngine: Generates adversarial inputs
    - Agent: The system under test
    - InvariantVerifier: Validates responses
    - Reporter: Generates output reports
    """

    def __init__(
        self,
        config: FlakeStormConfig,
        agent: BaseAgentAdapter,
        mutation_engine: MutationEngine,
        verifier: InvariantVerifier,
        console: Console | None = None,
        show_progress: bool = True,
    ):
        """
        Initialize the orchestrator.

        Args:
            config: flakestorm configuration
            agent: Agent adapter to test
            mutation_engine: Engine for generating mutations
            verifier: Invariant verification engine
            console: Rich console for output
            show_progress: Whether to show progress bars
        """
        self.config = config
        self.agent = agent
        self.mutation_engine = mutation_engine
        self.verifier = verifier
        self.console = console or Console()
        self.show_progress = show_progress
        self.state = OrchestratorState()

    async def run(self) -> TestResults:
        """
        Execute the full test run.

        Runs tests sequentially with a maximum of 50 mutations per run.

        Returns:
            TestResults containing all test outcomes
        """
        from flakestorm.reports.models import (
            TestResults,
        )

        self.state = OrchestratorState()
        all_results: list[MutationResult] = []

        # Phase 1: Generate all mutations
        all_mutations = await self._generate_mutations()

        # Enforce mutation limit
        if len(all_mutations) > MAX_MUTATIONS_PER_RUN:
            # Truncate to limit
            all_mutations = all_mutations[:MAX_MUTATIONS_PER_RUN]
            if self.show_progress:
                self.console.print(
                    f"[yellow]⚠️ Limited to {MAX_MUTATIONS_PER_RUN} mutations per run[/yellow]\n"
                )

        self.state.total_mutations = len(all_mutations)

        # Phase 2: Run mutations against agent
        if self.show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    "Running attacks...",
                    total=len(all_mutations),
                )

                all_results = await self._run_mutations_with_progress(
                    all_mutations,
                    progress,
                    task,
                )
        else:
            all_results = await self._run_mutations(all_mutations)

        # Phase 3: Compile results
        self.state.completed_at = datetime.now()

        statistics = self._calculate_statistics(all_results)

        return TestResults(
            config=self.config,
            started_at=self.state.started_at,
            completed_at=self.state.completed_at,
            mutations=all_results,
            statistics=statistics,
        )

    async def _generate_mutations(self) -> list[tuple[str, Mutation]]:
        """Generate all mutations for all golden prompts."""

        all_mutations: list[tuple[str, Mutation]] = []

        if self.show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    "Generating mutations...",
                    total=len(self.config.golden_prompts),
                )

                for prompt in self.config.golden_prompts:
                    mutations = await self.mutation_engine.generate_mutations(
                        prompt,
                        self.config.mutations.types,
                        self.config.mutations.count,
                    )
                    for mutation in mutations:
                        all_mutations.append((prompt, mutation))
                    progress.update(task, advance=1)
        else:
            for prompt in self.config.golden_prompts:
                mutations = await self.mutation_engine.generate_mutations(
                    prompt,
                    self.config.mutations.types,
                    self.config.mutations.count,
                )
                for mutation in mutations:
                    all_mutations.append((prompt, mutation))

        return all_mutations

    async def _run_mutations(
        self,
        mutations: list[tuple[str, Mutation]],
    ) -> list[MutationResult]:
        """
        Run all mutations sequentially (one at a time).
        """
        # Sequential execution only
        semaphore = asyncio.Semaphore(1)
        results = []
        for original, mutation in mutations:
            result = await self._run_single_mutation(original, mutation, semaphore)
            results.append(result)
        return results

    async def _run_mutations_with_progress(
        self,
        mutations: list[tuple[str, Mutation]],
        progress: Progress,
        task_id: int,
    ) -> list[MutationResult]:
        """
        Run all mutations with progress display (sequential execution).
        """
        # Sequential execution only
        semaphore = asyncio.Semaphore(1)
        results: list[MutationResult] = []

        for original, mutation in mutations:
            result = await self._run_single_mutation(original, mutation, semaphore)
            progress.update(task_id, advance=1)
            results.append(result)
        return results

    async def _run_single_mutation(
        self,
        original_prompt: str,
        mutation: Mutation,
        semaphore: asyncio.Semaphore,
    ) -> MutationResult:
        """Run a single mutation against the agent."""
        from flakestorm.reports.models import CheckResult, MutationResult

        async with semaphore:
            # Invoke agent
            response = await self.agent.invoke_with_timing(mutation.mutated)

            # Verify invariants
            if response.success:
                verification = self.verifier.verify(
                    response.output,
                    response.latency_ms,
                )
                passed = verification.all_passed
                checks = [
                    CheckResult(
                        check_type=check.type.value,
                        passed=check.passed,
                        details=check.details,
                    )
                    for check in verification.checks
                ]
            else:
                passed = False
                checks = [
                    CheckResult(
                        check_type="agent_error",
                        passed=False,
                        details=response.error or "Unknown error",
                    )
                ]

            # Update state
            self.state.completed_mutations += 1
            if passed:
                self.state.passed_mutations += 1
            else:
                self.state.failed_mutations += 1

            return MutationResult(
                original_prompt=original_prompt,
                mutation=mutation,
                response=response.output,
                latency_ms=response.latency_ms,
                passed=passed,
                checks=checks,
                error=response.error,
            )

    def _calculate_statistics(
        self,
        results: list[MutationResult],
    ) -> TestStatistics:
        """Calculate test statistics from results."""
        from flakestorm.reports.models import TestStatistics, TypeStatistics

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # Calculate weighted robustness score
        total_weight = sum(
            self.config.mutations.weights.get(r.mutation.type, 1.0) for r in results
        )
        passed_weight = sum(
            self.config.mutations.weights.get(r.mutation.type, 1.0)
            for r in results
            if r.passed
        )
        robustness_score = passed_weight / total_weight if total_weight > 0 else 0.0

        # Latency statistics
        latencies = sorted(r.latency_ms for r in results)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        def percentile(sorted_vals: list[float], p: int) -> float:
            if not sorted_vals:
                return 0.0
            idx = int(p / 100 * (len(sorted_vals) - 1))
            return sorted_vals[idx]

        # Statistics by mutation type
        type_stats: dict[str, TypeStatistics] = {}
        for result in results:
            type_name = result.mutation.type.value
            if type_name not in type_stats:
                type_stats[type_name] = TypeStatistics(
                    mutation_type=type_name,
                    total=0,
                    passed=0,
                    pass_rate=0.0,
                )
            type_stats[type_name].total += 1
            if result.passed:
                type_stats[type_name].passed += 1

        # Calculate pass rates
        for stats in type_stats.values():
            stats.pass_rate = stats.passed / stats.total if stats.total > 0 else 0.0

        return TestStatistics(
            total_mutations=total,
            passed_mutations=passed,
            failed_mutations=failed,
            robustness_score=robustness_score,
            avg_latency_ms=avg_latency,
            p50_latency_ms=percentile(latencies, 50),
            p95_latency_ms=percentile(latencies, 95),
            p99_latency_ms=percentile(latencies, 99),
            by_type=list(type_stats.values()),
            duration_seconds=self.state.duration_seconds,
        )
