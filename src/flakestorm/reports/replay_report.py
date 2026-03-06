"""HTML report for replay regression results (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_replay_html(results: list[dict[str, Any]], title: str = "Replay Regression Report") -> str:
    """Generate HTML for replay run results."""
    rows = []
    for r in results:
        passed = r.get("passed", False)
        rows.append(
            f"<tr><td>{r.get('id', '')}</td><td>{r.get('name', '')}</td><td>{'PASS' if passed else 'FAIL'}</td></tr>"
        )
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<table border="1">
<tr><th>ID</th><th>Name</th><th>Result</th></tr>
{body}
</table>
</body>
</html>"""


def save_replay_report(results: list[dict[str, Any]], path: str | Path, title: str = "Replay Regression Report") -> Path:
    """Write replay report HTML to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_replay_html(results, title), encoding="utf-8")
    return path
