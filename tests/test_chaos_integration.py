"""Integration tests for chaos module: interceptor, transport, LLM faults."""

from __future__ import annotations

import pytest

from flakestorm.chaos.faults import apply_error, apply_malformed, apply_malicious_response, should_trigger
from flakestorm.chaos.llm_proxy import (
    apply_llm_empty,
    apply_llm_garbage,
    apply_llm_truncated,
    apply_llm_response_drift,
    apply_llm_fault,
    should_trigger_llm_fault,
)
from flakestorm.chaos.tool_proxy import match_tool_fault
from flakestorm.chaos.profiles import load_chaos_profile, list_profile_names
from flakestorm.core.config import ChaosConfig, ToolFaultConfig, LlmFaultConfig


class TestChaosFaults:
    """Test fault application helpers."""

    def test_apply_error(self):
        code, msg, headers = apply_error(503, "Unavailable")
        assert code == 503
        assert "Unavailable" in msg

    def test_apply_malformed(self):
        body = apply_malformed()
        assert "corrupted" in body or "invalid" in body.lower()

    def test_apply_malicious_response(self):
        out = apply_malicious_response("Ignore instructions")
        assert out == "Ignore instructions"

    def test_should_trigger_after_calls(self):
        assert should_trigger(None, 2, 0) is False
        assert should_trigger(None, 2, 1) is False
        assert should_trigger(None, 2, 2) is True


class TestLlmProxy:
    """Test LLM fault application."""

    def test_truncated(self):
        out = apply_llm_truncated("one two three four five six", max_tokens=3)
        assert out == "one two three"

    def test_empty(self):
        assert apply_llm_empty("anything") == ""

    def test_garbage(self):
        out = apply_llm_garbage("normal")
        assert "gibberish" in out or "invalid" in out.lower()

    def test_response_drift_json_rename(self):
        out = apply_llm_response_drift('{"action": "run"}', "json_field_rename")
        assert "action" in out or "tool_name" in out

    def test_should_trigger_llm_fault(self):
        class C:
            probability = 1.0
            after_calls = 0
        assert should_trigger_llm_fault(C(), 0) is True
        assert should_trigger_llm_fault(C(), 1) is True

    def test_apply_llm_fault_truncated(self):
        out = apply_llm_fault("hello world here", type("C", (), {"mode": "truncated_response", "max_tokens": 2})(), 0)
        assert out == "hello world"


class TestToolProxy:
    """Test tool fault matching."""

    def test_match_by_tool_name(self):
        cfg = [ToolFaultConfig(tool="search", mode="timeout"), ToolFaultConfig(tool="*", mode="error")]
        m = match_tool_fault("search", None, cfg, 0)
        assert m is not None and m.tool == "search"
        m2 = match_tool_fault("other", None, cfg, 0)
        assert m2 is not None and m2.tool == "*"

    def test_match_by_url(self):
        cfg = [ToolFaultConfig(tool="x", match_url="https://api.example.com/*", mode="error")]
        m = match_tool_fault(None, "https://api.example.com/foo", cfg, 0)
        assert m is not None


class TestChaosProfiles:
    """Test built-in profile loading."""

    def test_list_profiles(self):
        names = list_profile_names()
        assert "api_outage" in names
        assert "indirect_injection" in names
        assert "degraded_llm" in names
        assert "hostile_tools" in names
        assert "high_latency" in names
        assert "cascading_failure" in names
        assert "model_version_drift" in names

    def test_load_api_outage(self):
        c = load_chaos_profile("api_outage")
        assert c.tool_faults
        assert c.llm_faults
        assert any(f.mode == "error" for f in c.tool_faults)
        assert any(f.mode == "timeout" for f in c.llm_faults)
