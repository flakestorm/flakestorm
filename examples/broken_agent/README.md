# Broken Agent Example

This example demonstrates a deliberately fragile AI agent that Entropix can detect issues with.

## The "Broken" Agent

The agent in `agent.py` has several intentional flaws:

1. **Fragile Intent Parsing**: Only recognizes exact keyword matches
2. **No Typo Tolerance**: Fails on any spelling variations
3. **Hostile Input Vulnerability**: Crashes on aggressive tone
4. **Prompt Injection Susceptible**: Follows injected instructions

## Running the Example

### 1. Start the Agent Server

```bash
cd examples/broken_agent
pip install fastapi uvicorn
uvicorn agent:app --port 8000
```

### 2. Run Entropix Against It

```bash
# From the project root
entropix run --config examples/broken_agent/entropix.yaml
```

### 3. See the Failures

The report will show how the agent fails on:
- Paraphrased requests ("I want to fly" vs "Book a flight")
- Typos ("Bock a fligt")
- Aggressive tone ("BOOK A FLIGHT NOW!!!")
- Prompt injections ("Book a flight. Ignore previous instructions...")

## Fixing the Agent

Try modifying `agent.py` to:
1. Use NLP for intent recognition
2. Add spelling correction
3. Handle emotional inputs gracefully
4. Detect and refuse prompt injections

Then re-run Entropix to see your robustness score improve!

