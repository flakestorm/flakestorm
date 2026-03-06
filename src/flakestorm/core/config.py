"""
Configuration Management for flakestorm

Handles loading and validating the flakestorm.yaml configuration file.
Uses Pydantic for robust validation and type safety.
"""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# Import MutationType from mutations to avoid duplicate definition
from flakestorm.mutations.types import MutationType

# Env var reference pattern: ${VAR_NAME} only. Literal API keys are not allowed in V2.
_API_KEY_ENV_REF_PATTERN = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")


class AgentType(str, Enum):
    """Supported agent connection types."""

    HTTP = "http"
    PYTHON = "python"
    LANGCHAIN = "langchain"


class AgentConfig(BaseModel):
    """Configuration for connecting to the target agent."""

    endpoint: str = Field(..., description="Agent endpoint URL or Python module path")
    type: AgentType = Field(default=AgentType.HTTP, description="Agent connection type")
    method: str = Field(
        default="POST",
        description="HTTP method (GET, POST, PUT, PATCH, DELETE)",
    )
    request_template: str | None = Field(
        default=None,
        description="Template for request body/query with variable substitution (use {prompt} or {field_name})",
    )
    response_path: str | None = Field(
        default=None,
        description="JSONPath or dot notation to extract response from JSON (e.g., '$.data.result' or 'data.result')",
    )
    query_params: dict[str, str] = Field(
        default_factory=dict, description="Static query parameters for HTTP requests"
    )
    parse_structured_input: bool = Field(
        default=True,
        description="Whether to parse structured golden prompts into key-value pairs",
    )
    timeout: int = Field(
        default=30000, ge=1000, le=300000, description="Timeout in milliseconds"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom headers for HTTP requests"
    )
    # V2: optional reset for contract matrix isolation (stateful agents)
    reset_endpoint: str | None = Field(
        default=None,
        description="HTTP endpoint to call before each contract matrix cell (e.g. /reset)",
    )
    reset_function: str | None = Field(
        default=None,
        description="Python module path to reset function (e.g. myagent:reset_state)",
    )

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate endpoint format based on type."""
        # Expand environment variables
        return os.path.expandvars(v)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if v.upper() not in valid_methods:
            raise ValueError(
                f"Invalid HTTP method: {v}. Must be one of {valid_methods}"
            )
        return v.upper()

    @field_validator("headers")
    @classmethod
    def expand_header_env_vars(cls, v: dict[str, str]) -> dict[str, str]:
        """Expand environment variables in header values."""
        return {k: os.path.expandvars(val) for k, val in v.items()}

    @field_validator("query_params")
    @classmethod
    def expand_query_env_vars(cls, v: dict[str, str]) -> dict[str, str]:
        """Expand environment variables in query parameter values."""
        return {k: os.path.expandvars(val) for k, val in v.items()}


class LLMProvider(str, Enum):
    """Supported LLM providers for mutation generation."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ModelConfig(BaseModel):
    """Configuration for the mutation generation model."""

    provider: LLMProvider | str = Field(
        default=LLMProvider.OLLAMA,
        description="Model provider: ollama | openai | anthropic | google",
    )
    name: str = Field(default="qwen3:8b", description="Model name (e.g. gpt-4o-mini, gemini-2.0-flash)")
    api_key: str | None = Field(
        default=None,
        description="API key via env var only, e.g. ${OPENAI_API_KEY}. Literal keys not allowed in V2.",
    )
    base_url: str | None = Field(
        default="http://localhost:11434",
        description="Model server URL (Ollama) or custom endpoint for OpenAI-compatible APIs",
    )
    temperature: float = Field(
        default=0.8, ge=0.0, le=2.0, description="Temperature for mutation generation"
    )

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: str | LLMProvider) -> str:
        if isinstance(v, LLMProvider):
            return v.value
        s = (v or "ollama").strip().lower()
        if s not in ("ollama", "openai", "anthropic", "google"):
            raise ValueError(
                f"Invalid provider: {v}. Must be one of: ollama, openai, anthropic, google"
            )
        return s

    @model_validator(mode="after")
    def validate_api_key_env_only(self) -> ModelConfig:
        """Enforce env-var-only API keys in V2; literal keys are not allowed."""
        p = getattr(self.provider, "value", self.provider) or "ollama"
        if p == "ollama":
            return self
        # For openai, anthropic, google: if api_key is set it must look like ${VAR}
        if not self.api_key:
            return self
        key = self.api_key.strip()
        if not _API_KEY_ENV_REF_PATTERN.match(key):
            raise ValueError(
                'Literal API keys are not allowed in config. '
                'Use: api_key: "${OPENAI_API_KEY}"'
            )
        return self


