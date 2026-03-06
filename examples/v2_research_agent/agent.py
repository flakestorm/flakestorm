"""
V2 Research Assistant Agent — Working example for Flakestorm v2.

A minimal HTTP agent that simulates a research assistant: it responds to queries
and always cites a source (so behavioral contracts can be verified). Supports
/reset for contract matrix isolation. Used to demonstrate:
- flakestorm run (mutation testing)
- flakestorm run --chaos / --chaos-profile (environment chaos)
- flakestorm contract run (behavioral contract × chaos matrix)
- flakestorm replay run (replay regression)
- flakestorm ci (unified run with overall score)
"""

import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="V2 Research Assistant Agent")

# In-memory state (cleared by /reset for contract isolation)
_state = {"calls": 0}


class InvokeRequest(BaseModel):
    """Request body: prompt or input."""
    input: str | None = None
    prompt: str | None = None
    query: str | None = None


class InvokeResponse(BaseModel):
    """Response with result and optional metadata."""
    result: str
    source: str = "demo_knowledge_base"
    latency_ms: float | None = None


@app.post("/reset")
def reset():
    """Reset agent state. Called by Flakestorm before each contract matrix cell."""
    _state["calls"] = 0
    return {"ok": True}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    """Handle a single user query. Always cites a source (contract invariant)."""
    _state["calls"] += 1
    text = req.input or req.prompt or req.query or ""
    if not text.strip():
        return InvokeResponse(
            result="I didn't receive a question. Please ask something.",
            source="none",
        )
    # Simulate a research response that cites a source (contract: always-cite-source)
    response = (
        f"According to [source: {_state['source']}], "
        f"here is what I found for your query: \"{text[:100]}\". "
        "Data may be incomplete when tools are degraded."
    )
    return InvokeResponse(result=response, source=_state["source"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8790"))
    uvicorn.run(app, host="0.0.0.0", port=port)
