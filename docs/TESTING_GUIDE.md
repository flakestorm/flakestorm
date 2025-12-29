# Testing Guide

This guide explains how to run, write, and expand tests for flakestorm. It covers the remaining testing items from the implementation checklist.

---

## Table of Contents

1. [Running Tests](#running-tests)
2. [Test Structure](#test-structure)
3. [Writing Tests: Agent Adapters](#writing-tests-agent-adapters)
4. [Writing Tests: Orchestrator](#writing-tests-orchestrator)
5. [Writing Tests: Report Generation](#writing-tests-report-generation)
6. [Integration Tests](#integration-tests)
7. [CLI Tests](#cli-tests)
8. [Test Fixtures](#test-fixtures)

---

## Running Tests

### Prerequisites

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Or manually
pip install pytest pytest-asyncio pytest-cov
```

### Running All Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=src/flakestorm --cov-report=html

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py

# Run specific test class
pytest tests/test_assertions.py::TestContainsChecker

# Run specific test
pytest tests/test_assertions.py::TestContainsChecker::test_contains_match
```

### Test Categories

```bash
# Unit tests only (fast)
pytest tests/test_config.py tests/test_mutations.py tests/test_assertions.py

# Performance tests (requires Rust module)
pytest tests/test_performance.py

# Integration tests (requires Ollama)
pytest tests/test_integration.py
```

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_config.py        # Configuration loading tests
├── test_mutations.py     # Mutation engine tests
├── test_assertions.py    # Assertion checkers tests
├── test_performance.py   # Rust/Python bridge tests
├── test_adapters.py      # Agent adapter tests (TO CREATE)
├── test_orchestrator.py  # Orchestrator tests (TO CREATE)
├── test_reports.py       # Report generation tests (TO CREATE)
├── test_cli.py           # CLI command tests (TO CREATE)
└── test_integration.py   # Full integration tests (TO CREATE)
```

---

## Writing Tests: Agent Adapters

### Location: `tests/test_adapters.py`

### What to Test

1. **HTTPAgentAdapter**
   - Sends correct HTTP request format
   - Handles successful responses
   - Handles error responses (4xx, 5xx)
   - Respects timeout settings
   - Retries on transient failures
   - Extracts response using JSONPath

2. **PythonAgentAdapter**
   - Imports module correctly
   - Calls sync and async functions
   - Handles exceptions gracefully
   - Measures latency correctly

3. **LangChainAgentAdapter**
   - Invokes LangChain agents correctly
   - Handles different chain types

### Example Test File

```python
# tests/test_adapters.py
"""Tests for agent adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

# Import the modules to test
from flakestorm.core.protocol import (
    HTTPAgentAdapter,
    PythonAgentAdapter,
    AgentResponse,
)
from flakestorm.core.config import AgentConfig, AgentType


class TestHTTPAgentAdapter:
    """Tests for HTTP agent adapter."""

    @pytest.fixture
    def http_config(self):
        """Create a test HTTP agent config."""
        return AgentConfig(
            endpoint="http://localhost:8000/chat",
            type=AgentType.HTTP,
            timeout=30,
            request_template='{"message": "{prompt}"}',
            response_path="$.reply",
        )

    @pytest.fixture
    def adapter(self, http_config):
        """Create adapter instance."""
        return HTTPAgentAdapter(http_config)

    @pytest.mark.asyncio
    async def test_invoke_success(self, adapter):
        """Test successful invocation."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"reply": "Hello there!"}
            mock_post.return_value = mock_response

            result = await adapter.invoke("Hello")

            assert isinstance(result, AgentResponse)
            assert result.text == "Hello there!"
            assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_formats_request(self, adapter):
        """Test that request template is formatted correctly."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"reply": "OK"}
            mock_post.return_value = mock_response

            await adapter.invoke("Test prompt")

            # Verify the request body
            call_args = mock_post.call_args
            assert '"message": "Test prompt"' in str(call_args)

    @pytest.mark.asyncio
    async def test_invoke_timeout(self, adapter):
        """Test timeout handling."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()

            with pytest.raises(TimeoutError):
                await adapter.invoke("Hello")

    @pytest.mark.asyncio
    async def test_invoke_http_error(self, adapter):
        """Test HTTP error handling."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(Exception):
                await adapter.invoke("Hello")


class TestPythonAgentAdapter:
    """Tests for Python function adapter."""

    @pytest.fixture
    def python_config(self):
        """Create a test Python agent config."""
        return AgentConfig(
            endpoint="tests.fixtures.mock_agent:handle_message",
            type=AgentType.PYTHON,
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_invoke_sync_function(self):
        """Test invoking a sync function."""
        # Create a mock module with a sync function
        def mock_handler(prompt: str) -> str:
            return f"Echo: {prompt}"

        with patch.dict("sys.modules", {"mock_module": MagicMock(handler=mock_handler)}):
            config = AgentConfig(
                endpoint="mock_module:handler",
                type=AgentType.PYTHON,
            )
            adapter = PythonAgentAdapter(config)

            # This would need the actual implementation to work
            # For now, test the structure

    @pytest.mark.asyncio
    async def test_invoke_async_function(self):
        """Test invoking an async function."""
        async def mock_handler(prompt: str) -> str:
            await asyncio.sleep(0.01)
            return f"Async Echo: {prompt}"

        # Similar test structure


class TestAgentAdapterFactory:
    """Tests for adapter factory function."""

    def test_creates_http_adapter(self):
        """Factory creates HTTP adapter for HTTP type."""
        from flakestorm.core.protocol import create_agent_adapter

        config = AgentConfig(
            endpoint="http://localhost:8000/chat",
            type=AgentType.HTTP,
        )
        adapter = create_agent_adapter(config)
        assert isinstance(adapter, HTTPAgentAdapter)

    def test_creates_python_adapter(self):
        """Factory creates Python adapter for Python type."""
        from flakestorm.core.protocol import create_agent_adapter

        config = AgentConfig(
            endpoint="my_module:my_function",
            type=AgentType.PYTHON,
        )
        adapter = create_agent_adapter(config)
        assert isinstance(adapter, PythonAgentAdapter)
```

### How to Run

```bash
# Run adapter tests
pytest tests/test_adapters.py -v

# Run with coverage
pytest tests/test_adapters.py --cov=src/flakestorm/core/protocol
```

---

## Writing Tests: Orchestrator

### Location: `tests/test_orchestrator.py`

### What to Test

1. **Mutation Generation Phase**
   - Generates correct number of mutations
   - Handles all mutation types
   - Handles LLM failures gracefully

2. **Test Execution Phase**
   - Runs mutations in parallel
   - Respects concurrency limits
   - Handles agent failures
   - Measures latency correctly

3. **Result Aggregation**
   - Calculates statistics correctly
   - Scores results with correct weights
   - Groups results by mutation type

### Example Test File

```python
# tests/test_orchestrator.py
"""Tests for the flakestorm orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from flakestorm.core.orchestrator import flakestormOrchestrator, OrchestratorState
from flakestorm.core.config import flakestormConfig, AgentConfig, MutationConfig
from flakestorm.mutations.types import Mutation, MutationType
from flakestorm.assertions.verifier import CheckResult


class TestOrchestratorState:
    """Tests for orchestrator state tracking."""

    def test_initial_state(self):
        """State initializes correctly."""
        state = OrchestratorState()
        assert state.total_mutations == 0
        assert state.completed_mutations == 0
        assert state.completed_at is None

    def test_state_updates(self):
        """State updates as tests run."""
        state = OrchestratorState()
        state.total_mutations = 10
        state.completed_mutations = 5
        assert state.completed_mutations == 5


class TestEntropixOrchestrator:
    """Tests for main orchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create a minimal test config."""
        return EntropixConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type="http",
            ),
            golden_prompts=["Test prompt 1", "Test prompt 2"],
            mutations=MutationConfig(
                count=5,
                types=[MutationType.PARAPHRASE],
            ),
        )

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent adapter."""
        agent = AsyncMock()
        agent.invoke.return_value = MagicMock(
            text="Agent response",
            latency_ms=100.0,
        )
        return agent

    @pytest.fixture
    def mock_mutation_engine(self):
        """Create a mock mutation engine."""
        engine = AsyncMock()
        engine.generate_mutations.return_value = [
            Mutation(
                original="Test",
                mutated="Test variation",
                type=MutationType.PARAPHRASE,
                difficulty=1.0,
            )
        ]
        return engine

    @pytest.fixture
    def mock_verifier(self):
        """Create a mock verifier."""
        verifier = MagicMock()
        verifier.verify.return_value = [
            CheckResult(passed=True, check_type="contains", details="OK")
        ]
        return verifier

    @pytest.mark.asyncio
    async def test_run_generates_mutations(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator generates mutations for all golden prompts."""
        orchestrator = EntropixOrchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )

        await orchestrator.run()

        # Should have called generate_mutations for each golden prompt
        assert mock_mutation_engine.generate_mutations.call_count == 2

    @pytest.mark.asyncio
    async def test_run_invokes_agent(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator invokes agent for each mutation."""
        orchestrator = EntropixOrchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )

        await orchestrator.run()

        # Should have invoked agent for each mutation
        # 2 golden prompts × 1 mutation each = 2 invocations
        assert mock_agent.invoke.call_count >= 2

    @pytest.mark.asyncio
    async def test_run_returns_results(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator returns complete test results."""
        orchestrator = EntropixOrchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )

        results = await orchestrator.run()

        assert results is not None
        assert hasattr(results, "statistics")
        assert hasattr(results, "mutations")

    @pytest.mark.asyncio
    async def test_handles_agent_failure(
        self, mock_config, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator handles agent failures gracefully."""
        failing_agent = AsyncMock()
        failing_agent.invoke.side_effect = Exception("Agent error")

        orchestrator = EntropixOrchestrator(
            config=mock_config,
            agent=failing_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )

        # Should not raise, should mark test as failed
        results = await orchestrator.run()
        assert results is not None
```

---

## Writing Tests: Report Generation

### Location: `tests/test_reports.py`

### What to Test

1. **HTMLReportGenerator**
   - Generates valid HTML
   - Contains all required sections
   - Includes statistics
   - Includes mutation details

2. **JSONReportGenerator**
   - Generates valid JSON
   - Contains all required fields
   - Serializes datetime correctly

3. **TerminalReporter**
   - Formats output correctly
   - Handles different result types

### Example Test File

```python
# tests/test_reports.py
"""Tests for report generation."""

import pytest
import json
from datetime import datetime
from pathlib import Path
import tempfile

from flakestorm.reports.models import TestResults, TestStatistics, MutationResult
from flakestorm.reports.html import HTMLReportGenerator
from flakestorm.reports.json_export import JSONReportGenerator


class TestHTMLReportGenerator:
    """Tests for HTML report generation."""

    @pytest.fixture
    def sample_results(self):
        """Create sample test results."""
        return TestResults(
            config=None,  # Simplified for testing
            mutations=[
                MutationResult(
                    mutation=None,
                    response="Test response",
                    latency_ms=100.0,
                    passed=True,
                    checks=[],
                )
            ],
            statistics=TestStatistics(
                total_mutations=10,
                passed_mutations=8,
                failed_mutations=2,
                robustness_score=0.8,
                avg_latency_ms=150.0,
                p50_latency_ms=120.0,
                p95_latency_ms=300.0,
                p99_latency_ms=450.0,
                by_type=[],
            ),
            timestamp=datetime.now(),
        )

    def test_generate_returns_string(self, sample_results):
        """Generator returns HTML string."""
        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        assert isinstance(html, str)
        assert len(html) > 0

    def test_generate_valid_html(self, sample_results):
        """Generated HTML is valid."""
        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

    def test_contains_robustness_score(self, sample_results):
        """Report contains robustness score."""
        generator = HTMLReportGenerator(sample_results)
        html = generator.generate()

        assert "0.8" in html or "80%" in html

    def test_save_creates_file(self, sample_results):
        """save() creates file on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = HTMLReportGenerator(sample_results)
            path = generator.save(Path(tmpdir) / "report.html")

            assert path.exists()
            assert path.read_text().startswith("<!DOCTYPE html>")


class TestJSONReportGenerator:
    """Tests for JSON report generation."""

    @pytest.fixture
    def sample_results(self):
        """Create sample test results."""
        return TestResults(
            config=None,
            mutations=[],
            statistics=TestStatistics(
                total_mutations=10,
                passed_mutations=8,
                failed_mutations=2,
                robustness_score=0.8,
                avg_latency_ms=150.0,
                p50_latency_ms=120.0,
                p95_latency_ms=300.0,
                p99_latency_ms=450.0,
                by_type=[],
            ),
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
        )

    def test_generate_valid_json(self, sample_results):
        """Generator produces valid JSON."""
        generator = JSONReportGenerator(sample_results)
        json_str = generator.generate()

        # Should not raise
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_contains_statistics(self, sample_results):
        """JSON contains statistics."""
        generator = JSONReportGenerator(sample_results)
        data = json.loads(generator.generate())

        assert "statistics" in data
        assert data["statistics"]["robustness_score"] == 0.8
```

---

## Integration Tests

### Location: `tests/test_integration.py`

### Prerequisites

Integration tests require:
1. Ollama running locally
2. A model pulled (e.g., `ollama pull qwen2.5-coder:7b`)
3. A mock agent running

### Example Test File

```python
# tests/test_integration.py
"""Integration tests for full flakestorm workflow."""

import pytest
import asyncio
from pathlib import Path
import tempfile

# Skip all tests if Ollama is not running
pytest_plugins = ["pytest_asyncio"]


def ollama_available():
    """Check if Ollama is running."""
    from flakestorm.integrations.huggingface import HuggingFaceModelProvider
    return HuggingFaceModelProvider.verify_ollama_connection()


@pytest.mark.skipif(not ollama_available(), reason="Ollama not running")
class TestFullWorkflow:
    """Integration tests for complete test runs."""

    @pytest.mark.asyncio
    async def test_full_run_with_mock_agent(self):
        """Test complete workflow with mock agent."""
        # This test would:
        # 1. Start a mock agent
        # 2. Create config
        # 3. Run flakestorm
        # 4. Verify results
        pass

    @pytest.mark.asyncio
    async def test_mutation_generation(self):
        """Test that mutation engine generates valid mutations."""
        from flakestorm.mutations.engine import MutationEngine
        from flakestorm.core.config import LLMConfig

        config = LLMConfig(
            model="qwen2.5-coder:7b",
            host="http://localhost:11434",
        )
        engine = MutationEngine(config)

        mutations = await engine.generate_mutations(
            prompt="Hello, world!",
            types=[MutationType.PARAPHRASE],
            count=3,
        )

        assert len(mutations) > 0
        assert all(m.mutated != "Hello, world!" for m in mutations)
```

---

## CLI Tests

### Location: `tests/test_cli.py`

### How to Test CLI Commands

Use the `CliRunner` from Typer for testing:

```python
# tests/test_cli.py
"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner
import tempfile
from pathlib import Path

from flakestorm.cli.main import app

runner = CliRunner()


class TestInitCommand:
    """Tests for `flakestorm init`."""

    def test_init_creates_config(self):
        """init creates flakestorm.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app, ["init", "--dir", tmpdir]
            )
            assert result.exit_code == 0
            assert (Path(tmpdir) / "flakestorm.yaml").exists()

    def test_init_no_overwrite(self):
        """init doesn't overwrite existing config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flakestorm.yaml"
            config_path.write_text("existing: content")

            result = runner.invoke(
                app, ["init", "--dir", tmpdir]
            )
            # Should warn about existing file
            assert "exists" in result.output.lower() or result.exit_code != 0


class TestVerifyCommand:
    """Tests for `flakestorm verify`."""

    def test_verify_valid_config(self):
        """verify accepts valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flakestorm.yaml"
            config_path.write_text("""
agent:
  endpoint: "http://localhost:8000/chat"
  type: http

golden_prompts:
  - "Test prompt"
""")
            result = runner.invoke(
                app, ["verify", "--config", str(config_path)]
            )
            assert result.exit_code == 0

    def test_verify_invalid_config(self):
        """verify rejects invalid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flakestorm.yaml"
            config_path.write_text("invalid: yaml: content:")

            result = runner.invoke(
                app, ["verify", "--config", str(config_path)]
            )
            assert result.exit_code != 0


class TestHelpCommand:
    """Tests for help output."""

    def test_main_help(self):
        """Main help displays commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "init" in result.output

    def test_run_help(self):
        """Run command help displays options."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--output" in result.output
```

---

## Test Fixtures

### Shared Fixtures in `conftest.py`

```python
# tests/conftest.py
"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yaml():
    """Sample valid config YAML."""
    return """
agent:
  endpoint: "http://localhost:8000/chat"
  type: http
  timeout: 30

golden_prompts:
  - "Test prompt 1"
  - "Test prompt 2"

mutations:
  count: 5
  types:
    - paraphrase
    - noise

invariants:
  - type: latency
    max_ms: 5000
"""


@pytest.fixture
def config_file(temp_dir, sample_config_yaml):
    """Create a config file in temp directory."""
    config_path = temp_dir / "flakestorm.yaml"
    config_path.write_text(sample_config_yaml)
    return config_path
```

---

## Summary: Remaining Test Items

| Checklist Item | Test File | Status |
|----------------|-----------|--------|
| Test agent adapters | `tests/test_adapters.py` | Template provided above |
| Test orchestrator | `tests/test_orchestrator.py` | Template provided above |
| Test report generation | `tests/test_reports.py` | Template provided above |
| Test CLI commands | `tests/test_cli.py` | Template provided above |
| Full integration test | `tests/test_integration.py` | Template provided above |

### Quick Start

1. Copy the templates above to create test files
2. Run: `pytest tests/test_<module>.py -v`
3. Add more test cases as needed
4. Run full suite: `pytest`

---

*Happy testing! 🧪*

