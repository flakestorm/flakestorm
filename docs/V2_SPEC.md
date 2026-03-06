# V2 Spec Clarifications

## Python callable / tool interception

For `agent.type: python`, **tool fault injection** requires one of:

- An explicit list of tool callables in config that Flakestorm can wrap, or
- A `ToolRegistry` interface that Flakestorm wraps.

If neither is provided, Flakestorm **fails with a clear error** (does not silently skip tool fault injection).

## Contract matrix isolation

Each (invariant × scenario) cell is an **independent invocation**. Agent state must not leak between cells.

- **Reset is optional:** configure `agent.reset_endpoint` (HTTP) or `agent.reset_function` (Python) to clear state before each cell.
- If no reset is configured and the agent **appears stateful** (response variance across identical inputs), Flakestorm **warns** (does not fail):  
  *"Warning: No reset_endpoint configured. Contract matrix cells may share state. Results may be contaminated. Add reset_endpoint to your config for accurate isolation."*

## Resilience score formula

**Per-contract score:**

```
score = (Σ(passed_critical×3) + Σ(passed_high×2) + Σ(passed_medium×1))
      / (Σ(total_critical×3) + Σ(total_high×2) + Σ(total_medium×1)) × 100
```

**Automatic FAIL:** If any **critical** severity invariant fails in any scenario, the overall result is FAIL regardless of the numeric score.

**Overall score (mutation + chaos + contract + replay):** Configurable via `scoring.weights` (default: mutation 20%, chaos 35%, contract 35%, replay 10%).
