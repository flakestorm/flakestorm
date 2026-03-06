"""HTML report for contract resilience matrix (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flakestorm.contracts.matrix import ResilienceMatrix


def generate_contract_html(matrix: ResilienceMatrix, title: str = "Contract Resilience Report") -> str:
    """Generate HTML for the contract × chaos matrix."""
    rows = []
    for c in matrix.cell_results:
        status = "PASS" if c.passed else "FAIL"
        rows.append(f"<tr><td>{c.invariant_id}</td><td>{c.scenario_name}</td><td>{c.severity}</td><td>{status}</td></tr>")
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p><strong>Resilience score:</strong> {matrix.resilience_score:.1f}%</p>
<p><strong>Overall:</strong> {"PASS" if matrix.passed else "FAIL"}</p>
<table border="1">
<tr><th>Invariant</th><th>Scenario</th><th>Severity</th><th>Result</th></tr>
{body}
</table>
</body>
</html>"""


def save_contract_report(matrix: ResilienceMatrix, path: str | Path, title: str = "Contract Resilience Report") -> Path:
    """Write contract report HTML to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_contract_html(matrix, title), encoding="utf-8")
    return path
