"""
HTML Report Generator

Generates interactive HTML reports with:
- Robustness score visualization
- Pass/fail matrix grid
- Drill-down into failed mutations
- Latency charts
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Template

if TYPE_CHECKING:
    from flakestorm.reports.models import MutationResult, TestResults


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>flakestorm Report - {{ report_date }}</title>
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --text-primary: #e8e8ed;
            --text-secondary: #8b8b9e;
            --accent: #6366f1;
            --accent-light: #818cf8;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --border: #2a2a3a;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent), var(--accent-light));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.25rem;
        }

        .logo-text {
            font-size: 1.5rem;
            font-weight: 600;
        }

        .report-meta {
            text-align: right;
            color: var(--text-secondary);
            font-size: 0.875rem;
        }

        .score-section {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .score-card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .score-ring {
            position: relative;
            width: 180px;
            height: 180px;
        }

        .score-ring svg {
            transform: rotate(-90deg);
        }

        .score-ring circle {
            fill: none;
            stroke-width: 12;
        }

        .score-ring .bg {
            stroke: var(--border);
        }

        .score-ring .progress {
            stroke: var(--accent);
            stroke-linecap: round;
            transition: stroke-dashoffset 1s ease-out;
        }

        .score-value {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 2.5rem;
            font-weight: 700;
        }

        .score-label {
            margin-top: 1rem;
            font-size: 1.125rem;
            color: var(--text-secondary);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }

        .stat-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.25rem;
        }

        .stat-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
        }

        .stat-value.success { color: var(--success); }
        .stat-value.danger { color: var(--danger); }

        .section {
            margin-bottom: 2rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .matrix-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }

        .matrix-cell {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1rem;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .matrix-cell:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }

        .matrix-cell.passed {
            border-left: 4px solid var(--success);
        }

        .matrix-cell.failed {
            border-left: 4px solid var(--danger);
        }

        .mutation-type {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .mutation-text {
            font-size: 0.875rem;
            line-height: 1.4;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }

        .mutation-meta {
            display: flex;
            justify-content: space-between;
            margin-top: 0.75rem;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .type-breakdown {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }

        .type-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.25rem;
        }

        .type-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .type-name {
            font-weight: 600;
            text-transform: capitalize;
        }

        .type-rate {
            font-size: 1.125rem;
            font-weight: 600;
        }

        .progress-bar {
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--accent-light));
            border-radius: 4px;
            transition: width 0.5s ease-out;
        }

        .modal {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: var(--bg-secondary);
            border-radius: 16px;
            max-width: 800px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            padding: 2rem;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
        }

        .detail-section {
            margin-bottom: 1.5rem;
        }

        .detail-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .detail-content {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .check-list {
            list-style: none;
        }

        .check-item {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-card);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }

        .check-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 0.75rem;
        }

        .check-icon.passed {
            background: var(--success);
            color: white;
        }

        .check-icon.failed {
            background: var(--danger);
            color: white;
        }

        .check-details {
            flex: 1;
        }

        .check-type {
            font-weight: 600;
            text-transform: capitalize;
        }

        .check-message {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        @media (max-width: 768px) {
            .score-section {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">E</div>
                <span class="logo-text">flakestorm</span>
            </div>
            <div class="report-meta">
                <div>{{ report_date }}</div>
                <div>Duration: {{ duration }}s</div>
            </div>
        </header>

        <div class="score-section">
            <div class="score-card">
                <div class="score-ring">
                    <svg width="180" height="180">
                        <circle class="bg" cx="90" cy="90" r="78"></circle>
                        <circle class="progress" cx="90" cy="90" r="78"
                            stroke-dasharray="{{ circumference }}"
                            stroke-dashoffset="{{ score_offset }}">
                        </circle>
                    </svg>
                    <div class="score-value">{{ score_percent }}%</div>
                </div>
                <div class="score-label">Robustness Score</div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Mutations</div>
                    <div class="stat-value">{{ total_mutations }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value success">{{ passed_mutations }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value danger">{{ failed_mutations }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Avg Latency</div>
                    <div class="stat-value">{{ avg_latency }}ms</div>
                </div>
            </div>
        </div>

        {% if summary.total_failures > 0 %}
        <div class="section">
            <h2 class="section-title">📋 Executive Summary & Action Items</h2>
            <div class="summary-card" style="background: var(--bg-card); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;">
                <div style="margin-bottom: 1rem;">
                    <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem;">Overall Assessment</h3>
                    <p style="color: var(--text-secondary); line-height: 1.6;">
                        Your agent has a <strong>{{ score_percent }}%</strong> robustness score with 
                        <strong>{{ failed_mutations }}</strong> failures out of <strong>{{ total_mutations }}</strong> tests.
                        {% if score_percent < 70 %}
                        <span style="color: var(--danger);">⚠️ This indicates significant vulnerabilities that need immediate attention.</span>
                        {% elif score_percent < 85 %}
                        <span style="color: var(--warning);">⚠️ Your agent needs improvement before production deployment.</span>
                        {% else %}
                        <span style="color: var(--success);">✓ Your agent shows good robustness, but there's room for improvement.</span>
                        {% endif %}
                    </p>
                </div>

                {% if summary.recommendations %}
                <div style="margin-top: 1.5rem;">
                    <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem;">Priority Action Items</h3>
                    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                        {% for rec in summary.recommendations %}
                        <div style="background: var(--bg-secondary); border-left: 4px solid 
                            {% if rec.priority == 'critical' %}var(--danger)
                            {% elif rec.priority == 'high' %}var(--warning)
                            {% else %}var(--accent)
                            {% endif %};
                            padding: 1rem; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                                <div>
                                    <strong style="text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em;
                                        color: {% if rec.priority == 'critical' %}var(--danger)
                                        {% elif rec.priority == 'high' %}var(--warning)
                                        {% else %}var(--accent)
                                        {% endif %};">
                                        {{ rec.priority }} Priority
                                    </strong>
                                    <h4 style="margin: 0.25rem 0; font-size: 1rem;">{{ rec.issue }}</h4>
                                </div>
                                <span style="background: var(--bg-primary); padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.875rem;">
                                    {{ rec.count }} occurrence{{ 's' if rec.count != 1 else '' }}
                                </span>
                            </div>
                            <p style="margin: 0; color: var(--text-secondary); line-height: 1.5;">{{ rec.action }}</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                {% if summary.top_issues %}
                <div style="margin-top: 1.5rem;">
                    <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem;">Top Failure Types</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem;">
                        {% for issue in summary.top_issues %}
                        <div style="background: var(--bg-secondary); padding: 0.75rem; border-radius: 8px;">
                            <div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                                {{ issue.type.replace('_', ' ').title() }}
                            </div>
                            <div style="font-size: 1.25rem; font-weight: 600;">{{ issue.count }}</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2 class="section-title">📊 By Mutation Type</h2>
            <div class="type-breakdown">
                {% for type_stat in type_stats %}
                <div class="type-card">
                    <div class="type-header">
                        <span class="type-name">{{ type_stat.mutation_type }}</span>
                        <span class="type-rate">{{ type_stat.pass_rate_percent }}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ type_stat.pass_rate_percent }}%"></div>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-secondary);">
                        {{ type_stat.passed }}/{{ type_stat.total }} passed
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🔬 Mutation Results</h2>
            <div class="matrix-grid">
                {% for result in mutations %}
                <div class="matrix-cell {{ 'passed' if result.passed else 'failed' }}"
                     onclick="showDetail({{ loop.index0 }})">
                    <div class="mutation-type">{{ result.mutation.type }}</div>
                    <div class="mutation-text">{{ result.mutation.mutated[:100] }}...</div>
                    <div class="mutation-meta">
                        <span>{{ result.latency_ms|round(0)|int }}ms</span>
                        <span>{{ '✓' if result.passed else '✗' }}</span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <div class="modal" id="detail-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Mutation Details</h3>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        const mutations = {{ mutations_json|safe }};

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showDetail(index) {
            const m = mutations[index];
            const modal = document.getElementById('detail-modal');
            const body = document.getElementById('modal-body');

            const hasRecommendation = m.recommendation && !m.passed;
            
            body.innerHTML = `
                <div class="detail-section">
                    <div class="detail-label">Original Prompt</div>
                    <div class="detail-content">${escapeHtml(m.original_prompt)}</div>
                </div>
                <div class="detail-section">
                    <div class="detail-label">Mutated (${m.mutation.type})</div>
                    <div class="detail-content">${escapeHtml(m.mutation.mutated)}</div>
                </div>
                <div class="detail-section">
                    <div class="detail-label">Agent Response</div>
                    <div class="detail-content">${escapeHtml(m.response || '(empty)')}</div>
                </div>
                ${m.error ? `
                <div class="detail-section">
                    <div class="detail-label" style="color: var(--danger);">Error</div>
                    <div class="detail-content" style="color: var(--danger);">${escapeHtml(m.error)}</div>
                </div>
                ` : ''}
                <div class="detail-section">
                    <div class="detail-label">Invariant Checks</div>
                    <ul class="check-list">
                        ${m.checks.map(c => `
                            <li class="check-item">
                                <div class="check-icon ${c.passed ? 'passed' : 'failed'}">
                                    ${c.passed ? '✓' : '✗'}
                                </div>
                                <div class="check-details">
                                    <div class="check-type">${escapeHtml(c.check_type)}</div>
                                    <div class="check-message">${escapeHtml(c.details)}</div>
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                </div>
                ${hasRecommendation ? `
                <div class="detail-section" style="background: var(--bg-card); border-left: 4px solid 
                    ${m.recommendation.priority === 'critical' ? 'var(--danger)' : 
                      m.recommendation.priority === 'high' ? 'var(--warning)' : 'var(--accent)'};
                    padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <div>
                            <div style="text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em;
                                color: ${m.recommendation.priority === 'critical' ? 'var(--danger)' : 
                                         m.recommendation.priority === 'high' ? 'var(--warning)' : 'var(--accent)'};
                                font-weight: 600; margin-bottom: 0.25rem;">
                                ${m.recommendation.priority} Priority
                            </div>
                            <h4 style="margin: 0; font-size: 1.125rem; color: var(--text-primary);">
                                💡 ${escapeHtml(m.recommendation.title)}
                            </h4>
                        </div>
                    </div>
                    <p style="color: var(--text-secondary); line-height: 1.6; margin-bottom: 1rem;">
                        ${escapeHtml(m.recommendation.description)}
                    </p>
                    ${m.recommendation.code ? `
                    <div style="background: var(--bg-primary); border-radius: 8px; padding: 1rem; overflow-x: auto;">
                        <pre style="margin: 0; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.875rem; line-height: 1.5; color: var(--text-primary);"><code>${escapeHtml(m.recommendation.code)}</code></pre>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
            `;

            modal.classList.add('active');
        }

        function closeModal() {
            document.getElementById('detail-modal').classList.remove('active');
        }

        document.getElementById('detail-modal').addEventListener('click', (e) => {
            if (e.target.id === 'detail-modal') closeModal();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>
"""


