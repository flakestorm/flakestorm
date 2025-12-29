# flakestorm Module Documentation

This document provides a comprehensive explanation of each module in the flakestorm codebase, what it does, how it works, and analysis of its design decisions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Modules](#core-modules)
   - [config.py](#configpy---configuration-management)
   - [protocol.py](#protocolpy---agent-adapters)
   - [orchestrator.py](#orchestratorpy---test-orchestration)
   - [runner.py](#runnerpy---test-execution)
   - [performance.py](#performancepy---rustpython-bridge)
3. [Mutation Modules](#mutation-modules)
   - [types.py](#typespm---mutation-types)
   - [templates.py](#templatespy---prompt-templates)
   - [engine.py](#enginepy---mutation-generation)
4. [Assertion Modules](#assertion-modules)
   - [deterministic.py](#deterministicpy---rule-based-checks)
   - [semantic.py](#semanticpy---ai-based-checks)
   - [safety.py](#safetypy---security-checks)
   - [verifier.py](#verifierpy---assertion-orchestration)
5. [Reporting Modules](#reporting-modules)
   - [models.py](#modelspy---data-structures)
   - [html.py](#htmlpy---html-report-generation)
   - [terminal.py](#terminalpy---cli-output)
6. [CLI Module](#cli-module)
   - [main.py](#mainpy---command-line-interface)
7. [Rust Performance Module](#rust-performance-module)
8. [Design Analysis](#design-analysis)

---

## Architecture Overview

```
flakestorm/
├── core/                    # Core orchestration logic
│   ├── config.py           # Configuration loading & validation
│   ├── protocol.py         # Agent adapter interfaces
│   ├── orchestrator.py     # Main test coordination
│   ├── runner.py           # High-level test runner
│   └── performance.py      # Rust/Python bridge
├── mutations/               # Adversarial input generation
│   ├── types.py            # Mutation type definitions
│   ├── templates.py        # LLM prompt templates
│   └── engine.py           # Mutation generation engine
├── assertions/              # Response validation
│   ├── deterministic.py    # Rule-based assertions
│   ├── semantic.py         # AI-based assertions
│   ├── safety.py           # Security assertions
│   └── verifier.py         # Assertion orchestrator
├── reports/                 # Output generation
│   ├── models.py           # Report data models
│   ├── html.py             # HTML report generator
│   ├── json_export.py      # JSON export
│   └── terminal.py         # Terminal output
├── cli/                     # Command-line interface
│   └── main.py             # Typer CLI commands
└── integrations/            # External integrations
    ├── huggingface.py      # HuggingFace model support
    ├── embeddings.py       # Local embeddings
    └── github_actions.py   # CI/CD integration
```

---

## Core Modules

### config.py - Configuration Management

**Location:** `src/flakestorm/core/config.py`

**Purpose:** Handles loading, validating, and providing type-safe access to the `flakestorm.yaml` configuration file.

**Key Components:**

```python
class AgentConfig(BaseModel):
    """Configuration for connecting to the target agent."""
    endpoint: str          # Agent URL or Python module path
    type: AgentType        # http, python, or langchain
    timeout: int = 30      # Request timeout
    headers: dict = {}     # HTTP headers
    request_template: str  # How to format requests
    response_path: str     # JSONPath to extract response
```

```python
class EntropixConfig(BaseModel):
    """Root configuration model."""
    agent: AgentConfig
    golden_prompts: list[str]
    mutations: MutationConfig
    llm: LLMConfig
    invariants: list[InvariantConfig]
    advanced: AdvancedConfig
```

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `load_config(path)` | Load and validate YAML config file |
| `expand_env_vars()` | Replace `${VAR}` with environment values |
| `validate_config()` | Run Pydantic validation |

**Design Analysis:**

✅ **Strengths:**
- Uses Pydantic for robust validation with clear error messages
- Environment variable expansion for secrets management
- Type safety prevents runtime configuration errors
- Default values reduce required configuration

⚠️ **Considerations:**
- Large config model - could be split into smaller files for maintainability
- No schema versioning - future config changes need migration support

**Why This Design:**
Pydantic was chosen over alternatives (dataclasses, attrs) because:
1. Built-in YAML/JSON serialization
2. Automatic validation with descriptive errors
3. Environment variable support
4. Wide ecosystem adoption

---

### protocol.py - Agent Adapters

**Location:** `src/flakestorm/core/protocol.py`

**Purpose:** Provides a unified interface for communicating with different types of AI agents (HTTP APIs, Python functions, LangChain).

**Key Components:**

```python
class AgentProtocol(Protocol):
    """Protocol that all agent adapters must implement."""

    async def invoke(self, prompt: str) -> AgentResponse:
        """Send prompt to agent and return response."""
        ...
```

```python
class HTTPAgentAdapter(BaseAgentAdapter):
    """Adapter for HTTP-based agents."""

    async def invoke(self, prompt: str) -> AgentResponse:
        # 1. Format request using template
        # 2. Send HTTP POST with headers
        # 3. Extract response using JSONPath
        # 4. Return with latency measurement
```

```python
class PythonAgentAdapter(BaseAgentAdapter):
    """Adapter for Python function agents."""

    async def invoke(self, prompt: str) -> AgentResponse:
        # 1. Import the specified module
        # 2. Call the function with prompt
        # 3. Return response with timing
```

**Design Analysis:**

✅ **Strengths:**
- Protocol pattern allows easy extension for new agent types
- Async-first design for efficient parallel testing
- Built-in latency measurement for performance tracking
- Retry logic handles transient failures

⚠️ **Considerations:**
- HTTP adapter assumes JSON request/response format
- Python adapter uses dynamic import which can be security-sensitive

**Why This Design:**
The adapter pattern was chosen because:
1. Decouples test logic from agent communication
2. Easy to add new agent types without modifying core
3. Allows mocking for unit tests

---

### orchestrator.py - Test Orchestration

**Location:** `src/flakestorm/core/orchestrator.py`

**Purpose:** Coordinates the entire testing process: mutation generation, parallel test execution, and result aggregation.

**Key Components:**

```python
class EntropixOrchestrator:
    """Main orchestration class."""

    async def run(self) -> TestResults:
        """Execute the full test suite."""
        # 1. Generate mutations for all golden prompts
        # 2. Run mutations in parallel with semaphore
        # 3. Verify responses against invariants
        # 4. Aggregate and score results
        # 5. Return comprehensive results
```

**Execution Flow:**

```
run()
  ├─► _generate_mutations()     # Create adversarial inputs
  │     └─► MutationEngine.generate_mutations()
  │
  ├─► _run_mutations()          # Execute tests in parallel
  │     ├─► Semaphore(concurrency)
  │     └─► _run_single_mutation()
  │           ├─► agent.invoke(mutated_prompt)
  │           └─► verifier.verify(response)
  │
  └─► _aggregate_results()      # Calculate statistics
        └─► calculate_statistics()
```

**Design Analysis:**

✅ **Strengths:**
- Async/await for efficient I/O-bound operations
- Semaphore controls concurrency to prevent overwhelming the agent
- Progress tracking with Rich for user feedback
- Clean separation between generation, execution, and verification

⚠️ **Considerations:**
- All mutations held in memory - could be memory-intensive for large runs
- No checkpointing - failed runs restart from beginning

**Why This Design:**
Async orchestration was chosen because:
1. Agent calls are I/O-bound, not CPU-bound
2. Parallelism improves test throughput significantly
3. Semaphore pattern is standard for rate limiting

---

### performance.py - Rust/Python Bridge

**Location:** `src/flakestorm/core/performance.py`

**Purpose:** Provides high-performance implementations of compute-intensive operations using Rust, with pure Python fallbacks.

**Key Functions:**

```python
def is_rust_available() -> bool:
    """Check if Rust extension is installed."""

def calculate_robustness_score(...) -> float:
    """Calculate weighted robustness score."""
    # Uses Rust if available, else Python

def levenshtein_distance(s1, s2) -> int:
    """Fast string edit distance calculation."""
    # 88x faster in Rust vs Python

def string_similarity(s1, s2) -> float:
    """Calculate string similarity ratio."""
```

**Performance Comparison:**

| Function | Python Time | Rust Time | Speedup |
|----------|------------|-----------|---------|
| Levenshtein (5000 iter) | 5864ms | 67ms | **88x** |
| Robustness Score | 0.5ms | 0.01ms | **50x** |
| String Similarity | 1.2ms | 0.02ms | **60x** |

**Design Analysis:**

✅ **Strengths:**
- Graceful fallback if Rust not available
- Same API regardless of implementation
- Significant performance improvement for scoring

⚠️ **Considerations:**
- Requires Rust toolchain for compilation
- Binary compatibility across platforms

**Why This Design:**
The bridge pattern was chosen because:
1. Pure Python works everywhere (easy installation)
2. Rust acceleration for production (performance)
3. Same tests validate both implementations

---

## Mutation Modules

### types.py - Mutation Types

**Location:** `src/flakestorm/mutations/types.py`

**Purpose:** Defines the types of adversarial mutations and their data structures.

**Key Components:**

```python
class MutationType(str, Enum):
    """Types of adversarial mutations."""
    PARAPHRASE = "paraphrase"       # Same meaning, different words
    NOISE = "noise"                 # Typos and errors
    TONE_SHIFT = "tone_shift"       # Different emotional tone
    PROMPT_INJECTION = "prompt_injection"  # Jailbreak attempts
```

```python
@dataclass
class Mutation:
    """A single mutation of a golden prompt."""
    original: str           # Original prompt
    mutated: str           # Mutated version
    type: MutationType     # Type of mutation
    difficulty: float      # Scoring weight
    metadata: dict         # Additional info

    @property
    def id(self) -> str:
        """Unique hash for this mutation."""
        return hashlib.md5(..., usedforsecurity=False)
```

**Design Analysis:**

✅ **Strengths:**
- Enum prevents invalid mutation types
- Dataclass provides clean, typed structure
- Built-in difficulty scoring for weighted results

**Why This Design:**
String enum was chosen because:
1. Values serialize directly to YAML/JSON
2. Type checking catches typos
3. Easy to extend with new types

---

### engine.py - Mutation Generation

**Location:** `src/flakestorm/mutations/engine.py`

**Purpose:** Generates adversarial mutations using a local LLM (Ollama/Qwen).

**Key Components:**

```python
class MutationEngine:
    """Engine for generating adversarial mutations."""

    def __init__(self, config: LLMConfig):
        self.client = ollama.AsyncClient(host=config.host)
        self.model = config.model

    async def generate_mutations(
        self,
        prompt: str,
        types: list[MutationType],
        count: int
    ) -> list[Mutation]:
        """Generate multiple mutations for a prompt."""
```

**Generation Flow:**

```
generate_mutations(prompt, types, count)
  │
  ├─► For each mutation type:
  │     ├─► Get template from templates.py
  │     ├─► Format with original prompt
  │     └─► Call Ollama API
  │
  ├─► Parse LLM responses
  │     └─► Extract mutated prompts
  │
  └─► Create Mutation objects
        └─► Assign difficulty weights
```

**Design Analysis:**

✅ **Strengths:**
- Async API calls for parallel generation
- Local LLM (no API costs, no data leakage)
- Customizable templates per mutation type

⚠️ **Considerations:**
- Depends on Ollama being installed and running
- LLM output parsing can be fragile
- Model quality affects mutation quality

**Why This Design:**
Local LLM was chosen over cloud APIs because:
1. Zero cost at scale
2. No rate limits
3. Privacy - prompts stay local
4. Works offline

---

## Assertion Modules

### deterministic.py - Rule-Based Checks

**Location:** `src/flakestorm/assertions/deterministic.py`

**Purpose:** Implements deterministic, rule-based assertions that check responses against exact criteria.

**Key Checkers:**

```python
class ContainsChecker(BaseChecker):
    """Check if response contains a value."""

class NotContainsChecker(BaseChecker):
    """Check if response does NOT contain a value."""

class RegexChecker(BaseChecker):
    """Check if response matches a regex pattern."""

class LatencyChecker(BaseChecker):
    """Check if response time is within limit."""

class ValidJsonChecker(BaseChecker):
    """Check if response is valid JSON."""
```

**Design Analysis:**

✅ **Strengths:**
- Fast execution (no AI/ML involved)
- Predictable, reproducible results
- Easy to debug failures

**Why This Design:**
Checker pattern with registry allows:
1. Easy addition of new check types
2. Configuration-driven selection
3. Consistent error reporting

---

### semantic.py - AI-Based Checks

**Location:** `src/flakestorm/assertions/semantic.py`

**Purpose:** Implements semantic assertions using embeddings for meaning-based comparison.

**Key Components:**

```python
class LocalEmbedder:
    """Local sentence embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text)

    def similarity(self, text1: str, text2: str) -> float:
        emb1, emb2 = self.embed(text1), self.embed(text2)
        return cosine_similarity(emb1, emb2)
```

```python
class SimilarityChecker(BaseChecker):
    """Check semantic similarity to expected response."""

    def check(self, response: str, latency_ms: float) -> CheckResult:
        similarity = self.embedder.similarity(response, expected)
        return CheckResult(passed=similarity >= threshold)
```

**Design Analysis:**

✅ **Strengths:**
- Catches semantic equivalence (not just string matching)
- Lazy loading of heavy ML models
- Configurable similarity thresholds

⚠️ **Considerations:**
- Requires sentence-transformers (optional dependency)
- First call is slow (model loading)
- Memory usage for embedding model

**Why This Design:**
sentence-transformers was chosen because:
1. High-quality embeddings out of the box
2. Runs locally (no API calls)
3. Small model size (all-MiniLM-L6-v2 is 23MB)

---

### safety.py - Security Checks

**Location:** `src/flakestorm/assertions/safety.py`

**Purpose:** Implements security-focused assertions for PII detection and refusal verification.

**Key Checkers:**

```python
class ExcludesPIIChecker(BaseChecker):
    """Check that response doesn't contain PII."""

    PII_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',      # SSN
        r'\b\d{16}\b',                   # Credit card
        r'\b[A-Za-z0-9._%+-]+@...',     # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}', # Phone
    ]
```

```python
class RefusalChecker(BaseChecker):
    """Check that agent refuses dangerous requests."""

    REFUSAL_PHRASES = [
        "I cannot", "I'm unable to", "I won't",
        "against my guidelines", "not appropriate"
    ]
```

**Design Analysis:**

✅ **Strengths:**
- Essential for production safety
- Regex-based PII detection is fast
- Catches common refusal patterns

⚠️ **Considerations:**
- PII patterns may miss edge cases
- Refusal detection is heuristic-based

**Why This Design:**
Pattern-based detection was chosen because:
1. Fast and deterministic
2. No false positives from ML
3. Easy to audit and extend

---

## Reporting Modules

### models.py - Data Structures

**Location:** `src/flakestorm/reports/models.py`

**Purpose:** Defines data structures for test results and reports.

**Key Models:**

```python
@dataclass
class MutationResult:
    """Result of testing a single mutation."""
    mutation: Mutation
    response: str
    latency_ms: float
    passed: bool
    checks: list[CheckResult]

@dataclass
class TestResults:
    """Complete test run results."""
    config: EntropixConfig
    mutations: list[MutationResult]
    statistics: TestStatistics
    timestamp: datetime
```

---

### html.py - HTML Report Generation

**Location:** `src/flakestorm/reports/html.py`

**Purpose:** Generates interactive HTML reports with visualizations.

**Key Features:**
- Embedded CSS (no external dependencies)
- Pass/fail grid visualization
- Latency charts
- Failure details with expandable sections
- Mobile-responsive design

**Design Analysis:**

✅ **Strengths:**
- Self-contained HTML (single file, works offline)
- No JavaScript framework dependencies
- Professional appearance

---

## CLI Module

### main.py - Command-Line Interface

**Location:** `src/flakestorm/cli/main.py`

**Purpose:** Provides the `flakestorm` command-line tool using Typer.

**Commands:**

```bash
flakestorm init      # Create config file
flakestorm run       # Run tests
flakestorm verify    # Validate config
flakestorm report    # Generate report from JSON
flakestorm score     # Show score from results
```

**Design Analysis:**

✅ **Strengths:**
- Typer provides automatic help generation
- Rich integration for beautiful output
- Consistent exit codes for CI

---

## Rust Performance Module

**Location:** `rust/src/`

**Components:**

| File | Purpose |
|------|---------|
| `lib.rs` | PyO3 bindings and main functions |
| `scoring.rs` | Statistics calculation algorithms |
| `parallel.rs` | Rayon-based parallel processing |

**Key Functions:**

```rust
#[pyfunction]
fn calculate_robustness_score(
    semantic_passed: u32,
    deterministic_passed: u32,
    total: u32,
    semantic_weight: f64,
    deterministic_weight: f64,
) -> f64

#[pyfunction]
fn levenshtein_distance(s1: &str, s2: &str) -> usize

#[pyfunction]
fn string_similarity(s1: &str, s2: &str) -> f64
```

**Design Analysis:**

✅ **Strengths:**
- PyO3 provides seamless Python integration
- Rayon enables easy parallelism
- Comprehensive test suite

---

## Design Analysis

### Overall Architecture Assessment

**Strengths:**
1. **Modularity**: Clear separation of concerns makes code maintainable
2. **Extensibility**: Easy to add new mutation types, checkers, adapters
3. **Type Safety**: Pydantic and type hints catch errors early
4. **Performance**: Rust acceleration where it matters
5. **Usability**: Rich CLI with progress bars and beautiful output

**Areas for Improvement:**
1. **Memory Usage**: Large test runs keep all results in memory
2. **Checkpointing**: No resume capability for interrupted runs
3. **Distributed Execution**: Single-machine only

### Performance Characteristics

| Operation | Complexity | Bottleneck |
|-----------|------------|------------|
| Mutation Generation | O(n*m) | LLM inference |
| Test Execution | O(n) | Agent response time |
| Scoring | O(n) | CPU (optimized with Rust) |
| Report Generation | O(n) | I/O |

Where n = number of mutations, m = mutation types.

### Security Considerations

1. **Secrets Management**: Environment variable expansion keeps secrets out of config files
2. **Local LLM**: No data sent to external APIs
3. **PII Detection**: Built-in checks for sensitive data
4. **Injection Testing**: Helps harden agents against attacks

---

*This documentation reflects the current implementation. Always refer to the source code for the most up-to-date information.*
