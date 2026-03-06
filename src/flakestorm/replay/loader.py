"""
Replay loader: load replay sessions from YAML/JSON or LangSmith.

Contract reference resolution: by name (main config) then by file path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from flakestorm.core.config import ContractConfig, ReplaySessionConfig

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

    def load_langsmith_run(self, run_id: str) -> ReplaySessionConfig:
        """
        Load a LangSmith run as a replay session. Requires langsmith>=0.1.0.
        Target API: /api/v1/runs/{run_id}
        Fails clearly if LangSmith schema has changed (expected fields missing).
        """
        try:
            from langsmith import Client
        except ImportError as e:
            raise ImportError(
                "LangSmith import requires: pip install flakestorm[langsmith] or pip install langsmith"
            ) from e
        client = Client()
        run = client.read_run(run_id)
        self._validate_langsmith_run_schema(run)
        return self._langsmith_run_to_session(run)

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
