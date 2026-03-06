# V2 Research Assistant — Flakestorm v2 Example

A **working** HTTP agent and v2.0 config that demonstrates all three V2 pillars: **Environment Chaos**, **Behavioral Contracts**, and **Replay-Based Regression**.

## Prerequisites

- Python 3.10+
- **Ollama** running with a model (e.g. `ollama pull gemma3:1b` then `ollama run gemma3:1b`). The agent calls Ollama to generate real LLM responses; Flakestorm uses the same Ollama for mutation generation.
- Dependencies: `pip install -r requirements.txt` (fastapi, uvicorn, pydantic, httpx)

## 1. Start the agent

From the project root or this directory:

```bash
cd examples/v2_research_agent
uvicorn agent:app --host 0.0.0.0 --port 8790
```

Or: `python agent.py` (uses port 8790 by default).

Verify: `curl -X POST http://localhost:8790/invoke -H "Content-Type: application/json" -d "{\"input\": \"Hello\"}"`

## 2. Run Flakestorm v2 commands

From the **project root** (so `flakestorm` and config paths resolve):

```bash
# Mutation testing only (v1 style)
flakestorm run -c examples/v2_research_agent/flakestorm.yaml

# With chaos (tool/LLM faults)
flakestorm run -c examples/v2_research_agent/flakestorm.yaml --chaos

# Chaos only (no mutations, golden prompts under chaos)
flakestorm run -c examples/v2_research_agent/flakestorm.yaml --chaos-only

# Built-in chaos profile
flakestorm run -c examples/v2_research_agent/flakestorm.yaml --chaos-profile api_outage

# Behavioral contract × chaos matrix
flakestorm contract run -c examples/v2_research_agent/flakestorm.yaml

# Contract score only (CI gate)
flakestorm contract score -c examples/v2_research_agent/flakestorm.yaml

# Replay regression (one session)
flakestorm replay run examples/v2_research_agent/replays/incident_001.yaml -c examples/v2_research_agent/flakestorm.yaml

# Export failures from a report as replay files
flakestorm replay export --from-report reports/report.json -o examples/v2_research_agent/replays/

# Full CI run (mutation + contract + chaos + replay, overall weighted score)
flakestorm ci -c examples/v2_research_agent/flakestorm.yaml --min-score 0.5
```

## 3. What this example demonstrates

| Feature | Config / usage |
|--------|-----------------|
| **Chaos** | `chaos.tool_faults` (503 with probability), `chaos.llm_faults` (truncated); `--chaos`, `--chaos-profile` |
| **Contract** | `contract` with invariants (always-cite-source, completes, max-latency) and `chaos_matrix` (no-chaos, api-outage) |
| **Replay** | `replays.sessions` with `file: replays/incident_001.yaml`; contract resolved by name "Research Agent Contract" |
| **Scoring** | `scoring` weights (mutation 20%, chaos 35%, contract 35%, replay 10%); used in `flakestorm ci` |
| **Reset** | `agent.reset_endpoint: http://localhost:8790/reset` for contract matrix isolation |

## 4. Config layout (v2.0)

- `version: "2.0"`
- `agent` + `reset_endpoint`
- `chaos` (tool_faults, llm_faults)
- `contract` (invariants, chaos_matrix)
- `replays.sessions` (file reference)
- `scoring` (weights)

The agent calls **Ollama** (same model as in `flakestorm.yaml`: `gemma3:1b` by default). Set `OLLAMA_BASE_URL` or `OLLAMA_MODEL` if your Ollama runs elsewhere or uses a different model. The agent is stateless except for a call counter; `/reset` clears it so contract cells stay isolated.
