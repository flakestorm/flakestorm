# FlakeStorm Connection Guide

This guide explains how to connect FlakeStorm to your agent, covering different scenarios from localhost to public endpoints, and options for internal code.

---

## Table of Contents

1. [Connection Requirements](#connection-requirements)
2. [Localhost vs Public Endpoints](#localhost-vs-public-endpoints)
3. [Internal Code Options](#internal-code-options)
4. [Exposing Local Endpoints](#exposing-local-endpoints)
5. [Troubleshooting](#troubleshooting)

---

## Connection Requirements

### When Do You Need an HTTP Endpoint?

| Your Agent Code | Adapter Type | Endpoint Needed? | Notes |
|----------------|--------------|------------------|-------|
| Python (internal) | Python adapter | ❌ No | Use `type: "python"`, call function directly |
| TypeScript/JavaScript | HTTP adapter | ✅ Yes | Must create HTTP endpoint (can be localhost) |
| Java/Go/Rust | HTTP adapter | ✅ Yes | Must create HTTP endpoint (can be localhost) |
| Already has HTTP API | HTTP adapter | ✅ Yes | Use existing endpoint |

**Key Point:** FlakeStorm is a Python CLI tool. It can only directly call Python functions. For non-Python code, you **must** create an HTTP endpoint wrapper.

---

## Localhost vs Public Endpoints

### When Localhost Works

| FlakeStorm Location | Agent Location | Endpoint Type | Works? |
|---------------------|----------------|---------------|--------|
| Same machine | Same machine | `localhost:8000` | ✅ Yes |
| Different machine | Your machine | `localhost:8000` | ❌ No |
| CI/CD server | Your machine | `localhost:8000` | ❌ No |
| CI/CD server | Cloud (AWS/GCP) | `https://api.example.com` | ✅ Yes |

**Rule of Thumb:** If FlakeStorm and your agent run on the **same machine**, use `localhost`. Otherwise, you need a **public endpoint**.

**Note:** Native CI/CD integrations (scheduled runs, pipeline plugins) are **Cloud only**. OSS users run `flakestorm ci` from their own scripts or job runners.

**V2 — API keys:** When using cloud LLM providers (OpenAI, Anthropic, Google) for mutation generation or agent backends, API keys must be set via **environment variables only** (e.g. `OPENAI_API_KEY`). Reference them in config as `api_key: "${OPENAI_API_KEY}"`. Do not put literal keys in config files. See [LLM Providers](LLM_PROVIDERS.md).

---

## Internal Code Options

### Option 1: Python Adapter (Recommended for Python Code)

If your agent code is in Python, use the Python adapter - **no HTTP endpoint needed**:

```python
# my_agent.py
async def flakestorm_agent(input: str) -> str:
    """
    FlakeStorm will call this function directly.

    Args:
        input: The golden prompt text (may be structured)

    Returns:
        The agent's response as a string
    """
    # Parse input, call your internal functions
    params = parse_structured_input(input)
    result = await your_internal_function(params)
    return result
```

```yaml
# flakestorm.yaml
agent:
  endpoint: "my_agent:flakestorm_agent"
  type: "python"  # ← No HTTP endpoint needed!
  # V2: optional reset between contract matrix cells (stateful agents)
  # reset_function: "my_agent:reset_state"
```

**Benefits:**
- No server setup required
- Faster (no HTTP overhead)
- Works offline
- No network configuration

### Option 2: HTTP Wrapper Endpoint (Required for Non-Python Code)

For TypeScript/JavaScript/Java/Go/Rust, create a simple HTTP wrapper:

**TypeScript/Node.js Example:**
```typescript
// test-endpoint.ts
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

**Python FastAPI Example:**
```python
# test_endpoint.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Request(BaseModel):
    input: str

@app.post("/flakestorm-test")
async def flakestorm_test(request: Request):
    # Parse structured input
    params = parse_structured_input(request.input)

    # Call your internal function
    result = await your_internal_function(params)

    return {"output": result}
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

## Exposing Local Endpoints

If FlakeStorm runs on a different machine (e.g., CI/CD), you need to expose your local endpoint publicly.

### Option 1: ngrok (Recommended)

```bash
# Install ngrok
brew install ngrok  # macOS
# Or download from https://ngrok.com/download

# Expose local port 8000
ngrok http 8000

# Output:
# Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

Then use the ngrok URL in your config:
```yaml
agent:
  endpoint: "https://abc123.ngrok.io/flakestorm-test"
  type: "http"
```

### Option 2: localtunnel

```bash
# Install
npm install -g localtunnel

# Expose port
lt --port 8000

# Output:
# your url is: https://xyz.localtunnel.me
```

### Option 3: Deploy to Cloud

Deploy your test endpoint to a cloud service:
- **Vercel** (for Node.js/TypeScript)
- **Railway** (any language)
- **Fly.io** (any language)
- **AWS Lambda** (serverless)

### Option 4: VPN/SSH Tunnel

If both machines are on the same network:
```bash
# SSH tunnel
ssh -L 8000:localhost:8000 user@agent-machine

# Then use localhost:8000 in config
```

---

## Troubleshooting

### "Connection Refused" Error

**Problem:** FlakeStorm can't reach your endpoint.

**Solutions:**
1. **Check if agent is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify endpoint URL in config:**
   ```yaml
   agent:
     endpoint: "http://localhost:8000/invoke"  # Check this matches your server
   ```

3. **Check firewall:**
   ```bash
   # macOS: System Preferences > Security & Privacy > Firewall
   # Linux: sudo ufw allow 8000
   ```

4. **For Docker/containers:**
   - Use `host.docker.internal:8000` instead of `localhost:8000`
   - Or use container networking

### "Timeout" Error

**Problem:** Agent takes too long to respond.

**Solutions:**
1. **Increase timeout:**
   ```yaml
   agent:
     timeout: 60000  # 60 seconds
   ```

2. **Check agent performance:**
   - Is the agent actually processing requests?
   - Are there network issues?

### "Invalid Response Format" Error

**Problem:** Response doesn't match expected format.

**Solutions:**
1. **Use response_path:**
   ```yaml
   agent:
     response_path: "$.data.result"  # Extract from nested JSON
   ```

2. **Check actual response:**
   ```bash
   curl -X POST http://localhost:8000/invoke \
     -H "Content-Type: application/json" \
     -d '{"input": "test"}'
   ```

3. **Update request_template if needed:**
   ```yaml
   agent:
     request_template: |
       {"your_field": "{prompt}"}
   ```

### Network Connectivity Issues

**Problem:** Can't connect from CI/CD or remote machine.

**Solutions:**
1. **Use public endpoint** (ngrok, cloud deployment)
2. **Check network policies** (corporate firewall, VPN)
3. **Verify DNS resolution** (if using domain name)
4. **Test with curl** from the same machine FlakeStorm runs on

---

## V2: Reset for stateful agents (contract matrix)

When running **behavioral contracts** (`flakestorm contract run` or `flakestorm ci`), each (invariant × scenario) cell should start from a clean state. Configure one of:

- **`reset_endpoint`** — HTTP POST endpoint (e.g. `http://localhost:8000/reset`) called before each cell.
- **`reset_function`** — Python module path (e.g. `myagent:reset_state`) for `type: python`; the function is called (or awaited if async) before each cell.

If the agent appears stateful and neither is set, Flakestorm logs a warning. See [Behavioral Contracts](BEHAVIORAL_CONTRACTS.md) and [V2 Spec](V2_SPEC.md).

## Best Practices

1. **For Development:** Use Python adapter if possible (fastest, simplest)
2. **For Testing:** Use localhost HTTP endpoint (easy to debug)
3. **For CI/CD:** Use public endpoint or cloud deployment (native CI/CD is Cloud only)
4. **For Production Testing:** Use production endpoint with proper authentication
5. **Security:** Never commit API keys — use environment variables (V2 enforces env-only for `model.api_key`)

---

## Quick Reference

| Scenario | Solution |
|----------|----------|
| Python code, same machine | Python adapter (`type: "python"`) |
| TypeScript/JS, same machine | HTTP endpoint (`localhost:8000`) |
| Any language, CI/CD | Public endpoint (ngrok/cloud) |
| Already has HTTP API | Use existing endpoint |
| Need custom request format | Use `request_template` |
| Complex response structure | Use `response_path` |
| Stateful agent + contract (V2) | Use `reset_endpoint` or `reset_function` |

---

*For more examples, see [Configuration Guide](CONFIGURATION_GUIDE.md) and [Usage Guide](USAGE_GUIDE.md).*
