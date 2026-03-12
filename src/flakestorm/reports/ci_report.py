"""HTML report for flakestorm ci (all phases + overall score)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _escape(s: Any) -> str:
    if s is None:
        return ""
    t = str(s)
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_ci_report_html(
    phase_scores: dict[str, float],
    overall: float,
    passed: bool,
    min_score: float = 0.0,
    timestamp: str | None = None,
    report_links: dict[str, str] | None = None,
    phase_overall_passed: dict[str, bool] | None = None,
) -> str:
    """Generate HTML for the CI run: phase scores, overall, and links to detailed reports.
    phase_overall_passed: when a phase has its own pass/fail (e.g. contract: critical fail = FAIL),
    pass False for that key so the summary matches the detailed report."""
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_links = report_links or {}
    phase_overall_passed = phase_overall_passed or {}
    phase_names = {
        "mutation_robustness": "Mutation",
        "chaos_resilience": "Chaos",
        "contract_compliance": "Contract",
        "replay_regression": "Replay",
    }
    rows = []
    for key, score in phase_scores.items():
        name = phase_names.get(key, key.replace("_", " ").title())
        pct = round(score * 100, 1)
        # Fail if score below threshold OR phase has its own fail (e.g. contract critical failure)
        phase_passed = phase_overall_passed.get(key, True)
        row_failed = score < min_score or phase_passed is False
        status = "FAIL" if row_failed else "PASS"
        row_class = "fail" if row_failed else ""
        link = report_links.get(key)
        link_cell = f'<a href="{_escape(link)}" style="color: var(--accent);">View detailed report</a>' if link else "<span style=\"color: var(--text-secondary);\">—</span>"
        rows.append(
            f'<tr class="{row_class}"><td>{_escape(name)}</td><td>{pct}%</td><td>{status}</td><td>{link_cell}</td></tr>'
        )
    body = "\n".join(rows)
    overall_pct = round(overall * 100, 1)
    overall_status = "PASS" if passed else "FAIL"
    overall_class = "fail" if not passed else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>flakestorm CI Report - {_escape(timestamp)}</title>
<style>
:root {{
  --bg-primary: #0a0a0f;
  --bg-card: #1a1a24;
  --text-primary: #e8e8ed;
  --text-secondary: #8b8b9e;
  --success: #22c55e;
  --danger: #ef4444;
  --accent: #818cf8;
  --border: #2a2a3a;
}}
body {{ font-family: system-ui, sans-serif; background: var(--bg-primary); color: var(--text-primary); padding: 2rem; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ margin-bottom: 0.5rem; }}
.meta {{ color: var(--text-secondary); margin-bottom: 1.5rem; }}
table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: rgba(99,102,241,0.2); }}
tr.fail {{ color: var(--danger); }}
.overall {{ margin-top: 1.5rem; padding: 1rem; background: var(--bg-card); border-radius: 8px; font-size: 1.25rem; }}
.overall.fail {{ color: var(--danger); }}
.overall:not(.fail) {{ color: var(--success); }}
a {{ text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
<h1>flakestorm CI Report</h1>
<p class="meta">Run at {_escape(timestamp)} · min score: {min_score:.0%}</p>
<p class="meta">Each phase has a <strong>detailed report</strong> with failure reasons and recommended next steps. Use the links below to inspect failures.</p>
<table>
<thead><tr><th>Phase</th><th>Score</th><th>Status</th><th>Detailed report</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
<div class="overall {overall_class}"><strong>Overall (weighted):</strong> {overall_pct}% — {overall_status}</div>
</div>
</body>
</html>
"""


def save_ci_report(
    phase_scores: dict[str, float],
    overall: float,
    passed: bool,
    path: Path,
    min_score: float = 0.0,
    report_links: dict[str, str] | None = None,
    phase_overall_passed: dict[str, bool] | None = None,
) -> Path:
    """Write CI report HTML to path. report_links: phase key -> filename. phase_overall_passed: phase key -> False when phase failed (e.g. contract critical fail)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = generate_ci_report_html(
        phase_scores=phase_scores,
        overall=overall,
        passed=passed,
        min_score=min_score,
        report_links=report_links,
        phase_overall_passed=phase_overall_passed,
    )
    path.write_text(html, encoding="utf-8")
    return path
