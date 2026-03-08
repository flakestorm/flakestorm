"""HTML report for replay regression results (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _escape(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _suggested_action_for_replay(r: dict[str, Any]) -> str:
    """Return a suggested action for a failed replay session."""
    passed = r.get("passed", True)
    if passed:
        return ""
    session_id = r.get("id", "")
    name = r.get("name", "")
    details = r.get("verification_details", []) or r.get("details", [])
    expected_failure = r.get("expected_failure", "")

    if expected_failure:
        return (
            f"This replay captures a known production failure: {_escape(expected_failure)}. "
            "Re-run the agent with the same input and (if any) injected tool responses; "
            "ensure the fix satisfies the contract invariants. If it still fails, check invariant types (e.g. regex, latency, excludes_pattern)."
        )
    if details:
        return (
            "One or more contract checks failed. Review verification_details and ensure the agent response "
            "satisfies all invariants for this session. Add reset_endpoint or reset_function if the agent is stateful."
        )
    return (
        f"Replay session '{_escape(session_id or name)}' failed. Re-run with the same input and tool responses; "
        "verify the contract used for this session and that the agent's response meets all invariant rules."
    )


def generate_replay_html(results: list[dict[str, Any]], title: str = "Replay Regression Report") -> str:
    """Generate HTML for replay run results with suggested actions for failures."""
    rows = []
    failed = [r for r in results if not r.get("passed", True)]
    for r in results:
        passed = r.get("passed", False)
        status = "PASS" if passed else "FAIL"
        row_class = "fail" if not passed else ""
        sid = r.get("id", "")
        name = r.get("name", "") or sid
        rows.append(
            f'<tr class="{row_class}"><td>{_escape(sid)}</td><td>{_escape(name)}</td><td>{status}</td></tr>'
        )
    body = "\n".join(rows)

    suggestions_html = ""
    if failed:
        suggestions_html = """
<h2>Suggested actions (failed sessions)</h2>
<p>Use these suggestions to fix the failed replay sessions:</p>
<ul>
"""
        for r in failed:
            action = _suggested_action_for_replay(r)
            if action:
                sid = r.get("id", "")
                name = r.get("name", "") or sid
                suggestions_html += f"<li><strong>{_escape(name)}</strong>: {action}</li>\n"
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
  --border: #2a2a3a;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: system-ui, sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.6; min-height: 100vh; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ margin-bottom: 0.5rem; }}
h2 {{ margin-top: 2rem; margin-bottom: 0.75rem; font-size: 1.1rem; color: var(--text-secondary); }}
.report-meta {{ color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 1.5rem; }}
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
<p class="report-meta">Replay sessions: production failure replay results</p>
<table>
<thead><tr><th>ID</th><th>Name</th><th>Result</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
{suggestions_html}
</div>
</body>
</html>"""


def save_replay_report(results: list[dict[str, Any]], path: str | Path, title: str = "Replay Regression Report") -> Path:
    """Write replay report HTML to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_replay_html(results, title), encoding="utf-8")
    return path
