"""Integration tests for replay: loader, resolve_contract, runner."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from flakestorm.core.config import (
    FlakeStormConfig,
    AgentConfig,
    AgentType,
    ModelConfig,
    MutationConfig,
    InvariantConfig,
    InvariantType,
    OutputConfig,
    AdvancedConfig,
    ContractConfig,
    ContractInvariantConfig,
    ReplaySessionConfig,
    ReplayToolResponseConfig,
)
from flakestorm.replay.loader import ReplayLoader, resolve_contract
from flakestorm.replay.runner import ReplayRunner, ReplayResult
from flakestorm.core.protocol import AgentResponse, BaseAgentAdapter


class _MockAgent(BaseAgentAdapter):
    """Sync mock adapter that returns a fixed response."""

    def __init__(self, output: str = "ok", error: str | None = None):
        self._output = output
        self._error = error

    async def invoke(self, input: str) -> AgentResponse:
        return AgentResponse(
            output=self._output,
            latency_ms=10.0,
            error=self._error,
        )


class TestReplayLoader:
    """Test replay file and contract resolution."""

    def test_load_file_yaml(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w", encoding="utf-8"
        ) as f:
            yaml.dump({
                "id": "r1",
                "input": "What is 2+2?",
                "tool_responses": [],
                "contract": "default",
            }, f)
            f.flush()
            path = f.name
        try:
            loader = ReplayLoader()
            session = loader.load_file(path)
            assert session.id == "r1"
            assert session.input == "What is 2+2?"
            assert session.contract == "default"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_resolve_contract_by_name(self):
        contract = ContractConfig(
            name="my_contract",
            invariants=[ContractInvariantConfig(id="i1", type="contains", value="x")],
        )
        config = FlakeStormConfig(
            agent=AgentConfig(endpoint="http://x", type=AgentType.HTTP),
            model=ModelConfig(),
            mutations=MutationConfig(),
            golden_prompts=["p"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=1000)],
            output=OutputConfig(),
            advanced=AdvancedConfig(),
            contract=contract,
        )
        resolved = resolve_contract("my_contract", config, None)
        assert resolved.name == "my_contract"
        assert len(resolved.invariants) == 1

    def test_resolve_contract_not_found(self):
        config = FlakeStormConfig(
            agent=AgentConfig(endpoint="http://x", type=AgentType.HTTP),
            model=ModelConfig(),
            mutations=MutationConfig(),
            golden_prompts=["p"],
            invariants=[InvariantConfig(type=InvariantType.LATENCY, max_ms=1000)],
            output=OutputConfig(),
            advanced=AdvancedConfig(),
        )
        with pytest.raises(FileNotFoundError):
            resolve_contract("nonexistent", config, None)


class TestReplayRunner:
    """Test replay runner and verification."""

    @pytest.mark.asyncio
    async def test_run_without_contract(self):
        agent = _MockAgent(output="hello")
        runner = ReplayRunner(agent)
        session = ReplaySessionConfig(
            id="s1",
            input="hi",
            tool_responses=[],
            contract="default",
        )
        result = await runner.run(session)
        assert isinstance(result, ReplayResult)
        assert result.response.output == "hello"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_run_with_contract_passes(self):
        agent = _MockAgent(output="the answer is 42")
        contract = ContractConfig(
            name="c1",
            invariants=[
                ContractInvariantConfig(id="i1", type="contains", value="answer"),
            ],
        )
        runner = ReplayRunner(agent, contract=contract)
        session = ReplaySessionConfig(id="s1", input="?", tool_responses=[], contract="c1")
        result = await runner.run(session, contract=contract)
        assert result.passed is True
        assert "contains" in str(result.verification_details).lower() or result.verification_details

    @pytest.mark.asyncio
    async def test_run_with_contract_fails(self):
        agent = _MockAgent(output="no match")
        contract = ContractConfig(
            name="c1",
            invariants=[
                ContractInvariantConfig(id="i1", type="contains", value="required_word"),
            ],
        )
        runner = ReplayRunner(agent, contract=contract)
        session = ReplaySessionConfig(id="s1", input="?", tool_responses=[], contract="c1")
        result = await runner.run(session, contract=contract)
        assert result.passed is False
