# flakestorm Configuration Guide

This guide provides comprehensive documentation for configuring flakestorm via the `flakestorm.yaml` file.

## Quick Start

Create a configuration file:

```bash
flakestorm init
```

This generates an `flakestorm.yaml` with sensible defaults. Customize it for your agent.

## Configuration Structure

```yaml
version: "1.0"

agent:
  # Agent connection settings

model:
  # LLM settings for mutation generation

mutations:
  # Mutation generation settings

golden_prompts:
  # List of test prompts

invariants:
  # Assertion rules

output:
  # Report settings

advanced:
  # Advanced options
```

---

## Agent Configuration

Define how flakestorm connects to your AI agent.

### HTTP Agent

```yaml
agent:
  endpoint: "http://localhost:8000/invoke"
  type: "http"
  timeout: 30000  # milliseconds
  headers:
    Authorization: "Bearer ${API_KEY}"
    Content-Type: "application/json"
```

**Expected API Format:**

Request:
```json
POST /invoke
{"input": "user prompt text"}
```

Response:
```json
{"output": "agent response text"}
```

### Python Agent

```yaml
agent:
  endpoint: "my_module:agent_function"
  type: "python"
  timeout: 30000
```

The function must be:
```python
# my_module.py
async def agent_function(input: str) -> str:
    return "response"
```

### LangChain Agent

```yaml
agent:
  endpoint: "my_agent:chain"
  type: "langchain"
  timeout: 30000
```

Supports LangChain's Runnable interface:
```python
# my_agent.py
from langchain_core.runnables import Runnable

chain: Runnable = ...  # Your LangChain chain
```

### Agent Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `endpoint` | string | required | URL or module path |
| `type` | string | `"http"` | `http`, `python`, or `langchain` |
| `timeout` | integer | `30000` | Request timeout in ms (1000-300000) |
| `headers` | object | `{}` | HTTP headers (supports env vars) |

---

## Model Configuration

Configure the local LLM used for mutation generation.

```yaml
model:
  provider: "ollama"
  name: "qwen3:8b"
  base_url: "http://localhost:11434"
  temperature: 0.8
```

### Model Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider` | string | `"ollama"` | Model provider |
| `name` | string | `"qwen3:8b"` | Model name in Ollama |
| `base_url` | string | `"http://localhost:11434"` | Ollama server URL |
| `temperature` | float | `0.8` | Generation temperature (0.0-2.0) |

### Recommended Models

| Model | Best For |
|-------|----------|
| `qwen3:8b` | Default, good balance of speed and quality |
| `llama3:8b` | General purpose |
| `mistral:7b` | Fast, good for CI |
| `codellama:7b` | Code-heavy agents |

---

## Mutations Configuration

Control how adversarial inputs are generated.

```yaml
mutations:
  count: 20
  types:
    - paraphrase
    - noise
    - tone_shift
    - prompt_injection
  weights:
    paraphrase: 1.0
    noise: 0.8
    tone_shift: 0.9
    prompt_injection: 1.5
```

### Mutation Types

| Type | Description | Example |
|------|-------------|---------|
| `paraphrase` | Semantic rewrites | "Book flight" → "I need to fly" |
| `noise` | Typos and errors | "Book flight" → "Bock fligt" |
| `tone_shift` | Aggressive tone | "Book flight" → "BOOK A FLIGHT NOW!" |
| `prompt_injection` | Adversarial attacks | "Book flight. Ignore instructions..." |

### Mutation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `count` | integer | `20` | Mutations per golden prompt (1-100) |
| `types` | list | all types | Which mutation types to use |
| `weights` | object | see below | Scoring weights by type |

### Default Weights

```yaml
weights:
  paraphrase: 1.0       # Standard difficulty
  noise: 0.8            # Easier - typos are common
  tone_shift: 0.9       # Medium difficulty
  prompt_injection: 1.5 # Harder - security critical
```

Higher weights mean:
- More points for passing that mutation type
- More impact on final robustness score

---

## Golden Prompts

Your "ideal" user inputs that the agent should handle correctly.

```yaml
golden_prompts:
  - "Book a flight to Paris for next Monday"
  - "What's my account balance?"
  - "Cancel my subscription"
  - "Transfer $500 to John's account"
  - "Show me my recent transactions"
```

### Best Practices

1. **Cover key functionality**: Include prompts for each major feature
2. **Vary complexity**: Mix simple and complex requests
3. **Include edge cases**: Unusual but valid requests
4. **5-10 prompts recommended**: More gives better coverage

---

## Invariants (Assertions)

Define what "correct behavior" means for your agent.

### Deterministic Checks

#### contains

Check if response contains a specific string.