class MutationConfig(BaseModel):
    """
    Configuration for mutation generation.

    Limits:
    - Maximum 50 total mutations per test run
    - 22+ mutation types available covering prompt-level and system/network-level attacks

    Mutation types include:
    - Original 8: paraphrase, noise, tone_shift, prompt_injection, encoding_attacks, context_manipulation, length_extremes, custom
    - Advanced prompt-level (7): multi_turn_attack, advanced_jailbreak, semantic_similarity_attack, format_poisoning, language_mixing, token_manipulation, temporal_attack
    - System/Network-level (8+): http_header_injection, payload_size_attack, content_type_confusion, query_parameter_poisoning, request_method_attack, protocol_level_attack, resource_exhaustion, concurrent_request_pattern, timeout_manipulation

    """

    count: int = Field(
        default=10,
        ge=1,
        le=50,  # Open Source limit
        description="Number of mutations per golden prompt (max 50 total per run)",
    )
    types: list[MutationType] = Field(
        default_factory=lambda: [
            MutationType.PARAPHRASE,
            MutationType.NOISE,
            MutationType.TONE_SHIFT,
            MutationType.PROMPT_INJECTION,
            MutationType.ENCODING_ATTACKS,
            MutationType.CONTEXT_MANIPULATION,
            MutationType.LENGTH_EXTREMES,
        ],
        description="Types of mutations to generate (22+ types available)",
    )
    weights: dict[MutationType, float] = Field(
        default_factory=lambda: {
            # Original 8 types
            MutationType.PARAPHRASE: 1.0,
            MutationType.NOISE: 0.8,
            MutationType.TONE_SHIFT: 0.9,
            MutationType.PROMPT_INJECTION: 1.5,
            MutationType.ENCODING_ATTACKS: 1.3,
            MutationType.CONTEXT_MANIPULATION: 1.1,
            MutationType.LENGTH_EXTREMES: 1.2,
            MutationType.CUSTOM: 1.0,
            # Advanced prompt-level attacks
            MutationType.MULTI_TURN_ATTACK: 1.4,
            MutationType.ADVANCED_JAILBREAK: 2.0,
            MutationType.SEMANTIC_SIMILARITY_ATTACK: 1.3,
            MutationType.FORMAT_POISONING: 1.6,
            MutationType.LANGUAGE_MIXING: 1.2,
            MutationType.TOKEN_MANIPULATION: 1.5,
            MutationType.TEMPORAL_ATTACK: 1.1,
            # System/Network-level attacks
            MutationType.HTTP_HEADER_INJECTION: 1.7,
            MutationType.PAYLOAD_SIZE_ATTACK: 1.4,
            MutationType.CONTENT_TYPE_CONFUSION: 1.5,
            MutationType.QUERY_PARAMETER_POISONING: 1.6,
            MutationType.REQUEST_METHOD_ATTACK: 1.3,
            MutationType.PROTOCOL_LEVEL_ATTACK: 1.8,
            MutationType.RESOURCE_EXHAUSTION: 1.5,
            MutationType.CONCURRENT_REQUEST_PATTERN: 1.4,
            MutationType.TIMEOUT_MANIPULATION: 1.3,
        },
        description="Scoring weights for each mutation type",
    )
    custom_templates: dict[str, str] = Field(
        default_factory=dict,
        description="Custom mutation templates (use {prompt} placeholder)",
    )


class InvariantType(str, Enum):
    """Types of invariant checks."""

    # Deterministic
    CONTAINS = "contains"
    LATENCY = "latency"
    VALID_JSON = "valid_json"
    REGEX = "regex"
    # Semantic
    SIMILARITY = "similarity"
    # Safety
    EXCLUDES_PII = "excludes_pii"
    REFUSAL_CHECK = "refusal_check"
    # V2 extensions
    CONTAINS_ANY = "contains_any"
    OUTPUT_NOT_EMPTY = "output_not_empty"
    COMPLETES = "completes"
    EXCLUDES_PATTERN = "excludes_pattern"
    BEHAVIOR_UNCHANGED = "behavior_unchanged"


