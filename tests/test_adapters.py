"""Tests for agent adapters."""

import pytest


class TestHTTPAgentAdapter:
    """Tests for HTTP agent adapter."""

    def test_adapter_creation(self):
        """Test adapter can be created."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/chat",
            timeout=30000,  # 30 seconds in milliseconds
        )
        assert adapter is not None
        assert adapter.endpoint == "http://localhost:8000/chat"

    def test_adapter_has_invoke_method(self):
        """Adapter has invoke method."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(endpoint="http://localhost:8000/chat")
        assert hasattr(adapter, "invoke")
        assert callable(adapter.invoke)

    def test_timeout_conversion(self):
        """Timeout is converted to seconds."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/chat",
            timeout=30000,
        )
        # Timeout should be stored in seconds
        assert adapter.timeout == 30.0

    def test_custom_headers(self):
        """Custom headers can be set."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        headers = {"Authorization": "Bearer token123"}
        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/chat",
            headers=headers,
        )
        assert adapter.headers == headers


class TestPythonAgentAdapter:
    """Tests for Python function adapter."""

    def test_adapter_creation_with_callable(self):
        """Test adapter can be created with a callable."""
        from flakestorm.core.protocol import PythonAgentAdapter

        def my_agent(input: str) -> str:
            return f"Response to: {input}"

        adapter = PythonAgentAdapter(my_agent)
        assert adapter is not None
        assert adapter.agent == my_agent

    def test_adapter_has_invoke_method(self):
        """Adapter has invoke method."""
        from flakestorm.core.protocol import PythonAgentAdapter

        def my_agent(input: str) -> str:
            return f"Response to: {input}"

        adapter = PythonAgentAdapter(my_agent)
        assert hasattr(adapter, "invoke")
        assert callable(adapter.invoke)


class TestLangChainAgentAdapter:
    """Tests for LangChain agent adapter."""

    @pytest.fixture
    def langchain_config(self):
        """Create a test LangChain agent config."""
        from flakestorm.core.config import AgentConfig, AgentType

        return AgentConfig(
            endpoint="my_agent:chain",
            type=AgentType.LANGCHAIN,
            timeout=60000,  # 60 seconds in milliseconds
        )

    def test_adapter_creation(self, langchain_config):
        """Test adapter can be created."""
        from flakestorm.core.protocol import LangChainAgentAdapter

        adapter = LangChainAgentAdapter(langchain_config)
        assert adapter is not None


class TestAgentAdapterFactory:
    """Tests for adapter factory function."""

    def test_creates_http_adapter(self):
        """Factory creates HTTP adapter for HTTP type."""
        from flakestorm.core.config import AgentConfig, AgentType
        from flakestorm.core.protocol import HTTPAgentAdapter, create_agent_adapter

        config = AgentConfig(
            endpoint="http://localhost:8000/chat",
            type=AgentType.HTTP,
        )
        adapter = create_agent_adapter(config)
        assert isinstance(adapter, HTTPAgentAdapter)

    def test_creates_python_adapter(self):
        """Python adapter can be created with a callable."""
        from flakestorm.core.protocol import PythonAgentAdapter

        def my_agent(input: str) -> str:
            return f"Response: {input}"

        adapter = PythonAgentAdapter(my_agent)
        assert isinstance(adapter, PythonAgentAdapter)

    def test_creates_langchain_adapter(self):
        """Factory creates LangChain adapter for LangChain type."""
        from flakestorm.core.config import AgentConfig, AgentType
        from flakestorm.core.protocol import LangChainAgentAdapter, create_agent_adapter

        config = AgentConfig(
            endpoint="my_agent:chain",
            type=AgentType.LANGCHAIN,
        )
        adapter = create_agent_adapter(config)
        assert isinstance(adapter, LangChainAgentAdapter)


