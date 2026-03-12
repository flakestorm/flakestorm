"""
Performance Module - Rust/Python Bridge

This module provides high-performance implementations for:
- Robustness score calculation
- String similarity scoring
- Parallel processing utilities
- V2: Contract resilience matrix score (severity-weighted)
- V2: Overall resilience (weighted combination of mutation/chaos/contract/replay)

Uses Rust bindings when available, falls back to pure Python otherwise.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Try to import Rust bindings
_RUST_AVAILABLE = False
try:
    import flakestorm_rust

    _RUST_AVAILABLE = True
    logger.debug("Rust performance module loaded successfully")
except ImportError:
    logger.debug("Rust module not available, using pure Python fallback")


def is_rust_available() -> bool:
    """Check if the Rust performance module is available."""
    return _RUST_AVAILABLE


def calculate_robustness_score(
    semantic_passed: int,
    deterministic_passed: int,
    total: int,
    semantic_weight: float = 1.0,
    deterministic_weight: float = 1.0,
) -> float:
    """
    Calculate the robustness score for a test run.

    The robustness score R is calculated as:
    R = (W_s * S_passed + W_d * D_passed) / N_total

    Args:
        semantic_passed: Number of semantic variations that passed
        deterministic_passed: Number of deterministic tests that passed
        total: Total number of tests
        semantic_weight: Weight for semantic tests (default 1.0)
        deterministic_weight: Weight for deterministic tests (default 1.0)

    Returns:
        Robustness score between 0.0 and 1.0
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.calculate_robustness_score(
            semantic_passed,
            deterministic_passed,
            total,
            semantic_weight,
            deterministic_weight,
        )

    # Pure Python fallback
    if total == 0:
        return 0.0

    weighted_sum = (
        semantic_weight * semantic_passed + deterministic_weight * deterministic_passed
    )
    return weighted_sum / total


def calculate_weighted_score(results: Sequence[tuple[bool, float]]) -> float:
    """
    Calculate weighted robustness score with per-mutation weights.

    Each mutation has its own weight based on difficulty.
    Passing a prompt injection attack is worth more than passing a typo test.

    Args:
        results: List of (passed, weight) tuples

    Returns:
        Weighted robustness score between 0.0 and 1.0
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.calculate_weighted_score(list(results))

    # Pure Python fallback
    if not results:
        return 0.0

    total_weight = sum(weight for _, weight in results)
    passed_weight = sum(weight for passed, weight in results if passed)

    if total_weight == 0.0:
        return 0.0

    return passed_weight / total_weight


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance between the strings
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.levenshtein_distance(s1, s2)

    # Pure Python fallback
    len1 = len(s1)
    len2 = len(s2)

    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Create distance matrix
    prev_row = list(range(len2 + 1))
    curr_row = [0] * (len2 + 1)

    for i in range(1, len1 + 1):
        curr_row[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[j] = min(
                prev_row[j] + 1,  # deletion
                curr_row[j - 1] + 1,  # insertion
                prev_row[j - 1] + cost,  # substitution
            )
        prev_row, curr_row = curr_row, prev_row

    return prev_row[len2]


def string_similarity(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings (0.0 to 1.0).

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score between 0.0 (completely different) and 1.0 (identical)
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.string_similarity(s1, s2)

    # Pure Python fallback
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))

    if max_len == 0:
        return 1.0

    return 1.0 - (distance / max_len)


def calculate_resilience_matrix_score(
    severities: list[str],
    passed: list[bool],
) -> tuple[float, bool, bool]:
    """
    V2: Contract resilience matrix score (severity-weighted, 0–100).

    Returns (score, overall_passed, critical_failed).
    Severity weights: critical=3, high=2, medium=1, low=1.
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.calculate_resilience_matrix_score(severities, passed)

    # Pure Python fallback
    n = min(len(severities), len(passed))
    if n == 0:
        return (100.0, True, False)
    weight_map = {"critical": 3, "high": 2, "medium": 1, "low": 1}
    weighted_pass = 0.0
    weighted_total = 0.0
    critical_failed = False
    for i in range(n):
        w = weight_map.get(severities[i].lower(), 1)
        weighted_total += w
        if passed[i]:
            weighted_pass += w
        elif severities[i].lower() == "critical":
            critical_failed = True
    score = (weighted_pass / weighted_total * 100.0) if weighted_total else 100.0
    score = round(score, 2)
    return (score, not critical_failed, critical_failed)


def calculate_overall_resilience(scores: list[float], weights: list[float]) -> float:
    """
    V2: Overall resilience from component scores and weights.

    Weighted average for mutation_robustness, chaos_resilience, contract_compliance, replay_regression.
    """
    if _RUST_AVAILABLE:
        rust_fn = getattr(flakestorm_rust, "calculate_overall_resilience", None)
        if rust_fn is not None:
            return rust_fn(scores, weights)

    n = min(len(scores), len(weights))
    if n == 0:
        return 1.0
    sum_w = sum(weights[i] for i in range(n))
    sum_ws = sum(scores[i] * weights[i] for i in range(n))
    return sum_ws / sum_w if sum_w else 1.0


