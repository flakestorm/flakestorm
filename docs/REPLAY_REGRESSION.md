# Replay-Based Regression (Pillar 3)

**What it is:** You **import real production failure sessions** (exact user input, tool responses, and failure description) and **replay** them as deterministic tests. Flakestorm sends the same input to the agent, injects the same tool responses via the chaos layer, and verifies the response against a **contract**. If the agent now passes, you’ve confirmed the fix.

**Why it matters:** The best test cases come from production. Replay closes the loop: incident → capture → fix → replay → pass.

**Question answered:** *Did we fix this incident?*

---

## When to use it

- You had a production incident (e.g. agent fabricated data when a tool returned 504).
- You fixed the agent and want to **prove** the same scenario passes.
- You run replays via `flakestorm replay run` for one-off checks, or `flakestorm ci` to include **replay_regression** in the overall score.

---

## Replay file format

A replay session is a YAML (or JSON) file with the following shape. You can reference it from `flakestorm.yaml` with `file: "replays/incident_001.yaml"` or run it directly with `flakestorm replay run path/to/file.yaml`.

```yaml
id: "incident-2026-02-15"
name: "Prod incident: fabricated revenue figure"
source: manual
input: "What was ACME Corp's Q3 revenue?"
tool_responses:
  - tool: market_data_api
    response: null
    status: 504
    latency_ms: 30000
  - tool: web_search
    response: "Connection reset by peer"
    status: 0
expected_failure: "Agent fabricated revenue instead of saying data unavailable"
contract: "Finance Agent Contract"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `file` | No | Path to replay file; when set, session is loaded from file and `id`/`input`/`contract` may be omitted. |
| `id` | Yes (if not using `file`) | Unique replay id. |
| `input` | Yes (if not using `file`) | Exact user input from the incident. |
| `contract` | Yes (if not using `file`) | Contract **name** (from main config) or **path** to a contract YAML file. Used to verify the agent’s response. |
| `tool_responses` | No | List of recorded tool responses to inject during replay. Each has `tool`, optional `response`, `status`, `latency_ms`. |
| `name` | No | Human-readable name. |
| `source` | No | e.g. `manual`, `langsmith`. |
| `expected_failure` | No | Short description of what went wrong (for documentation). |
| `context` | No | Optional conversation/system context. |

**Validation:** A replay session must have either `file` or both `id` and `input` (inline session).

---

## Contract reference

- **By name:** `contract: "Finance Agent Contract"` — the contract must be defined in the same `flakestorm.yaml` (under `contract:`).
- **By path:** `contract: "./contracts/safety.yaml"` — path relative to the config file directory.

Flakestorm resolves name first, then path; if not found, replay may fail or fall back depending on setup.

---

## Configuration in flakestorm.yaml

You can define replay sessions inline, by file, or via **LangSmith sources**:

```yaml
version: "2.0"
# ... agent, contract, etc. ...

replays:
  sessions:
    - file: "replays/incident_001.yaml"
    - id: "inline-001"
      input: "What is the capital of France?"
      contract: "Research Agent Contract"
      tool_responses: []
  # LangSmith sources (import by project or run ID; auto_import re-fetches on each run/ci)
  sources:
    - type: langsmith
      project: "my-production-agent"
      filter:
        status: error           # error | warning | all
        date_range: last_7_days
        min_latency_ms: 5000
      auto_import: true
    - type: langsmith_run
      run_id: "abc123def456"
```

When you use `file:`, the session’s `id`, `input`, and `contract` come from the loaded file. When you use inline `id` and `input`, you must provide them. **`replays.sources`** sessions are merged when running `flakestorm ci` or when `auto_import` is true (project sources).

---

## Commands

| Command | What it does |
|---------|----------------|
| `flakestorm replay run path/to/replay.yaml -c flakestorm.yaml` | Run a single replay file. `-c` supplies agent and contract config. |
| `flakestorm replay run path/to/dir -c flakestorm.yaml` | Run all replay files in the directory. |
| `flakestorm replay export --from-report REPORT.json --output ./replays` | Export failed mutations from a Flakestorm report as replay YAML files. |
| `flakestorm replay run --from-langsmith RUN_ID -c flakestorm.yaml` | Import a single session from LangSmith by run ID (requires `flakestorm[langsmith]`). |
| `flakestorm replay run --from-langsmith RUN_ID --run -o replay.yaml` | Import, optionally write to file, and run the replay. |
| `flakestorm replay run --from-langsmith-project PROJECT --filter-status error -o ./replays/` | Import all runs from a LangSmith project; write one YAML per run. Add `--run` to run after import. |
| `flakestorm ci -c flakestorm.yaml` | Runs mutation, contract, chaos-only, **and all replay sessions** (including `replays.sources` with `auto_import`); reports **replay_regression** and **overall** weighted score. |

---

## Import sources

- **Manual** — Write YAML/JSON replay files from incident reports.
- **Flakestorm export** — `flakestorm replay export --from-report REPORT.json` turns failed runs into replay files.
- **LangSmith (single run)** — `flakestorm replay run --from-langsmith RUN_ID` (requires `pip install flakestorm[langsmith]`).
- **LangSmith (project)** — `flakestorm replay run --from-langsmith-project PROJECT --filter-status error -o ./replays/` imports failed runs from a project; or use `replays.sources` in config with `auto_import: true` so CI re-fetches from the project each run.

---

## See also

- [Behavioral Contracts](BEHAVIORAL_CONTRACTS.md) — How contracts and invariants are defined (replay verifies against a contract).
- [Environment Chaos](ENVIRONMENT_CHAOS.md) — Replay uses the same chaos/interceptor layer to inject recorded tool responses.
