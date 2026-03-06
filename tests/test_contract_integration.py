"""Integration tests for contract engine: matrix, verifier integration, reset."""

from __future__ import annotations

import pytest

from flakestorm.contracts.matrix import ResilienceMatrix, SEVERITY_WEIGHT, CellResult
from flakestorm.contracts.engine import (
    _contract_invariant_to_invariant_config,
    _scenario_to_chaos_config,
    STATEFUL_WARNING,
)
from flakestorm.core.config import (
    ContractConfig,
    ContractInvariantConfig,
    ChaosScenarioConfig,
    ChaosConfig,
    ToolFaultConfig,
    InvariantType,
)


class TestResilienceMatrix:
    """Test resilience matrix and score."""

    def test_empty_score(self):
        m = ResilienceMatrix()
        assert m.resilience_score == 100.0
        assert m.passed is True

    def test_weighted_score(self):
        m = ResilienceMatrix()
        m.add_result("inv1", "sc1", "critical", True)
        m.add_result("inv2", "sc1", "high", False)
        m.add_result("inv3", "sc1", "medium", True)
        assert m.resilience_score < 100.0
        assert m.passed is True  # no critical failed yet
        m.add_result("inv0", "sc1", "critical", False)
        assert m.critical_failed is True
        assert m.passed is False

    def test_severity_weights(self):
        assert SEVERITY_WEIGHT["critical"] == 3
        assert SEVERITY_WEIGHT["high"] == 2
        assert SEVERITY_WEIGHT["medium"] == 1


class TestContractEngineHelpers:
    """Test contract invariant conversion and scenario to chaos."""

    def test_contract_invariant_to_invariant_config(self):
        c = ContractInvariantConfig(id="t1", type="contains", value="ok", severity="high")
        inv = _contract_invariant_to_invariant_config(c)
        assert inv.type == InvariantType.CONTAINS
        assert inv.value == "ok"
        assert inv.severity == "high"

    def test_scenario_to_chaos_config(self):
        sc = ChaosScenarioConfig(
            name="test",
            tool_faults=[ToolFaultConfig(tool="*", mode="error", error_code=503)],
            llm_faults=[],
        )
        chaos = _scenario_to_chaos_config(sc)
        assert isinstance(chaos, ChaosConfig)
        assert len(chaos.tool_faults) == 1
        assert chaos.tool_faults[0].mode == "error"
