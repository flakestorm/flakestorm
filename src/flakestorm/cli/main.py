"""
flakestorm CLI Main Entry Point

Provides the main Typer application and command routing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from flakestorm import __version__
from flakestorm.core.runner import FlakeStormRunner

# Create the main app
app = typer.Typer(
    name="flakestorm",
    help="The Agent Reliability Engine - Chaos Engineering for AI Agents [Open Source Edition]",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]flakestorm[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    flakestorm - The Agent Reliability Engine

    Apply chaos engineering to your AI agents. Generate adversarial
    mutations, test reliability, and prove production readiness.
    """
    pass


@app.command()
def init(
    path: Path = typer.Argument(
        Path("flakestorm.yaml"),
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
    Initialize a new flakestorm configuration file.

    Creates an flakestorm.yaml with sensible defaults that you can
    customize for your agent.
    """
    from flakestorm.core.config import create_default_config

    if path.exists() and not force:
        console.print(
            f"[yellow]Configuration file already exists:[/yellow] {path}\n"
            "Use --force to overwrite."
        )
        raise typer.Exit(1)

    config = create_default_config()
    yaml_content = config.to_yaml()

    path.write_text(yaml_content, encoding="utf-8")

    console.print(
        Panel(
            f"[green]✓ Created configuration file:[/green] {path}\n\n"
            "Next steps:\n"
            "1. Edit the file to configure your agent endpoint\n"
            "2. Add your golden prompts\n"
            "3. Run: [bold]flakestorm run[/bold]",
            title="flakestorm Initialized",
            border_style="green",
        )
    )


@app.command()
def run(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
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
    min_score: float | None = typer.Option(
        None,
        "--min-score",
        help="Minimum score to pass",
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help="Exit with error code if score is below min-score",
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
    chaos: bool = typer.Option(
        False,
        "--chaos",
        help="Enable environment chaos (tool/LLM faults) for this run",
    ),
    chaos_profile: str | None = typer.Option(
        None,
        "--chaos-profile",
        help="Use built-in chaos profile (e.g. api_outage, degraded_llm)",
    ),
    chaos_only: bool = typer.Option(
        False,
        "--chaos-only",
        help="Run only chaos tests (no mutation generation)",
    ),
) -> None:
    """
    Run chaos testing against your agent.

    Generates adversarial mutations from your golden prompts,
    runs them against your agent, and produces a reliability report.
    """
    asyncio.run(
        _run_async(
            config=config,
            output=output,
            min_score=min_score,
            ci=ci,
            verify_only=verify_only,
            quiet=quiet,
            chaos=chaos,
            chaos_profile=chaos_profile,
            chaos_only=chaos_only,
        )
    )


async def _run_async(
    config: Path,
    output: str,
    min_score: float | None,
    ci: bool,
    verify_only: bool,
    quiet: bool,
    chaos: bool = False,
    chaos_profile: str | None = None,
    chaos_only: bool = False,
) -> None:
    """Async implementation of the run command."""
    from flakestorm.reports.html import HTMLReportGenerator
    from flakestorm.reports.json_export import JSONReportGenerator
    from flakestorm.reports.terminal import TerminalReporter

    # Print header
    if not quiet:
        console.print()
        console.print(
            f"[bold blue]flakestorm[/bold blue] - Agent Reliability Engine v{__version__}"
        )
        console.print()

    # Load configuration and apply chaos flags
    try:
        runner = FlakeStormRunner(
            config=config,
            console=console,
            show_progress=not quiet,
            chaos=chaos,
            chaos_profile=chaos_profile,
            chaos_only=chaos_only,
        )
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[dim]Run 'flakestorm init' to create a configuration file.[/dim]"
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
        html_gen = HTMLReportGenerator(results)
        report_path = html_gen.save()
        if not quiet:
            console.print()
            TerminalReporter(results, console).print_summary()
            console.print()
            console.print(f"[green]Report saved to:[/green] {report_path}")
    elif output == "json":
        json_gen = JSONReportGenerator(results)
        report_path = json_gen.save()
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
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Verify that flakestorm is properly configured.

    Checks:
    - Ollama server is running and model is available
    - Agent endpoint is reachable
    - Configuration file is valid
    """
    asyncio.run(_verify_async(config))


async def _verify_async(config: Path) -> None:
    """Async implementation of verify command."""

    console.print()
    console.print("[bold blue]flakestorm[/bold blue] - Setup Verification")
    console.print()

    try:
        runner = FlakeStormRunner(
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

    from flakestorm.core.config import create_default_config
    from flakestorm.mutations.types import Mutation
    from flakestorm.reports.html import HTMLReportGenerator
    from flakestorm.reports.models import (
        CheckResult,
        MutationResult,
        TestResults,
        TestStatistics,
        TypeStatistics,
    )
    from flakestorm.reports.terminal import TerminalReporter

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
    by_type = [TypeStatistics(**t) for t in stats_data.get("by_type", [])]

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
        checks = [CheckResult(**c) for c in m_data.get("checks", [])]
        mutations.append(
            MutationResult(
                original_prompt=m_data.get("original_prompt", ""),
                mutation=mutation,
                response=m_data.get("response", ""),
                latency_ms=m_data.get("latency_ms", 0),
                passed=m_data.get("passed", False),
                checks=checks,
                error=m_data.get("error"),
            )
        )

    results = TestResults(
        config=create_default_config(),
        started_at=datetime.fromisoformat(
            data.get("started_at", datetime.now().isoformat())
        ),
        completed_at=datetime.fromisoformat(
            data.get("completed_at", datetime.now().isoformat())
        ),
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
        Path("flakestorm.yaml"),
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

    try:
        runner = FlakeStormRunner(
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


# --- V2: chaos, contract, replay, ci ---

@app.command()
def chaos_cmd(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Built-in chaos profile name",
    ),
) -> None:
    """Run environment chaos testing (tool/LLM faults) only."""
    asyncio.run(_chaos_async(config, profile))


async def _chaos_async(config: Path, profile: str | None) -> None:
    from flakestorm.core.config import load_config
    from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
    cfg = load_config(config)
    agent = create_agent_adapter(cfg.agent)
    if cfg.chaos:
        agent = create_instrumented_adapter(agent, cfg.chaos)
    console.print("[bold blue]Chaos run[/bold blue] (v2) - use flakestorm run --chaos for full flow.")
    console.print("[dim]Chaos module active.[/dim]")


contract_app = typer.Typer(help="Behavioral contract (v2): run, validate, score")

@contract_app.command("run")
def contract_run(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save HTML report to this path (e.g. ./reports/contract-report.html)",
    ),
) -> None:
    """Run behavioral contract across chaos matrix."""
    asyncio.run(_contract_async(config, validate=False, score_only=False, output_path=output))

@contract_app.command("validate")
def contract_validate(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Validate contract YAML without executing."""
    asyncio.run(_contract_async(config, validate=True, score_only=False))

@contract_app.command("score")
def contract_score(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Output only the resilience score (for CI gates)."""
    asyncio.run(_contract_async(config, validate=False, score_only=True))

app.add_typer(contract_app, name="contract")


async def _contract_async(
    config: Path, validate: bool, score_only: bool, output_path: str | None = None
) -> None:
    from rich.progress import SpinnerColumn, TextColumn, Progress

    from flakestorm.core.config import load_config
    from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
    from flakestorm.contracts.engine import ContractEngine
    from flakestorm.reports.contract_report import save_contract_report

    cfg = load_config(config)
    if not cfg.contract:
        console.print("[yellow]No contract defined in config.[/yellow]")
        raise typer.Exit(0)
    if validate:
        console.print("[green]Contract YAML valid.[/green]")
        raise typer.Exit(0)
    agent = create_agent_adapter(cfg.agent)
    if cfg.chaos:
        agent = create_instrumented_adapter(agent, cfg.chaos)
    invariants = cfg.contract.invariants or []
    scenarios = cfg.contract.chaos_matrix or []
    num_cells = len(invariants) * len(scenarios) if scenarios else len(invariants)
    console.print(f"[dim]Contract: {len(invariants)} invariant(s) × {len(scenarios)} scenario(s) = {num_cells} cells[/dim]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running contract matrix...", total=None)
        engine = ContractEngine(cfg, cfg.contract, agent)
        matrix = await engine.run()
        progress.update(task, completed=1)
    if score_only:
        print(f"{matrix.resilience_score:.2f}")
    else:
        console.print(f"[bold]Resilience score:[/bold] {matrix.resilience_score:.1f}%")
        console.print(f"[bold]Passed:[/bold] {matrix.passed}")
        if output_path:
            out = save_contract_report(matrix, output_path)
            console.print(f"[green]Report saved to:[/green] {out}")


replay_app = typer.Typer(help="Replay sessions: run, import, export (v2)")

@replay_app.command("run")
def replay_run(
    path: Path = typer.Argument(None, help="Path to replay file or directory"),
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    from_langsmith: str | None = typer.Option(None, "--from-langsmith", help="LangSmith run ID"),
    from_langsmith_project: str | None = typer.Option(
        None,
        "--from-langsmith-project",
        help="Import runs from a LangSmith project (filter by status, then write to --output)",
    ),
    filter_status: str = typer.Option(
        "error",
        "--filter-status",
        help="When using --from-langsmith-project: error | warning | all",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="When importing: output file/dir for YAML; when running: path to save HTML report",
    ),
    run_after_import: bool = typer.Option(False, "--run", help="Run replay(s) after import"),
) -> None:
    """Run or import replay sessions."""
    asyncio.run(
        _replay_async(
            path, config, from_langsmith, from_langsmith_project,
            filter_status, output, run_after_import,
        )
    )


@replay_app.command("export")
def replay_export(
    from_report: Path = typer.Option(..., "--from-report", help="JSON report file from flakestorm run"),
    output: Path = typer.Option(Path("./replays"), "--output", "-o", help="Output directory"),
) -> None:
    """Export failed mutations from a report as replay session YAML files."""
    import json
    import yaml
    if not from_report.exists():
        console.print(f"[red]Report not found:[/red] {from_report}")
        raise typer.Exit(1)
    data = json.loads(from_report.read_text(encoding="utf-8"))
    mutations = data.get("mutations", [])
    failed = [m for m in mutations if not m.get("passed", True)]
    if not failed:
        console.print("[yellow]No failed mutations in report.[/yellow]")
        raise typer.Exit(0)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(failed):
        session = {
            "id": f"export-{i}",
            "name": f"Exported failure: {m.get('mutation', {}).get('type', 'unknown')}",
            "source": "flakestorm_export",
            "input": m.get("original_prompt", ""),
            "tool_responses": [],
            "expected_failure": m.get("error") or "One or more invariants failed",
            "contract": "default",
        }
        out_path = output / f"replay-{i}.yaml"
        out_path.write_text(yaml.dump(session, default_flow_style=False, sort_keys=False), encoding="utf-8")
        console.print(f"[green]Wrote[/green] {out_path}")
    console.print(f"[bold]Exported {len(failed)} replay session(s).[/bold]")


app.add_typer(replay_app, name="replay")




async def _replay_async(
    path: Path | None,
    config: Path,
    from_langsmith: str | None,
    from_langsmith_project: str | None,
    filter_status: str,
    output: Path | None,
    run_after_import: bool,
) -> None:
    import yaml
    from flakestorm.core.config import load_config
    from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
    from flakestorm.replay.loader import ReplayLoader, resolve_contract
    from flakestorm.replay.runner import ReplayResult, ReplayRunner
    cfg = load_config(config)
    agent = create_agent_adapter(cfg.agent)
    if cfg.chaos:
        agent = create_instrumented_adapter(agent, cfg.chaos)
    loader = ReplayLoader()

    if from_langsmith_project:
        sessions = loader.load_langsmith_project(
            project_name=from_langsmith_project,
            filter_status=filter_status,
        )
        console.print(f"[green]Imported {len(sessions)} replay(s) from LangSmith project.[/green]")
        out_path = Path(output) if output else Path("./replays")
        out_path.mkdir(parents=True, exist_ok=True)
        for i, session in enumerate(sessions):
            safe_id = (session.id or str(i)).replace("/", "_").replace("\\", "_")[:64]
            fpath = out_path / f"replay-{safe_id}.yaml"
            fpath.write_text(
                yaml.dump(
                    session.model_dump(mode="json", exclude_none=True),
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            console.print(f"  [dim]Wrote[/dim] {fpath}")
        if run_after_import and sessions:
            contract = None
            try:
                contract = resolve_contract(sessions[0].contract, cfg, config.parent)
            except FileNotFoundError:
                pass
            runner = ReplayRunner(agent, contract=contract)
            passed = 0
            for session in sessions:
                result = await runner.run(session, contract=contract)
                if result.passed:
                    passed += 1
            console.print(f"[bold]Replay results:[/bold] {passed}/{len(sessions)} passed")
        raise typer.Exit(0)

    if from_langsmith:
        session = loader.load_langsmith_run(from_langsmith)
        console.print(f"[green]Imported replay:[/green] {session.id}")
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                yaml.dump(
                    session.model_dump(mode="json", exclude_none=True),
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            console.print(f"[dim]Wrote[/dim] {out_path}")
        if run_after_import:
            contract = None
            try:
                contract = resolve_contract(session.contract, cfg, config.parent)
            except FileNotFoundError:
                pass
            runner = ReplayRunner(agent, contract=contract)
            replay_result = await runner.run(session, contract=contract)
            console.print(f"[bold]Replay result:[/bold] passed={replay_result.passed}")
            console.print(f"[dim]Response:[/dim] {(replay_result.response.output or '')[:200]}...")
        raise typer.Exit(0)

    if path and path.exists() and path.is_file():
        session = loader.load_file(path)
        contract = None
        try:
            contract = resolve_contract(session.contract, cfg, path.parent)
        except FileNotFoundError as e:
            console.print(f"[yellow]{e}[/yellow]")
        runner = ReplayRunner(agent, contract=contract)
        replay_result = await runner.run(session, contract=contract)
        console.print(f"[bold]Replay result:[/bold] passed={replay_result.passed}")
        if replay_result.verification_details:
            console.print(f"[dim]Checks:[/dim] {', '.join(replay_result.verification_details)}")
        if output:
            from flakestorm.reports.replay_report import save_replay_report
            report_results = [{
                "id": session.id,
                "name": session.name or session.id,
                "passed": replay_result.passed,
                "verification_details": replay_result.verification_details or [],
                "expected_failure": getattr(session, "expected_failure", None),
            }]
            out_path = save_replay_report(report_results, output)
            console.print(f"[green]Report saved to:[/green] {out_path}")
    elif path and path.exists() and path.is_dir():
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from flakestorm.replay.loader import resolve_sessions_from_config
        from flakestorm.reports.replay_report import save_replay_report
        replay_files = sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml")) + sorted(path.glob("*.json"))
        replay_files = [f for f in replay_files if f.is_file()]
        if not replay_files:
            console.print("[yellow]No replay YAML/JSON files in directory.[/yellow]")
        else:
            report_results = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Running replay sessions...", total=len(replay_files))
                for fpath in replay_files:
                    session = loader.load_file(fpath)
                    contract = None
                    try:
                        contract = resolve_contract(session.contract, cfg, fpath.parent)
                    except FileNotFoundError:
                        pass
                    runner = ReplayRunner(agent, contract=contract)
                    replay_result = await runner.run(session, contract=contract)
                    report_results.append({
                        "id": session.id,
                        "name": session.name or session.id,
                        "passed": replay_result.passed,
                        "verification_details": replay_result.verification_details or [],
                        "expected_failure": getattr(session, "expected_failure", None),
                    })
                    progress.update(task, advance=1)
            passed = sum(1 for r in report_results if r["passed"])
            console.print(f"[bold]Replay results:[/bold] {passed}/{len(report_results)} passed")
            if output:
                out_path = save_replay_report(report_results, output)
                console.print(f"[green]Report saved to:[/green] {out_path}")
    else:
        console.print(
            "[yellow]Provide a replay file path, --from-langsmith RUN_ID, or --from-langsmith-project PROJECT.[/yellow]"
        )


@app.command()
def ci(
    config: Path = typer.Option(
        Path("flakestorm.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    min_score: float = typer.Option(0.0, "--min-score", help="Minimum overall score"),
) -> None:
    """Run all configured modes and output unified exit code (v2)."""
    asyncio.run(_ci_async(config, min_score))


async def _ci_async(config: Path, min_score: float) -> None:
    from flakestorm.core.config import load_config
    cfg = load_config(config)
    exit_code = 0
    scores = {}
    phases = ["mutation"]
    if cfg.contract:
        phases.append("contract")
    if cfg.chaos:
        phases.append("chaos")
    if cfg.replays and (cfg.replays.sessions or cfg.replays.sources):
        phases.append("replay")
    n_phases = len(phases)

    # Run mutation tests
    idx = phases.index("mutation") + 1 if "mutation" in phases else 0
    console.print(f"[bold blue][{idx}/{n_phases}] Mutation[/bold blue]")
    runner = FlakeStormRunner(config=config, console=console, show_progress=False)
    results = await runner.run()
    mutation_score = results.statistics.robustness_score
    scores["mutation_robustness"] = mutation_score
    console.print(f"[bold]Mutation score:[/bold] {mutation_score:.1%}")
    if mutation_score < min_score:
        exit_code = 1

    # Contract
    contract_score = 1.0
    if cfg.contract:
        idx = phases.index("contract") + 1
        console.print(f"[bold blue][{idx}/{n_phases}] Contract[/bold blue]")
        from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
        from flakestorm.contracts.engine import ContractEngine
        agent = create_agent_adapter(cfg.agent)
        if cfg.chaos:
            agent = create_instrumented_adapter(agent, cfg.chaos)
        engine = ContractEngine(cfg, cfg.contract, agent)
        matrix = await engine.run()
        contract_score = matrix.resilience_score / 100.0
        scores["contract_compliance"] = contract_score
        console.print(f"[bold]Contract score:[/bold] {matrix.resilience_score:.1f}%")
        if not matrix.passed or matrix.resilience_score < min_score * 100:
            exit_code = 1

    # Chaos-only run when chaos configured
    chaos_score = 1.0
    if cfg.chaos:
        idx = phases.index("chaos") + 1
        console.print(f"[bold blue][{idx}/{n_phases}] Chaos[/bold blue]")
        chaos_runner = FlakeStormRunner(
            config=config, console=console, show_progress=False,
            chaos_only=True, chaos=True,
        )
        chaos_results = await chaos_runner.run()
        chaos_score = chaos_results.statistics.robustness_score
        scores["chaos_resilience"] = chaos_score
        console.print(f"[bold]Chaos score:[/bold] {chaos_score:.1%}")
        if chaos_score < min_score:
            exit_code = 1

    # Replay sessions (from replays.sessions and replays.sources with auto_import)
    replay_score = 1.0
    if cfg.replays and (cfg.replays.sessions or cfg.replays.sources):
        idx = phases.index("replay") + 1
        console.print(f"[bold blue][{idx}/{n_phases}] Replay[/bold blue]")
        from flakestorm.core.protocol import create_agent_adapter, create_instrumented_adapter
        from flakestorm.replay.loader import resolve_contract, resolve_sessions_from_config
        from flakestorm.replay.runner import ReplayRunner
        agent = create_agent_adapter(cfg.agent)
        if cfg.chaos:
            agent = create_instrumented_adapter(agent, cfg.chaos)
        config_path = Path(config)
        sessions = resolve_sessions_from_config(
            cfg.replays, config_path.parent, include_sources=True
        )
        if sessions:
            passed = 0
            total = 0
            for session in sessions:
                contract = None
                try:
                    contract = resolve_contract(session.contract, cfg, config_path.parent)
                except FileNotFoundError:
                    pass
                runner = ReplayRunner(agent, contract=contract)
                result = await runner.run(session, contract=contract)
                total += 1
                if result.passed:
                    passed += 1
            replay_score = passed / total if total else 1.0
            scores["replay_regression"] = replay_score
            console.print(f"[bold]Replay score:[/bold] {replay_score:.1%} ({passed}/{total})")
            if replay_score < min_score:
                exit_code = 1

    # Overall weighted score (only for components that ran)
    from flakestorm.core.config import ScoringConfig
    from flakestorm.core.performance import calculate_overall_resilience
    scoring = cfg.scoring or ScoringConfig()
    w = {"mutation_robustness": scoring.mutation, "chaos_resilience": scoring.chaos, "contract_compliance": scoring.contract, "replay_regression": scoring.replay}
    used_w = [w[k] for k in scores if k in w]
    used_s = [scores[k] for k in scores if k in w]
    overall = calculate_overall_resilience(used_s, used_w)
    console.print(f"[bold]Overall (weighted):[/bold] {overall:.1%}")
    if overall < min_score:
        exit_code = 1
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    app()
