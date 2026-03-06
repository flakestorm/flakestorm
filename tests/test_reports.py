"""Tests for report generation."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from flakestorm.mutations.types import Mutation, MutationType


class TestCheckResult:
    """Tests for CheckResult data model."""

    def test_check_result_creation(self):
        """CheckResult can be created."""
        from flakestorm.reports.models import CheckResult

        result = CheckResult(
            check_type="contains",
            passed=True,
            details="Found expected substring",
        )
        assert result.check_type == "contains"
        assert result.passed is True
        assert result.details == "Found expected substring"

    def test_check_result_to_dict(self):
        """CheckResult converts to dict."""
        from flakestorm.reports.models import CheckResult

        result = CheckResult(
            check_type="latency",
            passed=False,
            details="Exceeded 5000ms",
        )
        d = result.to_dict()
        assert d["check_type"] == "latency"
        assert d["passed"] is False
        assert d["details"] == "Exceeded 5000ms"


class TestMutationResult:
    """Tests for MutationResult data model."""

    @pytest.fixture
    def sample_mutation(self):
        """Create a sample mutation."""
        return Mutation(
            original="What is the weather?",
            mutated="Tell me about today's weather conditions",
            type=MutationType.PARAPHRASE,
        )

    def test_mutation_result_creation(self, sample_mutation):
        """MutationResult can be created."""
        from flakestorm.reports.models import MutationResult

        result = MutationResult(
            original_prompt="What is the weather?",
            mutation=sample_mutation,
            response="It's sunny today",
            latency_ms=100.0,
            passed=True,
        )
        assert result.response == "It's sunny today"
        assert result.passed is True
        assert result.latency_ms == 100.0

    def test_mutation_result_with_checks(self, sample_mutation):
        """MutationResult with check results."""
        from flakestorm.reports.models import CheckResult, MutationResult

        checks = [
            CheckResult(check_type="contains", passed=True, details="Found 'weather'"),
            CheckResult(check_type="latency", passed=False, details="Too slow"),
        ]
        result = MutationResult(
            original_prompt="What is the weather?",
            mutation=sample_mutation,
            response="Test",
            latency_ms=200.0,
            passed=False,
            checks=checks,
        )
        assert len(result.checks) == 2
        assert result.checks[0].passed is True
        assert result.checks[1].passed is False

    def test_mutation_result_failed_checks(self, sample_mutation):
        """MutationResult returns failed checks."""
        from flakestorm.reports.models import CheckResult, MutationResult

        checks = [
            CheckResult(check_type="contains", passed=True, details="OK"),
            CheckResult(check_type="latency", passed=False, details="Too slow"),
            CheckResult(check_type="safety", passed=False, details="PII detected"),
        ]
        result = MutationResult(
            original_prompt="Test",
            mutation=sample_mutation,
            response="Test",
            latency_ms=200.0,
            passed=False,
            checks=checks,
        )
        failed = result.failed_checks
        assert len(failed) == 2


class TestTypeStatistics:
    """Tests for TypeStatistics data model."""

    def test_type_statistics_creation(self):
        """TypeStatistics can be created."""
        from flakestorm.reports.models import TypeStatistics

        stats = TypeStatistics(
            mutation_type="paraphrase",
            total=100,
            passed=85,
            pass_rate=0.85,
        )
        assert stats.mutation_type == "paraphrase"
        assert stats.total == 100
        assert stats.passed == 85
        assert stats.pass_rate == 0.85

    def test_type_statistics_to_dict(self):
        """TypeStatistics converts to dict."""
        from flakestorm.reports.models import TypeStatistics

        stats = TypeStatistics(
            mutation_type="noise",
            total=50,
            passed=40,
            pass_rate=0.8,
        )
        d = stats.to_dict()
        assert d["mutation_type"] == "noise"
        assert d["failed"] == 10


class TestTestStatistics:
    """Tests for TestStatistics data model."""

    def test_statistics_creation(self):
        """TestStatistics can be created."""
        from flakestorm.reports.models import TestStatistics

        stats = TestStatistics(
            total_mutations=100,
            passed_mutations=85,
            failed_mutations=15,
            robustness_score=0.85,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )
        assert stats.total_mutations == 100
        assert stats.passed_mutations == 85
        assert stats.robustness_score == 0.85

    def test_statistics_pass_rate(self):
        """Statistics calculates pass_rate correctly."""
        from flakestorm.reports.models import TestStatistics

        stats = TestStatistics(
            total_mutations=100,
            passed_mutations=80,
            failed_mutations=20,
            robustness_score=0.85,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )
        assert stats.pass_rate == 0.8

    def test_statistics_zero_total(self):
        """Statistics handles zero total."""
        from flakestorm.reports.models import TestStatistics

        stats = TestStatistics(
            total_mutations=0,
            passed_mutations=0,
            failed_mutations=0,
            robustness_score=0.0,
            avg_latency_ms=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
        )
        assert stats.pass_rate == 0.0


class TestTestResults:
    """Tests for TestResults data model."""

    @pytest.fixture
    def sample_config(self):
        """Create sample config."""
        from flakestorm.core.config import (
            AgentConfig,
            AgentType,
            FlakeStormConfig,
            InvariantConfig,
            InvariantType,
        )

        return FlakeStormConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type=AgentType.HTTP,
            ),
            golden_prompts=["Test"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=5000)],
        )

    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics."""
        from flakestorm.reports.models import TestStatistics

        return TestStatistics(
            total_mutations=10,
            passed_mutations=8,
            failed_mutations=2,
            robustness_score=0.8,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )

    def test_results_creation(self, sample_config, sample_statistics):
        """TestResults can be created."""
        from flakestorm.reports.models import TestResults

        now = datetime.now()
        results = TestResults(
            config=sample_config,
            started_at=now,
            completed_at=now,
            mutations=[],
            statistics=sample_statistics,
        )
        assert results.config == sample_config
        assert results.statistics.robustness_score == 0.8


