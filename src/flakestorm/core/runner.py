"""
flakestorm Test Runner

High-level interface for running flakestorm tests. Combines all components
and provides a simple API for executing reliability tests.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from flakestorm.assertions.verifier import InvariantVerifier
from flakestorm.core.config import ChaosConfig, FlakeStormConfig, load_config
from flakestorm.core.orchestrator import Orchestrator
from flakestorm.core.protocol import BaseAgentAdapter, create_agent_adapter
from flakestorm.mutations.engine import MutationEngine

if TYPE_CHECKING:
    from flakestorm.reports.models import TestResults


class FlakeStormRunner:
    """
    Main runner for flakestorm tests.

    Provides a high-level interface for running reliability tests
    against AI agents. Handles configuration loading, component
    initialization, and test execution.

    Example:
        >>> config = load_config("flakestorm.yaml")
        >>> runner = FlakeStormRunner(config)
        >>> results = await runner.run()
        >>> print(f"Score: {results.statistics.robustness_score:.1%}")
    """

    def __init__(
        self,
        config: FlakeStormConfig | str | Path,
        agent: BaseAgentAdapter | None = None,
        console: Console | None = None,
        show_progress: bool = True,
        chaos: bool = False,
        chaos_profile: str | None = None,
        chaos_only: bool = False,
    ):
        """
        Initialize the test runner.

        Args:
            config: Configuration object or path to config file
            agent: Optional pre-configured agent adapter
            console: Rich console for output
            show_progress: Whether to show progress bars
            chaos: Enable environment chaos (tool/LLM faults) for this run
            chaos_profile: Use built-in chaos profile (e.g. api_outage, degraded_llm)
            chaos_only: Run only chaos tests (no mutation generation)
        """
        # Load config if path provided
        if isinstance(config, str | Path):
            self.config = load_config(config)
        else:
            self.config = config

        # Reproducibility: fix Python random seed so chaos and any sampling are deterministic
        if self.config.advanced.seed is not None:
            random.seed(self.config.advanced.seed)

        self.chaos_only = chaos_only

        # Load chaos profile if requested
        if chaos_profile:
            from flakestorm.chaos.profiles import load_chaos_profile
            profile_chaos = load_chaos_profile(chaos_profile)
            # Merge with config.chaos or replace
            if self.config.chaos:
                merged = self.config.chaos.model_dump()
                for key in ("tool_faults", "llm_faults", "context_attacks"):
                    existing = merged.get(key) or []
                    from_profile = getattr(profile_chaos, key, None) or []
                    if isinstance(existing, list) and isinstance(from_profile, list):
                        merged[key] = existing + from_profile
                    elif from_profile:
                        merged[key] = from_profile
                self.config = self.config.model_copy(
                    update={"chaos": ChaosConfig.model_validate(merged)}
                )
            else:
                self.config = self.config.model_copy(update={"chaos": profile_chaos})
        elif (chaos or chaos_only) and not self.config.chaos:
            # Chaos requested but no config: use default profile or minimal
            from flakestorm.chaos.profiles import load_chaos_profile
            try:
                self.config = self.config.model_copy(
                    update={"chaos": load_chaos_profile("api_outage")}
                )
            except FileNotFoundError:
                self.config = self.config.model_copy(
                    update={"chaos": ChaosConfig(tool_faults=[], llm_faults=[])}
                )

        self.console = console or Console()
        self.show_progress = show_progress

        # Initialize components
        base_agent = agent or create_agent_adapter(self.config.agent)
        if self.config.chaos:
            from flakestorm.core.protocol import create_instrumented_adapter
            self.agent = create_instrumented_adapter(base_agent, self.config.chaos)
        else:
            self.agent = base_agent
        # When seed is set, use temperature=0 for mutation generation so same prompts → same mutations
        model_cfg = self.config.model
        if self.config.advanced.seed is not None:
            model_cfg = model_cfg.model_copy(update={"temperature": 0.0})
        self.mutation_engine = MutationEngine(model_cfg)
        self.verifier = InvariantVerifier(self.config.invariants)

        # When agent is chaos-wrapped, pre-flight must use the raw agent so we don't fail on
        # chaos-injected 503 (e.g. in CI mutation phase or chaos_only phase).
        preflight_agent = base_agent if self.config.chaos else None

        # Create orchestrator
        self.orchestrator = Orchestrator(
            config=self.config,
            agent=self.agent,
            mutation_engine=self.mutation_engine,
            verifier=self.verifier,
            console=self.console,
            preflight_agent=preflight_agent,
            show_progress=self.show_progress,
            chaos_only=chaos_only,
        )

    async def run(self) -> TestResults:
        """
        Execute the full test suite.

        Generates mutations from golden prompts, runs them against
        the agent, verifies invariants, and compiles results.
        When config.contract and chaos_matrix are present, also runs contract engine.
        """
        results = await self.orchestrator.run()
        # Dispatch to contract engine when contract + chaos_matrix present
        if self.config.contract and (
            (self.config.contract.chaos_matrix or []) or (self.config.chaos_matrix or [])
        ):
            from flakestorm.contracts.engine import ContractEngine
            from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
            base_agent = create_agent_adapter(self.config.agent)
            contract_agent = (
                create_instrumented_adapter(base_agent, self.config.chaos)
                if self.config.chaos
                else base_agent
            )
            engine = ContractEngine(self.config, self.config.contract, contract_agent)
            matrix = await engine.run()
            if self.show_progress:
                self.console.print(
                    f"[bold]Contract resilience score:[/bold] {matrix.resilience_score:.1f}%"
                )
            if results.resilience_scores is None:
                results.resilience_scores = {}
            results.resilience_scores["contract_compliance"] = matrix.resilience_score / 100.0
        return results

    async def verify_setup(self) -> bool:
        """
        Verify that all components are properly configured.

        Checks:
        - Ollama server is running and model is available
        - Agent endpoint is reachable
        - Configuration is valid

        Returns:
            True if setup is valid, False otherwise
        """
        from rich.panel import Panel

        all_ok = True

        # Check LLM connection (Ollama or API provider)
        provider = getattr(self.config.model.provider, "value", self.config.model.provider) or "ollama"
        self.console.print(f"Checking LLM connection ({provider})...", style="dim")
        llm_ok = await self.mutation_engine.verify_connection()
        if llm_ok:
            self.console.print(
                f"  [green]✓[/green] Connected to {provider} ({self.config.model.name})"
            )
        else:
            base = self.config.model.base_url or "(default)"
            self.console.print(
                f"  [red]✗[/red] Failed to connect to {provider} at {base}"
            )
            all_ok = False

        # Check agent endpoint
        self.console.print("Checking agent endpoint...", style="dim")
        try:
            response = await self.agent.invoke_with_timing("test")
            if response.success or response.error:
                self.console.print(
                    f"  [green]✓[/green] Agent endpoint reachable ({response.latency_ms:.0f}ms)"
                )
            else:
                self.console.print(
                    f"  [yellow]![/yellow] Agent returned error: {response.error}"
                )
        except Exception as e:
            self.console.print(f"  [red]✗[/red] Agent connection failed: {e}")
            all_ok = False

        # Summary
        if all_ok:
            self.console.print(
                Panel(
                    "[green]All checks passed. Ready to run tests.[/green]",
                    title="Setup Verification",
                    border_style="green",
                )
            )
        else:
            self.console.print(
                Panel(
                    "[red]Some checks failed. Please fix the issues above.[/red]",
                    title="Setup Verification",
                    border_style="red",
                )
            )

        return all_ok

    def get_config_summary(self) -> str:
        """Get a summary of the current configuration."""
        lines = [
            f"Golden Prompts: {len(self.config.golden_prompts)}",
            f"Mutations per Prompt: {self.config.mutations.count}",
            f"Mutation Types: {', '.join(t.value for t in self.config.mutations.types)}",
            f"Total Tests: {len(self.config.golden_prompts) * self.config.mutations.count}",
            f"Invariants: {len(self.config.invariants)}",
            f"Concurrency: {self.config.advanced.concurrency}",
        ]
        return "\n".join(lines)
