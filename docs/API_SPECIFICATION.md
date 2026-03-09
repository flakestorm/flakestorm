# flakestorm API Specification

## Python SDK

### Quick Start

```python
import asyncio
from flakestorm import FlakeStormRunner, load_config

async def main():
    config = load_config("flakestorm.yaml")
    runner = FlakeStormRunner(config)
    results = await runner.run()
    print(f"Robustness Score: {results.statistics.robustness_score:.1%}")

asyncio.run(main())
```

---

## Core Classes

### FlakeStormConfig

Configuration container for all flakestorm settings.

```python
from flakestorm import FlakeStormConfig, load_config

# Load from file
config = load_config("flakestorm.yaml")

# Access properties
config.agent.endpoint  # str
config.model.name      # str
config.golden_prompts  # list[str]
config.invariants      # list[InvariantConfig]

# Serialize
yaml_str = config.to_yaml()

# Parse from string
config = FlakeStormConfig.from_yaml(yaml_content)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `version` | `str` | Config version (`1.0` \| `2.0`) |
| `agent` | `AgentConfig` | Agent connection settings (includes V2 `reset_endpoint`, `reset_function`) |
| `model` | `ModelConfig` | LLM settings (V2: `api_key` env-only) |
| `mutations` | `MutationConfig` | Mutation generation (max 50/run OSS, 22+ types) |
| `golden_prompts` | `list[str]` | Test prompts |
| `invariants` | `list[InvariantConfig]` | Assertion rules |
| `output` | `OutputConfig` | Report settings |
| `advanced` | `AdvancedConfig` | Advanced options |
| **V2** `chaos` | `ChaosConfig \| None` | Tool/LLM faults and context_attacks (list or dict) |
| **V2** `contract` | `ContractConfig \| None` | Behavioral contract and chaos_matrix (scenarios may include context_attacks) |
| **V2** `chaos_matrix` | `list[ChaosScenarioConfig] \| None` | Top-level chaos scenarios when not using contract.chaos_matrix |
| **V2** `replays` | `ReplayConfig \| None` | Replay sessions (file or inline) and LangSmith sources |
| **V2** `scoring` | `ScoringConfig \| None` | Weights for mutation, chaos, contract, replay (must sum to 1.0) |

---

### FlakeStormRunner

Main test runner class.

```python
from flakestorm import FlakeStormRunner

runner = FlakeStormRunner(
    config="flakestorm.yaml",  # or FlakeStormConfig object
    agent=None,              # optional: pre-configured adapter
    console=None,            # optional: Rich console
    show_progress=True,      # show progress bars
)

# Run tests
results = await runner.run()

# Verify setup only
is_valid = await runner.verify_setup()

# Get config summary
summary = runner.get_config_summary()
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `run()` | `TestResults` | Execute full test suite |
| `verify_setup()` | `bool` | Check configuration validity |
| `get_config_summary()` | `str` | Human-readable config summary |

---

### Agent Adapters

#### AgentProtocol

Interface for custom agent implementations.

```python
from typing import Protocol

class AgentProtocol(Protocol):
    async def invoke(self, input: str) -> str:
        """Execute agent and return response."""
        ...
```

#### HTTPAgentAdapter

Adapter for HTTP-based agents.

```python
from flakestorm import HTTPAgentAdapter

adapter = HTTPAgentAdapter(
    endpoint="http://localhost:8000/invoke",
    timeout=30000,  # ms
    headers={"Authorization": "Bearer token"},
    retries=2,
)

response = await adapter.invoke("Hello")
# Returns AgentResponse with .output, .latency_ms, .error
```

#### PythonAgentAdapter

Adapter for Python callable agents.

```python
from flakestorm import PythonAgentAdapter

async def my_agent(input: str) -> str:
    return f"Response to: {input}"

adapter = PythonAgentAdapter(my_agent)
response = await adapter.invoke("Test")
```

#### create_agent_adapter

Factory function for creating adapters from config.

```python
from flakestorm import create_agent_adapter

adapter = create_agent_adapter(config.agent)
```

---

### Mutation Engine

#### MutationType

