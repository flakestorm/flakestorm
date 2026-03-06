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
    ReplayConfig,
    ReplaySessionConfig,
    ReplayToolResponseConfig,
)
from flakestorm.replay.loader import ReplayLoader, resolve_contract, resolve_sessions_from_config
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

    def test_resolve_sessions_from_config_inline_only(self):
        """resolve_sessions_from_config returns inline sessions when no sources."""
        replays = ReplayConfig(
            sessions=[
                ReplaySessionConfig(id="a", input="q1", contract="default"),
                ReplaySessionConfig(id="b", input="q2", contract="default"),
            ],
            sources=[],
        )
        out = resolve_sessions_from_config(replays, None, include_sources=True)
        assert len(out) == 2
        assert out[0].id == "a"
        assert out[1].id == "b"

    def test_resolve_sessions_from_config_file_backed(self):
        """resolve_sessions_from_config loads file-backed sessions from config_dir."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w", encoding="utf-8"
        ) as f:
            yaml.dump({
                "id": "file-session",
                "input": "from file",
                "tool_responses": [],
                "contract": "default",
            }, f)
            f.flush()
            fpath = Path(f.name)
        try:
            config_dir = fpath.parent
            replays = ReplayConfig(
                sessions=[ReplaySessionConfig(id="", input="", file=fpath.name)],
                sources=[],
            )
            out = resolve_sessions_from_config(replays, config_dir, include_sources=True)
            assert len(out) == 1
            assert out[0].id == "file-session"
            assert out[0].input == "from file"
        finally:
            fpath.unlink(missing_ok=True)

    def test_replay_config_sources_parsed_from_dict(self):
        """ReplayConfig.sources parses langsmith and langsmith_run from dict (YAML)."""
        cfg = ReplayConfig.model_validate({
            "sessions": [],
            "sources": [
                {"type": "langsmith", "project": "my-agent", "auto_import": True},
                {"type": "langsmith_run", "run_id": "abc-123"},
            ],
        })
        assert len(cfg.sources) == 2
        assert cfg.sources[0].project == "my-agent"
        assert cfg.sources[0].auto_import is True
        assert cfg.sources[1].run_id == "abc-123"


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
