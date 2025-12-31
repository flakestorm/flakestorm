# flakestorm Developer FAQ

This document answers common questions developers might have about the flakestorm codebase. It's designed to help project maintainers explain design decisions and help contributors understand the codebase.

---

## Table of Contents

1. [Architecture Questions](#architecture-questions)
2. [Configuration System](#configuration-system)
3. [Mutation Engine](#mutation-engine)
4. [Assertion System](#assertion-system)
5. [Performance & Rust](#performance--rust)
6. [Agent Adapters](#agent-adapters)
7. [Testing & Quality](#testing--quality)
8. [Extending flakestorm](#extending-flakestorm)
9. [Common Issues](#common-issues)

---

## Architecture Questions

### Q: Why is the codebase split into core, mutations, assertions, and reports?

**A:** This follows the **Single Responsibility Principle (SRP)** and makes the codebase maintainable:

| Module | Responsibility |
|--------|---------------|
| `core/` | Orchestration, configuration, agent communication |
| `mutations/` | Adversarial input generation |
| `assertions/` | Response validation |
| `reports/` | Output formatting |

This separation means:
- Changes to mutation logic don't affect assertions
- New report formats can be added without touching core logic
- Each module can be tested independently

---

### Q: Why use async/await throughout the codebase?

**A:** Agent testing is **I/O-bound**, not CPU-bound. The bottleneck is waiting for:
1. LLM responses (mutation generation)
2. Agent responses (test execution)

Async allows running many operations concurrently:

```python
# Without async: 100 tests × 500ms = 50 seconds
# With async (10 concurrent): 100 tests / 10 × 500ms = 5 seconds
```

The semaphore in `orchestrator.py` controls concurrency:

```python
semaphore = asyncio.Semaphore(self.config.advanced.concurrency)

async def _run_single_mutation(self, mutation):
    async with semaphore:  # Limits concurrent executions
        return await self.agent.invoke(mutation.mutated)
```

---

### Q: Why is there both an `orchestrator.py` and a `runner.py`?

**A:** They serve different purposes:

- **`runner.py`**: High-level API for users - simple `FlakeStormRunner.run()` interface
- **`orchestrator.py`**: Internal coordination logic - handles the complex flow

This separation allows:
- `runner.py` to provide a clean facade
- `orchestrator.py` to be refactored without breaking the public API
- Different entry points (CLI, programmatic) to use the same core logic

---

## Configuration System

### Q: Why Pydantic instead of dataclasses or attrs?

**A:** Pydantic was chosen for several reasons:

1. **Automatic Validation**: Built-in validators with clear error messages
   ```python
   class MutationConfig(BaseModel):
       count: int = Field(ge=1, le=100)  # Validates range automatically
   ```

2. **Environment Variable Support**: Native expansion
   ```python
   endpoint: str = Field(default="${AGENT_URL}")
   ```

3. **YAML/JSON Serialization**: Works out of the box
4. **IDE Support**: Type hints provide autocomplete

---

### Q: Why use environment variable expansion in config?

**A:** Security best practice - secrets should never be in config files:

```yaml
# BAD: Secret in file (gets committed to git)
headers:
  Authorization: "Bearer sk-1234567890"

# GOOD: Reference environment variable
headers:
  Authorization: "Bearer ${API_KEY}"
```

Implementation in `config.py`:

```python
def expand_env_vars(value: str) -> str:
    """Replace ${VAR} with environment variable value."""
    pattern = r'\$\{([^}]+)\}'
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(pattern, replacer, value)
```

---

### Q: Why is MutationType defined as `str, Enum`?

**A:** String enums serialize directly to YAML/JSON:

```python
class MutationType(str, Enum):
    PARAPHRASE = "paraphrase"
```

This allows:
```yaml
# In config file - uses string value directly
mutations:
  types:
    - paraphrase  # Works!
    - noise
```

If we used a regular Enum, we'd need custom serialization logic.

---

## Mutation Engine

### Q: Why use a local LLM (Ollama) instead of cloud APIs?

**A:** Several important reasons:

| Factor | Local LLM | Cloud API |
|--------|-----------|-----------|
| **Cost** | Free | $0.01-0.10 per mutation |
| **Privacy** | Data stays local | Prompts sent to third party |
| **Rate Limits** | None | Often restrictive |
| **Latency** | Low | Network dependent |
| **Offline** | Works | Requires internet |

For a test run with 100 prompts × 20 mutations = 2000 API calls, cloud costs would add up quickly.

---

### Q: Why Qwen Coder 3 8B as the default model?

**A:** We evaluated several models:

| Model | Mutation Quality | Speed | Memory |
|-------|-----------------|-------|--------|
| Qwen Coder 3 8B | ⭐⭐⭐⭐ | ⭐⭐⭐ | 8GB |
| Llama 3 8B | ⭐⭐⭐ | ⭐⭐⭐ | 8GB |
| Mistral 7B | ⭐⭐⭐ | ⭐⭐⭐⭐ | 6GB |
| Phi-3 Mini | ⭐⭐ | ⭐⭐⭐⭐⭐ | 4GB |

Qwen Coder 3 was chosen because:
1. Excellent at understanding and modifying prompts
2. Good balance of quality vs. speed
3. Runs on consumer hardware (8GB VRAM)

---

### Q: How does the mutation template system work?

**A:** Templates are stored in `templates.py` and formatted with the original prompt:

```python
TEMPLATES = {
    MutationType.PARAPHRASE: """
    Rewrite this prompt with different words but same meaning.

    Original: {prompt}

    Rewritten:
    """,
    MutationType.NOISE: """
    Add 2-3 realistic typos to this prompt:

    Original: {prompt}

    With typos:
    """
}
```

The engine fills in `{prompt}` and sends to the LLM:

```python
template = TEMPLATES[mutation_type]
filled = template.format(prompt=original_prompt)
response = await self.client.generate(model=self.model, prompt=filled)
```

---

### Q: What if the LLM returns malformed mutations?

**A:** We have several safeguards:

1. **Parsing Logic**: Extracts text between known markers
2. **Validation**: Checks mutation isn't identical to original
3. **Retry Logic**: Regenerates if parsing fails
4. **Fallback**: Uses simple string manipulation if LLM fails

```python
def _parse_mutation(self, response: str) -> str:
    # Try to extract the mutated text
    lines = response.strip().split('\n')
    for line in lines:
        if line and not line.startswith('#'):
            return line.strip()
    raise MutationParseError("Could not extract mutation")
```

---

## Assertion System

### Q: Why separate deterministic and semantic assertions?

**A:** They have fundamentally different characteristics:

| Aspect | Deterministic | Semantic |
|--------|---------------|----------|
| **Speed** | Nanoseconds | Milliseconds |
| **Dependencies** | None | sentence-transformers |
| **Reproducibility** | 100% | May vary slightly |
| **Use Case** | Exact matching | Meaning matching |

Separating them allows:
- Running deterministic checks first (fast-fail)
- Making semantic checks optional (lighter installation)

---

### Q: How does the SimilarityChecker work internally?

**A:** It uses sentence embeddings and cosine similarity:

```python
class SimilarityChecker:
    def check(self, response: str, latency_ms: float) -> CheckResult:
        # 1. Embed both texts to vectors
        response_vec = self.embedder.embed(response)      # [0.1, 0.2, ...]
        expected_vec = self.embedder.embed(self.expected) # [0.15, 0.18, ...]

        # 2. Calculate cosine similarity
        similarity = cosine_similarity(response_vec, expected_vec)
        # Returns value between -1 and 1 (typically 0-1 for text)

        # 3. Compare to threshold
        return CheckResult(passed=similarity >= self.threshold)
```

The embedding model (`all-MiniLM-L6-v2`) converts text to 384-dimensional vectors that capture semantic meaning.

---

### Q: Why is the embedder a class variable with lazy loading?

**A:** The embedding model is large (23MB) and takes 1-2 seconds to load:

```python
class SimilarityChecker:
    _embedder: LocalEmbedder | None = None  # Class variable, shared

    @property
    def embedder(self) -> LocalEmbedder:
        if SimilarityChecker._embedder is None:
            SimilarityChecker._embedder = LocalEmbedder()  # Load once
        return SimilarityChecker._embedder
```

Benefits:
1. **Lazy Loading**: Only loads if semantic checks are used
2. **Shared Instance**: All SimilarityCheckers share one model
3. **Memory Efficient**: One copy in memory, not one per checker

---

### Q: How does PII detection work?

**A:** Uses regex patterns for common PII formats:

```python
PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),           # 123-45-6789
    (r'\b\d{16}\b', 'Credit Card'),              # 1234567890123456
    (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', 'Email'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'Phone'), # 123-456-7890
]

def check(self, response: str, latency_ms: float) -> CheckResult:
    for pattern, pii_type in self.PII_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            return CheckResult(
                passed=False,
                details=f"Found potential {pii_type}"
            )
    return CheckResult(passed=True)
```

---

## Performance & Rust

### Q: Why Rust for performance-critical code?

**A:** Python is slow for CPU-bound operations. Benchmarks show:

```
Levenshtein Distance (5000 iterations):
  Python: 5864ms
  Rust:     67ms
  Speedup: 88x
```

Rust was chosen over alternatives because:
- **vs C/C++**: Memory safety, easier to write correct code
- **vs Cython**: Better tooling (cargo), cleaner code
- **vs NumPy**: Works on strings, not just numbers

---

### Q: How does the Rust/Python bridge work?

**A:** Uses PyO3 for bindings:

```rust
// Rust side (lib.rs)
#[pyfunction]
fn levenshtein_distance(s1: &str, s2: &str) -> usize {
    // Rust implementation
}

#[pymodule]
fn flakestorm_rust(m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(levenshtein_distance, m)?)?;
    Ok(())
}
```

```python
# Python side (performance.py)
try:
    import flakestorm_rust
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

def levenshtein_distance(s1: str, s2: str) -> int:
    if _RUST_AVAILABLE:
        return flakestorm_rust.levenshtein_distance(s1, s2)
    # Pure Python fallback
    ...
```

---

### Q: Why provide pure Python fallbacks?

**A:** Accessibility and reliability:

1. **Easy Installation**: `pip install flakestorm` works without Rust toolchain
2. **Platform Support**: Works on any Python platform
3. **Development**: Faster iteration without recompiling Rust
4. **Testing**: Can test both implementations for parity

The tradeoff is speed, but most time is spent waiting for LLM/agent responses anyway.

---

## Agent Adapters

### Q: Why use the Protocol pattern for agents?

**A:** Enables type-safe duck typing:

```python
class AgentProtocol(Protocol):
    async def invoke(self, prompt: str) -> AgentResponse: ...
```

Any class with a matching `invoke` method works, even if it doesn't inherit from a base class. This is more Pythonic than Java-style interfaces.

---

### Q: How does the HTTP adapter handle different API formats?

**A:** Through configurable templates:

```yaml
agent:
  endpoint: "https://api.example.com/v1/chat"
  request_template: |
    {"messages": [{"role": "user", "content": "{prompt}"}]}
  response_path: "$.choices[0].message.content"
```

The adapter:
1. Replaces `{prompt}` in the template
2. Sends the formatted JSON
3. Uses JSONPath to extract the response

This supports OpenAI, Anthropic, custom APIs, etc.

---

### Q: Why is there a Python adapter?

**A:** Bypasses HTTP overhead for local testing:

```python
# Instead of: HTTP request → your server → your code → HTTP response
# Just: your_function(prompt) → response

class PythonAgentAdapter:
    async def invoke(self, prompt: str) -> AgentResponse:
        # Import the module dynamically
        module_path, func_name = self.endpoint.rsplit(":", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # Call directly
        start = time.perf_counter()
        response = await func(prompt) if asyncio.iscoroutinefunction(func) else func(prompt)
        latency = (time.perf_counter() - start) * 1000

        return AgentResponse(text=response, latency_ms=latency)
```

---

### Q: When do I need to create an HTTP endpoint vs use Python adapter?

**A:** It depends on your agent's language and setup:

| Your Agent Code | Adapter Type | Endpoint Needed? | Notes |
|----------------|--------------|------------------|-------|
| Python (internal) | Python adapter | ❌ No | Use `type: "python"`, call function directly |
| TypeScript/JavaScript | HTTP adapter | ✅ Yes | Must create HTTP endpoint (can be localhost) |
| Java/Go/Rust | HTTP adapter | ✅ Yes | Must create HTTP endpoint (can be localhost) |
| Already has HTTP API | HTTP adapter | ✅ Yes | Use existing endpoint |

**For non-Python code (TypeScript example):**

Since FlakeStorm is a Python CLI tool, it can only directly call Python functions. For TypeScript/JavaScript/other languages, you **must** create an HTTP endpoint:

```typescript
// test-endpoint.ts - Wrapper endpoint for FlakeStorm
import express from 'express';
import { generateRedditSearchQuery } from './your-internal-code';

const app = express();
app.use(express.json());

app.post('/flakestorm-test', async (req, res) => {
  // FlakeStorm sends: {"input": "Industry: X\nProduct: Y..."}
  const structuredText = req.body.input;

  // Parse structured input
  const params = parseStructuredInput(structuredText);

  // Call your internal function
  const query = await generateRedditSearchQuery(params);

  // Return in FlakeStorm's expected format
  res.json({ output: query });
});

app.listen(8000, () => {
  console.log('FlakeStorm test endpoint: http://localhost:8000/flakestorm-test');
});
```

Then in `flakestorm.yaml`:
```yaml
agent:
  endpoint: "http://localhost:8000/flakestorm-test"
  type: "http"
  request_template: |
    {
      "industry": "{industry}",
      "productName": "{productName}",
      "businessModel": "{businessModel}",
      "targetMarket": "{targetMarket}",
      "description": "{description}"
    }
  response_path: "$.output"
```

---

### Q: Do I need a public endpoint or can I use localhost?

**A:** It depends on where FlakeStorm runs:

| FlakeStorm Location | Agent Location | Endpoint Type | Works? |
|---------------------|----------------|---------------|--------|
| Same machine | Same machine | `localhost:8000` | ✅ Yes |
| Different machine | Your machine | `localhost:8000` | ❌ No - use public endpoint or ngrok |
| CI/CD server | Your machine | `localhost:8000` | ❌ No - use public endpoint |
| CI/CD server | Cloud (AWS/GCP) | `https://api.example.com` | ✅ Yes |

**Options for exposing local endpoint:**
1. **ngrok**: `ngrok http 8000` → get public URL
2. **localtunnel**: `lt --port 8000` → get public URL
3. **Deploy to cloud**: Deploy your test endpoint to a cloud service
4. **VPN/SSH tunnel**: If both machines are on same network

---

### Q: Can I test internal code without creating an endpoint?

**A:** Only if your code is in Python:

```python
# my_agent.py
async def flakestorm_agent(input: str) -> str:
    # Parse input, call your internal functions
    return result
```

```yaml
# flakestorm.yaml
agent:
  endpoint: "my_agent:flakestorm_agent"
  type: "python"  # ← No HTTP endpoint needed!
```

For non-Python code, you **must** create an HTTP endpoint wrapper.

See [Connection Guide](CONNECTION_GUIDE.md) for detailed examples and troubleshooting.

---

## Testing & Quality

### Q: Why are tests split by module?

**A:** Mirrors the source structure for maintainability:

```
tests/
├── test_config.py       # Tests for core/config.py
├── test_mutations.py    # Tests for mutations/
├── test_assertions.py   # Tests for assertions/
├── test_performance.py  # Tests for performance module
```

When fixing a bug in `config.py`, you immediately know to check `test_config.py`.

---

### Q: Why use pytest over unittest?

**A:** Pytest is more Pythonic and powerful:

```python
# unittest style (verbose)
class TestConfig(unittest.TestCase):
    def test_load_config(self):
        self.assertEqual(config.agent.type, AgentType.HTTP)

# pytest style (concise)
def test_load_config():
    assert config.agent.type == AgentType.HTTP
```

Pytest also offers:
- Fixtures for setup/teardown
- Parametrized tests
- Better assertion introspection

---

### Q: How should I add tests for a new feature?

**A:** Follow this pattern:

1. **Create test file** if needed: `tests/test_<module>.py`
2. **Write failing test first** (TDD)
3. **Group related tests** in a class
4. **Use fixtures** for common setup

```python
# tests/test_new_feature.py
import pytest
from flakestorm.new_module import NewFeature

class TestNewFeature:
    @pytest.fixture
    def feature(self):
        return NewFeature(config={...})

    def test_basic_functionality(self, feature):
        result = feature.do_something()
        assert result == expected

    def test_edge_case(self, feature):
        with pytest.raises(ValueError):
            feature.do_something(invalid_input)
```

---

## Extending flakestorm

### Q: How do I add a new mutation type?

**A:** Three steps:

1. **Add to enum** (`mutations/types.py`):
   ```python
   class MutationType(str, Enum):
       # ... existing types
       MY_NEW_TYPE = "my_new_type"
   ```

2. **Add template** (`mutations/templates.py`):
   ```python
   TEMPLATES[MutationType.MY_NEW_TYPE] = """
   Your prompt template here.

   Original: {prompt}

   Modified:
   """
   ```

3. **Add default weight** (`core/config.py`):
   ```python
   class MutationConfig(BaseModel):
       weights: dict = {
           # ... existing weights
           MutationType.MY_NEW_TYPE: 1.0,
       }
   ```

---

### Q: How do I add a new assertion type?

**A:** Four steps:

1. **Create checker class** (`assertions/deterministic.py` or `semantic.py`):
   ```python
   class MyNewChecker(BaseChecker):
       def check(self, response: str, latency_ms: float) -> CheckResult:
           # Your logic here
           passed = some_condition(response)
           return CheckResult(
               passed=passed,
               check_type=InvariantType.MY_NEW_TYPE,
               details="Explanation"
           )
   ```

2. **Add to enum** (`core/config.py`):
   ```python
   class InvariantType(str, Enum):
       # ... existing types
       MY_NEW_TYPE = "my_new_type"
   ```

3. **Register in verifier** (`assertions/verifier.py`):
   ```python
   CHECKER_REGISTRY = {
       # ... existing checkers
       InvariantType.MY_NEW_TYPE: MyNewChecker,
   }
   ```

4. **Add tests** (`tests/test_assertions.py`)

---

### Q: How do I add a new report format?

**A:** Create a new generator:

```python
# reports/markdown.py
class MarkdownReportGenerator:
    def __init__(self, results: TestResults):
        self.results = results

    def generate(self) -> str:
        """Generate markdown content."""
        md = f"# flakestorm Report\n\n"
        md += f"**Score:** {self.results.statistics.robustness_score:.2f}\n"
        # ... more content
        return md

    def save(self, path: Path = None) -> Path:
        path = path or Path(f"reports/report_{timestamp}.md")
        path.write_text(self.generate())
        return path
```

Then add CLI option in `cli/main.py`.

---

## Common Issues

### Q: Why am I getting "Cannot connect to Ollama"?

**A:** Ollama service isn't running. Fix:

```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/version
```

---

### Q: Why is mutation generation slow?

**A:** LLM inference is inherently slow. Options:
1. Use a faster model: `ollama pull phi3:mini`
2. Reduce mutation count: `mutations.count: 10`
3. Use GPU: Ensure Ollama uses GPU acceleration

---

### Q: Why do tests pass locally but fail in CI?

**A:** Common causes:
1. **Missing Ollama**: CI needs Ollama service
2. **Different model**: Ensure same model is pulled
3. **Timing**: CI may be slower, increase timeouts
4. **Environment variables**: Ensure secrets are set in CI

---

### Q: How do I debug a failing assertion?

**A:** Enable verbose mode and check the report:

```bash
flakestorm run --verbose --output html
```

The HTML report shows:
- Original prompt
- Mutated prompt
- Agent response
- Which assertion failed and why

---

*Have more questions? Open an issue on GitHub!*