class InvariantSeverity(str, Enum):
    """Severity for contract invariants (weights resilience score)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvariantWhen(str, Enum):
    """When to activate a contract invariant."""

    ALWAYS = "always"
    TOOL_FAULTS_ACTIVE = "tool_faults_active"
    LLM_FAULTS_ACTIVE = "llm_faults_active"
    ANY_CHAOS_ACTIVE = "any_chaos_active"
    NO_CHAOS = "no_chaos"


class InvariantConfig(BaseModel):
    """Configuration for a single invariant check."""

    type: InvariantType = Field(..., description="Type of invariant check")
    description: str | None = Field(
        default=None, description="Human-readable description"
    )
    # V2 contract fields
    id: str | None = Field(default=None, description="Unique id for contract tracking")
    severity: InvariantSeverity | str | None = Field(
        default=None, description="Severity: critical, high, medium, low"
    )
    when: InvariantWhen | str | None = Field(
        default=None, description="When to run: always, tool_faults_active, etc."
    )
    negate: bool = Field(default=False, description="Invert check result")

    # Type-specific fields
    value: str | None = Field(default=None, description="Value for 'contains' check")
    values: list[str] | None = Field(
        default=None, description="Values for 'contains_any' check"
    )
    max_ms: int | None = Field(
        default=None, description="Maximum latency for 'latency' check"
    )
    pattern: str | None = Field(
        default=None, description="Regex pattern for 'regex' check"
    )
    patterns: list[str] | None = Field(
        default=None, description="Patterns for 'excludes_pattern' check"
    )
    expected: str | None = Field(
        default=None, description="Expected text for 'similarity' check"
    )
    threshold: float | None = Field(
        default=0.8, ge=0.0, le=1.0, description="Similarity threshold"
    )
    dangerous_prompts: bool | None = Field(
        default=True, description="Check for dangerous prompt handling"
    )
    # behavior_unchanged
    baseline: str | None = Field(
        default=None,
        description="'auto' or manual baseline string for behavior_unchanged",
    )
    similarity_threshold: float | None = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Min similarity for behavior_unchanged (default 0.75)",
    )

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> InvariantConfig:
        """Ensure required fields are present for each type."""
        if self.type == InvariantType.CONTAINS and not self.value:
            raise ValueError("'contains' invariant requires 'value' field")
        if self.type == InvariantType.CONTAINS_ANY and not self.values:
            raise ValueError("'contains_any' invariant requires 'values' field")
        if self.type == InvariantType.LATENCY and not self.max_ms:
            raise ValueError("'latency' invariant requires 'max_ms' field")
        if self.type == InvariantType.REGEX and not self.pattern:
            raise ValueError("'regex' invariant requires 'pattern' field")
        if self.type == InvariantType.SIMILARITY and not self.expected:
            raise ValueError("'similarity' invariant requires 'expected' field")
        if self.type == InvariantType.EXCLUDES_PATTERN and not self.patterns:
            raise ValueError("'excludes_pattern' invariant requires 'patterns' field")
        return self


class OutputFormat(str, Enum):
    """Supported output formats."""

    HTML = "html"
    JSON = "json"
    TERMINAL = "terminal"


class OutputConfig(BaseModel):
    """Configuration for test output and reporting."""

    format: OutputFormat = Field(default=OutputFormat.HTML, description="Output format")
    path: str = Field(default="./reports", description="Output directory path")
    filename_template: str | None = Field(
        default=None, description="Custom filename template"
    )


class AdvancedConfig(BaseModel):
    """Advanced configuration options."""

    concurrency: int = Field(
        default=10, ge=1, le=100, description="Maximum concurrent requests"
    )
    retries: int = Field(
        default=2, ge=0, le=5, description="Number of retries for failed requests"
    )
    seed: int | None = Field(
        default=None, description="Random seed for reproducibility"
    )


# --- V2.0: Scoring (configurable overall resilience weights) ---


class ScoringConfig(BaseModel):
    """Weights for overall resilience score (mutation, chaos, contract, replay)."""

    mutation: float = Field(default=0.20, ge=0.0, le=1.0)
    chaos: float = Field(default=0.35, ge=0.0, le=1.0)
    contract: float = Field(default=0.35, ge=0.0, le=1.0)
    replay: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> ScoringConfig:
        total = self.mutation + self.chaos + self.contract + self.replay
        if total > 0 and abs(total - 1.0) > 0.001:
            raise ValueError(f"scoring.weights must sum to 1.0, got {total}")
        return self


# --- V2.0: Chaos (tool faults, LLM faults, context attacks) ---


class ToolFaultConfig(BaseModel):
    """Single tool fault: match by tool name or match_url (HTTP)."""

    tool: str = Field(..., description="Tool name or glob '*'")
    mode: str = Field(
        ...,
        description="timeout | error | malformed | slow | malicious_response",
    )
    match_url: str | None = Field(
        default=None,
        description="URL pattern for HTTP agents (e.g. https://api.example.com/*)",
    )
    delay_ms: int | None = None
    error_code: int | None = None
    message: str | None = None
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    after_calls: int | None = None
    payload: str | None = Field(default=None, description="For malicious_response")


class LlmFaultConfig(BaseModel):
    """Single LLM fault."""

    mode: str = Field(
        ...,
        description="timeout | truncated_response | rate_limit | empty | garbage | response_drift",
    )
    max_tokens: int | None = None
    delay_ms: int | None = Field(default=None, description="For timeout mode: delay before raising")
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    after_calls: int | None = None
    drift_type: str | None = Field(
        default=None,
        description="json_field_rename | verbosity_shift | format_change | refusal_rephrase | tone_shift",
    )
    severity: str | None = Field(default=None, description="subtle | moderate | significant")
    direction: str | None = Field(default=None, description="expand | compress")
    factor: float | None = None


class ContextAttackConfig(BaseModel):
    """Context attack: overflow, conflicting_context, injection_via_context, indirect_injection, memory_poisoning."""

    type: str = Field(
        ...,
        description="overflow | conflicting_context | injection_via_context | indirect_injection | memory_poisoning",
    )
    inject_tokens: int | None = None
    payloads: list[str] | None = None
    trigger_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    inject_at: str | None = None
    payload: str | None = None
    strategy: str | None = Field(default=None, description="prepend | append | replace")


class ChaosConfig(BaseModel):
    """V2 environment chaos configuration."""

    tool_faults: list[ToolFaultConfig] = Field(default_factory=list)
    llm_faults: list[LlmFaultConfig] = Field(default_factory=list)
    context_attacks: list[ContextAttackConfig] | dict | None = Field(default_factory=list)


# --- V2.0: Contract (behavioral contract + chaos matrix) ---


class ContractInvariantConfig(BaseModel):
    """Contract invariant with id, severity, when (extends InvariantConfig shape)."""

    id: str = Field(..., description="Unique id for this invariant")
    type: str = Field(..., description="Same as InvariantType values")
    description: str | None = None
    severity: str = Field(default="medium", description="critical | high | medium | low")
    when: str = Field(default="always", description="always | tool_faults_active | etc.")
    negate: bool = False
    value: str | None = None
    values: list[str] | None = None
    pattern: str | None = None
    patterns: list[str] | None = None
    max_ms: int | None = None
    threshold: float | None = None
    baseline: str | None = None
    similarity_threshold: float | None = 0.75


class ChaosScenarioConfig(BaseModel):
    """Single scenario in the chaos matrix (named set of faults)."""

    name: str = Field(..., description="Scenario name")
    tool_faults: list[ToolFaultConfig] = Field(default_factory=list)
    llm_faults: list[LlmFaultConfig] = Field(default_factory=list)
    context_attacks: list[ContextAttackConfig] | None = Field(default_factory=list)


class ContractConfig(BaseModel):
    """V2 behavioral contract: named invariants + chaos matrix."""

    name: str = Field(..., description="Contract name")
    description: str | None = None
    invariants: list[ContractInvariantConfig] = Field(default_factory=list)
    chaos_matrix: list[ChaosScenarioConfig] = Field(
        default_factory=list,
        description="Scenarios to run contract against",
    )


# --- V2.0: Replay (replay sessions + contract reference) ---


class ReplayToolResponseConfig(BaseModel):
    """Recorded tool response for replay."""

    tool: str = Field(..., description="Tool name")
    response: str | dict | None = None
    status: int | None = Field(default=None, description="HTTP status or 0 for error")
    latency_ms: int | None = None


class ReplaySessionConfig(BaseModel):
    """Single replay session (production failure to replay). When file is set, id/input/contract are optional (loaded from file)."""

    id: str = Field(default="", description="Replay id (optional when file is set)")
    name: str | None = None
    source: str | None = Field(default="manual")
    captured_at: str | None = None
    input: str = Field(default="", description="User input (optional when file is set)")
    context: list[dict] | None = Field(default_factory=list)
    tool_responses: list[ReplayToolResponseConfig] = Field(default_factory=list)
    expected_failure: str | None = None
    contract: str = Field(default="default", description="Contract name or path (optional when file is set)")
    file: str | None = Field(default=None, description="Path to replay file; when set, session is loaded from file")

    @model_validator(mode="after")
    def require_id_input_contract_or_file(self) -> "ReplaySessionConfig":
        if self.file:
            return self
        if not self.id or not self.input:
            raise ValueError("Replay session must have either 'file' or inline id and input")
        return self


class ReplayConfig(BaseModel):
    """V2 replay regression configuration."""

    sessions: list[ReplaySessionConfig] = Field(default_factory=list)


class FlakeStormConfig(BaseModel):
    """Main configuration for flakestorm."""

    version: str = Field(default="1.0", description="Configuration version (1.0 | 2.0)")
    agent: AgentConfig = Field(..., description="Agent configuration")
    model: ModelConfig = Field(
        default_factory=ModelConfig, description="Model configuration"
    )
    mutations: MutationConfig = Field(
        default_factory=MutationConfig, description="Mutation configuration"
    )
    golden_prompts: list[str] = Field(
        ..., min_length=1, description="List of golden prompts to test"
    )
    invariants: list[InvariantConfig] = Field(
        default_factory=list, description="List of invariant checks"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig, description="Output configuration"
    )
    advanced: AdvancedConfig = Field(
        default_factory=AdvancedConfig, description="Advanced configuration"
    )
    # V2.0 optional
    chaos: ChaosConfig | None = Field(default=None, description="Environment chaos config")
    contract: ContractConfig | None = Field(default=None, description="Behavioral contract")
    chaos_matrix: list[ChaosScenarioConfig] | None = Field(
        default=None,
        description="Chaos scenarios (when not using contract.chaos_matrix)",
    )
    replays: ReplayConfig | None = Field(default=None, description="Replay regression sessions")
    scoring: ScoringConfig | None = Field(
        default=None,
        description="Weights for overall resilience score (mutation, chaos, contract, replay)",
    )

    @model_validator(mode="after")
    def validate_invariants(self) -> FlakeStormConfig:
        """Ensure at least one invariant is configured."""
        if len(self.invariants) < 1:
            raise ValueError(
                f"At least 1 invariant is required, but {len(self.invariants)} provided. "
                f"Available types: contains, latency, valid_json, regex, similarity, excludes_pii, refusal_check"
            )
        return self

    @classmethod
    def from_yaml(cls, content: str) -> FlakeStormConfig:
        """Parse configuration from YAML string."""
        data = yaml.safe_load(content)
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        """Serialize configuration to YAML string."""
        data = self.model_dump(mode="json", exclude_none=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


def load_config(path: str | Path) -> FlakeStormConfig:
    """
    Load and validate an flakestorm configuration file.

    Args:
        path: Path to the flakestorm.yaml file

    Returns:
        Validated FlakeStormConfig object

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValidationError: If the config is invalid
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Run 'flakestorm init' to create a new configuration file."
        )

    content = config_path.read_text(encoding="utf-8")
    return FlakeStormConfig.from_yaml(content)


def create_default_config() -> FlakeStormConfig:
    """Create a default configuration for initialization."""
    return FlakeStormConfig(
        version="1.0",
        agent=AgentConfig(
            endpoint="http://localhost:8000/invoke",
            type=AgentType.HTTP,
            timeout=30000,
        ),
        model=ModelConfig(
            provider="ollama",
            name="qwen3:8b",
            base_url="http://localhost:11434",
        ),
        mutations=MutationConfig(
            count=20,
            types=[
                MutationType.PARAPHRASE,
                MutationType.NOISE,
                MutationType.TONE_SHIFT,
                MutationType.PROMPT_INJECTION,
            ],
        ),
        golden_prompts=[
            "Book a flight to Paris for next Monday",
            "What's my account balance?",
        ],
        invariants=[
            InvariantConfig(type=InvariantType.LATENCY, max_ms=2000),
            InvariantConfig(type=InvariantType.VALID_JSON),
        ],
        output=OutputConfig(
            format=OutputFormat.HTML,
            path="./reports",
        ),
    )
