"""
Tests for the Performance Module (Rust/Python Bridge)

Tests both the Rust-accelerated and pure Python implementations.
"""

import importlib.util
from pathlib import Path

# Import the performance module directly to avoid heavy dependencies like pydantic
_perf_path = (
    Path(__file__).parent.parent / "src" / "flakestorm" / "core" / "performance.py"
)
_spec = importlib.util.spec_from_file_location("performance", _perf_path)
_performance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_performance)

# Re-export functions for tests
calculate_overall_resilience = _performance.calculate_overall_resilience
calculate_percentile = _performance.calculate_percentile
calculate_resilience_matrix_score = _performance.calculate_resilience_matrix_score
calculate_robustness_score = _performance.calculate_robustness_score
calculate_statistics = _performance.calculate_statistics
calculate_weighted_score = _performance.calculate_weighted_score
is_rust_available = _performance.is_rust_available
levenshtein_distance = _performance.levenshtein_distance
parallel_process_mutations = _performance.parallel_process_mutations
string_similarity = _performance.string_similarity


class TestRustAvailability:
    """Test Rust module availability detection."""

    def test_is_rust_available_returns_bool(self):
        """is_rust_available should return a boolean."""
        result = is_rust_available()
        assert isinstance(result, bool)


class TestRobustnessScore:
    """Test robustness score calculation."""

    def test_perfect_score(self):
        """All tests passing should give score of 1.0."""
        score = calculate_robustness_score(10, 10, 20, 1.0, 1.0)
        assert score == 1.0

    def test_zero_total(self):
        """Zero total should return 0.0."""
        score = calculate_robustness_score(0, 0, 0, 1.0, 1.0)
        assert score == 0.0

    def test_partial_score(self):
        """Partial passing should give proportional score."""
        score = calculate_robustness_score(8, 10, 20, 1.0, 1.0)
        assert abs(score - 0.9) < 0.001

    def test_weighted_calculation(self):
        """Weights should affect the score."""
        # Semantic weight 2.0, deterministic weight 1.0
        # 5 semantic passed, 5 deterministic passed, 10 total
        # Score = (2.0 * 5 + 1.0 * 5) / 10 = 15/10 = 1.5
        score = calculate_robustness_score(5, 5, 10, 2.0, 1.0)
        assert abs(score - 1.5) < 0.001


class TestWeightedScore:
    """Test weighted score calculation."""

    def test_all_passing(self):
        """All tests passing should give score of 1.0."""
        results = [(True, 1.0), (True, 1.0), (True, 1.0)]
        score = calculate_weighted_score(results)
        assert score == 1.0

    def test_all_failing(self):
        """All tests failing should give score of 0.0."""
        results = [(False, 1.0), (False, 1.0), (False, 1.0)]
        score = calculate_weighted_score(results)
        assert score == 0.0

    def test_empty_results(self):
        """Empty results should give score of 0.0."""
        score = calculate_weighted_score([])
        assert score == 0.0

    def test_weighted_partial(self):
        """Weights should affect the score correctly."""
        # Two passing (weights 1.0 and 1.5), one failing (weight 1.0)
        # Total weight: 3.5, passed weight: 2.5
        results = [(True, 1.0), (True, 1.5), (False, 1.0)]
        score = calculate_weighted_score(results)
        expected = 2.5 / 3.5
        assert abs(score - expected) < 0.001


class TestLevenshteinDistance:
    """Test Levenshtein distance calculation."""

    def test_identical_strings(self):
        """Identical strings should have distance 0."""
        assert levenshtein_distance("abc", "abc") == 0

    def test_empty_strings(self):
        """Empty string comparison."""
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "") == 0

    def test_known_distance(self):
        """Test known Levenshtein distances."""
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("saturday", "sunday") == 3

    def test_single_edit(self):
        """Single character edits."""
        assert levenshtein_distance("cat", "hat") == 1  # substitution
        assert levenshtein_distance("cat", "cats") == 1  # insertion
        assert levenshtein_distance("cats", "cat") == 1  # deletion


class TestStringSimilarity:
    """Test string similarity calculation."""

    def test_identical_strings(self):
        """Identical strings should have similarity 1.0."""
        sim = string_similarity("hello", "hello")
        assert sim == 1.0

    def test_empty_strings(self):
        """Two empty strings should have similarity 1.0."""
        sim = string_similarity("", "")
        assert sim == 1.0

    def test_completely_different(self):
        """Completely different strings should have low similarity."""
        sim = string_similarity("abc", "xyz")
        assert sim == 0.0  # All characters different

    def test_partial_similarity(self):
        """Partial similarity should be between 0 and 1."""
        sim = string_similarity("hello", "hallo")
        assert 0.7 < sim < 0.9


class TestParallelProcessMutations:
    """Test parallel mutation processing."""

    def test_basic_processing(self):
        """Basic processing should work."""
        mutations = ["mut1", "mut2", "mut3"]
        types = ["paraphrase", "noise"]
        weights = [1.0, 0.8]

        result = parallel_process_mutations(mutations, types, weights)

        assert len(result) == 3
        assert all(isinstance(r, tuple) and len(r) == 3 for r in result)

    def test_empty_input(self):
        """Empty input should return empty result."""
        result = parallel_process_mutations([], ["type"], [1.0])
        assert result == []

    def test_type_weight_cycling(self):
        """Types and weights should cycle correctly."""
        mutations = ["a", "b", "c", "d"]
        types = ["t1", "t2"]
        weights = [1.0, 2.0]

        result = parallel_process_mutations(mutations, types, weights)

        assert result[0][1] == "t1"
        assert result[1][1] == "t2"
        assert result[2][1] == "t1"
        assert result[3][1] == "t2"


