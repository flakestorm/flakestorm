"""
Entropix CLI Main Entry Point

Provides the main Typer application and command routing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from entropix import __version__

# Create the main app
app = typer.Typer(
    name="entropix",
    help="The Agent Reliability Engine - Chaos Engineering for AI Agents",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]Entropix[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    Entropix - The Agent Reliability Engine
    
    Apply chaos engineering to your AI agents. Generate adversarial
    mutations, test reliability, and prove production readiness.
    """
    pass


@app.command()
def init(
    path: Path = typer.Argument(
        Path("entropix.yaml"),
        help="Path for the configuration file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
) -> None:
    """
    Initialize a new Entropix configuration file.
    
    Creates an entropix.yaml with sensible defaults that you can
    customize for your agent.
    """
    from entropix.core.config import create_default_config
    
    if path.exists() and not force:
        console.print(
            f"[yellow]Configuration file already exists:[/yellow] {path}\n"
            "Use --force to overwrite."
        )
        raise typer.Exit(1)
    
    config = create_default_config()
    yaml_content = config.to_yaml()
    
    path.write_text(yaml_content, encoding="utf-8")
    
    console.print(Panel(
        f"[green]✓ Created configuration file:[/green] {path}\n\n"
        "Next steps:\n"
        "1. Edit the file to configure your agent endpoint\n"
        "2. Add your golden prompts\n"
        "3. Run: [bold]entropix run[/bold]",
        title="Entropix Initialized",
        border_style="green",
    ))


@app.command()
def run(
    config: Path = typer.Option(
        Path("entropix.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    output: str = typer.Option(
        "html",
        "--output",
        "-o",
        help="Output format: html, json, terminal",
    ),
    min_score: Optional[float] = typer.Option(
        None,
        "--min-score",
        help="Minimum score to pass (for CI/CD)",
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help="CI mode: exit with error if below min-score",
    ),
    verify_only: bool = typer.Option(
        False,
        "--verify-only",
        help="Only verify setup, don't run tests",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output",
    ),
) -> None:
    """
    Run chaos testing against your agent.
    
    Generates adversarial mutations from your golden prompts,
    runs them against your agent, and produces a reliability report.
    """
    asyncio.run(_run_async(
        config=config,
        output=output,
        min_score=min_score,
        ci=ci,
        verify_only=verify_only,
        quiet=quiet,
    ))


async def _run_async(
    config: Path,
    output: str,
    min_score: Optional[float],
    ci: bool,
    verify_only: bool,
    quiet: bool,
) -> None:
    """Async implementation of the run command."""
    from entropix.core.runner import EntropixRunner
    from entropix.reports.html import HTMLReportGenerator
    from entropix.reports.json_export import JSONReportGenerator
    from entropix.reports.terminal import TerminalReporter
    
    # Print header
    if not quiet:
        console.print()
        console.print(
            f"[bold blue]Entropix[/bold blue] - Agent Reliability Engine v{__version__}"
        )
        console.print()
    
    # Load configuration
    try:
        runner = EntropixRunner(
            config=config,
            console=console,
            show_progress=not quiet,
        )
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[dim]Run 'entropix init' to create a configuration file.[/dim]"
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    
    # Print config summary
    if not quiet:
        console.print(f"[dim]Loading configuration from {config}[/dim]")
        console.print(f"[dim]{runner.get_config_summary()}[/dim]")
        console.print()
    
    # Verify setup if requested
    if verify_only:
        setup_ok = await runner.verify_setup()
        raise typer.Exit(0 if setup_ok else 1)
    
    # Run tests
    try:
        results = await runner.run()
    except Exception as e:
        console.print(f"[red]Test execution failed:[/red] {e}")
        raise typer.Exit(1)
    
    # Generate reports
    if output == "html":
        generator = HTMLReportGenerator(results)
        report_path = generator.save()
        if not quiet:
            console.print()
            TerminalReporter(results, console).print_summary()
            console.print()
            console.print(f"[green]Report saved to:[/green] {report_path}")
    elif output == "json":
        generator = JSONReportGenerator(results)
        report_path = generator.save()
        if not quiet:
            console.print(f"[green]Report saved to:[/green] {report_path}")
    else:  # terminal
        TerminalReporter(results, console).print_full_report()
    
    # Check minimum score for CI
    score = results.statistics.robustness_score
    if ci and min_score is not None:
        if score < min_score:
            console.print(
                f"\n[red]CI FAILED:[/red] Score {score:.1%} < {min_score:.1%} threshold"
            )
            raise typer.Exit(1)
        else:
            console.print(
                f"\n[green]CI PASSED:[/green] Score {score:.1%} >= {min_score:.1%} threshold"
            )


@app.command()
def verify(
    config: Path = typer.Option(
        Path("entropix.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Verify that Entropix is properly configured.
    
    Checks:
    - Ollama server is running and model is available
    - Agent endpoint is reachable
    - Configuration file is valid
    """
    asyncio.run(_verify_async(config))


async def _verify_async(config: Path) -> None:
    """Async implementation of verify command."""
    from entropix.core.runner import EntropixRunner
    
    console.print()
    console.print(
        f"[bold blue]Entropix[/bold blue] - Setup Verification"
    )
    console.print()
    
    try:
        runner = EntropixRunner(
            config=config,
            console=console,
            show_progress=False,
        )
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    
    setup_ok = await runner.verify_setup()
    raise typer.Exit(0 if setup_ok else 1)


@app.command()
def report(
    path: Path = typer.Argument(
        ...,
        help="Path to JSON report file",
    ),
    output: str = typer.Option(
        "terminal",
        "--output",
        "-o",
        help="Output format: terminal, html",
    ),
) -> None:
    """
    View or convert a previous test report.
    
    Load a JSON report and display it or convert to HTML.
    """
    import json
    from datetime import datetime
    from entropix.core.config import EntropixConfig, create_default_config
    from entropix.reports.models import (
        TestResults, TestStatistics, MutationResult, 
        CheckResult, TypeStatistics
    )
    from entropix.mutations.types import Mutation, MutationType
    from entropix.reports.html import HTMLReportGenerator
    from entropix.reports.terminal import TerminalReporter
    
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)
    
    # Reconstruct results from JSON
    # This is a simplified reconstruction
    console.print(f"[dim]Loading report from {path}...[/dim]")
    
    stats_data = data.get("statistics", {})
    by_type = [
        TypeStatistics(**t) for t in stats_data.get("by_type", [])
    ]
    
    statistics = TestStatistics(
        total_mutations=stats_data.get("total_mutations", 0),
        passed_mutations=stats_data.get("passed_mutations", 0),
        failed_mutations=stats_data.get("failed_mutations", 0),
        robustness_score=stats_data.get("robustness_score", 0),
        avg_latency_ms=stats_data.get("avg_latency_ms", 0),
        p50_latency_ms=stats_data.get("p50_latency_ms", 0),
        p95_latency_ms=stats_data.get("p95_latency_ms", 0),
        p99_latency_ms=stats_data.get("p99_latency_ms", 0),
        duration_seconds=stats_data.get("duration_seconds", 0),
        by_type=by_type,
    )
    
    mutations = []
    for m_data in data.get("mutations", []):
        mutation = Mutation.from_dict(m_data.get("mutation", {}))
        checks = [
            CheckResult(**c) for c in m_data.get("checks", [])
        ]
        mutations.append(MutationResult(
            original_prompt=m_data.get("original_prompt", ""),
            mutation=mutation,
            response=m_data.get("response", ""),
            latency_ms=m_data.get("latency_ms", 0),
            passed=m_data.get("passed", False),
            checks=checks,
            error=m_data.get("error"),
        ))
    
    results = TestResults(
        config=create_default_config(),
        started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
        completed_at=datetime.fromisoformat(data.get("completed_at", datetime.now().isoformat())),
        mutations=mutations,
        statistics=statistics,
    )
    
    if output == "html":
        generator = HTMLReportGenerator(results)
        html_path = path.with_suffix(".html")
        generator.save(html_path)
        console.print(f"[green]HTML report saved to:[/green] {html_path}")
    else:
        TerminalReporter(results, console).print_full_report()


@app.command()
def score(
    config: Path = typer.Option(
        Path("entropix.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Run tests and output only the robustness score.
    
    Useful for CI/CD scripts that need to parse the score.
    """
    asyncio.run(_score_async(config))


async def _score_async(config: Path) -> None:
    """Async implementation of score command."""
    from entropix.core.runner import EntropixRunner
    
    try:
        runner = EntropixRunner(
            config=config,
            console=console,
            show_progress=False,
        )
        results = await runner.run()
        # Output just the score as a decimal (0.0-1.0)
        print(f"{results.statistics.robustness_score:.4f}")
    except Exception as e:
        console.print(f"Error: {e}", style="red", file=sys.stderr)
        print("0.0")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

