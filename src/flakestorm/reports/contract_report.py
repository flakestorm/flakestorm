"""HTML report for contract resilience matrix (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flakestorm.contracts.matrix import CellResult, ResilienceMatrix


def _suggested_action_for_cell(c: "CellResult") -> str:
    """Return a suggested action for a failed contract cell."""
    scenario_lower = (c.scenario_name or "").lower()
    sev = (c.severity or "").lower()
    inv = c.invariant_id or ""

    if "tool" in scenario_lower or "timeout" in scenario_lower or "error" in scenario_lower:
        return (
            "Harden agent behavior when tools fail: ensure the agent does not fabricate data, "
            "and returns a clear 'data unavailable' or error message when tools return errors or timeouts."
        )
    if "llm" in scenario_lower or "truncat" in scenario_lower or "degraded" in scenario_lower:
        return (
            "Handle degraded LLM responses: ensure the agent detects truncated or empty responses "
            "and does not hallucinate; add fallbacks or user-facing error messages."
        )
    if "chaos" in scenario_lower or "no-chaos" not in scenario_lower:
        return (
            "Under this chaos scenario the invariant failed. Review agent logic for this scenario: "
            "add input validation, error handling, or invariant-specific fixes (e.g. regex, latency, PII)."
        )
    if sev == "critical":
        return (
            "Critical invariant failed. Fix this first: ensure the agent always satisfies the invariant "
            f"({inv}) under all scenarios—e.g. add reset between runs or fix the underlying behavior."
        )
    return (
        f"Invariant '{inv}' failed in scenario '{c.scenario_name}'. "
        "Review contract rules and agent behavior; consider adding reset_endpoint or reset_function for stateful agents."
    )


def generate_contract_html(matrix: "ResilienceMatrix", title: str = "Contract Resilience Report") -> str:
    """Generate HTML for the contract × chaos matrix with suggested actions for failures."""
    rows = []
    failed_cells = [c for c in matrix.cell_results if not c.passed]
    for c in matrix.cell_results:
        status = "PASS" if c.passed else "FAIL"
        row_class = "fail" if not c.passed else ""
        rows.append(
            f'<tr class="{row_class}"><td>{_escape(c.invariant_id)}</td><td>{_escape(c.scenario_name)}</td>'
            f'<td>{_escape(c.severity)}</td><td>{status}</td></tr>'
        )
    body = "\n".join(rows)

    suggestions_html = ""
    if failed_cells:
        suggestions_html = """
<h2>Suggested actions (failed cells)</h2>
<p>The following actions may help fix the failed contract cells:</p>
<ul>
"""
        for c in failed_cells:
            action = _suggested_action_for_cell(c)
            suggestions_html += f"<li><strong>{_escape(c.invariant_id)}</strong> in scenario <strong>{_escape(c.scenario_name)}</strong> (severity: {_escape(c.severity)}): {_escape(action)}</li>\n"
        suggestions_html += "</ul>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(title)}</title>
<style>
:root {{
  --bg-primary: #0a0a0f;
  --bg-card: #1a1a24;
  --text-primary: #e8e8ed;
  --text-secondary: #8b8b9e;
  --success: #22c55e;
  --danger: #ef4444;
  --warning: #f59e0b;
  --border: #2a2a3a;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: system-ui, sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.6; min-height: 100vh; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ margin-bottom: 0.5rem; }}
h2 {{ margin-top: 2rem; margin-bottom: 0.75rem; font-size: 1.1rem; color: var(--text-secondary); }}
.report-meta {{ color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 1.5rem; }}
.score-card {{ background: var(--bg-card); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; display: inline-block; }}
.score-card .score {{ font-size: 2rem; font-weight: 700; }}
.score-card.pass .score {{ color: var(--success); }}
.score-card.fail .score {{ color: var(--danger); }}
table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 12px; overflow: hidden; }}
th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: rgba(0,0,0,0.2); color: var(--text-secondary); font-size: 0.875rem; }}
tr.fail {{ background: rgba(239, 68, 68, 0.08); }}
tr.fail td {{ color: #fca5a5; }}
ul {{ margin: 0.5rem 0; padding-left: 1.5rem; }}
li {{ margin: 0.5rem 0; }}
</style>
</head>
<body>
<div class="container">
<h1>{_escape(title)}</h1>
<p class="report-meta">Resilience matrix: invariant × scenario cells</p>
<div class="score-card {'pass' if matrix.passed else 'fail'}">
  <strong>Resilience score:</strong> <span class="score">{matrix.resilience_score:.1f}%</span><br>
  <strong>Overall:</strong> {'PASS' if matrix.passed else 'FAIL'}
</div>
<table>
<thead><tr><th>Invariant</th><th>Scenario</th><th>Severity</th><th>Result</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
{suggestions_html}
</div>
</body>
</html>"""


def _escape(s: str) -> str:
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def save_contract_report(matrix: "ResilienceMatrix", path: str | Path, title: str = "Contract Resilience Report") -> Path:
    """Write contract report HTML to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_contract_html(matrix, title), encoding="utf-8")
    return path
