"""
Replay runner: run replay sessions and verify against contract.

For HTTP agents, deterministic tool response injection is not possible
(we only see one request). We send session.input and verify the response
against the resolved contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from flakestorm.core.protocol import AgentResponse, BaseAgentAdapter

from flakestorm.core.config import ContractConfig, ReplaySessionConfig


@dataclass
class ReplayResult:
    """Result of a replay run including verification against contract."""

    response: AgentResponse
    passed: bool = True
    verification_details: list[str] = field(default_factory=list)


class ReplayRunner:
    """Run a single replay session and verify against contract."""

    def __init__(
        self,
        agent: BaseAgentAdapter,
        contract: ContractConfig | None = None,
        verifier=None,
    ):
        self._agent = agent
        self._contract = contract
        self._verifier = verifier

    async def run(
        self,
        session: ReplaySessionConfig,
        contract: ContractConfig | None = None,
    ) -> ReplayResult:
        """
        Replay the session: send session.input to agent and verify against contract.
        Contract can be passed in or resolved from session.contract by caller.
        """
        contract = contract or self._contract
        response = await self._agent.invoke(session.input)
        if not contract:
            return ReplayResult(response=response, passed=response.success)

        # Verify against contract invariants
        from flakestorm.contracts.engine import _contract_invariant_to_invariant_config
        from flakestorm.assertions.verifier import InvariantVerifier

        invariant_configs = [
            _contract_invariant_to_invariant_config(inv)
            for inv in contract.invariants
        ]
        if not invariant_configs:
            return ReplayResult(response=response, passed=not response.error)
        verifier = InvariantVerifier(invariant_configs)
        result = verifier.verify(
            response.output or "",
            response.latency_ms,
        )
        details = [f"{c.type.value}: {'pass' if c.passed else 'fail'}" for c in result.checks]
        return ReplayResult(
            response=response,
            passed=result.all_passed and not response.error,
            verification_details=details,
        )
