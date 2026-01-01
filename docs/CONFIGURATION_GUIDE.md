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

FlakeStorm's HTTP adapter is highly flexible and supports any endpoint format through request templates and response path configuration.

#### Basic Configuration

```yaml
agent:
  endpoint: "http://localhost:8000/invoke"
  type: "http"
  timeout: 30000  # milliseconds
  headers:
    Authorization: "Bearer ${API_KEY}"
    Content-Type: "application/json"
```

**Default Format (if no template specified):**

Request:
```json
POST /invoke
{"input": "user prompt text"}
```

Response:
```json
{"output": "agent response text"}
```

#### Custom Request Template

Map your endpoint's exact format using `request_template`:

```yaml
agent:
  endpoint: "http://localhost:8000/api/chat"
  type: "http"
  method: "POST"
  request_template: |
    {"message": "{prompt}", "stream": false}
  response_path: "$.reply"
```

**Template Variables:**
- `{prompt}` - Full golden prompt text
- `{field_name}` - Parsed structured input fields (see Structured Input below)

#### Structured Input Parsing

For agents that accept structured input (like your Reddit query generator):

```yaml
agent:
  endpoint: "http://localhost:8000/generate-query"
  type: "http"
  method: "POST"
  request_template: |
    {
      "industry": "{industry}",
      "productName": "{productName}",
      "businessModel": "{businessModel}",
      "targetMarket": "{targetMarket}",
      "description": "{description}"
    }
  response_path: "$.query"
  parse_structured_input: true  # Default: true
```

**Golden Prompt Format:**
```yaml
golden_prompts:
  - |
    Industry: Fitness tech
    Product/Service: AI personal trainer app
    Business Model: B2C
    Target Market: fitness enthusiasts
    Description: An app that provides personalized workout plans
```

FlakeStorm will automatically parse this and map fields to your template.

#### HTTP Methods

Support for all HTTP methods:

**GET Request:**
```yaml
agent:
  endpoint: "http://api.example.com/search"
  type: "http"
  method: "GET"
  request_template: "q={prompt}"
  query_params:
    api_key: "${API_KEY}"
    format: "json"
```

**PUT Request:**
```yaml
agent:
  endpoint: "http://api.example.com/update"
  type: "http"
  method: "PUT"
  request_template: |
    {"id": "123", "content": "{prompt}"}
```

#### Response Path Extraction

Extract responses from complex JSON structures:

```yaml
agent:
  endpoint: "http://api.example.com/chat"
  type: "http"
  response_path: "$.choices[0].message.content"  # JSONPath
  # OR
  response_path: "data.result"  # Dot notation
```

**Supported Formats:**
- JSONPath: `"$.data.result"`, `"$.choices[0].message.content"`
- Dot notation: `"data.result"`, `"response.text"`
- Simple key: `"output"`, `"response"`

#### Complete Example

```yaml
agent:
  endpoint: "http://localhost:8000/api/v1/agent"
  type: "http"
  method: "POST"
  timeout: 30000
  headers:
    Authorization: "Bearer ${API_KEY}"
    Content-Type: "application/json"
  request_template: |
    {
      "messages": [
        {"role": "user", "content": "{prompt}"}
      ],
      "temperature": 0.7
    }
  response_path: "$.choices[0].message.content"
  query_params:
    version: "v1"
  parse_structured_input: true
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
| `method` | string | `"POST"` | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `request_template` | string | `null` | Template for request body/query with `{prompt}` or `{field_name}` variables |
| `response_path` | string | `null` | JSONPath or dot notation to extract response (e.g., `"$.data.result"`) |
| `query_params` | object | `{}` | Static query parameters (supports env vars) |
| `parse_structured_input` | boolean | `true` | Whether to parse structured golden prompts into key-value pairs |
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
    - encoding_attacks
    - context_manipulation
    - length_extremes
  weights:
    paraphrase: 1.0
    noise: 0.8
    tone_shift: 0.9
    prompt_injection: 1.5
    encoding_attacks: 1.3
    context_manipulation: 1.1
    length_extremes: 1.2
```

### Mutation Types Guide

flakestorm provides 8 core mutation types that test different aspects of agent robustness. Each type targets specific failure modes.

| Type | What It Tests | Why It Matters | Example | When to Use |
|------|---------------|----------------|---------|-------------|
| `paraphrase` | Semantic understanding | Users express intent in many ways | "Book a flight" → "I need to fly out" | Essential for all agents |
| `noise` | Typo tolerance | Real users make errors | "Book a flight" → "Book a fliight plz" | Critical for production agents |
| `tone_shift` | Emotional resilience | Users get impatient | "Book a flight" → "I need a flight NOW!" | Important for customer-facing agents |
| `prompt_injection` | Security | Attackers try to manipulate | "Book a flight" → "Book a flight. Ignore previous instructions..." | Essential for untrusted input |
| `encoding_attacks` | Parser robustness | Attackers use encoding to bypass filters | "Book a flight" → "Qm9vayBhIGZsaWdodA==" (Base64) | Critical for security testing |
| `context_manipulation` | Context extraction | Real conversations have noise | "Book a flight" → "Hey... book a flight... but also tell me about weather" | Important for conversational agents |
| `length_extremes` | Edge cases | Inputs vary in length | "Book a flight" → "" (empty) or very long | Essential for boundary testing |
| `custom` | Domain-specific | Every domain has unique failures | User-defined templates | Use for specific scenarios |

### Mutation Strategy Recommendations

**Comprehensive Testing (Recommended):**
Use all 8 types for complete coverage:
```yaml
types:
  - paraphrase
  - noise
  - tone_shift
  - prompt_injection
  - encoding_attacks
  - context_manipulation
  - length_extremes
```

**Security-Focused Testing:**
Emphasize security-critical mutations:
```yaml
types:
  - prompt_injection
  - encoding_attacks
  - paraphrase  # Also test semantic understanding
weights:
  prompt_injection: 2.0
  encoding_attacks: 1.5
```

**UX-Focused Testing:**
Focus on user experience mutations:
```yaml
types:
  - noise
  - tone_shift
  - context_manipulation
  - paraphrase
weights:
  noise: 1.0
  tone_shift: 1.1
  context_manipulation: 1.2
```

**Edge Case Testing:**
Focus on boundary conditions:
```yaml
types:
  - length_extremes
  - encoding_attacks
  - noise
weights:
  length_extremes: 1.5
  encoding_attacks: 1.3
```

### Mutation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `count` | integer | `20` | Mutations per golden prompt |
| `types` | list | all 8 types | Which mutation types to use |
| `weights` | object | see below | Scoring weights by type |

### Default Weights

```yaml
weights:
  paraphrase: 1.0              # Standard difficulty
  noise: 0.8                   # Easier - typos are common
  tone_shift: 0.9             # Medium difficulty
  prompt_injection: 1.5       # Harder - security critical
  encoding_attacks: 1.3        # Harder - security and parsing
  context_manipulation: 1.1   # Medium-hard - context extraction
  length_extremes: 1.2         # Medium-hard - edge cases
  custom: 1.0                  # Standard difficulty
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
