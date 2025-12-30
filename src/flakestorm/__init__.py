"""
flakestorm - The Agent Reliability Engine

Chaos Engineering for AI Agents. Apply adversarial fuzzing to prove
your agents are production-ready before deployment.

Example:
    >>> from flakestorm import FlakeStormRunner, load_config
    >>> config = load_config("flakestorm.yaml")
    >>> runner = FlakeStormRunner(config)
    >>> results = await runner.run()
    >>> print(f"Robustness Score: {results.robustness_score:.1%}")
"""

__version__ = "0.1.0"
__author__ = "flakestorm Team"
__license__ = "Apache-2.0"

from flakestorm.assertions.verifier import InvariantVerifier, VerificationResult
from flakestorm.core.config import (
    AgentConfig,
    FlakeStormConfig,
    InvariantConfig,
    ModelConfig,
    MutationConfig,
    OutputConfig,
    load_config,
)
from flakestorm.core.orchestrator import Orchestrator
from flakestorm.core.protocol import (
    AgentProtocol,
    HTTPAgentAdapter,
    PythonAgentAdapter,
    create_agent_adapter,
)
from flakestorm.core.runner import FlakeStormRunner
from flakestorm.mutations.engine import MutationEngine
from flakestorm.mutations.types import Mutation, MutationType
from flakestorm.reports.models import TestResults, TestStatistics

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Configuration
    "FlakeStormConfig",
    "load_config",
    "AgentConfig",
    "ModelConfig",
    "MutationConfig",
    "InvariantConfig",
    "OutputConfig",
    # Agent Protocol
    "AgentProtocol",
    "HTTPAgentAdapter",
    "PythonAgentAdapter",
    "create_agent_adapter",
    # Core
    "FlakeStormRunner",
    "Orchestrator",
    # Mutations
    "MutationEngine",
    "MutationType",
    "Mutation",
    # Assertions
    "InvariantVerifier",
    "VerificationResult",
    # Results
    "TestResults",
    "TestStatistics",
]
