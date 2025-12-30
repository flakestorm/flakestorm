# Flakestorm

<p align="center">
  <strong>The Agent Reliability Engine</strong><br>
  <em>Chaos Engineering for AI Agents</em>
</p>

<p align="center">
  <a href="https://github.com/flakestorm/flakestorm/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License">
  </a>
  <a href="https://github.com/flakestorm/flakestorm">
    <img src="https://img.shields.io/github/stars/flakestorm/flakestorm?style=social" alt="GitHub Stars">
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

**Flakestorm** is a local-first testing engine that applies **Chaos Engineering** principles to AI Agents.

Instead of running one test case, Flakestorm takes a single "Golden Prompt", generates adversarial mutations (semantic variations, noise injection, hostile tone, prompt injections), runs them against your agent, and calculates a **Robustness Score**.

> **"If it passes Flakestorm, it won't break in Production."**

## Features

- ✅ **5 Mutation Types**: Paraphrasing, noise, tone shifts, basic adversarial, custom templates
- ✅ **Invariant Assertions**: Deterministic checks, semantic similarity, basic safety
- ✅ **Local-First**: Uses Ollama with Qwen 3 8B for free testing
- ✅ **Beautiful Reports**: Interactive HTML reports with pass/fail matrices
- ✅ **50 Mutations Max**: Per test run
- ✅ **Sequential Execution**: One test at a time

## Quick Start

### Installation Order

1. **Install Ollama first** (system-level service)
2. **Create virtual environment** (for Python packages)
3. **Install flakestorm** (Python package)
4. **Start Ollama and pull model** (required for mutations)

### Step 1: Install Ollama (System-Level)

FlakeStorm uses [Ollama](https://ollama.ai) for local model inference. Install this first:

**macOS Installation:**

```bash
# Option 1: Homebrew (recommended)
brew install ollama

# If you get permission errors, fix permissions first:
sudo chown -R $(whoami) /Users/imac-frank/Library/Logs/Homebrew
sudo chown -R $(whoami) /usr/local/Cellar
sudo chown -R $(whoami) /usr/local/Homebrew
brew install ollama

# Option 2: Official Installer
# Visit https://ollama.ai/download and download the macOS installer (.dmg)
```

**Windows Installation:**

1. Visit https://ollama.com/download/windows
2. Download `OllamaSetup.exe`
3. Run the installer and follow the wizard
4. Ollama will be installed and start automatically

**Linux Installation:**

```bash
# Using the official install script
curl -fsSL https://ollama.com/install.sh | sh

# Or using package managers (Ubuntu/Debian example):
sudo apt install ollama
```

**After installation, start Ollama and pull the model:**

```bash
# Start Ollama
# macOS (Homebrew): brew services start ollama
# macOS (Manual) / Linux: ollama serve
# Windows: Starts automatically as a service

# In another terminal, pull the model
ollama pull qwen3:8b
```

**Troubleshooting:** If you get `syntax error: <!doctype html>` or `command not found` when running `ollama` commands:

```bash
# 1. Remove the bad binary
sudo rm /usr/local/bin/ollama

# 2. Find Homebrew's Ollama location
brew --prefix ollama  # Shows /usr/local/opt/ollama or /opt/homebrew/opt/ollama

# 3. Create symlink to make it available
# Intel Mac:
sudo ln -s /usr/local/opt/ollama/bin/ollama /usr/local/bin/ollama

# Apple Silicon:
sudo ln -s /opt/homebrew/opt/ollama/bin/ollama /opt/homebrew/bin/ollama
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. Verify and use
which ollama
brew services start ollama
ollama pull qwen3:8b
```

### Step 2: Install flakestorm (Python Package)

**Using a virtual environment (recommended):**

```bash
# 1. Check if Python 3.11 is installed
python3.11 --version  # Should work if installed via Homebrew

# If not installed:
# macOS: brew install python@3.11
# Linux: sudo apt install python3.11 (Ubuntu/Debian)

# 2. DEACTIVATE any existing venv first (if active)
deactivate  # Run this if you see (venv) in your prompt

# 3. Remove old venv if it exists (created with Python 3.9)
rm -rf venv

# 4. Create venv with Python 3.11 EXPLICITLY
python3.11 -m venv venv
# Or use full path: /usr/local/bin/python3.11 -m venv venv

# 5. Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 6. CRITICAL: Verify Python version in venv (MUST be 3.11.x, NOT 3.9.x)
python --version  # Should show 3.11.x
which python  # Should point to venv/bin/python

# 7. If it still shows 3.9.x, the venv creation failed - remove and recreate:
# deactivate && rm -rf venv && python3.11 -m venv venv && source venv/bin/activate

# 8. Upgrade pip (required for pyproject.toml support)
pip install --upgrade pip

# 9. Install flakestorm
pip install flakestorm
```

**Troubleshooting:** If you get `Package requires a different Python: 3.9.6 not in '>=3.10'`:
- Your venv is still using Python 3.9 even though Python 3.11 is installed
- **Solution:** `deactivate && rm -rf venv && python3.11 -m venv venv && source venv/bin/activate && python --version`
- Always verify with `python --version` after activating venv - it MUST show 3.10+

**Or using pipx (for CLI use only):**

```bash
pipx install flakestorm
```

**Note:** Requires Python 3.10 or higher. On macOS, Python environments are externally managed, so using a virtual environment is required. Ollama runs independently and doesn't need to be in your virtual environment.

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

## Local Testing

For local testing and validation:
```bash
# Run with minimum score check
flakestorm run --min-score 0.9

# Exit with error code if score is too low
flakestorm run --min-score 0.9 --ci
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

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Tested with Flakestorm</strong><br>
  <img src="https://img.shields.io/badge/tested%20with-flakestorm-brightgreen" alt="Tested with Flakestorm">
</p>