```python
from flakestorm import MutationType

# Original 8 types
MutationType.PARAPHRASE            # Semantic rewrites
MutationType.NOISE                 # Typos and errors
MutationType.TONE_SHIFT            # Aggressive tone
MutationType.PROMPT_INJECTION      # Basic adversarial attacks
MutationType.ENCODING_ATTACKS      # Encoded inputs (Base64, Unicode, URL)
MutationType.CONTEXT_MANIPULATION  # Context manipulation
MutationType.LENGTH_EXTREMES       # Edge cases (empty/long inputs)
MutationType.CUSTOM                # User-defined templates

# Advanced prompt-level attacks (7 new types)
MutationType.MULTI_TURN_ATTACK     # Context persistence and conversation state
MutationType.ADVANCED_JAILBREAK    # Advanced prompt injection (DAN, role-playing)
MutationType.SEMANTIC_SIMILARITY_ATTACK  # Adversarial examples
MutationType.FORMAT_POISONING      # Structured data injection (JSON, XML)
MutationType.LANGUAGE_MIXING       # Multilingual, code-switching, emoji
MutationType.TOKEN_MANIPULATION    # Tokenizer edge cases, special tokens
MutationType.TEMPORAL_ATTACK       # Time-sensitive context, impossible dates

# System/Network-level attacks (8+ new types)
MutationType.HTTP_HEADER_INJECTION # HTTP header manipulation
MutationType.PAYLOAD_SIZE_ATTACK   # Extremely large payloads, DoS
MutationType.CONTENT_TYPE_CONFUSION # MIME type manipulation
MutationType.QUERY_PARAMETER_POISONING # Malicious query parameters
MutationType.REQUEST_METHOD_ATTACK  # HTTP method confusion
MutationType.PROTOCOL_LEVEL_ATTACK  # Protocol-level exploits
MutationType.RESOURCE_EXHAUSTION    # CPU/memory exhaustion, DoS
MutationType.CONCURRENT_REQUEST_PATTERN # Race conditions, concurrent state
MutationType.TIMEOUT_MANIPULATION   # Timeout handling, slow requests

# Properties
MutationType.PARAPHRASE.display_name    # "Paraphrase"
MutationType.PARAPHRASE.default_weight  # 1.0
MutationType.PARAPHRASE.description     # "Rewrite using..."
```

**Mutation Types Overview (22+ types):**

#### Prompt-Level Attacks

| Type | Description | Default Weight | When to Use |
|------|-------------|----------------|-------------|
| `PARAPHRASE` | Semantically equivalent rewrites | 1.0 | Test semantic understanding |
| `NOISE` | Typos and spelling errors | 0.8 | Test input robustness |
| `TONE_SHIFT` | Aggressive/impatient phrasing | 0.9 | Test emotional resilience |
| `PROMPT_INJECTION` | Basic adversarial attack attempts | 1.5 | Test security |
| `ENCODING_ATTACKS` | Base64, Unicode, URL encoding | 1.3 | Test parser robustness and security |
| `CONTEXT_MANIPULATION` | Adding/removing/reordering context | 1.1 | Test context extraction |
| `LENGTH_EXTREMES` | Empty, minimal, or very long inputs | 1.2 | Test boundary conditions |
| `MULTI_TURN_ATTACK` | Context persistence and conversation state | 1.4 | Test conversational agents |
| `ADVANCED_JAILBREAK` | Advanced prompt injection (DAN, role-playing) | 2.0 | Test advanced security |
| `SEMANTIC_SIMILARITY_ATTACK` | Adversarial examples - similar but different | 1.3 | Test robustness |
| `FORMAT_POISONING` | Structured data injection (JSON, XML, markdown) | 1.6 | Test structured data parsing |
| `LANGUAGE_MIXING` | Multilingual, code-switching, emoji | 1.2 | Test internationalization |
| `TOKEN_MANIPULATION` | Tokenizer edge cases, special tokens | 1.5 | Test LLM tokenization |
| `TEMPORAL_ATTACK` | Time-sensitive context, impossible dates | 1.1 | Test temporal reasoning |
| `CUSTOM` | User-defined mutation templates | 1.0 | Test domain-specific scenarios |

#### System/Network-Level Attacks

| Type | Description | Default Weight | When to Use |
|------|-------------|----------------|-------------|
| `HTTP_HEADER_INJECTION` | HTTP header manipulation attacks | 1.7 | Test HTTP API security |
| `PAYLOAD_SIZE_ATTACK` | Extremely large payloads, DoS | 1.4 | Test resource limits |
| `CONTENT_TYPE_CONFUSION` | MIME type manipulation | 1.5 | Test HTTP parsers |
| `QUERY_PARAMETER_POISONING` | Malicious query parameters | 1.6 | Test GET-based APIs |
| `REQUEST_METHOD_ATTACK` | HTTP method confusion | 1.3 | Test REST APIs |
| `PROTOCOL_LEVEL_ATTACK` | Protocol-level exploits (request smuggling) | 1.8 | Test protocol handling |
| `RESOURCE_EXHAUSTION` | CPU/memory exhaustion, DoS | 1.5 | Test production resilience |
| `CONCURRENT_REQUEST_PATTERN` | Race conditions, concurrent state | 1.4 | Test high-traffic agents |
| `TIMEOUT_MANIPULATION` | Timeout handling, slow requests | 1.3 | Test timeout resilience |

