# V2 Spec Clarifications

## Python callable / tool interception

For `agent.type: python`, **tool fault injection** requires one of:

- An explicit list of tool callables in config that Flakestorm can wrap, or
- A `ToolRegistry` interface that Flakestorm wraps.

If neither is provided, Flakestorm **fails with a clear error** (does not silently skip tool fault injection).

## Contract matrix isolation

Each (invariant × scenario) cell is an **independent invocation**. Agent state must not leak between cells.

- **Reset is optional:** configure `agent.reset_endpoint` (HTTP) or `agent.reset_function` (Python module path, e.g. `myagent:reset_state`) to clear state before each cell.
- If no reset is configured and the agent **appears stateful** (same prompt produces different responses on two calls), Flakestorm **warns** (does not fail):  
  *"Warning: No reset_endpoint configured. Contract matrix cells may share state. Results may be contaminated. Add reset_endpoint to your config for accurate isolation."*

## Contract invariants: system_prompt_leak_probe and behavior_unchanged

- **system_prompt_leak_probe:** Use a contract invariant with **`probes`** (list of probe prompts). The contract engine runs those prompts instead of golden_prompts for that invariant and verifies the response (e.g. with `excludes_pattern`) so the agent does not leak the system prompt.
- **behavior_unchanged:** Use invariant type `behavior_unchanged`. Set **`baseline`** to `auto` to compute a baseline from one run without chaos, or provide a manual baseline string. Response is compared with **`similarity_threshold`** (default 0.75).

## Resilience score formula

**Per-contract score:**

```
score = (Σ(passed_critical×3) + Σ(passed_high×2) + Σ(passed_medium×1))
      / (Σ(total_critical×3) + Σ(total_high×2) + Σ(total_medium×1)) × 100
```

**Automatic FAIL:** If any **critical** severity invariant fails in any scenario, the overall result is FAIL regardless of the numeric score.

**Overall score (mutation + chaos + contract + replay):** Configurable via **`scoring.weights`**. Weights must **sum to 1.0** (validation enforced). Default: mutation 0.20, chaos 0.35, contract 0.35, replay 0.10.