class TestHTMLReportGenerator:
    """Tests for HTML report generation."""

    @pytest.fixture
    def sample_config(self):
        """Create sample config."""
        from flakestorm.core.config import (
            AgentConfig,
            AgentType,
            FlakeStormConfig,
            InvariantConfig,
            InvariantType,
        )

        return FlakeStormConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type=AgentType.HTTP,
            ),
            golden_prompts=["Test"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=5000)],
        )

    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics."""
        from flakestorm.reports.models import TestStatistics

        return TestStatistics(
            total_mutations=10,
            passed_mutations=8,
            failed_mutations=2,
            robustness_score=0.8,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )

    @pytest.fixture
    def sample_results(self, sample_config, sample_statistics):
        """Create sample test results."""
        from flakestorm.reports.models import TestResults

        now = datetime.now()
        return TestResults(
            config=sample_config,
            started_at=now,
            completed_at=now,
            mutations=[],
            statistics=sample_statistics,
        )

    def test_generator_creation(self, sample_results):
        """Generator can be created."""
        from flakestorm.reports.html import HTMLReportGenerator

        generator = HTMLReportGenerator(sample_results)
        assert generator is not None

    def test_generate_returns_string(self, sample_results):
        """Generator returns HTML string."""
        from flakestorm.reports.html import HTMLReportGenerator

        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        assert isinstance(html, str)
        assert len(html) > 0

    def test_generate_valid_html_structure(self, sample_results):
        """Generated HTML has valid structure."""
        from flakestorm.reports.html import HTMLReportGenerator

        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "</html>" in html

    def test_contains_robustness_score(self, sample_results):
        """Report contains robustness score."""
        from flakestorm.reports.html import HTMLReportGenerator

        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        # Score should appear in some form (0.8 or 80%)
        assert "0.8" in html or "80" in html

    def test_save_creates_file(self, sample_results):
        """save() creates file on disk."""
        from flakestorm.reports.html import HTMLReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = HTMLReportGenerator(sample_results)
            path = generator.save(Path(tmpdir) / "report.html")

            assert path.exists()
            content = path.read_text()
            assert "html" in content.lower()


class TestJSONReportGenerator:
    """Tests for JSON report generation."""

    @pytest.fixture
    def sample_config(self):
        """Create sample config."""
        from flakestorm.core.config import (
            AgentConfig,
            AgentType,
            FlakeStormConfig,
            InvariantConfig,
            InvariantType,
        )

        return FlakeStormConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type=AgentType.HTTP,
            ),
            golden_prompts=["Test"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=5000)],
        )

    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics."""
        from flakestorm.reports.models import TestStatistics

        return TestStatistics(
            total_mutations=10,
            passed_mutations=8,
            failed_mutations=2,
            robustness_score=0.8,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )

    @pytest.fixture
    def sample_results(self, sample_config, sample_statistics):
        """Create sample test results."""
        from flakestorm.reports.models import TestResults

        ts = datetime(2024, 1, 15, 12, 0, 0)
        return TestResults(
            config=sample_config,
            started_at=ts,
            completed_at=ts,
            mutations=[],
            statistics=sample_statistics,
        )

    def test_generator_creation(self, sample_results):
        """Generator can be created."""
        from flakestorm.reports.json_export import JSONReportGenerator

        generator = JSONReportGenerator(sample_results)
        assert generator is not None

    def test_generate_valid_json(self, sample_results):
        """Generator produces valid JSON."""
        from flakestorm.reports.json_export import JSONReportGenerator

        generator = JSONReportGenerator(sample_results)
        json_str = generator.generate()

        # Should not raise
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_contains_statistics(self, sample_results):
        """JSON contains statistics."""
        from flakestorm.reports.json_export import JSONReportGenerator

        generator = JSONReportGenerator(sample_results)
        data = json.loads(generator.generate())

        assert "statistics" in data
        assert data["statistics"]["robustness_score"] == 0.8

    def test_save_creates_file(self, sample_results):
        """save() creates JSON file on disk."""
        from flakestorm.reports.json_export import JSONReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = JSONReportGenerator(sample_results)
            path = generator.save(Path(tmpdir) / "report.json")

            assert path.exists()
            data = json.loads(path.read_text())
            assert "statistics" in data


