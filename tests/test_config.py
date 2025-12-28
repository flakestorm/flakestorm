"""
Tests for configuration loading and validation.
"""

import pytest
from pathlib import Path
import tempfile

from entropix.core.config import (
    EntropixConfig,
    AgentConfig,
    ModelConfig,
    MutationConfig,
    InvariantConfig,
    OutputConfig,
    load_config,
    create_default_config,
    AgentType,
    MutationType,
    InvariantType,
    OutputFormat,
)


class TestEntropixConfig:
    """Tests for EntropixConfig."""
    
    def test_create_default_config(self):
        """Test creating a default configuration."""
        config = create_default_config()
        
        assert config.version == "1.0"
        assert config.agent.type == AgentType.HTTP
        assert config.model.provider == "ollama"
        assert config.model.name == "qwen3:8b"
        assert len(config.golden_prompts) >= 1
    
    def test_config_to_yaml(self):
        """Test serializing config to YAML."""
        config = create_default_config()
        yaml_str = config.to_yaml()
        
        assert "version" in yaml_str
        assert "agent" in yaml_str
        assert "golden_prompts" in yaml_str
    
    def test_config_from_yaml(self):
        """Test parsing config from YAML."""
        yaml_content = """
version: "1.0"
agent:
  endpoint: "http://localhost:8000/test"
  type: "http"
  timeout: 5000
model:
  provider: "ollama"
  name: "qwen3:8b"
golden_prompts:
  - "Test prompt 1"
  - "Test prompt 2"
invariants:
  - type: "latency"
    max_ms: 1000
"""
        config = EntropixConfig.from_yaml(yaml_content)
        
        assert config.agent.endpoint == "http://localhost:8000/test"
        assert config.agent.timeout == 5000
        assert len(config.golden_prompts) == 2
        assert len(config.invariants) == 1
    
    def test_load_config_file_not_found(self):
        """Test loading a non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")
    
    def test_load_config_from_file(self):
        """Test loading config from an actual file."""
        yaml_content = """
version: "1.0"
agent:
  endpoint: "http://test:8000/invoke"
golden_prompts:
  - "Hello world"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            
            config = load_config(f.name)
            assert config.agent.endpoint == "http://test:8000/invoke"
            
            # Cleanup
            Path(f.name).unlink()


class TestAgentConfig:
    """Tests for AgentConfig validation."""
    
    def test_valid_http_config(self):
        """Test valid HTTP agent config."""
        config = AgentConfig(
            endpoint="http://localhost:8000/invoke",
            type=AgentType.HTTP,
            timeout=30000,
        )
        assert config.endpoint == "http://localhost:8000/invoke"
    
    def test_timeout_bounds(self):
        """Test timeout validation."""
        # Valid
        config = AgentConfig(endpoint="http://test", timeout=1000)
        assert config.timeout == 1000
        
        # Too low
        with pytest.raises(ValueError):
            AgentConfig(endpoint="http://test", timeout=500)
    
    def test_env_var_expansion(self):
        """Test environment variable expansion in headers."""
        import os
        os.environ["TEST_API_KEY"] = "secret123"
        
        config = AgentConfig(
            endpoint="http://test",
            headers={"Authorization": "Bearer ${TEST_API_KEY}"},
        )
        
        assert config.headers["Authorization"] == "Bearer secret123"
        
        del os.environ["TEST_API_KEY"]


class TestMutationConfig:
    """Tests for MutationConfig."""
    
    def test_default_mutation_types(self):
        """Test default mutation types are set."""
        config = MutationConfig()
        
        assert MutationType.PARAPHRASE in config.types
        assert MutationType.NOISE in config.types
        assert MutationType.PROMPT_INJECTION in config.types
    
    def test_mutation_weights(self):
        """Test mutation weights."""
        config = MutationConfig()
        
        # Prompt injection should have higher weight
        assert config.weights[MutationType.PROMPT_INJECTION] > config.weights[MutationType.NOISE]


class TestInvariantConfig:
    """Tests for InvariantConfig validation."""
    
    def test_latency_invariant(self):
        """Test latency invariant requires max_ms."""
        config = InvariantConfig(type=InvariantType.LATENCY, max_ms=2000)
        assert config.max_ms == 2000
    
    def test_latency_missing_max_ms(self):
        """Test latency invariant fails without max_ms."""
        with pytest.raises(ValueError):
            InvariantConfig(type=InvariantType.LATENCY)
    
    def test_contains_invariant(self):
        """Test contains invariant requires value."""
        config = InvariantConfig(type=InvariantType.CONTAINS, value="test")
        assert config.value == "test"
    
    def test_similarity_invariant(self):
        """Test similarity invariant."""
        config = InvariantConfig(
            type=InvariantType.SIMILARITY,
            expected="Expected response",
            threshold=0.8,
        )
        assert config.threshold == 0.8