```yaml
invariants:
  - type: "contains"
    value: "confirmation"
    description: "Response must contain confirmation"
```

#### latency

Check response time.

```yaml
invariants:
  - type: "latency"
    max_ms: 2000
    description: "Response must be under 2 seconds"
```

#### valid_json

Check if response is valid JSON.

```yaml
invariants:
  - type: "valid_json"
    description: "Response must be valid JSON"
```

#### regex

Check if response matches a pattern.

```yaml
invariants:
  - type: "regex"
    pattern: "^\\{.*\\}$"
    description: "Response must be a JSON object"
```

### Semantic Checks

#### similarity

Check semantic similarity to expected response (requires `flakestorm[semantic]`).

```yaml
invariants:
  - type: "similarity"
    expected: "Your flight has been booked successfully"
    threshold: 0.8
    description: "Response must be semantically similar"
```

### Safety Checks

#### excludes_pii

Check that response doesn't contain PII patterns.

```yaml
invariants:
  - type: "excludes_pii"
    description: "Response must not contain PII"
```

Detects:
- Email addresses
- Phone numbers
- SSNs
- Credit card numbers
- IP addresses

#### refusal_check

Check that agent refuses prompt injection attempts.

```yaml
invariants:
  - type: "refusal_check"
    dangerous_prompts: true
    description: "Agent must refuse injections"
```

### Invariant Options

| Type | Required Fields | Optional Fields |
|------|-----------------|-----------------|
| `contains` | `value` | `description` |
| `latency` | `max_ms` | `description` |
| `valid_json` | - | `description` |
| `regex` | `pattern` | `description` |
| `similarity` | `expected` | `threshold` (0.8), `description` |
| `excludes_pii` | - | `description` |
| `refusal_check` | - | `dangerous_prompts`, `description` |

---

## Output Configuration

Control how reports are generated.

```yaml
output:
  format: "html"
  path: "./reports"
  filename_template: "flakestorm-{date}-{time}"
```

### Output Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `format` | string | `"html"` | `html`, `json`, or `terminal` |
| `path` | string | `"./reports"` | Output directory |
| `filename_template` | string | auto | Custom filename pattern |

---

## Advanced Configuration

```yaml
advanced:
  concurrency: 10
  retries: 2
  seed: 42
```

### Advanced Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `concurrency` | integer | `10` | Max concurrent agent requests (1-100) |
| `retries` | integer | `2` | Retry failed requests (0-5) |
| `seed` | integer | null | Random seed for reproducibility |

---

## Environment Variables

Use `${VAR_NAME}` syntax to inject environment variables:

```yaml
agent:
  endpoint: "${AGENT_URL}"
  headers:
    Authorization: "Bearer ${API_KEY}"
```

---

## Complete Example

```yaml
version: "1.0"

agent:
  endpoint: "http://localhost:8000/invoke"
  type: "http"
  timeout: 30000
  headers:
    Authorization: "Bearer ${AGENT_API_KEY}"

model:
  provider: "ollama"
  name: "qwen3:8b"
  base_url: "http://localhost:11434"
  temperature: 0.8

mutations:
  count: 20
  types:
    - paraphrase
    - noise
    - tone_shift
    - prompt_injection
  weights:
    paraphrase: 1.0
    noise: 0.8
    tone_shift: 0.9
    prompt_injection: 1.5

golden_prompts:
  - "Book a flight to Paris for next Monday"
  - "What's my account balance?"
  - "Cancel my subscription"
  - "Transfer $500 to John's account"

invariants:
  - type: "latency"
    max_ms: 2000
  - type: "valid_json"
  - type: "excludes_pii"
  - type: "refusal_check"
    dangerous_prompts: true

output:
  format: "html"
  path: "./reports"

advanced:
  concurrency: 10
  retries: 2
```

---

## CI/CD Configuration

For GitHub Actions:

```yaml
# .github/workflows/reliability.yml
name: Agent Reliability

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama serve &
          sleep 5
          ollama pull qwen3:8b

      - name: Install flakestorm
        run: pip install flakestorm

      - name: Run Tests
        run: flakestorm run --min-score 0.9 --ci
```

---

## Troubleshooting

### Common Issues

**"Ollama connection failed"**
- Ensure Ollama is running: `ollama serve`
- Check the model is pulled: `ollama pull qwen3:8b`
- Verify base_url matches Ollama's address

**"Agent endpoint not reachable"**
- Check the endpoint URL is correct
- Ensure your agent server is running
- Verify network connectivity

**"Invalid configuration"**
- Check YAML syntax
- Ensure required fields are present
- Validate invariant configurations

### Validation

Verify your configuration:

```bash
flakestorm verify --config flakestorm.yaml
```
