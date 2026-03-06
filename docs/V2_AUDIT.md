# V2 Implementation Audit

**Date:** March 2026  
**Reference:** [Flakestorm v2.md](Flakestorm%20v2.md), [flakestorm-v2-addendum.md](flakestorm-v2-addendum.md)

## Scope

Verification of the codebase against the PRD and addendum: behavior, config schema, CLI, and examples.

---

## 1. PRD §8.1 — Environment Chaos

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Tool faults: timeout, error, malformed, slow, malicious_response | ✅ | `chaos/faults.py`, `chaos/http_transport.py` (by match_url or tool `*`) |
| LLM faults: timeout, truncated_response, rate_limit, empty, garbage | ✅ | `chaos/llm_proxy.py`, `chaos/interceptor.py` |
| probability, after_calls, tool `*` | ✅ | `chaos/faults.should_trigger`, transport and interceptor |
| Built-in profiles: api_outage, degraded_llm, hostile_tools, high_latency, cascading_failure | ✅ | `chaos/profiles/*.yaml` |
| InstrumentedAgentAdapter / httpx transport | ✅ | `ChaosInterceptor`, `ChaosHttpTransport`, `HTTPAgentAdapter(transport=...)` |

---

## 2. PRD §8.2 — Behavioral Contracts

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Contract with id, severity, when, negate | ✅ | `ContractInvariantConfig`, `contracts/engine.py` |
| Chaos matrix (scenarios) | ✅ | `contract.chaos_matrix`, scenario → ChaosConfig per run |
| Resilience matrix N×M, weighted score | ✅ | `contracts/matrix.py` (critical×3, high×2, medium×1), FAIL if any critical |
| Invariant types: contains_any, output_not_empty, completes, excludes_pattern, behavior_unchanged | ✅ | Assertions + verifier; contract engine runs verifier with contract invariants |
| reset_endpoint / reset_function | ✅ | `AgentConfig`, `ContractEngine._reset_agent()` before each cell |
| Stateful warning when no reset | ✅ | `ContractEngine._detect_stateful_and_warn()`, `STATEFUL_WARNING` |

---

## 3. PRD §8.3 — Replay-Based Regression

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Replay session: input, tool_responses, contract | ✅ | `ReplaySessionConfig`, `replay/loader.py`, `replay/runner.py` |
| Contract by name or path | ✅ | `resolve_contract()` in loader |
| Verify against contract | ✅ | `ReplayRunner.run()` uses `InvariantVerifier` with resolved contract |
| Export from report | ✅ | `flakestorm replay export --from-report FILE` |
| Replays in config: sessions with file or inline | ✅ | `replays.sessions`; session can have `file` only (load from file) or full inline |

---

## 4. PRD §9 — Combined Modes & Resilience Score

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Mutation only, chaos only, mutation+chaos, contract, replay | ✅ | `run` (with --chaos, --chaos-only), `contract run`, `replay run` |
| Unified resilience score (mutation_robustness, chaos_resilience, contract_compliance, replay_regression, overall) | ✅ | `reports/models.TestResults.resilience_scores`; `flakestorm ci` computes overall from `scoring.weights` |

---

## 5. PRD §10 — CLI

| Command | Status |
|---------|--------|
| flakestorm run --chaos, --chaos-profile, --chaos-only | ✅ |
| flakestorm chaos | ✅ |
| flakestorm contract run / validate / score | ✅ |
| flakestorm replay run [PATH] | ✅ (replay run, replay export) |
| flakestorm replay export --from-report FILE | ✅ |
| flakestorm ci | ✅ (mutation + contract + chaos + replay + overall score) |

---

## 6. Addendum — Context Attacks, Model Drift, LangSmith, Spec

| Item | Status |
|------|--------|
| Context attacks module (indirect_injection, etc.) | ✅ `chaos/context_attacks.py`; profile `indirect_injection.yaml` |
| response_drift in llm_proxy | ✅ `chaos/llm_proxy.py` (json_field_rename, verbosity_shift, format_change, refusal_rephrase, tone_shift) |
| LangSmith load + schema check | ✅ `replay/loader.py`: `load_langsmith_run`, `_validate_langsmith_run_schema` |
| Python tool fault: fail loudly when no tools | ✅ `create_instrumented_adapter` raises if type=python and tool_faults |
| Contract matrix isolation (reset) | ✅ Optional reset; warning if stateful and no reset |
| Resilience score formula (addendum §6.3) | ✅ In `contracts/matrix.py` and `docs/V2_SPEC.md` |

---

## 7. Config Schema (v2.0)

- `version: "2.0"` supported; v1.0 backward compatible.
- `chaos`, `contract`, `chaos_matrix`, `replays`, `scoring` present and used.
- Replay session can be `file: "path"` only; full session loaded from file. Validation updated so `id`/`input`/`contract` optional when `file` is set.

---

## 8. Changes Made During This Audit

1. **Replay session file-only** — `ReplaySessionConfig` allows session with only `file`; `id`/`input`/`contract` optional when `file` is set (defaults/loaded from file).
2. **CI replay path** — Replay session file path resolved relative to config file directory: `config_path.parent / s.file`.
3. **V2 example** — Added `examples/v2_research_agent/`: working HTTP agent (FastAPI), v2 flakestorm.yaml (chaos, contract, replays, scoring), replay file, README, requirements.txt.

---

## 9. Example: V2 Research Agent

- **Agent:** `examples/v2_research_agent/agent.py` — FastAPI app with `/invoke` and `/reset`.
- **Config:** `examples/v2_research_agent/flakestorm.yaml` — version 2.0, chaos, contract, chaos_matrix, replays.sessions with file, scoring.
- **Replay:** `examples/v2_research_agent/replays/incident_001.yaml`.
- **Usage:** See `examples/v2_research_agent/README.md` (start agent, then run `flakestorm run`, `flakestorm contract run`, `flakestorm replay run`, `flakestorm ci`).

---

## 10. Test Status

- **181 tests passing** (including chaos, contract, replay integration tests).
- V2 example config loads successfully (`load_config("examples/v2_research_agent/flakestorm.yaml")`).

---

*Audit complete. Implementation aligns with PRD and addendum; optional config and path resolution improved; V2 example added.*
