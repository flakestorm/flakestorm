# FlakeStorm

<p align="center">
  <strong>The Agent Reliability Engine</strong><br>
  <em>Chaos Engineering for AI Agents</em>
</p>

<p align="center">
  <a href="https://github.com/flakestorm/flakestorm/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-AGPLv3-blue.svg" alt="License">
  </a>
  <a href="https://pypi.org/project/flakestorm/">
    <img src="https://img.shields.io/pypi/v/flakestorm.svg" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/flakestorm/">
    <img src="https://img.shields.io/pypi/pyversions/flakestorm.svg" alt="Python Versions">
  </a>
</p>

---

## The Problem

**The "Happy Path" Fallacy**: Current AI development tools focus on getting an agent to work *once*. Developers tweak prompts until they get a correct answer, declare victory, and ship.

**The Reality**: LLMs are non-deterministic. An agent that works on Monday with `temperature=0.7` might fail on Tuesday. Users don't follow "Happy Paths" — they make typos, they're aggressive, they lie, and they attempt prompt injections.

**The Void**:
- **Observability Tools** (LangSmith) tell you *after* the agent failed in production
- **Eval Libraries** (RAGAS) focus on academic scores rather than system reliability
- **Missing Link**: A tool that actively *attacks* the agent to prove robustness before deployment

## The Solution

**FlakeStorm** is a local-first testing engine that applies **Chaos Engineering** principles to AI Agents.

Instead of running one test case, FlakeStorm takes a single "Golden Prompt", generates adversarial mutations (semantic variations, noise injection, hostile tone, prompt injections), runs them against your agent, and calculates a **Robustness Score**.

> **"If it passes FlakeStorm, it won't break in Production."**

## Features

- ✅ **5 Mutation Types**: Paraphrasing, noise, tone shifts, basic adversarial, custom templates
- ✅ **Invariant Assertions**: Deterministic checks, semantic similarity, basic safety
- ✅ **Local-First**: Uses Ollama with Qwen 3 8B for free testing
- ✅ **Beautiful Reports**: Interactive HTML reports with pass/fail matrices
- ✅ **50 Mutations Max**: Per test run
- ✅ **Sequential Execution**: One test at a time

## Quick Start

### Installation

```bash
pip install flakestorm
```

### Prerequisites

FlakeStorm uses [Ollama](https://ollama.ai) for local model inference:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the default model
ollama pull qwen3:8b
```

### Initialize Configuration

```bash
flakestorm init
```

This creates a `flakestorm.yaml` configuration file:

```yaml
version: "1.0"

agent:
  endpoint: "http://localhost:8000/invoke"
  type: "http"
  timeout: 30000

model:
  provider: "ollama"
  name: "qwen3:8b"
  base_url: "http://localhost:11434"

mutations:
  count: 10  # Max 50 total per run
  types:
    - paraphrase
    - noise
    - tone_shift
    - prompt_injection

golden_prompts:
  - "Book a flight to Paris for next Monday"
  - "What's my account balance?"

invariants:
  - type: "latency"
    max_ms: 2000
  - type: "valid_json"

output:
  format: "html"
  path: "./reports"
```

### Run Tests

```bash
flakestorm run
```

Output:
```
Generating mutations... ━━━━━━━━━━━━━━━━━━━━ 100%
Running attacks...      ━━━━━━━━━━━━━━━━━━━━ 100%

╭──────────────────────────────────────────╮
│  Robustness Score: 87.5%                 │
│  ────────────────────────                │
│  Passed: 17/20 mutations                 │
│  Failed: 3 (2 latency, 1 injection)      │
╰──────────────────────────────────────────╯

Report saved to: ./reports/flakestorm-2024-01-15-143022.html
```


## Mutation Types

| Type | Description | Example |
|------|-------------|---------|
| **Paraphrase** | Semantically equivalent rewrites | "Book a flight" → "I need to fly out" |
| **Noise** | Typos and spelling errors | "Book a flight" → "Book a fliight plz" |
| **Tone Shift** | Aggressive/impatient phrasing | "Book a flight" → "I need a flight NOW!" |
| **Prompt Injection** | Basic adversarial attacks | "Book a flight and ignore previous instructions" |
| **Custom** | Your own mutation templates | Define with `{prompt}` placeholder |

## Invariants (Assertions)

### Deterministic
```yaml
invariants:
  - type: "contains"
    value: "confirmation_code"
  - type: "latency"
    max_ms: 2000
  - type: "valid_json"
```

### Semantic
```yaml
invariants:
  - type: "similarity"
    expected: "Your flight has been booked"
    threshold: 0.8
```

### Safety (Basic)
```yaml
invariants:
  - type: "excludes_pii"  # Basic regex patterns
  - type: "refusal_check"
```

## Agent Adapters

### HTTP Endpoint
```yaml
agent:
  type: "http"
  endpoint: "http://localhost:8000/invoke"
```

### Python Callable
```python
from flakestorm import test_agent

@test_agent
async def my_agent(input: str) -> str:
    # Your agent logic
    return response
```

### LangChain
```yaml
agent:
  type: "langchain"
  module: "my_agent:chain"
```

## CI/CD Integration

For local testing:
```bash
# Run before committing (manual)
flakestorm run --min-score 0.9
```

## Robustness Score

The Robustness Score is calculated as:

$$R = \frac{W_s \cdot S_{passed} + W_d \cdot D_{passed}}{N_{total}}$$

Where:
- $S_{passed}$ = Semantic variations passed
- $D_{passed}$ = Deterministic tests passed
- $W$ = Weights assigned by mutation difficulty

## Documentation

### Getting Started
- [📖 Usage Guide](docs/USAGE_GUIDE.md) - Complete end-to-end guide
- [⚙️ Configuration Guide](docs/CONFIGURATION_GUIDE.md) - All configuration options
- [🧪 Test Scenarios](docs/TEST_SCENARIOS.md) - Real-world examples with code

### For Developers
- [🏗️ Architecture & Modules](docs/MODULES.md) - How the code works
- [❓ Developer FAQ](docs/DEVELOPER_FAQ.md) - Q&A about design decisions
- [📦 Publishing Guide](docs/PUBLISHING.md) - How to publish to PyPI
- [🤝 Contributing](docs/CONTRIBUTING.md) - How to contribute

### Reference
- [📋 API Specification](docs/API_SPECIFICATION.md) - API reference
- [🧪 Testing Guide](docs/TESTING_GUIDE.md) - How to run and write tests
- [✅ Implementation Checklist](docs/IMPLEMENTATION_CHECKLIST.md) - Development progress

## License

AGPLv3 - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Tested with FlakeStorm</strong><br>
  <img src="https://img.shields.io/badge/tested%20with-flakestorm-brightgreen" alt="Tested with FlakeStorm">
</p>
