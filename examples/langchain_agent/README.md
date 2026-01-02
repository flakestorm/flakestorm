# LangChain Agent Example

This example demonstrates how to test a LangChain agent with flakestorm. The agent uses LangChain's `LLMChain` to process user queries.

## Overview

The example includes:
- A LangChain agent that uses **Google Gemini AI** (if API key is set) or falls back to a mock LLM
- A `flakestorm.yaml` configuration file for testing the agent
- Instructions for running flakestorm against the agent
- Automatic fallback to mock LLM if API key is not set (no API keys required for basic testing)

## Features

- **Real LLM Support**: Uses Google Gemini AI (if API key is set) for realistic testing
- **Automatic Fallback**: Falls back to a mock LLM if API key is not set (no API keys required for basic testing)
- **Input-Aware Processing**: Actually processes input and can fail on certain inputs, making it realistic for testing
- **Realistic Failure Modes**: The agent can fail on empty inputs, very long inputs, and prompt injection attempts
- **flakestorm Integration**: Ready-to-use configuration for testing robustness with meaningful results

## Setup

### 1. Create Virtual Environment (Recommended)

```bash
cd examples/langchain_agent

# Create virtual environment
python -m venv lc_test_venv

# Activate virtual environment
# On macOS/Linux:
source lc_test_venv/bin/activate

# On Windows (PowerShell):
# lc_test_venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
# lc_test_venv\Scripts\activate.bat
```

**Note:** You should see `(venv)` in your terminal prompt after activation.

### 2. Install Dependencies

```bash
# Make sure virtual environment is activated
pip install -r requirements.txt

# This will install:
# - langchain-core, langchain-community (LangChain packages)
# - langchain-google-genai (for Google Gemini support)
# - flakestorm (for testing)

# Or install manually:
# For modern LangChain (0.3.x+) with Gemini:
# pip install langchain-core langchain-community langchain-google-genai flakestorm

# For older LangChain (0.1.x, 0.2.x):
# pip install langchain flakestorm
```

**Note:** The agent code automatically handles different LangChain versions. If you encounter import errors, try:
```bash
# Install all LangChain packages for maximum compatibility
pip install langchain langchain-core langchain-community
```

### 3. Verify the Agent Works

```bash
# Test the agent directly
python -c "from agent import chain; result = chain.invoke({'input': 'Hello!'}); print(result)"
```

Expected output:
```
{'input': 'Hello!', 'text': 'I can help you with that!'}
```

## Running flakestorm Tests

### From the Project Root (Recommended)

```bash
# Make sure you're in the project root (not in examples/langchain_agent)
cd /path/to/flakestorm

# Run flakestorm against the LangChain agent
flakestorm run --config examples/langchain_agent/flakestorm.yaml
```

**This is the easiest way** - no PYTHONPATH setup needed!

### From the Example Directory

If you want to run from `examples/langchain_agent`, you need to set the Python path:

```bash
# If you're in examples/langchain_agent
cd examples/langchain_agent

# Option 1: Set PYTHONPATH (recommended)
# On macOS/Linux:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
flakestorm run

# On Windows (PowerShell):
$env:PYTHONPATH = "$env:PYTHONPATH;$PWD"
flakestorm run

# Option 2: Update flakestorm.yaml to use full path
# Change: endpoint: "examples.langchain_agent.agent:chain"
# To: endpoint: "agent:chain"
# Then run: flakestorm run
```

**Note:** The `flakestorm.yaml` is configured to run from the project root by default. For easiest setup, run from the project root. If running from the example directory, either set `PYTHONPATH` or update the `endpoint` in `flakestorm.yaml`.

## Understanding the Configuration

### Agent Configuration

The `flakestorm.yaml` file configures flakestorm to test the LangChain agent:

```yaml
agent:
  endpoint: "examples.langchain_agent.agent:chain"  # Module path: imports chain from agent.py
  type: "langchain"         # Tells flakestorm to use LangChain adapter
  timeout: 30000            # 30 second timeout
```

**How it works:**
- flakestorm imports `chain` from the `agent` module
- It calls `chain.invoke({"input": prompt})` or `chain.ainvoke({"input": prompt})`
- The adapter handles different LangChain interfaces automatically

### Choosing the Right Invariants

**Important:** Only use invariants that match your agent's expected output format!

**For Text-Only Agents (like this example):**
```yaml
invariants:
  - type: "latency"
    max_ms: 10000
  - type: "not_contains"
    value: ""  # Response shouldn't be empty
  - type: "excludes_pii"
  - type: "refusal_check"
```

**For JSON-Only Agents:**
```yaml
invariants:
  - type: "valid_json"  # ✅ Use this if agent returns JSON
  - type: "latency"
    max_ms: 5000
```

**For Agents with Mixed Output:**
```yaml
invariants:
  - type: "latency"
    max_ms: 5000
  # Use prompt_filter to apply JSON check only to specific prompts
  - type: "valid_json"
    prompt_filter: "api|json|data"  # Only check JSON for prompts containing these words
```

### Golden Prompts

The configuration includes 8 example prompts that should work correctly:
- Weather queries
- Educational questions
- Help requests
- Technical explanations

flakestorm will generate mutations of these prompts to test robustness.

### Invariants

The tests verify:
- **Latency**: Response under 10 seconds
- **Contains "help"**: Response should contain helpful content (stricter than just checking for space)
- **Minimum Length**: Response must be at least 20 characters (ensures meaningful response)
- **PII Safety**: No personally identifiable information
- **Refusal**: Agent should refuse dangerous prompt injections

