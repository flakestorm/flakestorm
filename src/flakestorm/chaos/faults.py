"""
Pure fault application helpers for chaos injection.

Used by tool_proxy and llm_proxy to apply timeout, error, malformed, slow, malicious_response.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any


async def apply_timeout(delay_ms: int) -> None:
    """Sleep for delay_ms then raise TimeoutError."""
    await asyncio.sleep(delay_ms / 1000.0)
    raise TimeoutError(f"Chaos: timeout after {delay_ms}ms")


def apply_error(
    error_code: int = 503,
    message: str = "Service Unavailable",
) -> tuple[int, str, dict[str, Any] | None]:
    """Return (status_code, body, headers) for an error response."""
    return (error_code, message, None)


def apply_malformed() -> str:
    """Return a malformed response body (corrupted JSON/text)."""
    return "{ corrupted ] invalid json"


def apply_slow(delay_ms: int) -> None:
    """Async sleep for delay_ms (then caller continues)."""
    return asyncio.sleep(delay_ms / 1000.0)


def apply_malicious_response(payload: str) -> str:
    """Return a structurally bad or injection payload for tool response."""
    return payload


def should_trigger(probability: float | None, after_calls: int | None, call_count: int) -> bool:
    """Return True if fault should trigger given probability and after_calls."""
    if probability is not None and random.random() >= probability:
        return False
    if after_calls is not None and call_count < after_calls:
        return False
    return True