class TestAgentResponse:
    """Tests for AgentResponse data class."""

    def test_response_creation(self):
        """Test AgentResponse can be created."""
        from flakestorm.core.protocol import AgentResponse

        response = AgentResponse(
            output="Hello, world!",
            latency_ms=150.5,
        )
        assert response.output == "Hello, world!"
        assert response.latency_ms == 150.5

    def test_response_with_error(self):
        """Test AgentResponse with error."""
        from flakestorm.core.protocol import AgentResponse

        response = AgentResponse(
            output="",
            latency_ms=100.0,
            error="Connection timeout",
        )
        assert response.error == "Connection timeout"
        assert not response.success

    def test_response_success_property(self):
        """Test AgentResponse success property."""
        from flakestorm.core.protocol import AgentResponse

        # Success case
        success_response = AgentResponse(
            output="Response",
            latency_ms=100.0,
        )
        assert success_response.success is True

        # Error case
        error_response = AgentResponse(
            output="",
            latency_ms=100.0,
            error="Failed",
        )
        assert error_response.success is False


class TestStructuredInputParser:
    """Tests for structured input parsing."""

    def test_parse_colon_format(self):
        """Test parsing key:value format."""
        from flakestorm.core.protocol import parse_structured_input

        input_text = "Industry: Fitness tech\nProduct: AI trainer"
        result = parse_structured_input(input_text)

        assert result["industry"] == "Fitness tech"
        assert result["product"] == "AI trainer"

    def test_parse_equals_format(self):
        """Test parsing key=value format."""
        from flakestorm.core.protocol import parse_structured_input

        input_text = "Industry=Fitness tech\nProduct=AI trainer"
        result = parse_structured_input(input_text)

        assert result["industry"] == "Fitness tech"
        assert result["product"] == "AI trainer"

    def test_parse_dash_format(self):
        """Test parsing key - value format."""
        from flakestorm.core.protocol import parse_structured_input

        input_text = "Industry - Fitness tech\nProduct - AI trainer"
        result = parse_structured_input(input_text)

        assert result["industry"] == "Fitness tech"
        assert result["product"] == "AI trainer"

    def test_parse_multiline(self):
        """Test parsing multi-line structured input."""
        from flakestorm.core.protocol import parse_structured_input

        input_text = """
        Industry: Fitness tech
        Product/Service: AI personal trainer app
        Business Model: B2C
        Target Market: fitness enthusiasts
        Description: An app that provides personalized workout plans
        """
        result = parse_structured_input(input_text)

        assert result["industry"] == "Fitness tech"
        assert result["productservice"] == "AI personal trainer app"
        assert result["businessmodel"] == "B2C"
        assert result["targetmarket"] == "fitness enthusiasts"
        assert (
            result["description"] == "An app that provides personalized workout plans"
        )

    def test_parse_empty_input(self):
        """Test parsing empty input."""
        from flakestorm.core.protocol import parse_structured_input

        result = parse_structured_input("")
        assert result == {}

    def test_parse_normalizes_keys(self):
        """Test that keys are normalized (lowercase, no spaces)."""
        from flakestorm.core.protocol import parse_structured_input

        input_text = "Product Name: AI Trainer\nBusiness-Model: B2C"
        result = parse_structured_input(input_text)

        # Keys should be normalized
        assert "productname" in result
        assert "businessmodel" in result


class TestTemplateEngine:
    """Tests for template rendering."""

    def test_render_simple_template(self):
        """Test rendering template with {prompt}."""
        from flakestorm.core.protocol import render_template

        template = '{"message": "{prompt}"}'
        prompt = "Book a flight"
        result = render_template(template, prompt)

        assert result == {"message": "Book a flight"}

    def test_render_with_structured_data(self):
        """Test rendering template with structured data fields."""
        from flakestorm.core.protocol import render_template

        template = '{"industry": "{industry}", "product": "{productname}"}'
        prompt = "test"
        structured_data = {"industry": "Fitness tech", "productname": "AI trainer"}

        result = render_template(template, prompt, structured_data)

        assert result == {"industry": "Fitness tech", "product": "AI trainer"}

    def test_render_json_template(self):
        """Test rendering JSON template."""
        from flakestorm.core.protocol import render_template

        template = '{"messages": [{"role": "user", "content": "{prompt}"}]}'
        prompt = "Hello"
        result = render_template(template, prompt)

        assert isinstance(result, dict)
        assert result["messages"][0]["content"] == "Hello"

    def test_render_string_template(self):
        """Test rendering non-JSON template."""
        from flakestorm.core.protocol import render_template

        template = "q={prompt}&format=json"
        prompt = "search query"
        result = render_template(template, prompt)

        assert result == "q=search query&format=json"


