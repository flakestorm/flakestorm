# LLM Providers and API Keys

Flakestorm uses an LLM to generate adversarial prompt mutations. You can use a local model (Ollama) or cloud APIs (OpenAI, Anthropic, Google Gemini).

## Configuration

In `flakestorm.yaml`, the `model` section supports:

```yaml
model:
  provider: ollama   # ollama | openai | anthropic | google
  name: qwen3:8b     # model name (e.g. gpt-4o-mini, claude-3-5-sonnet, gemini-2.0-flash)
  api_key: ${OPENAI_API_KEY}   # required for non-Ollama; env var only
  base_url: null     # optional; for Ollama default is http://localhost:11434
  temperature: 0.8
```

## API Keys (Environment Variables Only)

**Literal API keys are not allowed in config.** Use environment variable references only:

- **Correct:** `api_key: "${OPENAI_API_KEY}"`
- **Wrong:** Pasting a key like `sk-...` into the YAML

If you use a literal key, Flakestorm will fail with:

```
Error: Literal API keys are not allowed in config.
Use: api_key: "${OPENAI_API_KEY}"
```

Set the variable in your shell or in a `.env` file before running:

```bash
export OPENAI_API_KEY="sk-..."
flakestorm run
```

## Providers

| Provider | `name` examples | API key env var |
|----------|-----------------|-----------------|
| **ollama** | `qwen3:8b`, `llama3.2` | Not needed |
| **openai** | `gpt-4o-mini`, `gpt-4o` | `OPENAI_API_KEY` |
| **anthropic** | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |
| **google** | `gemini-2.0-flash`, `gemini-1.5-pro` | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) |

Use `provider: google` for Gemini models (Google is the provider; Gemini is the model family).

## Optional Dependencies

Ollama is included by default. For cloud providers, install the optional extra:

```bash
# OpenAI
pip install flakestorm[openai]

# Anthropic
pip install flakestorm[anthropic]

# Google (Gemini)
pip install flakestorm[google]

# All providers
pip install flakestorm[all]
```

If you set `provider: openai` but do not install `flakestorm[openai]`, Flakestorm will raise a clear error telling you to install the extra.

## Custom Base URL (OpenAI-compatible)

For OpenAI, you can point to a custom endpoint (e.g. proxy or local server):

```yaml
model:
  provider: openai
  name: gpt-4o-mini
  api_key: ${OPENAI_API_KEY}
  base_url: "https://my-proxy.example.com/v1"
```

## Security

- Never commit config files that contain literal API keys.
- Use env vars only; Flakestorm expands `${VAR}` at runtime and does not log the resolved value.
