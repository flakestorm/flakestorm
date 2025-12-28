"""
Entropix Test Runner

High-level interface for running Entropix tests. Combines all components
and provides a simple API for executing reliability tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from entropix.core.config import EntropixConfig, load_config
from entropix.core.protocol import create_agent_adapter, BaseAgentAdapter
from entropix.core.orchestrator import Orchestrator
from entropix.mutations.engine import MutationEngine
from entropix.assertions.verifier import InvariantVerifier

if TYPE_CHECKING:
    from entropix.reports.models import TestResults


class EntropixRunner:
    """
    Main runner for Entropix tests.
    
    Provides a high-level interface for running reliability tests
    against AI agents. Handles configuration loading, component
    initialization, and test execution.
    
    Example:
        >>> config = load_config("entropix.yaml")
        >>> runner = EntropixRunner(config)
        >>> results = await runner.run()
        >>> print(f"Score: {results.statistics.robustness_score:.1%}")
    """
    
    def __init__(
        self,
        config: EntropixConfig | str | Path,
        agent: BaseAgentAdapter | None = None,
        console: Console | None = None,
        show_progress: bool = True,
    ):
        """
        Initialize the test runner.
        
        Args:
            config: Configuration object or path to config file
            agent: Optional pre-configured agent adapter
            console: Rich console for output
            show_progress: Whether to show progress bars
        """
        # Load config if path provided
        if isinstance(config, (str, Path)):
            self.config = load_config(config)
        else:
            self.config = config
        
        self.console = console or Console()
        self.show_progress = show_progress
        
        # Initialize components
        self.agent = agent or create_agent_adapter(self.config.agent)
        self.mutation_engine = MutationEngine(self.config.model)
        self.verifier = InvariantVerifier(self.config.invariants)
        
        # Create orchestrator
        self.orchestrator = Orchestrator(
            config=self.config,
            agent=self.agent,
            mutation_engine=self.mutation_engine,
            verifier=self.verifier,
            console=self.console,
            show_progress=self.show_progress,
        )
    
    async def run(self) -> "TestResults":
        """
        Execute the full test suite.
        
        Generates mutations from golden prompts, runs them against
        the agent, verifies invariants, and compiles results.
        
        Returns:
            TestResults containing all test outcomes and statistics
        """
        return await self.orchestrator.run()
    
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
        
        # Check Ollama connection
        self.console.print("Checking Ollama connection...", style="dim")
        ollama_ok = await self.mutation_engine.verify_connection()
        if ollama_ok:
            self.console.print(
                f"  [green]✓[/green] Connected to Ollama ({self.config.model.name})"
            )
        else:
            self.console.print(
                f"  [red]✗[/red] Failed to connect to Ollama at {self.config.model.base_url}"
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

