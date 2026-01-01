"""
Configuration Management for flakestorm

Handles loading and validating the flakestorm.yaml configuration file.
Uses Pydantic for robust validation and type safety.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# Import MutationType from mutations to avoid duplicate definition
from flakestorm.mutations.types import MutationType


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


class ModelConfig(BaseModel):
    """Configuration for the mutation generation model."""

    provider: str = Field(default="ollama", description="Model provider (ollama)")
    name: str = Field(default="qwen3:8b", description="Model name")
    base_url: str = Field(
        default="http://localhost:11434", description="Model server URL"
    )
    temperature: float = Field(
        default=0.8, ge=0.0, le=2.0, description="Temperature for mutation generation"
    )


class MutationConfig(BaseModel):
    """
    Configuration for mutation generation.

    Limits:
    - Maximum 50 total mutations per test run
    - 8 mutation types: paraphrase, noise, tone_shift, prompt_injection, encoding_attacks, context_manipulation, length_extremes, custom

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
        description="Types of mutations to generate (8 types available)",
    )
    weights: dict[MutationType, float] = Field(
        default_factory=lambda: {
            MutationType.PARAPHRASE: 1.0,
            MutationType.NOISE: 0.8,
            MutationType.TONE_SHIFT: 0.9,
            MutationType.PROMPT_INJECTION: 1.5,
            MutationType.ENCODING_ATTACKS: 1.3,
            MutationType.CONTEXT_MANIPULATION: 1.1,
            MutationType.LENGTH_EXTREMES: 1.2,
            MutationType.CUSTOM: 1.0,
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


class InvariantConfig(BaseModel):
    """Configuration for a single invariant check."""

    type: InvariantType = Field(..., description="Type of invariant check")
    description: str | None = Field(
        default=None, description="Human-readable description"
    )

    # Type-specific fields
    value: str | None = Field(default=None, description="Value for 'contains' check")
    max_ms: int | None = Field(
        default=None, description="Maximum latency for 'latency' check"
    )
    pattern: str | None = Field(
        default=None, description="Regex pattern for 'regex' check"
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

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> InvariantConfig:
        """Ensure required fields are present for each type."""
        if self.type == InvariantType.CONTAINS and not self.value:
            raise ValueError("'contains' invariant requires 'value' field")
        if self.type == InvariantType.LATENCY and not self.max_ms:
            raise ValueError("'latency' invariant requires 'max_ms' field")
        if self.type == InvariantType.REGEX and not self.pattern:
            raise ValueError("'regex' invariant requires 'pattern' field")
        if self.type == InvariantType.SIMILARITY and not self.expected:
            raise ValueError("'similarity' invariant requires 'expected' field")
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


class FlakeStormConfig(BaseModel):
    """Main configuration for flakestorm."""

    version: str = Field(default="1.0", description="Configuration version")
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
