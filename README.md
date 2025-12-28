# Entropix

<p align="center">
  <strong>The Agent Reliability Engine</strong><br>
  <em>Chaos Engineering for AI Agents</em>
</p>

<p align="center">
  <a href="https://github.com/entropix/entropix/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  </a>
  <a href="https://pypi.org/project/entropix/">
    <img src="https://img.shields.io/pypi/v/entropix.svg" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/entropix/">
    <img src="https://img.shields.io/pypi/pyversions/entropix.svg" alt="Python Versions">
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

**Entropix** is a local-first testing engine that applies **Chaos Engineering** principles to AI Agents.

Instead of running one test case, Entropix takes a single "Golden Prompt", generates 50+ adversarial mutations (semantic variations, noise injection, hostile tone, prompt injections), runs them in parallel against your agent, and calculates a **Robustness Score**.

> **"If it passes Entropix, it won't break in Production."**

## Features

- **Semantic Mutations**: Paraphrasing, noise injection, tone shifts, prompt injections
- **Invariant Assertions**: Deterministic checks, semantic similarity, safety validations
- **Local-First**: Uses Ollama with Qwen Coder 3 8B for free, unlimited attacks
- **Beautiful Reports**: Interactive HTML reports with pass/fail matrices
- **CI/CD Ready**: GitHub Actions integration to block PRs below reliability thresholds

## Quick Start

### Installation

```bash
pip install entropix
```

### Prerequisites

Entropix uses [Ollama](https://ollama.ai) for local model inference:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the default model
ollama pull qwen3:8b
```

### Initialize Configuration

```bash
entropix init
```

This creates an `entropix.yaml` configuration file:

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
  count: 20
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
entropix run
```

Output:
```
Entropix - Agent Reliability Engine v0.1.0

✓ Loading configuration from entropix.yaml
✓ Connected to Ollama (qwen3:8b)
✓ Agent endpoint verified

Generating mutations... ━━━━━━━━━━━━━━━━━━━━ 100%
Running attacks...      ━━━━━━━━━━━━━━━━━━━━ 100%
Verifying invariants... ━━━━━━━━━━━━━━━━━━━━ 100%

╭──────────────────────────────────────────╮
│  Robustness Score: 87.5%                 │
│  ────────────────────────                │
│  Passed: 35/40 mutations                 │
│  Failed: 5 (3 latency, 2 injection)      │
╰──────────────────────────────────────────╯

Report saved to: ./reports/entropix-2024-01-15-143022.html
```

## Mutation Types

| Type | Description | Example |
|------|-------------|---------|
| **Paraphrase** | Semantically equivalent rewrites | "Book a flight" → "I need to fly out" |
| **Noise** | Typos and spelling errors | "Book a flight" → "Book a fliight plz" |
| **Tone Shift** | Aggressive/impatient phrasing | "Book a flight" → "I need a flight NOW!" |
| **Prompt Injection** | Adversarial attack attempts | "Book a flight and ignore previous instructions" |

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

### Safety
```yaml
invariants:
  - type: "excludes_pii"
  - type: "refusal_check"
    dangerous_prompts: true
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
from entropix import test_agent

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

### GitHub Actions

```yaml
name: Agent Reliability Check

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama pull qwen3:8b
      
      - name: Install Entropix
        run: pip install entropix
      
      - name: Run Reliability Tests
        run: entropix run --min-score 0.9 --ci
```

## Robustness Score

The Robustness Score is calculated as:

$$R = \frac{W_s \cdot S_{passed} + W_d \cdot D_{passed}}{N_{total}}$$

Where:
- $S_{passed}$ = Semantic variations passed
- $D_{passed}$ = Deterministic tests passed
- $W$ = Weights assigned by mutation difficulty

## Documentation

- [Configuration Guide](docs/CONFIGURATION_GUIDE.md)
- [API Reference](docs/API_SPECIFICATION.md)
- [Contributing](docs/CONTRIBUTING.md)

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Tested with Entropix</strong><br>
  <img src="https://img.shields.io/badge/tested%20with-entropix-brightgreen" alt="Tested with Entropix">
</p>

