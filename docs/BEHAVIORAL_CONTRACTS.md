# Behavioral Contracts (Pillar 2)

**What it is:** A **contract** is a named set of **invariants** (rules the agent must always follow). Flakestorm runs your agent under each scenario in a **chaos matrix** and checks every invariant in every scenario. The result is a **resilience score** (0–100%) and a pass/fail matrix.

**Why it matters:** You need to know that the agent still obeys its rules when tools fail, the LLM is degraded, or context is poisoned — not just on the happy path.

**Question answered:** *Does the agent obey its rules when the world breaks?*

---

## When to use it

- You have hard rules: “always cite a source”, “never return PII”, “never fabricate numbers when tools fail”.
- You want a single **resilience score** for CI that reflects behavior across multiple failure modes.
- You run `flakestorm contract run` for contract-only checks, or `flakestorm ci` to include contract in the overall score.

---

## Configuration

In `flakestorm.yaml` with `version: "2.0"` add `contract` and `chaos_matrix`:

```yaml
contract:
  name: "Finance Agent Contract"
  description: "Invariants that must hold under all failure conditions"
  invariants:
    - id: always-cite-source
      type: regex
      pattern: "(?i)(source|according to|reference)"
      severity: critical
      when: always
      description: "Must always cite a data source"
    - id: never-fabricate-when-tools-fail
      type: regex
      pattern: '\\$[\\d,]+\\.\\d{2}'
      negate: true
      severity: critical
      when: tool_faults_active
      description: "Must not return dollar figures when tools are failing"
    - id: max-latency
      type: latency
      max_ms: 60000
      severity: medium
      when: always
  chaos_matrix:
    - name: "no-chaos"
      tool_faults: []
      llm_faults: []
    - name: "search-tool-down"
      tool_faults:
        - tool: market_data_api
          mode: error
          error_code: 503
    - name: "llm-degraded"
      llm_faults:
        - mode: truncated_response
          max_tokens: 20
```

### Invariant fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for this invariant. |
| `type` | Yes | Same as run invariants: `contains`, `regex`, `latency`, `valid_json`, `similarity`, `excludes_pii`, `refusal_check`, `completes`, `output_not_empty`, `contains_any`, etc. |
| `severity` | No | `critical` \| `high` \| `medium` \| `low` (default `medium`). Weights the resilience score; **any critical failure** = automatic fail. |
| `when` | No | `always` \| `tool_faults_active` \| `llm_faults_active` \| `any_chaos_active` \| `no_chaos`. When this invariant is evaluated. |
| `negate` | No | If true, the check passes when the pattern does **not** match (e.g. “must NOT contain dollar figures”). |
| `description` | No | Human-readable description. |
| Plus type-specific | — | `pattern`, `value`, `values`, `max_ms`, `threshold`, etc., same as [invariants](CONFIGURATION_GUIDE.md). |

### Chaos matrix

Each entry is a **scenario**: a name plus optional `tool_faults`, `llm_faults`, and `context_attacks`. The contract engine runs your golden prompts under each scenario and verifies every invariant. Result: **invariants × scenarios** cells; resilience score is severity-weighted pass rate, and **any critical failure** fails the contract.

---

## Resilience score

- **Formula:** (Σ passed × severity_weight) / (Σ total × severity_weight) × 100.
- **Weights:** critical = 3, high = 2, medium = 1, low = 1.
- **Automatic FAIL:** If any invariant with severity `critical` fails in any scenario, the contract is considered failed regardless of the numeric score.

---

## Commands

| Command | What it does |
|---------|----------------|
| `flakestorm contract run` | Run the contract across the chaos matrix; print resilience score and pass/fail. |
| `flakestorm contract validate` | Validate contract YAML without executing. |
| `flakestorm contract score` | Output only the resilience score (e.g. for CI: `flakestorm contract score -c flakestorm.yaml`). |
| `flakestorm ci` | Runs contract (if configured) and includes **contract_compliance** in the **overall** weighted score. |

---

## Stateful agents

If your agent keeps state between calls, each (invariant × scenario) cell should start from a clean state. Set **`reset_endpoint`** (HTTP) or **`reset_function`** (Python) in your `agent` config so Flakestorm can reset between cells. If the agent appears stateful and no reset is configured, Flakestorm warns but does not fail.

---

## See also

- [Environment Chaos](ENVIRONMENT_CHAOS.md) — How tool/LLM faults and context attacks are defined.
- [Configuration Guide](CONFIGURATION_GUIDE.md) — Full `invariants` and checker reference.
