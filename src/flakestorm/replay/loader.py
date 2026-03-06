"""
Replay loader: load replay sessions from YAML/JSON or LangSmith.

Contract reference resolution: by name (main config) then by file path.
LangSmith: single run by ID or project listing with filters (Addition 5).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from flakestorm.core.config import (
    ContractConfig,
    LangSmithProjectFilterConfig,
    LangSmithProjectSourceConfig,
    LangSmithRunSourceConfig,
    ReplayConfig,
    ReplaySessionConfig,
)

if TYPE_CHECKING:
    from flakestorm.core.config import FlakeStormConfig


def resolve_contract(
    contract_ref: str,
    main_config: FlakeStormConfig | None,
    config_dir: Path | None = None,
) -> ContractConfig:
    """
    Resolve contract by name (from main config) or by file path.
    Order: (1) contract name in main config, (2) file path, (3) fail.
    """
    if main_config and main_config.contract and main_config.contract.name == contract_ref:
        return main_config.contract
    path = Path(contract_ref)
    if not path.is_absolute() and config_dir:
        path = config_dir / path
    if path.exists():
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if path.suffix.lower() in (".yaml", ".yml") else json.loads(text)
        return ContractConfig.model_validate(data)
    raise FileNotFoundError(
        f"Contract not found: {contract_ref}. "
        "Define it in main config (contract.name) or provide a path to a contract file."
    )


class ReplayLoader:
    """Load replay sessions from files or LangSmith."""

    def load_file(self, path: str | Path) -> ReplaySessionConfig:
        """Load a single replay session from YAML or JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Replay file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".json",):
            data = json.loads(text)
        else:
            import yaml
            data = yaml.safe_load(text)
        return ReplaySessionConfig.model_validate(data)

    def _get_langsmith_client(self) -> Any:
        """Return LangSmith Client; raise ImportError if langsmith not installed."""
        try:
            from langsmith import Client
        except ImportError as e:
            raise ImportError(
                "LangSmith requires: pip install flakestorm[langsmith] or pip install langsmith"
            ) from e
        return Client()

    def load_langsmith_run(self, run_id: str) -> ReplaySessionConfig:
        """
        Load a LangSmith run as a replay session. Requires langsmith>=0.1.0.
        Target API: /api/v1/runs/{run_id}
        Fails clearly if LangSmith schema has changed (expected fields missing).
        """
        client = self._get_langsmith_client()
        run = client.read_run(run_id)
        self._validate_langsmith_run_schema(run)
        return self._langsmith_run_to_session(run)

    def load_langsmith_project(
        self,
        project_name: str,
        filter_status: str = "error",
        date_range: str | None = None,
        min_latency_ms: int | None = None,
        limit: int = 200,
    ) -> list[ReplaySessionConfig]:
        """
        Load runs from a LangSmith project as replay sessions. Requires langsmith>=0.1.0.
        Uses list_runs(project_name=..., error=..., start_time=..., filter=..., limit=...).
        Each run is fetched fully (read_run) to get child_runs for tool_responses.
        """
        client = self._get_langsmith_client()
        # Build list_runs kwargs
        error_filter: bool | None = None
        if filter_status == "error":
            error_filter = True
        elif filter_status == "all":
            error_filter = None
        else:
            # "warning" or unknown: treat as non-error runs
            error_filter = False
        start_time: datetime | None = None
        if date_range:
            date_range_lower = date_range.strip().lower().replace("-", "_")
            if "7" in date_range_lower and "day" in date_range_lower:
                start_time = datetime.now(timezone.utc) - timedelta(days=7)
            elif "24" in date_range_lower and ("hour" in date_range_lower or "day" in date_range_lower):
                start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            elif "30" in date_range_lower and "day" in date_range_lower:
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
        filter_str: str | None = None
        if min_latency_ms is not None and min_latency_ms > 0:
            # LangSmith filter uses seconds for latency
            latency_sec = min_latency_ms / 1000.0
            filter_str = f"gt(latency, {latency_sec})"
        runs_iterator = client.list_runs(
            project_name=project_name,
            error=error_filter,
            start_time=start_time,
            filter=filter_str,
            limit=limit,
            is_root=True,
        )
        sessions: list[ReplaySessionConfig] = []
        for run in runs_iterator:
            run_id = str(getattr(run, "id", ""))
            if not run_id:
                continue
            full_run = client.read_run(run_id)
            self._validate_langsmith_run_schema(full_run)
            sessions.append(self._langsmith_run_to_session(full_run))
        return sessions

    def _validate_langsmith_run_schema(self, run: Any) -> None:
        """Check that run has expected schema; fail clearly if LangSmith API changed."""
        required = ("id", "inputs", "outputs")
        missing = [k for k in required if not hasattr(run, k)]
        if missing:
            raise ValueError(
                f"LangSmith run schema unexpected: missing attributes {missing}. "
                "The LangSmith API may have changed. Pin langsmith>=0.1.0 and check compatibility."
            )
        if not isinstance(getattr(run, "inputs", None), dict) and run.inputs is not None:
            raise ValueError(
                "LangSmith run.inputs must be a dict. Schema may have changed."
            )

    def _langsmith_run_to_session(self, run: Any) -> ReplaySessionConfig:
        """Map LangSmith run to ReplaySessionConfig."""
        inputs = run.inputs or {}
        outputs = run.outputs or {}
        child_runs = getattr(run, "child_runs", None) or []
        tool_responses = []
        for cr in child_runs:
            name = getattr(cr, "name", "") or ""
            out = getattr(cr, "outputs", None)
            err = getattr(cr, "error", None)
            tool_responses.append({
                "tool": name,
                "response": out,
                "status": 0 if err else 200,
            })
        return ReplaySessionConfig(
            id=str(run.id),
            name=getattr(run, "name", None),
            source="langsmith",
            input=inputs.get("input", ""),
            tool_responses=tool_responses,
            contract="default",
        )


def resolve_sessions_from_config(
    replays: ReplayConfig | None,
    config_dir: Path | None = None,
    *,
    include_sources: bool = True,
) -> list[ReplaySessionConfig]:
    """
    Build full list of replay sessions from config: inline sessions, file-backed
    sessions (loaded from disk), and optionally sessions from replays.sources
    (LangSmith run_id or project with auto_import).
    """
    if not replays:
        return []
    loader = ReplayLoader()
    out: list[ReplaySessionConfig] = []
    for s in replays.sessions:
        if s.file:
            path = Path(s.file)
            if not path.is_absolute() and config_dir:
                path = config_dir / path
            out.append(loader.load_file(path))
        else:
            out.append(s)
    if not include_sources or not replays.sources:
        return out
    for src in replays.sources:
        if isinstance(src, LangSmithRunSourceConfig):
            out.append(loader.load_langsmith_run(src.run_id))
        elif isinstance(src, LangSmithProjectSourceConfig) and src.auto_import:
            filt = src.filter
            filter_status = filt.status if filt else "error"
            date_range = filt.date_range if filt else None
            min_latency_ms = filt.min_latency_ms if filt else None
            out.extend(
                loader.load_langsmith_project(
                    project_name=src.project,
                    filter_status=filter_status,
                    date_range=date_range,
                    min_latency_ms=min_latency_ms,
                )
            )
    return out