**Mutation Strategy:**

Choose mutation types based on your testing goals:
- **Comprehensive**: Use all 22+ types for complete coverage
- **Security-focused**: Emphasize `PROMPT_INJECTION`, `ADVANCED_JAILBREAK`, `PROTOCOL_LEVEL_ATTACK`, `HTTP_HEADER_INJECTION`
- **UX-focused**: Emphasize `NOISE`, `TONE_SHIFT`, `CONTEXT_MANIPULATION`, `LANGUAGE_MIXING`
- **Infrastructure-focused**: Emphasize all system/network-level types
- **Edge case testing**: Emphasize `LENGTH_EXTREMES`, `ENCODING_ATTACKS`, `TOKEN_MANIPULATION`, `RESOURCE_EXHAUSTION`

#### Mutation

```python
from flakestorm import Mutation, MutationType

mutation = Mutation(
    original="Book a flight",
    mutated="I need to fly",
    type=MutationType.PARAPHRASE,
    weight=1.0,
)

# Properties
mutation.id             # Unique hash
mutation.is_valid()     # Validity check
mutation.to_dict()      # Serialize
mutation.character_diff # Character count difference
```

#### MutationEngine

```python
from flakestorm import MutationEngine

engine = MutationEngine(config.model)

# Verify Ollama connection
is_connected = await engine.verify_connection()

# Generate mutations
mutations = await engine.generate_mutations(
    seed_prompt="Book a flight",
    types=[MutationType.PARAPHRASE, MutationType.NOISE],
    count=10,
)

# Batch generation
results = await engine.generate_batch(
    prompts=["Prompt 1", "Prompt 2"],
    types=[MutationType.PARAPHRASE],
    count_per_prompt=5,
)
```

---

### Invariant Verification

#### InvariantVerifier

```python
from flakestorm import InvariantVerifier

verifier = InvariantVerifier(config.invariants)

# Verify a response
result = verifier.verify(
    response="Agent output text",
    latency_ms=150.0,
)

# Result properties
result.all_passed      # bool
result.passed_count    # int
result.failed_count    # int
result.checks          # list[CheckResult]
result.get_failed_checks()
result.get_passed_checks()
```

#### Built-in Checkers

```python
from flakestorm.assertions import (
    ContainsChecker,
    LatencyChecker,
    ValidJsonChecker,
    RegexChecker,
    SimilarityChecker,
    ExcludesPIIChecker,
    RefusalChecker,
)
```

#### Custom Checker

```python
from flakestorm.assertions.deterministic import BaseChecker, CheckResult

class MyChecker(BaseChecker):
    def check(self, response: str, latency_ms: float) -> CheckResult:
        passed = "expected" in response
        return CheckResult(
            type=self.type,
            passed=passed,
            details="Custom check result",
        )
```

---

### Test Results

#### TestResults

```python
results = await runner.run()

# Statistics
results.statistics.robustness_score   # 0.0-1.0
results.statistics.total_mutations    # int
results.statistics.passed_mutations   # int
results.statistics.failed_mutations   # int
results.statistics.avg_latency_ms     # float
results.statistics.p95_latency_ms     # float
results.statistics.by_type            # list[TypeStatistics]

# Timing
results.started_at    # datetime
results.completed_at  # datetime
results.duration      # seconds

# Mutations
results.mutations            # list[MutationResult]
results.passed_mutations     # list[MutationResult]
results.failed_mutations     # list[MutationResult]
results.get_by_type("noise") # Filter by type
results.get_by_prompt("...")  # Filter by prompt

# Serialization
results.to_dict()  # Full JSON-serializable dict

# V2: Resilience and contract/replay (when config has contract/replays)
results.resilience_scores   # dict: mutation_robustness, chaos_resilience, contract_compliance, replay_regression
results.contract_compliance # ContractRunResult | None (when contract run was executed)
# Replay results are reported via flakestorm replay run --output; see Reports below.
```

#### MutationResult

```python
for result in results.mutations:
    result.original_prompt   # str
    result.mutation          # Mutation object
    result.response          # str
    result.latency_ms        # float
    result.passed            # bool
    result.checks            # list[CheckResult]
    result.error             # str | None
    result.failed_checks     # list[CheckResult]
```