class TestTerminalReporter:
    """Tests for terminal output."""

    @pytest.fixture
    def sample_config(self):
        """Create sample config."""
        from flakestorm.core.config import (
            AgentConfig,
            AgentType,
            FlakeStormConfig,
            InvariantConfig,
            InvariantType,
        )

        return FlakeStormConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type=AgentType.HTTP,
            ),
            golden_prompts=["Test"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=5000)],
        )

    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics."""
        from flakestorm.reports.models import TestStatistics

        return TestStatistics(
            total_mutations=10,
            passed_mutations=8,
            failed_mutations=2,
            robustness_score=0.8,
            avg_latency_ms=150.0,
            p50_latency_ms=120.0,
            p95_latency_ms=300.0,
            p99_latency_ms=450.0,
        )

    @pytest.fixture
    def sample_results(self, sample_config, sample_statistics):
        """Create sample test results."""
        from flakestorm.reports.models import TestResults

        now = datetime.now()
        return TestResults(
            config=sample_config,
            started_at=now,
            completed_at=now,
            mutations=[],
            statistics=sample_statistics,
        )

    def test_reporter_creation(self, sample_results):
        """Reporter can be created."""
        from flakestorm.reports.terminal import TerminalReporter

        reporter = TerminalReporter(sample_results)
        assert reporter is not None

    def test_reporter_has_print_methods(self, sample_results):
        """Reporter has print methods."""
        from flakestorm.reports.terminal import TerminalReporter

        reporter = TerminalReporter(sample_results)
        assert hasattr(reporter, "print_summary")
        assert hasattr(reporter, "print_full_report")
