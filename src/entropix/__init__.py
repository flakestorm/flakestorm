"""
Entropix - The Agent Reliability Engine

Chaos Engineering for AI Agents. Apply adversarial fuzzing to prove
your agents are production-ready before deployment.

Example:
    >>> from entropix import EntropixRunner, load_config
    >>> config = load_config("entropix.yaml")
    >>> runner = EntropixRunner(config)
    >>> results = await runner.run()
    >>> print(f"Robustness Score: {results.robustness_score:.1%}")
"""

__version__ = "0.1.0"
__author__ = "Entropix Team"
__license__ = "Apache-2.0"

from entropix.core.config import (
    EntropixConfig,
    load_config,
    AgentConfig,
    ModelConfig,
    MutationConfig,
    InvariantConfig,
    OutputConfig,
)
from entropix.core.protocol import (
    AgentProtocol,
    HTTPAgentAdapter,
    PythonAgentAdapter,
    create_agent_adapter,
)
from entropix.core.runner import EntropixRunner
from entropix.core.orchestrator import Orchestrator
from entropix.mutations.engine import MutationEngine
from entropix.mutations.types import MutationType, Mutation
from entropix.assertions.verifier import InvariantVerifier, VerificationResult
from entropix.reports.models import TestResults, TestStatistics

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Configuration
    "EntropixConfig",
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
    "EntropixRunner",
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

