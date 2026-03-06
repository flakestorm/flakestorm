"""
LLM fault proxy: apply LLM faults (timeout, truncated_response, rate_limit, empty, garbage, response_drift).

Used by ChaosInterceptor to modify or fail LLM responses.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from typing import Any

from flakestorm.chaos.faults import should_trigger


def should_trigger_llm_fault(
    fault_config: Any,
    call_count: int,
    probability: float | None = None,
    after_calls: int | None = None,
) -> bool:
    """Return True if this LLM fault should trigger."""
    return should_trigger(
        probability or getattr(fault_config, "probability", None),
        after_calls or getattr(fault_config, "after_calls", None),
        call_count,
    )


async def apply_llm_timeout(delay_ms: int = 300000) -> None:
    """Sleep then raise TimeoutError (simulate LLM hang)."""
    await asyncio.sleep(delay_ms / 1000.0)
    raise TimeoutError("Chaos: LLM timeout")


def apply_llm_truncated(response: str, max_tokens: int = 10) -> str:
    """Return response truncated to roughly max_tokens words."""
    words = response.split()
    if len(words) <= max_tokens:
        return response
    return " ".join(words[:max_tokens])


def apply_llm_empty(_response: str) -> str:
    """Return empty string."""
    return ""


def apply_llm_garbage(_response: str) -> str:
    """Return nonsensical text."""
    return " invalid utf-8 sequence \x00\x01 gibberish ##@@"


def apply_llm_rate_limit(_response: str) -> tuple[int, str]:
    """Return (429, rate limit message)."""
    return (429, "Rate limit exceeded")


def apply_llm_response_drift(
    response: str,
    drift_type: str,
    severity: str = "subtle",
    direction: str | None = None,
    factor: float | None = None,
) -> str:
    """
    Simulate model version drift: field renames, verbosity, format change, etc.
    """
    drift_type = (drift_type or "json_field_rename").lower()
    severity = (severity or "subtle").lower()

    if drift_type == "json_field_rename":
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                # Rename first key that looks like a common field
                for k in list(data.keys())[:5]:
                    if k in ("action", "tool_name", "name", "type", "output"):
                        data["tool_name" if k == "action" else "action" if k == "tool_name" else f"{k}_v2"] = data.pop(k)
                        break
            return json.dumps(data, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass
        return response

    if drift_type == "verbosity_shift":
        words = response.split()
        if not words:
            return response
        direction = (direction or "expand").lower()
        factor = factor or 2.0
        if direction == "expand":
            # Repeat some words to make longer
            n = max(1, int(len(words) * (factor - 1.0)))
            insert = words[: min(n, len(words))] if words else []
            return " ".join(words + insert)
        # compress
        n = max(1, int(len(words) / factor))
        return " ".join(words[:n]) if n < len(words) else response

    if drift_type == "format_change":
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                # Return as prose instead of JSON
                return " ".join(f"{k}: {v}" for k, v in list(data.items())[:10])
        except (json.JSONDecodeError, TypeError):
            pass
        return response

    if drift_type == "refusal_rephrase":
        # Replace common refusal phrases with alternate phrasing
        replacements = [
            (r"i can't do that", "I'm not able to assist with that", re.IGNORECASE),
            (r"i cannot", "I'm unable to", re.IGNORECASE),
            (r"not allowed", "against my guidelines", re.IGNORECASE),
        ]
        out = response
        for pat, repl, flags in replacements:
            out = re.sub(pat, repl, out, flags=flags)
        return out

    if drift_type == "tone_shift":
        # Casualize: replace formal with casual
        out = response.replace("I would like to", "I wanna").replace("cannot", "can't")
        return out

    return response


def apply_llm_fault(
    response: str,
    fault_config: Any,
    call_count: int,
) -> str | tuple[int, str]:
    """
    Apply a single LLM fault to the response. Returns modified response string,
    or (status_code, body) for rate_limit (caller should return error response).
    """
    mode = getattr(fault_config, "mode", None) or ""
    mode = mode.lower()

    if mode == "timeout":
        delay_ms = getattr(fault_config, "delay_ms", None) or 300000
        raise NotImplementedError("LLM timeout should be applied in interceptor with asyncio.wait_for")

    if mode == "truncated_response":
        max_tokens = getattr(fault_config, "max_tokens", None) or 10
        return apply_llm_truncated(response, max_tokens)

    if mode == "empty":
        return apply_llm_empty(response)

    if mode == "garbage":
        return apply_llm_garbage(response)

    if mode == "rate_limit":
        return apply_llm_rate_limit(response)

    if mode == "response_drift":
        drift_type = getattr(fault_config, "drift_type", None) or "json_field_rename"
        severity = getattr(fault_config, "severity", None) or "subtle"
        direction = getattr(fault_config, "direction", None)
        factor = getattr(fault_config, "factor", None)
        return apply_llm_response_drift(response, drift_type, severity, direction, factor)

    return response