class TestResponseExtractor:
    """Tests for response extraction."""

    def test_extract_simple_key(self):
        """Test extracting simple key from response."""
        from flakestorm.core.protocol import extract_response

        data = {"output": "Hello world"}
        result = extract_response(data, "output")

        assert result == "Hello world"

    def test_extract_dot_notation(self):
        """Test extracting nested field using dot notation."""
        from flakestorm.core.protocol import extract_response

        data = {"data": {"result": "Success"}}
        result = extract_response(data, "data.result")

        assert result == "Success"

    def test_extract_jsonpath(self):
        """Test extracting using JSONPath-style notation."""
        from flakestorm.core.protocol import extract_response

        data = {"data": {"result": "Success"}}
        result = extract_response(data, "$.data.result")

        assert result == "Success"

    def test_extract_default_fallback(self):
        """Test default extraction when path is None."""
        from flakestorm.core.protocol import extract_response

        data = {"output": "Hello"}
        result = extract_response(data, None)

        assert result == "Hello"

    def test_extract_fallback_to_response(self):
        """Test fallback to 'response' key."""
        from flakestorm.core.protocol import extract_response

        data = {"response": "Hello"}
        result = extract_response(data, None)

        assert result == "Hello"

    def test_extract_missing_path(self):
        """Test extraction with missing path falls back to default."""
        from flakestorm.core.protocol import extract_response

        data = {"output": "Hello"}
        result = extract_response(data, "nonexistent.path")

        # Should fall back to default extraction
        assert result == "Hello"


class TestHTTPAgentAdapterNewFeatures:
    """Tests for new HTTP adapter features."""

    def test_adapter_with_method(self):
        """Test adapter creation with custom HTTP method."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            method="GET",
        )
        assert adapter.method == "GET"

    def test_adapter_with_request_template(self):
        """Test adapter creation with request template."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        template = '{"message": "{prompt}"}'
        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            request_template=template,
        )
        assert adapter.request_template == template

    def test_adapter_with_response_path(self):
        """Test adapter creation with response path."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            response_path="$.data.result",
        )
        assert adapter.response_path == "$.data.result"

    def test_adapter_with_query_params(self):
        """Test adapter creation with query parameters."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        query_params = {"api_key": "test", "format": "json"}
        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            query_params=query_params,
        )
        assert adapter.query_params == query_params

    def test_adapter_parse_structured_input_flag(self):
        """Test adapter with parse_structured_input flag."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            parse_structured_input=False,
        )
        assert adapter.parse_structured_input is False

    def test_adapter_all_new_features(self):
        """Test adapter with all new features combined."""
        from flakestorm.core.protocol import HTTPAgentAdapter

        adapter = HTTPAgentAdapter(
            endpoint="http://localhost:8000/api",
            method="PUT",
            request_template='{"content": "{prompt}"}',
            response_path="$.result",
            query_params={"version": "v1"},
            parse_structured_input=True,
            timeout=60000,
            headers={"Authorization": "Bearer token"},
        )

        assert adapter.method == "PUT"
        assert adapter.request_template == '{"content": "{prompt}"}'
        assert adapter.response_path == "$.result"
        assert adapter.query_params == {"version": "v1"}
        assert adapter.parse_structured_input is True
        assert adapter.timeout == 60.0
        assert adapter.headers == {"Authorization": "Bearer token"}


class TestAgentAdapterFactoryNewFeatures:
    """Tests for factory with new config fields."""

    def test_factory_passes_all_fields(self):
        """Test factory passes all new config fields to HTTP adapter."""
        from flakestorm.core.config import AgentConfig, AgentType
        from flakestorm.core.protocol import HTTPAgentAdapter, create_agent_adapter

        config = AgentConfig(
            endpoint="http://localhost:8000/api",
            type=AgentType.HTTP,
            method="POST",
            request_template='{"message": "{prompt}"}',
            response_path="$.reply",
            query_params={"key": "value"},
            parse_structured_input=True,
        )

        adapter = create_agent_adapter(config)
        assert isinstance(adapter, HTTPAgentAdapter)
        assert adapter.method == "POST"
        assert adapter.request_template == '{"message": "{prompt}"}'
        assert adapter.response_path == "$.reply"
        assert adapter.query_params == {"key": "value"}
        assert adapter.parse_structured_input is True
