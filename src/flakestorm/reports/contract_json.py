"""JSON export for contract resilience matrix (v2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flakestorm.contracts.matrix import ResilienceMatrix


def export_contract_json(matrix: ResilienceMatrix, path: str | Path) -> Path:
    """Export contract matrix to JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "resilience_score": matrix.resilience_score,
        "passed": matrix.passed,
        "critical_failed": matrix.critical_failed,
        "cells": [
            {
                "invariant_id": c.invariant_id,
                "scenario_name": c.scenario_name,
                "severity": c.severity,
                "passed": c.passed,
            }
            for c in matrix.cell_results
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
