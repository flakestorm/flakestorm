"""Tests for the flakestorm orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest


class TestOrchestratorState:
    """Tests for orchestrator state tracking."""

    def test_initial_state(self):
        """State initializes correctly."""
        from flakestorm.core.orchestrator import OrchestratorState

        state = OrchestratorState()
        assert state.total_mutations == 0
        assert state.completed_mutations == 0
        assert state.completed_at is None

    def test_state_started_at(self):
        """State records start time."""
        from flakestorm.core.orchestrator import OrchestratorState

        state = OrchestratorState()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_state_updates(self):
        """State updates as tests run."""
        from flakestorm.core.orchestrator import OrchestratorState

        state = OrchestratorState()
        state.total_mutations = 10
        state.completed_mutations = 5
        assert state.completed_mutations == 5
        assert state.total_mutations == 10

    def test_state_duration_seconds(self):
        """State calculates duration."""
        from flakestorm.core.orchestrator import OrchestratorState

        state = OrchestratorState()
        duration = state.duration_seconds
        assert isinstance(duration, float)
        assert duration >= 0

    def test_state_progress_percentage(self):
        """State calculates progress percentage."""
        from flakestorm.core.orchestrator import OrchestratorState

        state = OrchestratorState()
        state.total_mutations = 100
        state.completed_mutations = 25
        assert state.progress_percentage == 25.0


class TestOrchestrator:
    """Tests for main orchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create a minimal test config."""
        from flakestorm.core.config import (
            AgentConfig,
            AgentType,
            FlakeStormConfig,
            InvariantConfig,
            InvariantType,
            MutationConfig,
        )
        from flakestorm.mutations.types import MutationType

        return FlakeStormConfig(
            agent=AgentConfig(
                endpoint="http://localhost:8000/chat",
                type=AgentType.HTTP,
            ),
            golden_prompts=["Test prompt 1", "Test prompt 2"],
            mutations=MutationConfig(
                count=5,
                types=[MutationType.PARAPHRASE],
            ),
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=5000)],
        )

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent adapter."""
        agent = MagicMock()
        agent.invoke = MagicMock()
        return agent

    @pytest.fixture
    def mock_mutation_engine(self):
        """Create a mock mutation engine."""
        engine = MagicMock()
        engine.generate_mutations = MagicMock()
        return engine

    @pytest.fixture
    def mock_verifier(self):
        """Create a mock verifier."""
        verifier = MagicMock()
        verifier.verify = MagicMock()
        return verifier

    def test_orchestrator_creation(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator can be created with all required arguments."""
        from flakestorm.core.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )
        assert orchestrator is not None
        assert orchestrator.config == mock_config

    def test_orchestrator_has_run_method(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator has run method."""
        from flakestorm.core.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )
        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)

    def test_orchestrator_state_initialization(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator initializes state correctly."""
        from flakestorm.core.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )
        assert hasattr(orchestrator, "state")
        assert orchestrator.state.total_mutations == 0

    def test_orchestrator_stores_components(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator stores all components."""
        from flakestorm.core.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
        )
        assert orchestrator.agent == mock_agent
        assert orchestrator.mutation_engine == mock_mutation_engine
        assert orchestrator.verifier == mock_verifier

    def test_orchestrator_optional_console(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator accepts optional console."""
        from rich.console import Console

        from flakestorm.core.orchestrator import Orchestrator

        custom_console = Console()
        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
            console=custom_console,
        )
        assert orchestrator.console == custom_console

    def test_orchestrator_show_progress_flag(
        self, mock_config, mock_agent, mock_mutation_engine, mock_verifier
    ):
        """Orchestrator accepts show_progress flag."""
        from flakestorm.core.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            config=mock_config,
            agent=mock_agent,
            mutation_engine=mock_mutation_engine,
            verifier=mock_verifier,
            show_progress=False,
        )
        assert orchestrator.show_progress is False


class TestMutationGeneration:
    """Tests for mutation generation phase."""

    def test_mutation_count_calculation(self):
        """Test mutation count is calculated correctly."""
        from flakestorm.core.config import MutationConfig
        from flakestorm.mutations.types import MutationType

        config = MutationConfig(
            count=10,
            types=[MutationType.PARAPHRASE, MutationType.NOISE],
        )
        assert config.count == 10

    def test_mutation_types_configuration(self):
        """Test mutation types are configured correctly."""
        from flakestorm.core.config import MutationConfig
        from flakestorm.mutations.types import MutationType

        config = MutationConfig(
            count=5,
            types=[MutationType.PARAPHRASE, MutationType.NOISE],
        )
        assert MutationType.PARAPHRASE in config.types
        assert MutationType.NOISE in config.types
        assert len(config.types) == 2