class HTMLReportGenerator:
    """
    Generates interactive HTML reports from test results.

    Creates a single-file HTML report with embedded CSS and JavaScript
    for easy sharing and viewing.
    """

    def __init__(self, results: TestResults):
        """
        Initialize the generator.

        Args:
            results: Test results to generate report from
        """
        self.results = results
        self.template = Template(HTML_TEMPLATE)

    def _generate_recommendation(
        self, mutation_result: Any
    ) -> dict[str, str]:
        """
        Generate actionable recommendation for a failed mutation.

        Args:
            mutation_result: The failed mutation result

        Returns:
            Dictionary with title, description, and code example
        """
        failed_checks = mutation_result.failed_checks
        mutation_type = mutation_result.mutation.type.value
        error = mutation_result.error

        # Check for agent errors (HTTP 500, connection errors, etc.)
        if error:
            if "JSON" in error or "json" in error.lower():
                if "control character" in error.lower():
                    return {
                        "title": "Fix JSON Input Sanitization",
                        "description": "The mutated input contains control characters (newlines, tabs) that break JSON parsing. Your agent needs to sanitize inputs before inserting them into JSON.",
                        "priority": "high",
                        "code": '''# Python example
import json
import re

def sanitize_for_json(text: str) -> str:
    """Remove control characters that break JSON."""
    # Remove control characters (0x00-0x1F, 0x7F-0x9F)
    return re.sub(r'[\\x00-\\x1f\\x7f-\\x9f]', '', text)

# In your request handler:
sanitized = sanitize_for_json(user_input)
request_body = json.dumps({"productDescription": sanitized})''',
                    }
                else:
                    return {
                        "title": "Fix JSON Parsing Error",
                        "description": f"The agent returned invalid JSON. Error: {error[:100]}",
                        "priority": "high",
                        "code": '''# Ensure your agent always returns valid JSON
# Wrap responses in try/except:
try:
    response = json.loads(agent_output)
except json.JSONDecodeError as e:
    return {"error": "Invalid JSON response", "details": str(e)}''',
                    }
            elif "HTTP 500" in error or "500" in error:
                return {
                    "title": "Fix Server Error Handling",
                    "description": "The agent's backend returned HTTP 500. This indicates a server-side error that needs investigation.",
                    "priority": "critical",
                    "code": '''# Add error handling in your agent:
# 1. Check server logs for the actual error
# 2. Add input validation before processing
# 3. Return proper error responses instead of 500

def handle_request(input_text):
    try:
        # Validate input
        if not input_text or len(input_text) > MAX_LENGTH:
            return {"error": "Invalid input"}
        
        # Process request
        result = process(input_text)
        return {"success": True, "data": result}
    except Exception as e:
        # Log error, return 400 instead of 500
        logger.error(f"Error: {e}")
        return {"error": "Processing failed", "status": 400}''',
                }
            else:
                return {
                    "title": "Fix Agent Error",
                    "description": f"The agent failed with error: {error[:150]}",
                    "priority": "high",
                    "code": "# Check agent logs and add proper error handling",
                }

        # Check for specific invariant failures
        check_types = [c.check_type for c in failed_checks]

        if "latency" in check_types:
            latency_check = next(c for c in failed_checks if c.check_type == "latency")
            return {
                "title": "Optimize Response Latency",
                "description": f"Response took {mutation_result.latency_ms:.0f}ms, exceeding the threshold. This mutation type ({mutation_type}) is causing performance issues.",
                "priority": "medium",
                "code": f'''# Performance optimization strategies:
# 1. Add caching for similar requests
# 2. Optimize LLM calls (reduce max_tokens, use faster models)
# 3. Add request timeout and circuit breaker
# 4. Consider async processing for long operations

# Example timeout:
import asyncio

async def process_with_timeout(input_text, max_ms=10000):
    try:
        return await asyncio.wait_for(
            process_request(input_text),
            timeout=max_ms / 1000
        )
    except asyncio.TimeoutError:
        return {{"error": "Request timeout"}}''',
            }

        if "valid_json" in check_types:
            return {
                "title": "Ensure Valid JSON Response",
                "description": "The agent's response is not valid JSON. All responses must be properly formatted JSON.",
                "priority": "high",
                "code": '''# Always return valid JSON:
import json

def format_response(data):
    """Ensure response is always valid JSON."""
    try:
        # If data is already a dict/list, serialize it
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        # If it's a string, try to parse it first
        try:
            parsed = json.loads(data)
            return json.dumps(parsed)
        except:
            # Wrap in a JSON object
            return json.dumps({"output": data})
    except Exception as e:
        return json.dumps({"error": str(e)})''',
            }

        if "contains" in check_types:
            contains_check = next(c for c in failed_checks if c.check_type == "contains")
            return {
                "title": "Fix Response Content Validation",
                "description": f"Response doesn't contain expected content. {contains_check.details}",
                "priority": "medium",
                "code": "# Review your agent's response logic to ensure it includes required content",
            }

        if "excludes_pii" in check_types:
            return {
                "title": "Fix PII Leakage",
                "description": "The response contains personally identifiable information (PII) that should not be exposed.",
                "priority": "critical",
                "code": '''# Add PII detection and filtering:
import re

PII_PATTERNS = [
    r'\\b\\d{3}-\\d{2}-\\d{4}\\b',  # SSN
    r'\\b\\d{16}\\b',  # Credit card
    r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b',  # Email
]

def filter_pii(text):
    """Remove PII from text."""
    for pattern in PII_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text)
    return text''',
            }

        # Default recommendation based on mutation type
        mutation_recommendations = {
            "encoding_attacks": {
                "title": "Handle Encoded Inputs",
                "description": "The agent failed on encoded inputs (Base64, Unicode, URL encoding). Add input decoding and validation.",
                "priority": "high",
                "code": '''# Decode various encoding formats:
import base64
import urllib.parse

def decode_input(text):
    """Try to decode various encoding formats."""
    # Try URL decoding
    try:
        decoded = urllib.parse.unquote(text)
        if decoded != text:
            return decoded
    except:
        pass
    
    # Try Base64
    try:
        decoded = base64.b64decode(text).decode('utf-8')
        return decoded
    except:
        pass
    
    return text''',
            },
            "context_manipulation": {
                "title": "Improve Context Extraction",
                "description": "The agent failed when context was manipulated. Improve intent extraction from noisy inputs.",
                "priority": "medium",
                "code": "# Use semantic search or LLM to extract core intent from noisy context",
            },
            "prompt_injection": {
                "title": "Strengthen Prompt Injection Defense",
                "description": "The agent is vulnerable to prompt injection attacks. Add input validation and filtering.",
                "priority": "critical",
                "code": '''# Add prompt injection detection:
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "forget your rules",
    "you are now",
    "system:",
    "assistant:",
]

def detect_injection(text):
    """Detect potential prompt injection."""
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            return True
    return False''',
            },
            "length_extremes": {
                "title": "Handle Edge Case Inputs",
                "description": "The agent failed on extreme input lengths (empty or very long). Add input validation.",
                "priority": "medium",
                "code": '''# Add input length validation:
MIN_LENGTH = 1
MAX_LENGTH = 10000

def validate_input(text):
    """Validate input length."""
    if len(text) < MIN_LENGTH:
        return {"error": "Input too short"}
    if len(text) > MAX_LENGTH:
        return {"error": "Input too long"}
    return None''',
            },
        }

        if mutation_type in mutation_recommendations:
            return mutation_recommendations[mutation_type]

        # Generic recommendation
        return {
            "title": "Review Agent Logic",
            "description": f"The agent failed on {mutation_type} mutation. Review the agent's handling of this input type.",
            "priority": "medium",
            "code": "# Review agent logs and add appropriate error handling",
        }

    def _generate_summary(self) -> dict[str, Any]:
        """
        Generate executive summary with actionable insights.

        Returns:
            Dictionary with summary data
        """
        stats = self.results.statistics
        failed = self.results.failed_mutations

        # Group failures by type
        failures_by_type: dict[str, list] = {}
        failures_by_check: dict[str, int] = {}
        error_types: dict[str, int] = {}

        for mutation in failed:
            # Group by mutation type
            mut_type = mutation.mutation.type.value
            if mut_type not in failures_by_type:
                failures_by_type[mut_type] = []
            failures_by_type[mut_type].append(mutation)

            # Count check failures
            for check in mutation.failed_checks:
                failures_by_check[check.check_type] = (
                    failures_by_check.get(check.check_type, 0) + 1
                )

            # Count error types
            if mutation.error:
                if "JSON" in mutation.error or "json" in mutation.error.lower():
                    error_types["JSON Parsing"] = error_types.get("JSON Parsing", 0) + 1
                elif "500" in mutation.error or "HTTP 500" in mutation.error:
                    error_types["HTTP 500"] = error_types.get("HTTP 500", 0) + 1
                elif "timeout" in mutation.error.lower():
                    error_types["Timeout"] = error_types.get("Timeout", 0) + 1
                else:
                    error_types["Other Errors"] = (
                        error_types.get("Other Errors", 0) + 1
                    )

        # Top issues
        top_issues = []
        if failures_by_check:
            sorted_checks = sorted(
                failures_by_check.items(), key=lambda x: x[1], reverse=True
            )
            top_issues = [
                {"type": check_type, "count": count}
                for check_type, count in sorted_checks[:5]
            ]

        # Recommendations
        recommendations = []
        if error_types.get("JSON Parsing", 0) > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "JSON Parsing Errors",
                    "count": error_types["JSON Parsing"],
                    "action": "Add input sanitization to remove control characters before JSON serialization",
                }
            )
        if error_types.get("HTTP 500", 0) > 0:
            recommendations.append(
                {
                    "priority": "critical",
                    "issue": "Server Errors",
                    "count": error_types["HTTP 500"],
                    "action": "Investigate server logs and add proper error handling to return 400 instead of 500",
                }
            )
        if failures_by_check.get("latency", 0) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "issue": "Performance Issues",
                    "count": failures_by_check["latency"],
                    "action": "Optimize agent response time - consider caching, reducing LLM tokens, or async processing",
                }
            )
        if failures_by_type.get("encoding_attacks", []):
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "Encoding Attack Vulnerabilities",
                    "count": len(failures_by_type["encoding_attacks"]),
                    "action": "Add input decoding for Base64, Unicode, and URL-encoded inputs",
                }
            )
        if failures_by_type.get("prompt_injection", []):
            recommendations.append(
                {
                    "priority": "critical",
                    "issue": "Prompt Injection Vulnerabilities",
                    "count": len(failures_by_type["prompt_injection"]),
                    "action": "Add prompt injection detection and filtering",
                }
            )

        return {
            "total_failures": len(failed),
            "failures_by_type": {
                k: len(v) for k, v in failures_by_type.items()
            },
            "failures_by_check": failures_by_check,
            "error_types": error_types,
            "top_issues": top_issues,
            "recommendations": recommendations,
        }

    def generate(self) -> str:
        """
        Generate the HTML report.

        Returns:
            Complete HTML document as a string
        """
        stats = self.results.statistics

        # Calculate score ring values
        circumference = 2 * 3.14159 * 78
        score_offset = circumference * (1 - stats.robustness_score)

        # Prepare type stats
        type_stats = [
            {
                "mutation_type": t.mutation_type.replace("_", " "),
                "total": t.total,
                "passed": t.passed,
                "pass_rate_percent": round(t.pass_rate * 100, 1),
            }
            for t in stats.by_type
        ]

        # Prepare mutations data with recommendations
        mutations_data = []
        for m in self.results.mutations:
            mut_dict = m.to_dict()
            if not m.passed:
                mut_dict["recommendation"] = self._generate_recommendation(m)
            mutations_data.append(mut_dict)

        # Generate summary
        summary = self._generate_summary()

        return self.template.render(
            report_date=self.results.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            duration=round(self.results.duration, 1),
            circumference=circumference,
            score_offset=score_offset,
            score_percent=round(stats.robustness_score * 100, 1),
            total_mutations=stats.total_mutations,
            passed_mutations=stats.passed_mutations,
            failed_mutations=stats.failed_mutations,
            avg_latency=round(stats.avg_latency_ms),
            type_stats=type_stats,
            mutations=self.results.mutations,
            mutations_json=json.dumps(mutations_data),
            summary=summary,
        )

    def save(self, path: str | Path | None = None) -> Path:
        """
        Save the HTML report to a file.

        Args:
            path: Output path (default: auto-generated in reports dir)

        Returns:
            Path to the saved file
        """
        if path is None:
            output_dir = Path(self.results.config.output.path)
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"flakestorm-{timestamp}.html"
            path = output_dir / filename
        else:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

        html = self.generate()
        path.write_text(html, encoding="utf-8")

        return path
