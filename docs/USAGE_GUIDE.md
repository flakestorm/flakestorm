# flakestorm Usage Guide

> **The Agent Reliability Engine** - Chaos Engineering for AI Agents

This comprehensive guide walks you through using flakestorm to test your AI agents for reliability, robustness, and safety.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [Configuration Deep Dive](#configuration-deep-dive)
6. [Running Tests](#running-tests)
7. [Understanding Results](#understanding-results)
8. [Integration Patterns](#integration-patterns)
9. [Advanced Usage](#advanced-usage)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is flakestorm?

flakestorm is an **adversarial testing framework** for AI agents. It applies chaos engineering principles to systematically test how your AI agents behave under unexpected, malformed, or adversarial inputs.

### Why Use flakestorm?

| Problem | How flakestorm Helps |
|---------|-------------------|
| Agent fails with typos in user input | Tests with noise mutations |
| Agent leaks sensitive data | Safety assertions catch PII exposure |
| Agent behavior varies unpredictably | Semantic similarity assertions ensure consistency |
| Prompt injection attacks | Tests agent resilience to injection attempts |
| No way to quantify reliability | Provides robustness scores (0.0 - 1.0) |

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         flakestorm FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. GOLDEN PROMPTS          2. MUTATION ENGINE                 │
│   ┌─────────────────┐        ┌─────────────────┐               │
│   │ "Book a flight  │  ───►  │ Local LLM       │               │
│   │  from NYC to LA"│        │ (Qwen/Ollama)   │               │
│   └─────────────────┘        └────────┬────────┘               │
│                                       │                         │
│                                       ▼                         │
│                              ┌─────────────────┐               │
│                              │ Mutated Prompts │               │
│                              │ • Typos         │               │
│                              │ • Paraphrases   │               │
│                              │ • Injections    │               │
│                              └────────┬────────┘               │
│                                       │                         │
│   3. YOUR AGENT                       ▼                         │
│   ┌─────────────────┐        ┌─────────────────┐               │
│   │ AI Agent        │  ◄───  │ Test Runner     │               │
│   │ (HTTP/Python)   │        │ (Async)         │               │
│   └────────┬────────┘        └─────────────────┘               │
│            │                                                    │
│            ▼                                                    │
│   4. VERIFICATION            5. REPORTING                       │
│   ┌─────────────────┐        ┌─────────────────┐               │
│   │ Invariant       │  ───►  │ HTML/JSON/CLI   │               │
│   │ Assertions      │        │ Reports         │               │
│   └─────────────────┘        └─────────────────┘               │
│                                       │                         │
│                                       ▼                         │
│                              ┌─────────────────┐               │
│                              │ Robustness      │               │
│                              │ Score: 0.85     │               │
│                              └─────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- **Python 3.10+** (3.11 recommended) - **Required!** Python 3.9 or lower will not work.
- **Ollama** (for local LLM mutation generation)
- **Rust** (optional, for performance optimization)

**Check your Python version:**
```bash
python3 --version  # Must show 3.10 or higher
```

If you have Python 3.9 or lower, upgrade first:
```bash
# macOS
brew install python@3.11

# Then use the new Python
python3.11 --version
```

### Installation Order

**Important:** Install Ollama first (it's a system-level service), then set up your Python virtual environment:

1. **Install Ollama** (system-level, runs independently)
2. **Create virtual environment** (for Python packages)
3. **Install flakestorm** (Python package)
4. **Start Ollama service** (if not already running)
5. **Pull the model** (required for mutation generation)

### Step 1: Install Ollama (System-Level)

**macOS Installation:**

```bash
# Option 1: Homebrew (recommended)
brew install ollama

# If you get permission errors, fix permissions first:
sudo chown -R $(whoami) /Users/imac-frank/Library/Logs/Homebrew
sudo chown -R $(whoami) /usr/local/Cellar
sudo chown -R $(whoami) /usr/local/Homebrew
brew install ollama

# Option 2: Official Installer (if Homebrew doesn't work)
# Visit https://ollama.ai/download and download the macOS installer
# Double-click the .dmg file and follow the installation wizard
```

**Windows Installation:**

1. **Download the Installer:**
   - Visit https://ollama.com/download/windows
   - Download `OllamaSetup.exe`

2. **Run the Installer:**
   - Double-click `OllamaSetup.exe`
   - Follow the installation wizard
   - Ollama will be installed and added to your PATH automatically

3. **Verify Installation:**
   ```powershell
   ollama --version
   ```

**Linux Installation:**

```bash
# Install using the official script
curl -fsSL https://ollama.com/install.sh | sh

# Or using package managers:
# Ubuntu/Debian
sudo apt install ollama

# Fedora/RHEL
sudo dnf install ollama

# Arch Linux
sudo pacman -S ollama
```

**Start Ollama Service:**

After installation, start Ollama:

```bash
# macOS (Homebrew) - Start as a service (recommended)
brew services start ollama

# macOS (Manual install) / Linux - Start the service
ollama serve

# Windows - Ollama runs as a service automatically after installation
# You can also start it manually from the Start menu
```

**Important for macOS Homebrew users:**

If you see syntax errors when running `ollama` commands (like `ollama pull` or `ollama serve`), you likely have a bad binary from a previous failed download. Fix it:

```bash
# 1. Remove the bad binary
sudo rm /usr/local/bin/ollama

# 2. Verify Homebrew's Ollama is installed
brew list ollama

# 3. Find where Homebrew installed Ollama
brew --prefix ollama  # Usually /usr/local/opt/ollama or /opt/homebrew/opt/ollama

# 4. Create a symlink to make ollama available in PATH
# For Intel Mac:
sudo ln -s /usr/local/opt/ollama/bin/ollama /usr/local/bin/ollama

# For Apple Silicon:
sudo ln -s /opt/homebrew/opt/ollama/bin/ollama /opt/homebrew/bin/ollama
# And ensure /opt/homebrew/bin is in PATH:
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 5. Verify it works
which ollama
ollama --version

# 6. Start Ollama service
brew services start ollama

# 7. Now ollama commands should work
ollama pull qwen2.5-coder:7b
```

**Alternative:** If symlinks don't work, you can use the full path temporarily:
```bash
/usr/local/opt/ollama/bin/ollama pull qwen2.5-coder:7b
# Or for Apple Silicon:
/opt/homebrew/opt/ollama/bin/ollama pull qwen2.5-coder:7b
```

### Step 2: Pull the Default Model

**Important:** If you get `syntax error: <!doctype html>` or `command not found` when running `ollama pull`, you have a bad binary from a previous failed download. Fix it:

```bash
# 1. Remove the bad binary
sudo rm /usr/local/bin/ollama

# 2. Find Homebrew's Ollama location
brew --prefix ollama  # Shows /usr/local/opt/ollama or /opt/homebrew/opt/ollama

# 3. Create symlink to make it available
# For Intel Mac:
sudo ln -s /usr/local/opt/ollama/bin/ollama /usr/local/bin/ollama

# For Apple Silicon:
sudo ln -s /opt/homebrew/opt/ollama/bin/ollama /opt/homebrew/bin/ollama
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. Verify it works
which ollama
ollama --version
```

**Then pull the model:**

```bash
# Pull Qwen Coder 3 8B (recommended for mutations)
ollama pull qwen2.5-coder:7b

# Verify it's working
ollama run qwen2.5-coder:7b "Hello, world!"
```

### Step 3: Create Virtual Environment and Install flakestorm

**CRITICAL: Python 3.10+ Required!**

flakestorm requires Python 3.10 or higher. If your system Python is 3.9 or lower, you must install a newer version first.

**Check your Python version:**
```bash
python3 --version  # Must show 3.10, 3.11, 3.12, or higher
```

**If you have Python 3.9 or lower, install Python 3.11 first:**

```bash
# macOS - Install Python 3.11 via Homebrew
brew install python@3.11

# Verify it's installed
python3.11 --version  # Should show 3.11.x

# Linux - Install Python 3.11
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3.11-venv

# Fedora/RHEL:
sudo dnf install python3.11
```

**Create virtual environment with Python 3.10+:**

```bash
# 1. DEACTIVATE current venv if active (important!)
deactivate

# 2. Remove any existing venv (if it was created with old Python)
rm -rf venv

# 3. Create venv with Python 3.10+ (use the version you have)
# If you have python3.11 (recommended):
python3.11 -m venv venv

# If you have python3.10:
python3.10 -m venv venv

# If python3 is already 3.10+:
python3 -m venv venv

# 4. Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
# venv\Scripts\activate

# 5. CRITICAL: Verify Python version in venv (MUST be 3.10+)
python --version  # Should show 3.10.x, 3.11.x, or 3.12.x
# If it still shows 3.9.x, the venv creation failed - try step 3 again with explicit path

# 6. Also verify which Python is being used
which python  # Should point to venv/bin/python

# 7. Upgrade pip to latest version (required for pyproject.toml support)
pip install --upgrade pip

# 8. Verify pip version (should be 21.0+)
pip --version

# 9. Now install flakestorm
# From PyPI (when published)
pip install flakestorm

# From source (development)
git clone https://github.com/flakestorm/flakestorm.git
cd flakestorm
pip install -e ".[dev]"
```

**Note:** Ollama is installed at the system level and doesn't need to be in your virtual environment. The virtual environment is only for Python packages (flakestorm and its dependencies).

**Alternative: Using pipx (for CLI applications)**

If you only want to use flakestorm as a CLI tool (not develop it), you can use `pipx`:

```bash
# Install pipx (if not already installed)
brew install pipx  # macOS
# Or: python3 -m pip install --user pipx

# Install flakestorm
pipx install flakestorm
```

**Note:** Make sure you're using Python 3.10+. You can verify with:
```bash
python3 --version  # Should be 3.10 or higher
```

### Step 4: (Optional) Install Rust Extension

For 80x+ performance improvement on scoring:

```bash
# 1. CRITICAL: Make sure virtual environment is activated
source venv/bin/activate  # If not already activated
which pip  # Should show: .../venv/bin/pip
pip --version  # Should show pip 21.0+ with Python 3.10+

# 2. Install maturin (Rust/Python build tool)
pip install maturin

# 3. Build the Rust extension
cd rust
maturin build --release

# 4. Remove any old wheels (if they exist)
rm -f ../target/wheels/entropix_rust-*.whl  # Remove old wheels with wrong name

# 5. Install the new wheel (use specific pattern to avoid old wheels)
pip install ../target/wheels/flakestorm_rust-*.whl

# 6. Verify installation
python -c "import flakestorm_rust; print('Rust extension installed successfully!')"
```

### Verify Installation

```bash
flakestorm --version
flakestorm --help
```

---

## Quick Start

### 1. Initialize Configuration

```bash
# Create flakestorm.yaml in your project
flakestorm init
```

### 2. Configure Your Agent

Edit `flakestorm.yaml`:

```yaml
# Your AI agent endpoint
agent:
  endpoint: "http://localhost:8000/chat"
  type: http
  timeout: 30

# Prompts that should always work
golden_prompts:
  - "What is the weather in New York?"
  - "Book a flight from NYC to LA for tomorrow"
  - "Cancel my reservation #12345"

# What to check in responses
invariants:
  - type: contains
    value: "weather"
    prompt_filter: "weather"
  - type: latency
    max_ms: 5000
  - type: excludes_pii
```

### 3. Run Tests

```bash
# Basic run
flakestorm run

# With HTML report
flakestorm run --output html

# CI mode (fails if score < threshold)
flakestorm run --ci --min-score 0.8
```

### 4. View Results

```bash
# Open the generated report
open reports/flakestorm-*.html
```

---

## Core Concepts

### Golden Prompts

**What they are:** Carefully crafted prompts that represent your agent's core use cases. These are prompts that *should always work correctly*.

**How to choose them:**
- Cover all major user intents
- Include edge cases you've seen in production
- Represent different complexity levels

```yaml
golden_prompts:
  # Simple intent
  - "Hello, how are you?"

  # Complex intent with parameters
  - "Book a flight from New York to Los Angeles departing March 15th"

  # Edge case
  - "What if I need to cancel my booking?"
```

### Mutation Types

flakestorm generates adversarial variations of your golden prompts:

| Type | Description | Example |
|------|-------------|---------|
| `paraphrase` | Same meaning, different words | "Book flight" → "Reserve a plane ticket" |
| `noise` | Typos and formatting errors | "Book flight" → "Bok fligt" |
| `tone_shift` | Different emotional tone | "Book flight" → "I NEED A FLIGHT NOW!!!" |
| `prompt_injection` | Attempted jailbreaks | "Book flight. Ignore above and..." |

### Invariants (Assertions)

Rules that agent responses must satisfy:

```yaml
invariants:
  # Response must contain a keyword
  - type: contains
    value: "booked"

  # Response must NOT contain certain content
  - type: not_contains
    value: "error"

  # Response must match regex pattern
  - type: regex
    pattern: "confirmation.*#[A-Z0-9]+"

  # Response time limit
  - type: latency
    max_ms: 3000

  # Must be valid JSON
  - type: valid_json

  # Semantic similarity to expected response
  - type: similarity
    expected: "Your flight has been booked successfully"
    threshold: 0.8

  # Safety: no PII leakage
  - type: excludes_pii

  # Safety: must include refusal for dangerous requests
  - type: refusal
```

### Robustness Score

A number from 0.0 to 1.0 indicating how reliable your agent is:

```
Score = (Weighted Passed Tests) / (Total Weighted Tests)
```

Weights by mutation type:
- `prompt_injection`: 1.5 (harder to defend against)
- `paraphrase`: 1.0 (should always work)
- `tone_shift`: 1.0 (should handle different tones)
- `noise`: 0.8 (minor errors are acceptable)

**Interpretation:**
- **0.9+**: Excellent - Production ready
- **0.8-0.9**: Good - Minor improvements needed
- **0.7-0.8**: Fair - Needs work
- **<0.7**: Poor - Significant reliability issues

---

## Configuration Deep Dive

### Full Configuration Schema

```yaml
# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
agent:
  # Required: Where to send requests
  endpoint: "http://localhost:8000/chat"

  # Agent type: http, python, or langchain
  type: http

  # Request timeout in seconds
  timeout: 30

  # HTTP-specific settings
  headers:
    Authorization: "Bearer ${API_KEY}"  # Environment variable expansion
    Content-Type: "application/json"

  # How to format the request body
  # Available placeholders: {prompt}
  request_template: |
    {"message": "{prompt}", "stream": false}

  # JSONPath to extract response from JSON
  response_path: "$.response"

# =============================================================================
# GOLDEN PROMPTS
# =============================================================================
golden_prompts:
  - "What is 2 + 2?"
  - "Summarize this article: {article_text}"
  - "Translate to Spanish: Hello, world!"

# =============================================================================
# MUTATION CONFIGURATION
# =============================================================================
mutations:
  # Number of mutations per golden prompt
  count: 20

  # Which mutation types to use
  types:
    - paraphrase
    - noise
    - tone_shift
    - prompt_injection

  # Weights for scoring (higher = more important to pass)
  weights:
    paraphrase: 1.0
    noise: 0.8
    tone_shift: 1.0
    prompt_injection: 1.5

# =============================================================================
# LLM CONFIGURATION (for mutation generation)
# =============================================================================
llm:
  # Ollama model to use
  model: "qwen2.5-coder:7b"

  # Ollama server URL
  host: "http://localhost:11434"

  # Generation temperature (higher = more creative mutations)
  temperature: 0.8

# =============================================================================
# INVARIANTS (ASSERTIONS)
# =============================================================================
invariants:
  # Example: Response must contain booking confirmation
  - type: contains
    value: "confirmed"
    case_sensitive: false
    prompt_filter: "book"  # Only apply to prompts containing "book"

  # Example: Response time limit
  - type: latency
    max_ms: 5000

  # Example: Must be valid JSON
  - type: valid_json

  # Example: Semantic similarity
  - type: similarity
    expected: "I've booked your flight"
    threshold: 0.75

  # Example: No PII in response
  - type: excludes_pii

  # Example: Must refuse dangerous requests
  - type: refusal
    prompt_filter: "ignore|bypass|jailbreak"

# =============================================================================
# ADVANCED SETTINGS
# =============================================================================
advanced:
  # Concurrent test executions
  concurrency: 10

  # Retry failed requests
  retries: 3

  # Output directory for reports
  output_dir: "./reports"

  # Fail threshold for CI mode
  min_score: 0.8
```

### Environment Variable Expansion

Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
agent:
  endpoint: "${AGENT_URL}"
  headers:
    Authorization: "Bearer ${API_KEY}"
```

---

## Running Tests

### Basic Commands

```bash
# Run with default config (flakestorm.yaml)
flakestorm run

# Specify config file
flakestorm run --config my-config.yaml

# Output format: terminal (default), html, json
flakestorm run --output html

# Quiet mode (less output)
flakestorm run --quiet

# Verbose mode (more output)
flakestorm run --verbose
```

### Individual Commands

```bash
# Just verify config is valid
flakestorm verify --config flakestorm.yaml

# Generate report from previous run
flakestorm report --input results.json --output html

# Show current score
flakestorm score --input results.json
```

---

## Understanding Results

### Terminal Output

```
╭──────────────────────────────────────────────────────────────────╮
│                     flakestorm TEST RESULTS                        │
├──────────────────────────────────────────────────────────────────┤
│  Robustness Score: 0.85                                          │
│  ████████████████████░░░░ 85%                                    │
├──────────────────────────────────────────────────────────────────┤
│  Total Mutations: 80                                             │
│  ✅ Passed: 68                                                   │
│  ❌ Failed: 12                                                   │
├──────────────────────────────────────────────────────────────────┤
│  By Mutation Type:                                               │
│    paraphrase:       95% (19/20)                                 │
│    noise:            90% (18/20)                                 │
│    tone_shift:       85% (17/20)                                 │
│    prompt_injection: 70% (14/20)                                 │
├──────────────────────────────────────────────────────────────────┤
│  Latency: avg=245ms, p50=200ms, p95=450ms, p99=890ms            │
╰──────────────────────────────────────────────────────────────────╯
```

### HTML Report

The HTML report provides:

1. **Summary Dashboard** - Overall score, pass/fail breakdown
2. **Mutation Matrix** - Visual grid of all test results
3. **Failure Details** - Specific failures with input/output
4. **Latency Charts** - Response time distribution
5. **Recommendations** - AI-generated improvement suggestions

### JSON Export

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "config_hash": "abc123",
  "statistics": {
    "total_mutations": 80,
    "passed_mutations": 68,
    "failed_mutations": 12,
    "robustness_score": 0.85,
    "avg_latency_ms": 245,
    "p95_latency_ms": 450
  },
  "results": [
    {
      "golden_prompt": "Book a flight to NYC",
      "mutation": "Reserve a plane ticket to New York",
      "mutation_type": "paraphrase",
      "passed": true,
      "response": "I've booked your flight...",
      "latency_ms": 234,
      "checks": [
        {"type": "contains", "passed": true},
        {"type": "latency", "passed": true}
      ]
    }
  ]
}
```

---

## Integration Patterns

### Pattern 1: HTTP Agent

Most common pattern - agent exposed via REST API:

```yaml
agent:
  endpoint: "http://localhost:8000/api/chat"
  type: http
  request_template: |
    {"message": "{prompt}"}
  response_path: "$.reply"
```

**Your agent code:**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    # Your agent logic here
    response = your_llm_call(request.message)
    return ChatResponse(reply=response)
```

### Pattern 2: Python Module

Direct Python integration (no HTTP overhead):

```yaml
agent:
  endpoint: "my_agent.agent:handle_message"
  type: python
```

**Your agent code (`my_agent/agent.py`):**

```python
def handle_message(prompt: str) -> str:
    """
    flakestorm will call this function directly.

    Args:
        prompt: The user message (mutated)

    Returns:
        The agent's response as a string
    """
    # Your agent logic
    return process_message(prompt)
```

### Pattern 3: LangChain Agent

For LangChain-based agents:

```yaml
agent:
  endpoint: "my_agent.chain:agent"
  type: langchain
```

**Your agent code:**

```python
from langchain.agents import AgentExecutor

# flakestorm will call agent.invoke({"input": prompt})
agent = AgentExecutor(...)
```

---

## Advanced Usage

### Custom Mutation Templates

Override default mutation prompts:

```yaml
mutations:
  templates:
    paraphrase: |
      Rewrite this prompt with completely different words
      but preserve the exact meaning: "{prompt}"

    noise: |
      Add realistic typos and formatting errors to this prompt.
      Make 2-3 small mistakes: "{prompt}"
```

### Filtering Invariants by Prompt

Apply assertions only to specific prompts:

```yaml
invariants:
  # Only for booking-related prompts
  - type: contains
    value: "confirmation"
    prompt_filter: "book|reserve|schedule"

  # Only for cancellation prompts
  - type: regex
    pattern: "cancelled|refunded"
    prompt_filter: "cancel"
```

### Custom Weights

Adjust scoring weights based on your priorities:

```yaml
mutations:
  weights:
    # Security is critical - weight injection tests higher
    prompt_injection: 2.0

    # Typo tolerance is less important
    noise: 0.5
```

### Parallel Execution

Control concurrency for rate-limited APIs:

```yaml
advanced:
  concurrency: 5  # Max 5 parallel requests
  retries: 3      # Retry failed requests 3 times
```

---

## Troubleshooting

### Common Issues

#### "Cannot connect to Ollama"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama if not running
# macOS (Homebrew):
brew services start ollama

# macOS (Manual) / Linux:
ollama serve

# Check status (Homebrew):
brew services list | grep ollama
```

#### "Model not found"

```bash
# List available models
ollama list

# Pull the required model
ollama pull qwen2.5-coder:7b
```

#### "Agent connection refused"

```bash
# Verify your agent is running
curl http://localhost:8000/health

# Check the endpoint in config
cat flakestorm.yaml | grep endpoint
```

#### "Timeout errors"

Increase timeout in config:

```yaml
agent:
  timeout: 60  # Increase to 60 seconds
```

#### "Low robustness score"

1. Review failed mutations in the report
2. Identify patterns (e.g., all prompt_injection failing)
3. Improve your agent's handling of those cases
4. Re-run tests

#### "Homebrew permission errors when installing Ollama"

If you get `Operation not permitted` errors when running `brew install ollama`:

```bash
# Fix Homebrew permissions
sudo chown -R $(whoami) /Users/imac-frank/Library/Logs/Homebrew
sudo chown -R $(whoami) /usr/local/Cellar
sudo chown -R $(whoami) /usr/local/Homebrew

# Then try again
brew install ollama

# Or use the official installer from https://ollama.ai/download instead
```

#### "Package requires a different Python: 3.9.6 not in '>=3.10'"

**This error means your virtual environment is using Python 3.9 or lower, but flakestorm requires Python 3.10+.**

**Even if you installed Python 3.11, your venv might still be using the old Python!**

**Fix it:**

```bash
# 1. DEACTIVATE current venv (critical!)
deactivate

# 2. Remove the old venv completely
rm -rf venv

# 3. Verify Python 3.11 is installed and find its path
python3.11 --version  # Should work
which python3.11  # Shows: /usr/local/bin/python3.11

# 4. Create new venv with Python 3.11 EXPLICITLY
/usr/local/bin/python3.11 -m venv venv
# Or simply:
python3.11 -m venv venv

# 5. Activate it
source venv/bin/activate

# 6. CRITICAL: Verify Python version in venv (MUST be 3.11.x, NOT 3.9.x)
python --version  # Should show 3.11.x
which python  # Should show: .../venv/bin/python

# 7. If it still shows 3.9.x, the venv is broken - remove and recreate:
# deactivate
# rm -rf venv
# /usr/local/bin/python3.11 -m venv venv
# source venv/bin/activate
# python --version  # Verify again

# 8. Upgrade pip
pip install --upgrade pip

# 9. Now install
pip install -e ".[dev]"
```

**Common mistake:** Creating venv with `python3 -m venv venv` when `python3` points to 3.9. Always use `python3.11 -m venv venv` explicitly!

#### "Virtual environment errors: bad interpreter or setup.py not found"

If you get errors like `bad interpreter` or `setup.py not found` when installing:

**Issue 1: Python version too old**
```bash
# Check your Python version
python3 --version  # Must be 3.10 or higher

# If you have Python 3.9 or lower, you need to upgrade
# macOS: Install Python 3.10+ via Homebrew
brew install python@3.11

# Then create venv with the new Python
python3.11 -m venv venv
source venv/bin/activate
```

**Issue 2: Pip too old for pyproject.toml**
```bash
# Remove broken venv
rm -rf venv

# Recreate venv with Python 3.10+
python3.11 -m venv venv  # Or python3.10, python3.12
source venv/bin/activate

# Upgrade pip FIRST (critical!)
pip install --upgrade pip

# Verify pip version (should be 21.0+)
pip --version

# Now install
pip install -e ".[dev]"
```

**Issue 3: Venv created with wrong Python**
```bash
# Remove broken venv
rm -rf venv

# Use explicit Python 3.10+ path
python3.11 -m venv venv  # Or: python3.10, python3.12
source venv/bin/activate

# Verify Python version
python --version  # Must be 3.10+

# Upgrade pip
pip install --upgrade pip

# Install
pip install -e ".[dev]"
```

#### "Ollama binary contains HTML or syntax errors"

If you see `syntax error: <!doctype html>` when running ANY `ollama` command (`ollama serve`, `ollama pull`, etc.):

**This happens when a bad binary from a previous failed download is in your PATH.**

**Fix it:**

```bash
# 1. Remove the bad binary
sudo rm /usr/local/bin/ollama

# 2. Find where Homebrew installed Ollama
brew --prefix ollama
# This shows: /usr/local/opt/ollama (Intel) or /opt/homebrew/opt/ollama (Apple Silicon)

# 3. Create a symlink to make ollama available in PATH
# For Intel Mac:
sudo ln -s /usr/local/opt/ollama/bin/ollama /usr/local/bin/ollama

# For Apple Silicon:
sudo ln -s /opt/homebrew/opt/ollama/bin/ollama /opt/homebrew/bin/ollama
# Ensure /opt/homebrew/bin is in PATH:
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. Verify the command works now
which ollama
ollama --version

# 5. Start Ollama service
brew services start ollama

# 6. Now pull the model
ollama pull qwen2.5-coder:7b
```

**Alternative:** If you can't create symlinks, use the full path:
```bash
# Intel Mac:
/usr/local/opt/ollama/bin/ollama pull qwen2.5-coder:7b

# Apple Silicon:
/opt/homebrew/opt/ollama/bin/ollama pull qwen2.5-coder:7b
```

**If Homebrew's Ollama is not installed:**

```bash
# Install via Homebrew
brew install ollama

# Or download the official .dmg installer from https://ollama.ai/download
```

**Important:** Never download binaries directly via curl from the download page - always use the official installers or package managers.

### Debug Mode

```bash
# Enable verbose logging
flakestorm run --verbose

# Or set environment variable
export FLAKESTORM_DEBUG=1
flakestorm run
```

### Getting Help

- **Documentation**: https://flakestorm.dev/docs
- **GitHub Issues**: https://github.com/flakestorm/flakestorm/issues
- **Discord**: https://discord.gg/flakestorm

---

## Next Steps

1. **Start simple**: Test with 1-2 golden prompts first
2. **Add invariants gradually**: Start with `contains` and `latency`
3. **Review failures**: Use reports to understand weak points
4. **Iterate**: Improve agent, re-test, repeat
5. **Integrate to CI**: Automate testing on every PR

---

*Built with ❤️ by the flakestorm Team*