---

### Report Generation

#### HTMLReportGenerator

```python
from flakestorm.reports import HTMLReportGenerator

generator = HTMLReportGenerator(results)

# Generate HTML string
html = generator.generate()

# Save to file
path = generator.save()  # Auto-generated path
path = generator.save("custom/path/report.html")
```

#### JSONReportGenerator

```python
from flakestorm.reports import JSONReportGenerator

generator = JSONReportGenerator(results)

# Full report
json_str = generator.generate(pretty=True)

# Summary only (for CI)
summary = generator.generate_summary()

# Save
path = generator.save()
path = generator.save(summary_only=True)
```

#### TerminalReporter

```python
from flakestorm.reports import TerminalReporter
from rich.console import Console

reporter = TerminalReporter(results, Console())

reporter.print_summary()
reporter.print_type_breakdown()
reporter.print_failures(limit=10)
reporter.print_full_report()
```

**V2 reports:** Contract runs (`flakestorm contract run --output report.html`) and replay runs (`flakestorm replay run --output report.html`) produce HTML reports that include **suggested actions** for failed cells or sessions (e.g. add reset_endpoint, tighten invariants, fix tool behavior). See [Behavioral Contracts](BEHAVIORAL_CONTRACTS.md) and [Replay Regression](REPLAY_REGRESSION.md).

---

## CLI Commands

### `flakestorm init [PATH]`

Initialize a new configuration file.

```bash
flakestorm init                    # Creates flakestorm.yaml
flakestorm init config/test.yaml   # Custom path
flakestorm init --force            # Overwrite existing
```

### `flakestorm run`

Run reliability tests (mutation run; optionally with chaos).

```bash
flakestorm run                              # Default config (mutation only)
flakestorm run --config custom.yaml         # Custom config
flakestorm run --chaos                       # Apply chaos (tool/LLM faults, context_attacks) during mutation run
flakestorm run --chaos-only                  # Chaos-only run (no mutations); requires chaos config
flakestorm run --chaos-profile api_outage    # Use a built-in chaos profile
flakestorm run --output json                 # JSON output
flakestorm run --output terminal             # Terminal only
flakestorm run --min-score 0.9 --ci          # CI mode
flakestorm run --verify-only                 # Just verify setup
flakestorm run --quiet                       # Minimal output
```

### `flakestorm verify`

Verify configuration and connections.

```bash
flakestorm verify
flakestorm verify --config custom.yaml
```

### `flakestorm report PATH`

View or convert existing reports.

```bash
flakestorm report results.json              # View in terminal
flakestorm report results.json --output html # Convert to HTML
```

### `flakestorm score`

Output only the robustness score (for CI scripts).

```bash
SCORE=$(flakestorm score)
if (( $(echo "$SCORE >= 0.9" | bc -l) )); then
    echo "Passed"
else
    echo "Failed"
    exit 1
fi
```

### V2: `flakestorm contract run` / `validate` / `score`

Run behavioral contract tests (invariants × chaos matrix).

```bash
flakestorm contract run                      # Run contract matrix; progress and score in terminal
flakestorm contract run --output report.html  # Save HTML report with suggested actions for failed cells
flakestorm contract validate                 # Validate contract config only
flakestorm contract score                    # Output contract resilience score only
```

### V2: `flakestorm replay run` / `export`

Replay regression: run saved sessions and verify against a contract.

```bash
flakestorm replay run                        # Replay sessions from config (file or inline)
flakestorm replay run path/to/session.yaml   # Replay a single session file
flakestorm replay run path/to/replays/       # Replay all sessions in directory
flakestorm replay run --output report.html   # Save HTML report with suggested actions for failed sessions
flakestorm replay export --from-report FILE  # Export from an existing report
```

### V2: `flakestorm ci`

Run full CI pipeline: mutation run, contract run (if configured), chaos-only (if chaos configured), replay (if configured); then compute overall weighted score from `scoring.weights`.

```bash
flakestorm ci
flakestorm ci --config custom.yaml
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OLLAMA_HOST` | Override Ollama server URL |
| Custom headers | Expanded in config via `${VAR}` syntax |

**V2 — API keys (env-only):** Model API keys must not be literal in config. Use environment variables and reference them in config (e.g. `api_key: "${OPENAI_API_KEY}"`). Supported: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, etc. See [LLM Providers](LLM_PROVIDERS.md).

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (config, connection, etc.) |
| 1 | CI mode: Score below threshold |