def parallel_process_mutations(
    mutations: list[str],
    mutation_types: list[str],
    weights: list[float],
) -> list[tuple[str, str, float]]:
    """
    Process mutations and assign types and weights.

    Uses Rust's Rayon for parallel processing when available.

    Args:
        mutations: List of mutation strings
        mutation_types: List of mutation type names
        weights: List of weights per type

    Returns:
        List of (mutation, type, weight) tuples
    """
    if _RUST_AVAILABLE:
        return flakestorm_rust.parallel_process_mutations(
            mutations, mutation_types, weights
        )

    # Pure Python fallback (sequential)
    results = []
    for i, mutation in enumerate(mutations):
        mutation_type = (
            mutation_types[i % len(mutation_types)] if mutation_types else "unknown"
        )
        weight = weights[i % len(weights)] if weights else 1.0
        results.append((mutation, mutation_type, weight))
    return results


def calculate_percentile(values: list[float], percentile: int) -> float:
    """
    Calculate a percentile from a list of values.

    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)

    Returns:
        The percentile value
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(percentile / 100.0 * (len(sorted_values) - 1) + 0.5)
    return sorted_values[min(index, len(sorted_values) - 1)]


def calculate_statistics(
    results: list[dict],
) -> dict:
    """
    Calculate comprehensive statistics from mutation results.

    Args:
        results: List of result dictionaries with keys:
            - passed: bool
            - weight: float
            - latency_ms: float
            - mutation_type: str

    Returns:
        Statistics dictionary with robustness score, latency percentiles, etc.
    """
    if not results:
        return {
            "total_mutations": 0,
            "passed_mutations": 0,
            "failed_mutations": 0,
            "robustness_score": 0.0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "by_type": [],
        }

    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))
    failed = total - passed

    # Calculate robustness score
    total_weight = sum(r.get("weight", 1.0) for r in results)
    passed_weight = sum(r.get("weight", 1.0) for r in results if r.get("passed", False))
    robustness_score = passed_weight / total_weight if total_weight > 0 else 0.0

    # Calculate latency statistics
    latencies = [r.get("latency_ms", 0.0) for r in results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # Statistics by mutation type
    type_stats: dict[str, dict] = {}
    for result in results:
        mutation_type = result.get("mutation_type", "unknown")
        if mutation_type not in type_stats:
            type_stats[mutation_type] = {"total": 0, "passed": 0}
        type_stats[mutation_type]["total"] += 1
        if result.get("passed", False):
            type_stats[mutation_type]["passed"] += 1

    by_type = [
        {
            "mutation_type": mt,
            "total": stats["total"],
            "passed": stats["passed"],
            "pass_rate": (
                stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            ),
        }
        for mt, stats in type_stats.items()
    ]

    return {
        "total_mutations": total,
        "passed_mutations": passed,
        "failed_mutations": failed,
        "robustness_score": robustness_score,
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": calculate_percentile(latencies, 50),
        "p95_latency_ms": calculate_percentile(latencies, 95),
        "p99_latency_ms": calculate_percentile(latencies, 99),
        "by_type": by_type,
    }


# Benchmark utilities for comparing Rust vs Python performance
def benchmark_levenshtein(iterations: int = 1000) -> dict:
    """
    Benchmark Levenshtein distance calculation.

    Returns timing comparison between Rust and Python implementations.
    """
    import time

    test_pairs = [
        ("kitten", "sitting"),
        ("hello world", "hallo welt"),
        (
            "The quick brown fox jumps over the lazy dog",
            "A quick brown dog jumps over the lazy fox",
        ),
    ]

    # Python implementation
    def python_levenshtein(s1: str, s2: str) -> int:
        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return len2
        if len2 == 0:
            return len1
        prev_row = list(range(len2 + 1))
        curr_row = [0] * (len2 + 1)
        for i in range(1, len1 + 1):
            curr_row[0] = i
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                curr_row[j] = min(
                    prev_row[j] + 1, curr_row[j - 1] + 1, prev_row[j - 1] + cost
                )
            prev_row, curr_row = curr_row, prev_row
        return prev_row[len2]

    # Benchmark Python
    start = time.perf_counter()
    for _ in range(iterations):
        for s1, s2 in test_pairs:
            python_levenshtein(s1, s2)
    python_time = time.perf_counter() - start

    result = {
        "iterations": iterations,
        "python_time_ms": python_time * 1000,
        "rust_available": _RUST_AVAILABLE,
    }

    # Benchmark Rust if available
    if _RUST_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            for s1, s2 in test_pairs:
                flakestorm_rust.levenshtein_distance(s1, s2)
        rust_time = time.perf_counter() - start
        result["rust_time_ms"] = rust_time * 1000
        result["speedup"] = python_time / rust_time if rust_time > 0 else 0

    return result
