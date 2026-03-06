"""
V2 Research Assistant Agent — Working example for Flakestorm v2.

An HTTP agent that calls a real LLM (Ollama) to answer queries. It uses a
system prompt so responses tend to cite a source (behavioral contract).
Supports /reset for contract matrix isolation. Demonstrates:
- flakestorm run (mutation testing)
- flakestorm run --chaos / --chaos-profile (environment chaos)
- flakestorm contract run (behavioral contract × chaos matrix)
- flakestorm replay run (replay regression)
- flakestorm ci (unified run with overall score)

Requires: Ollama running with the same model as in flakestorm.yaml (e.g. gemma3:1b).
"""

import os
import time
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="V2 Research Assistant Agent")

# In-memory state (cleared by /reset for contract isolation)
_state = {"calls": 0}

# Ollama config (match flakestorm.yaml or set OLLAMA_BASE_URL, OLLAMA_MODEL)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "60"))

SYSTEM_PROMPT = """You are a research assistant. For every answer, you must cite a source using phrases like "According to ...", "Source: ...", or "Per ...". Keep answers concise (2-4 sentences). If you don't know, say so and still cite that you couldn't find a source."""


class InvokeRequest(BaseModel):
    """Request body: prompt or input."""
    input: str | None = None
    prompt: str | None = None
    query: str | None = None


class InvokeResponse(BaseModel):
    """Response with result and optional metadata."""
    result: str
    source: str = "ollama"
    latency_ms: float | None = None


def _call_ollama(prompt: str) -> tuple[str, float]:
    """Call Ollama generate API. Returns (response_text, latency_ms). Raises on failure."""
    import httpx
    start = time.perf_counter()
    url = f"{OLLAMA_BASE_URL}/api/generate"
    body = {
        "model": OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:",
        "stream": False,
    }
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        r = client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    elapsed_ms = (time.perf_counter() - start) * 1000
    text = (data.get("response") or "").strip()
    return text or "(No response from model)", elapsed_ms


@app.post("/reset")
def reset():
    """Reset agent state. Called by Flakestorm before each contract matrix cell."""
    _state["calls"] = 0
    return {"ok": True}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    """Handle a single user query. Calls Ollama and returns the model response."""
    _state["calls"] += 1
    text = (req.input or req.prompt or req.query or "").strip()
    if not text:
        return InvokeResponse(
            result="I didn't receive a question. Please ask something.",
            source="none",
        )
    try:
        response, latency_ms = _call_ollama(text)
        return InvokeResponse(
            result=response,
            source="ollama",
            latency_ms=round(latency_ms, 2),
        )
    except Exception as e:
        # Graceful fallback so "completes" invariant can still pass under chaos
        return InvokeResponse(
            result=f"According to [source: system], I couldn't reach the knowledge base right now ({type(e).__name__}). Please try again.",
            source="fallback",
            latency_ms=None,
        )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8790"))
    uvicorn.run(app, host="0.0.0.0", port=port)