**Important:** 
- flakestorm requires **at least 3 invariants** to ensure comprehensive testing
- This agent returns plain text responses, so we don't use `valid_json` invariant
- Only use `valid_json` if your agent is supposed to return JSON responses
- The invariants are **stricter** than before to catch more issues and produce meaningful test results

## Using Google Gemini (Real LLM)

This example **already uses Google Gemini** if you set the API key! Just set the environment variable:

```bash
# macOS/Linux:
export GOOGLE_AI_API_KEY=your-api-key-here

# Windows (PowerShell):
$env:GOOGLE_AI_API_KEY="your-api-key-here"

# Windows (Command Prompt):
set GOOGLE_AI_API_KEY=your-api-key-here
```

**Get your API key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and set it as the environment variable above

**Without API Key:**
If you don't set the API key, the agent automatically falls back to a mock LLM that still processes input meaningfully. This is useful for testing without API costs.

**Other LLM Options:**
You can modify `agent.py` to use other LLMs:
- `ChatOpenAI` - OpenAI GPT models (requires `langchain-openai`)
- `ChatAnthropic` - Anthropic Claude (requires `langchain-anthropic`)
- `ChatOllama` - Local Ollama models (requires `langchain-ollama`)

## Expected Test Results

When you run flakestorm, you'll see:

1. **Mutation Generation**: flakestorm generates 20 mutations per golden prompt (200 total tests with 10 golden prompts)
2. **Test Execution**: Each mutation is tested against the agent
3. **Results Report**: HTML report showing:
   - Robustness score (0.0 - 1.0)
   - Pass/fail breakdown by mutation type
   - Detailed failure analysis
   - Recommendations for improvement

### Why This Agent is Better for Testing

**Previous Issue:** The original agent used `FakeListLLM`, which ignored input and just cycled through 8 predefined responses. This meant:
- Mutations had no effect (agent didn't read them)
- Invariants were too lax (always passed)
- 100% reliability score was meaningless

**Current Solution:** The agent uses **Google Gemini AI** (if API key is set) or a mock LLM:
- ✅ **With Gemini**: Real LLM that processes input naturally, can fail on edge cases
- ✅ **Without API Key**: Mock LLM that still processes input meaningfully
- ✅ Reads and analyzes the input
- ✅ Can fail on empty/whitespace inputs
- ✅ Can fail on very long inputs (>5000 chars)
- ✅ Detects and refuses prompt injection attempts
- ✅ Returns context-aware responses based on input content
- ✅ Stricter invariants (checks for meaningful content, not just non-empty)

**Expected Results:**
- **With Gemini**: More realistic failures, reliability score typically 70-90% (real LLM behavior)
- **With Mock LLM**: Some failures on edge cases, reliability score typically 80-95%
- You should see **some failures** on edge cases (empty inputs, prompt injections, etc.)
- This makes the test results **meaningful** and helps identify real robustness issues

## Common Issues

### "ModuleNotFoundError: No module named 'agent'" or "No module named 'examples'"

**Solution 1 (Recommended):** Run from the project root:
```bash
cd /path/to/flakestorm  # Go to project root
flakestorm run --config examples/langchain_agent/flakestorm.yaml
```

**Solution 2:** If running from `examples/langchain_agent`, set PYTHONPATH:
```bash
# macOS/Linux:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
flakestorm run

# Windows (PowerShell):
$env:PYTHONPATH = "$env:PYTHONPATH;$PWD"
flakestorm run
```

**Solution 3:** Update `flakestorm.yaml` to use relative path:
```yaml
agent:
  endpoint: "agent:chain"  # Instead of "examples.langchain_agent.agent:chain"
```

### "ModuleNotFoundError: No module named 'langchain.chains'" or "cannot import name 'LLMChain'"

**Solution:** This happens with newer LangChain versions (0.3.x+). Install the required packages:

```bash
# Install all LangChain packages for compatibility
pip install langchain langchain-core langchain-community

# Or if using requirements.txt:
pip install -r requirements.txt
```

The agent code automatically tries multiple import strategies, so installing all packages ensures compatibility.

### "AttributeError: 'LLMChain' object has no attribute 'invoke'"

**Solution:** Update your LangChain version:
```bash
pip install --upgrade langchain langchain-core
```

### "Timeout errors"

**Solution:** Increase timeout in `flakestorm.yaml`:
```yaml
agent:
  timeout: 60000  # 60 seconds
```

## Customizing the Agent

### Add Tools/Agents

You can extend the agent to use LangChain tools or agents:

```python
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI

llm = OpenAI(temperature=0)
tools = [
    Tool(
        name="Calculator",
        func=lambda x: str(eval(x)),
        description="Useful for mathematical calculations"
    )
]

agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

# Export for flakestorm
chain = agent
```

### Add Memory

Add conversation memory to your agent:

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
chain = LLMChain(llm=llm, prompt=prompt_template, memory=memory)
```

## Next Steps

1. **Run the tests**: `flakestorm run --config examples/langchain_agent/flakestorm.yaml`
2. **Review the report**: Check `reports/flakestorm-*.html`
3. **Improve robustness**: Fix issues found in the report
4. **Re-test**: Run flakestorm again to verify improvements

## Learn More

- [LangChain Documentation](https://python.langchain.com/)
- [flakestorm Usage Guide](../docs/USAGE_GUIDE.md)
- [flakestorm Configuration Guide](../docs/CONFIGURATION_GUIDE.md)