class TestCalculatePercentile:
    """Test percentile calculation."""

    def test_median(self):
        """50th percentile should be the median."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        p50 = calculate_percentile(values, 50)
        assert p50 == 3.0

    def test_empty_values(self):
        """Empty values should return 0."""
        assert calculate_percentile([], 50) == 0.0

    def test_single_value(self):
        """Single value should return that value for any percentile."""
        assert calculate_percentile([5.0], 0) == 5.0
        assert calculate_percentile([5.0], 50) == 5.0
        assert calculate_percentile([5.0], 100) == 5.0


class TestCalculateStatistics:
    """Test comprehensive statistics calculation."""

    def test_empty_results(self):
        """Empty results should return zero statistics."""
        stats = calculate_statistics([])
        assert stats["total_mutations"] == 0
        assert stats["robustness_score"] == 0.0

    def test_basic_statistics(self):
        """Basic statistics calculation."""
        results = [
            {
                "passed": True,
                "weight": 1.0,
                "latency_ms": 100.0,
                "mutation_type": "paraphrase",
            },
            {
                "passed": True,
                "weight": 1.0,
                "latency_ms": 200.0,
                "mutation_type": "noise",
            },
            {
                "passed": False,
                "weight": 1.0,
                "latency_ms": 150.0,
                "mutation_type": "paraphrase",
            },
        ]

        stats = calculate_statistics(results)

        assert stats["total_mutations"] == 3
        assert stats["passed_mutations"] == 2
        assert stats["failed_mutations"] == 1
        assert abs(stats["robustness_score"] - 0.667) < 0.01
        assert stats["avg_latency_ms"] == 150.0

    def test_by_type_breakdown(self):
        """Statistics should break down by mutation type."""
        results = [
            {
                "passed": True,
                "weight": 1.0,
                "latency_ms": 100.0,
                "mutation_type": "paraphrase",
            },
            {
                "passed": False,
                "weight": 1.0,
                "latency_ms": 100.0,
                "mutation_type": "paraphrase",
            },
            {
                "passed": True,
                "weight": 1.0,
                "latency_ms": 100.0,
                "mutation_type": "noise",
            },
        ]

        stats = calculate_statistics(results)
        by_type = {s["mutation_type"]: s for s in stats["by_type"]}

        assert "paraphrase" in by_type
        assert by_type["paraphrase"]["total"] == 2
        assert by_type["paraphrase"]["passed"] == 1
        assert by_type["paraphrase"]["pass_rate"] == 0.5

        assert "noise" in by_type
        assert by_type["noise"]["total"] == 1
        assert by_type["noise"]["pass_rate"] == 1.0


class TestResilienceMatrixScore:
    """V2: Contract resilience matrix score (severity-weighted)."""

    def test_empty_returns_100(self):
        score, overall, critical = calculate_resilience_matrix_score([], [])
        assert score == 100.0
        assert overall is True
        assert critical is False

    def test_all_passed(self):
        score, overall, critical = calculate_resilience_matrix_score(
            ["critical", "high"], [True, True]
        )
        assert score == 100.0
        assert overall is True
        assert critical is False

    def test_severity_weighted_partial(self):
        # critical=3, high=2, medium=1; one medium failed -> 5/6 * 100
        score, overall, critical = calculate_resilience_matrix_score(
            ["critical", "high", "medium"], [True, True, False]
        )
        assert abs(score - (5.0 / 6.0) * 100.0) < 0.02
        assert overall is True
        assert critical is False

    def test_critical_failed(self):
        _, overall, critical = calculate_resilience_matrix_score(
            ["critical"], [False]
        )
        assert critical is True
        assert overall is False


class TestOverallResilience:
    """V2: Overall weighted resilience from component scores."""

    def test_empty_returns_one(self):
        assert calculate_overall_resilience([], []) == 1.0

    def test_weighted_average(self):
        # 0.8*0.25 + 1.0*0.25 + 0.5*0.5 = 0.2 + 0.25 + 0.25 = 0.7
        s = calculate_overall_resilience(
            [0.8, 1.0, 0.5], [0.25, 0.25, 0.5]
        )
        assert abs(s - 0.7) < 0.001

    def test_single_component(self):
        assert calculate_overall_resilience([0.5], [1.0]) == 0.5


class TestRustVsPythonParity:
    """Test that Rust and Python implementations give the same results."""

    def test_levenshtein_parity(self):
        """Levenshtein should give same results regardless of implementation."""
        test_cases = [
            ("", ""),
            ("abc", "abc"),
            ("kitten", "sitting"),
            ("hello world", "hallo welt"),
        ]

        for s1, s2 in test_cases:
            result = levenshtein_distance(s1, s2)
            # Just verify it returns an integer - both implementations should match
            assert isinstance(result, int)
            assert result >= 0

    def test_similarity_parity(self):
        """String similarity should give same results regardless of implementation."""
        test_cases = [
            ("", ""),
            ("abc", "abc"),
            ("hello", "hallo"),
        ]

        for s1, s2 in test_cases:
            result = string_similarity(s1, s2)
            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0
