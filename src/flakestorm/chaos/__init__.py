"""
Environment chaos for Flakestorm v2.

Inject faults into tools, LLMs, and context to test agent resilience.
"""

from flakestorm.chaos.faults import (
    apply_error,
    apply_malformed,
    apply_malicious_response,
    apply_slow,
    apply_timeout,
)
from flakestorm.chaos.interceptor import ChaosInterceptor

__all__ = [
    "ChaosInterceptor",
    "apply_timeout",
    "apply_error",
    "apply_malformed",
    "apply_slow",
    "apply_malicious_response",
]
