"""
Contract engine: run contract invariants across chaos matrix cells.

For each (invariant, scenario) cell: optional reset, apply scenario chaos,
run golden prompts, run InvariantVerifier with contract invariants, record pass/fail.
Warns if no reset and agent appears stateful.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from flakestorm.assertions.verifier import InvariantVerifier
from flakestorm.contracts.matrix import ResilienceMatrix
from flakestorm.core.config import (
    ChaosConfig,
    ChaosScenarioConfig,
    ContractConfig,
    ContractInvariantConfig,
    FlakeStormConfig,
    InvariantConfig,
    InvariantType,
)

if TYPE_CHECKING:
    from flakestorm.core.protocol import BaseAgentAdapter

logger = logging.getLogger(__name__)

STATEFUL_WARNING = (
    "Warning: No reset_endpoint configured. Contract matrix cells may share state. "
    "Results may be contaminated. Add reset_endpoint to your config for accurate isolation."
)


def _contract_invariant_to_invariant_config(c: ContractInvariantConfig) -> InvariantConfig:
    """Convert a contract invariant to verifier InvariantConfig."""
    try:
        inv_type = InvariantType(c.type) if isinstance(c.type, str) else c.type
    except ValueError:
        inv_type = InvariantType.REGEX  # fallback
    return InvariantConfig(
        type=inv_type,
        description=c.description,
        id=c.id,
        severity=c.severity,
        when=c.when,
        negate=c.negate,
        value=c.value,
        values=c.values,
        pattern=c.pattern,
        patterns=c.patterns,
        max_ms=c.max_ms,
        threshold=c.threshold or 0.8,
        baseline=c.baseline,
        similarity_threshold=c.similarity_threshold or 0.75,
    )


def _invariant_has_probes(inv: ContractInvariantConfig) -> bool:
    """True if this invariant uses probe prompts (system_prompt_leak_probe)."""
    return bool(getattr(inv, "probes", None))


def _scenario_to_chaos_config(scenario: ChaosScenarioConfig) -> ChaosConfig:
    """Convert a chaos scenario to ChaosConfig for instrumented adapter."""
    return ChaosConfig(
        tool_faults=scenario.tool_faults or [],
        llm_faults=scenario.llm_faults or [],
        context_attacks=scenario.context_attacks or [],
    )


class ContractEngine:
    """
    Runs behavioral contract across chaos matrix.

    Optional reset_endpoint/reset_function per cell; warns if stateful and no reset.
    Runs InvariantVerifier with contract invariants for each cell.
    """

    def __init__(
        self,
        config: FlakeStormConfig,
        contract: ContractConfig,
        agent: BaseAgentAdapter,
    ):
        self.config = config
        self.contract = contract
        self.agent = agent
        self._matrix = ResilienceMatrix()
        # Build verifier from contract invariants (one verifier per invariant for per-check result, or one verifier for all)
        invariant_configs = [
            _contract_invariant_to_invariant_config(inv)
            for inv in (contract.invariants or [])
        ]
        self._verifier = InvariantVerifier(invariant_configs) if invariant_configs else None

    async def _reset_agent(self) -> None:
        """Call reset_endpoint or reset_function if configured."""
        agent_config = self.config.agent
        if agent_config.reset_endpoint:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(agent_config.reset_endpoint)
            except Exception as e:
                logger.warning("Reset endpoint failed: %s", e)
        elif agent_config.reset_function:
            import importlib
            mod_path = agent_config.reset_function
            module_name, attr_name = mod_path.rsplit(":", 1)
            mod = importlib.import_module(module_name)
            fn = getattr(mod, attr_name)
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                fn()

    async def _detect_stateful_and_warn(self, prompts: list[str]) -> bool:
        """Run same prompt twice without chaos; if responses differ, return True and warn."""
        if not prompts or not self._verifier:
            return False
        # Use first golden prompt
        prompt = prompts[0]
        try:
            r1 = await self.agent.invoke(prompt)
            r2 = await self.agent.invoke(prompt)
        except Exception:
            return False
        out1 = (r1.output or "").strip()
        out2 = (r2.output or "").strip()
        if out1 != out2:
            logger.warning(STATEFUL_WARNING)
            return True
        return False

    async def run(self) -> ResilienceMatrix:
        """
        Execute all (invariant × scenario) cells: reset (optional), apply scenario chaos,
        run golden prompts, verify with contract invariants, record pass/fail.
        """
        from flakestorm.core.protocol import create_instrumented_adapter

        scenarios = self.contract.chaos_matrix or []
        invariants = self.contract.invariants or []
        prompts = self.config.golden_prompts or ["test"]
        agent_config = self.config.agent
        has_reset = bool(agent_config.reset_endpoint or agent_config.reset_function)
        if not has_reset:
            if await self._detect_stateful_and_warn(prompts):
                logger.warning(STATEFUL_WARNING)

        for scenario in scenarios:
            scenario_chaos = _scenario_to_chaos_config(scenario)
            scenario_agent = create_instrumented_adapter(self.agent, scenario_chaos)

            for inv in invariants:
                if has_reset:
                    await self._reset_agent()

                passed = True
                baseline_response: str | None = None
                # For behavior_unchanged we need baseline: run once without chaos
                if inv.type == "behavior_unchanged" and (inv.baseline == "auto" or not inv.baseline):
                    try:
                        base_resp = await self.agent.invoke(prompts[0])
                        baseline_response = base_resp.output or ""
                    except Exception:
                        pass

                # system_prompt_leak_probe: use probe prompts instead of golden_prompts
                prompts_to_run = getattr(inv, "probes", None) or prompts
                for prompt in prompts_to_run:
                    try:
                        response = await scenario_agent.invoke(prompt)
                        if response.error:
                            passed = False
                            break
                        if self._verifier is None:
                            continue
                        # Run verifier for this invariant only (verifier has all; we check the one that matches inv.id)
                        result = self._verifier.verify(
                            response.output or "",
                            response.latency_ms,
                            baseline_response=baseline_response,
                        )
                        # Consider passed if the check for this invariant's type passes (by index)
                        inv_index = next(
                            (i for i, c in enumerate(invariants) if c.id == inv.id),
                            None,
                        )
                        if inv_index is not None and inv_index < len(result.checks):
                            if not result.checks[inv_index].passed:
                                passed = False
                                break
                    except Exception as e:
                        logger.warning("Contract cell failed: %s", e)
                        passed = False
                        break

                self._matrix.add_result(
                    inv.id,
                    scenario.name,
                    inv.severity,
                    passed,
                )

        return self._matrix
