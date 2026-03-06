"""
Agent Protocol and Adapters for flakestorm

Defines the interface that all agents must implement and provides
built-in adapters for common agent types (HTTP, Python callable, LangChain).
"""

from __future__ import annotations

import asyncio
import importlib
import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

from flakestorm.core.config import AgentConfig, AgentType


@dataclass
class AgentResponse:
    """Response from an agent invocation."""

    output: str
    latency_ms: float
    raw_response: Any = None
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if the invocation was successful."""
        return self.error is None


@runtime_checkable
class AgentProtocol(Protocol):
    """
    Protocol defining the interface for AI agents.

    All agents must implement this interface to be tested with flakestorm.
    The simplest implementation is an async function that takes a string
    input and returns a string output.
    """

    async def invoke(self, input: str) -> str:
        """
        Execute the agent with the given input.

        Args:
            input: The user prompt or query

        Returns:
            The agent's response as a string
        """
        ...


def parse_structured_input(input_text: str) -> dict[str, str]:
    """
    Parse structured input text into key-value dictionary.

    Supports formats:
    - "Key: Value"
    - "Key=Value"
    - "Key - Value"
    - Multi-line with newlines

    Args:
        input_text: Structured text input

    Returns:
        Dictionary of parsed key-value pairs (normalized keys)
    """
    result: dict[str, str] = {}
    lines = input_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try different separators: ":", "=", " - "
        if ":" in line:
            parts = line.split(":", 1)
        elif "=" in line:
            parts = line.split("=", 1)
        elif " - " in line:
            parts = line.split(" - ", 1)
        else:
            continue

        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()

            # Normalize key: lowercase, remove spaces/special chars
            normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized_key:
                result[normalized_key] = value

    return result


def render_template(
    template: str, prompt: str, structured_data: dict[str, str] | None = None
) -> dict | str:
    """
    Render request template with variable substitution.

    Supports:
    - {prompt} - Full golden prompt text
    - {field_name} - Parsed structured input values

    Args:
        template: Template string with {variable} placeholders
        prompt: Full golden prompt text
        structured_data: Parsed structured input data

    Returns:
        Rendered template (dict if JSON, str otherwise)
    """
    # Replace {prompt} first
    rendered = template.replace("{prompt}", prompt)

    # Replace structured data fields if available
    if structured_data:
        for key, value in structured_data.items():
            placeholder = f"{{{key}}}"
            rendered = rendered.replace(placeholder, value)

    # Try to parse as JSON, return dict if successful
    try:
        return json.loads(rendered)
    except json.JSONDecodeError:
        # Not JSON, return as string
        return rendered


def extract_response(data: dict | list | str, path: str | None) -> str:
    """
    Extract response from JSON using JSONPath or dot notation.

    Handles various response formats:
    - Direct values (string, number, array)
    - Nested objects with various field names
    - Arrays of objects
    - Auto-detection when path is None

    Supports:
    - JSONPath: "$.data.result"
    - Dot notation: "data.result"
    - Simple key: "result"
    - Array indices: "0" or "results.0"

    Args:
        data: JSON data (dict, list, or string)
        path: JSONPath or dot notation path (None for auto-detection)

    Returns:
        Extracted response as string
    """
    # Handle string responses directly
    if isinstance(data, str):
        return data

    # Auto-detection when path is None
    if path is None:
        return _auto_detect_response(data)

    # Remove leading $ if present (JSONPath style)
    path = path.lstrip("$.")

    # Split by dots for nested access
    keys = path.split(".")
    current: Any = data

    try:
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                # Try to use key as index
                try:
                    current = current[int(key)]
                except (ValueError, IndexError, KeyError):
                    # If key is not a valid index, try auto-detection
                    return _auto_detect_response(data)
            else:
                # Can't traverse further, try auto-detection
                return _auto_detect_response(data)

            if current is None:
                # Path found but value is None, try auto-detection
                return _auto_detect_response(data)

        # Successfully extracted value
        if current is None:
            return _auto_detect_response(data)

        # Convert to string, handling various types
        if isinstance(current, dict | list):
            # For complex types, use JSON stringification for better representation
            try:
                return json.dumps(current, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(current)
        return str(current)

    except (KeyError, TypeError, AttributeError, IndexError):
        # Path not found, fall back to auto-detection
        return _auto_detect_response(data)


def _auto_detect_response(data: dict | list | str) -> str:
    """
    Automatically detect and extract the response from various data structures.

    Tries multiple strategies to find the actual response content:
    1. Common response field names
    2. Single-item arrays
    3. First meaningful value in dict/list
    4. Direct string/number values

    Args:
        data: JSON data (dict, list, or string)

    Returns:
        Extracted response as string
    """
    # Already a string
    if isinstance(data, str):
        return data

    # Dictionary: try common response field names
    if isinstance(data, dict):
        # Try common response field names (case-insensitive)
        common_fields = [
            "output",
            "response",
            "result",
            "data",
            "content",
            "text",
            "message",
            "answer",
            "reply",
            "queries",
            "query",
            "results",
        ]

        # Case-sensitive first
        for field in common_fields:
            if field in data:
                value = data[field]
                if value is not None:
                    return _format_extracted_value(value)

        # Case-insensitive search
        data_lower = {k.lower(): v for k, v in data.items()}
        for field in common_fields:
            if field in data_lower:
                value = data_lower[field]
                if value is not None:
                    return _format_extracted_value(value)

        # If dict has only one key, return that value
        if len(data) == 1:
            value = next(iter(data.values()))
            if value is not None:
                return _format_extracted_value(value)

        # Last resort: stringify the dict
        try:
            return json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(data)

    # List/Array: handle various cases
    if isinstance(data, list):
        # Empty list
        if not data:
            return "[]"

        # Single item array - return that item
        if len(data) == 1:
            return _format_extracted_value(data[0])

        # Array of strings/numbers - join or stringify
        if all(isinstance(item, str | int | float | bool) for item in data):
            try:
                return json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(data)

        # Array of objects - try to extract from first object
        if len(data) > 0 and isinstance(data[0], dict):
            # Recursively try to extract from first object
            first_item = _auto_detect_response(data[0])
            if first_item and first_item != "{}":
                return first_item

        # Last resort: stringify the array
        try:
            return json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(data)

    # Primitive types (number, bool, None)
    if data is None:
        return ""
    return str(data)


def _format_extracted_value(value: Any) -> str:
    """
    Format an extracted value as a string.

    Handles various types and structures intelligently.

    Args:
        value: The value to format

    Returns:
        Formatted string representation
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, int | float | bool):
        return str(value)

    if isinstance(value, dict | list):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    return str(value)


class BaseAgentAdapter(ABC):
    """Base class for agent adapters."""

    @abstractmethod
    async def invoke(self, input: str) -> AgentResponse:
        """Invoke the agent and return a structured response."""
        ...

    async def invoke_with_timing(self, input: str) -> AgentResponse:
        """Invoke the agent and measure latency."""
        start_time = time.perf_counter()
        try:
            response = await self.invoke(input)
            if response.latency_ms == 0:
                response.latency_ms = (time.perf_counter() - start_time) * 1000
            return response
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                output="",
                latency_ms=latency_ms,
                error=str(e),
            )


class HTTPAgentAdapter(BaseAgentAdapter):
    """
    Adapter for agents exposed via HTTP endpoints.

    Supports flexible request templates, all HTTP methods, and custom response extraction.
    """

    def __init__(
        self,
        endpoint: str,
        method: str = "POST",
        request_template: str | None = None,
        response_path: str | None = None,
        query_params: dict[str, str] | None = None,
        parse_structured_input: bool = True,
        timeout: int = 30000,
        headers: dict[str, str] | None = None,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        """
        Initialize the HTTP adapter.

        Args:
            endpoint: The HTTP endpoint URL
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            request_template: Template for request body/query with variable substitution
            response_path: JSONPath or dot notation to extract response
            query_params: Static query parameters
            parse_structured_input: Whether to parse structured golden prompts
            timeout: Request timeout in milliseconds
            headers: Optional custom headers
            retries: Number of retry attempts
            transport: Optional custom transport (e.g. for chaos injection by match_url)
        """
        self.endpoint = endpoint
        self.method = method.upper()
        self.request_template = request_template
        self.response_path = response_path
        self.query_params = query_params or {}
        self.parse_structured_input = parse_structured_input
        self.timeout = timeout / 1000  # Convert to seconds
        self.headers = headers or {}
        self.retries = retries
        self.transport = transport

    async def invoke(self, input: str) -> AgentResponse:
        """Send request to HTTP endpoint."""
        start_time = time.perf_counter()
        client_kw: dict = {"timeout": self.timeout}
        if self.transport is not None:
            client_kw["transport"] = self.transport

        async with httpx.AsyncClient(**client_kw) as client:
            last_error: Exception | None = None

            for attempt in range(self.retries + 1):
                try:
                    # 1. Parse structured input if enabled
                    structured_data = None
                    if self.parse_structured_input:
                        structured_data = parse_structured_input(input)

                    # 2. Render request template
                    if self.request_template:
                        rendered = render_template(
                            self.request_template, input, structured_data
                        )
                        request_data = rendered
                    else:
                        # Default format
                        request_data = {"input": input}

                    # 3. Build request based on method
                    if self.method in ["GET", "DELETE"]:
                        # Query params only (merge template data as query params)
                        if isinstance(request_data, dict):
                            params = {**self.query_params, **request_data}
                        else:
                            # If template rendered to string, use as query string
                            params = {**self.query_params}
                            if request_data:
                                params["q"] = str(request_data)

                        response = await client.request(
                            self.method,
                            self.endpoint,
                            params=params,
                            headers=self.headers,
                        )
                    else:
                        # POST, PUT, PATCH: Body + optional query params
                        if isinstance(request_data, dict):
                            response = await client.request(
                                self.method,
                                self.endpoint,
                                json=request_data,
                                params=self.query_params,
                                headers=self.headers,
                            )
                        else:
                            # String body (e.g., for form data)
                            response = await client.request(
                                self.method,
                                self.endpoint,
                                content=str(request_data),
                                params=self.query_params,
                                headers=self.headers,
                            )

                    response.raise_for_status()

                    latency_ms = (time.perf_counter() - start_time) * 1000

                    # Parse response - handle both JSON and non-JSON responses
                    content_type = response.headers.get("content-type", "").lower()
                    is_json = (
                        "application/json" in content_type
                        or "text/json" in content_type
                    )

                    if is_json:
                        # Try to parse as JSON
                        try:
                            data = response.json()
                        except Exception:
                            # If JSON parsing fails, treat as text
                            data = response.text
                    else:
                        # Non-JSON response (plain text, HTML, etc.)
                        data = response.text
                        # extract_response can handle string data, so continue processing

                    # Check if response contains an error field (even if HTTP 200)
                    # Some agents return HTTP 200 with error in JSON body
                    if isinstance(data, dict):
                        # Check for error fields first (before trying to extract success path)
                        if "error" in data or "Error" in data:
                            error_msg = (
                                data.get("error")
                                or data.get("Error")
                                or data.get("message")
                                or "Unknown error"
                            )
                            return AgentResponse(
                                output="",
                                latency_ms=latency_ms,
                                error=f"Agent error: {error_msg}",
                                raw_response=data,
                            )
                        # Check for common error patterns
                        if "success" in data and data.get("success") is False:
                            error_msg = (
                                data.get("message")
                                or data.get("error")
                                or "Request failed"
                            )
                            return AgentResponse(
                                output="",
                                latency_ms=latency_ms,
                                error=f"Agent returned failure: {error_msg}",
                                raw_response=data,
                            )

                    # 4. Extract response using response_path
                    # Only extract if we didn't find an error above
                    try:
                        output = extract_response(data, self.response_path)
                    except Exception as extract_error:
                        # If extraction fails, return the raw data as string
                        return AgentResponse(
                            output=str(data),
                            latency_ms=latency_ms,
                            error=f"Failed to extract response using path '{self.response_path}': {str(extract_error)}",
                            raw_response=data,
                        )

                    return AgentResponse(
                        output=output,
                        latency_ms=latency_ms,
                        raw_response=data,
                    )

                except httpx.TimeoutException as e:
                    last_error = e
                    if attempt < self.retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue

                except httpx.HTTPStatusError as e:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    return AgentResponse(
                        output="",
                        latency_ms=latency_ms,
                        error=f"HTTP {e.response.status_code}: {e.response.text}",
                        raw_response=e.response,
                    )

                except Exception as e:
                    last_error = e
                    if attempt < self.retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue

            # All retries failed
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                output="",
                latency_ms=latency_ms,
                error=str(last_error),
            )


class PythonAgentAdapter(BaseAgentAdapter):
    """
    Adapter for Python callable agents.

    Wraps a Python async function or class that implements the AgentProtocol.
    """

    def __init__(
        self,
        agent: Callable[[str], str] | AgentProtocol,
    ):
        """
        Initialize the Python adapter.

        Args:
            agent: A callable or AgentProtocol implementation
        """
        self.agent = agent

    async def invoke(self, input: str) -> AgentResponse:
        """Invoke the Python agent."""
        start_time = time.perf_counter()

        try:
            # Check if it's a protocol implementation
            if hasattr(self.agent, "invoke"):
                if asyncio.iscoroutinefunction(self.agent.invoke):
                    output = await self.agent.invoke(input)
                else:
                    output = self.agent.invoke(input)
            # Otherwise treat as callable
            elif asyncio.iscoroutinefunction(self.agent):
                output = await self.agent(input)
            else:
                output = self.agent(input)

            latency_ms = (time.perf_counter() - start_time) * 1000

            return AgentResponse(
                output=str(output),
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                output="",
                latency_ms=latency_ms,
                error=str(e),
            )


class LangChainAgentAdapter(BaseAgentAdapter):
    """
    Adapter for LangChain agents and chains.

    Supports LangChain's Runnable interface.
    """

    def __init__(self, module_path: str):
        """
        Initialize the LangChain adapter.

        Args:
            module_path: Python module path to the chain (e.g., "my_agent:chain")
        """
        self.module_path = module_path
        self._chain = None

    def _load_chain(self) -> Any:
        """Lazily load the LangChain chain."""
        if self._chain is None:
            module_name, attr_name = self.module_path.rsplit(":", 1)
            module = importlib.import_module(module_name)
            self._chain = getattr(module, attr_name)
        return self._chain

    async def invoke(self, input: str) -> AgentResponse:
        """Invoke the LangChain chain."""
        start_time = time.perf_counter()

        try:
            chain = self._load_chain()

            # Try different LangChain interfaces
            if hasattr(chain, "ainvoke"):
                result = await chain.ainvoke({"input": input})
            elif hasattr(chain, "invoke"):
                result = chain.invoke({"input": input})
            elif hasattr(chain, "arun"):
                result = await chain.arun(input)
            elif hasattr(chain, "run"):
                result = chain.run(input)
            else:
                result = chain(input)

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract output from various result formats
            if isinstance(result, dict):
                output = result.get("output") or result.get("text") or str(result)
            else:
                output = str(result)

            return AgentResponse(
                output=output,
                latency_ms=latency_ms,
                raw_response=result,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                output="",
                latency_ms=latency_ms,
                error=str(e),
            )


def create_agent_adapter(config: AgentConfig) -> BaseAgentAdapter:
    """
    Create an appropriate agent adapter based on configuration.

    Args:
        config: Agent configuration

    Returns:
        An agent adapter instance

    Raises:
        ValueError: If the agent type is not supported
    """
    if config.type == AgentType.HTTP:
        return HTTPAgentAdapter(
            endpoint=config.endpoint,
            method=config.method,
            request_template=config.request_template,
            response_path=config.response_path,
            query_params=config.query_params,
            parse_structured_input=config.parse_structured_input,
            timeout=config.timeout,
            headers=config.headers,
        )

    elif config.type == AgentType.PYTHON:
        # Import the Python module/function
        module_name, attr_name = config.endpoint.rsplit(":", 1)
        module = importlib.import_module(module_name)
        agent = getattr(module, attr_name)
        return PythonAgentAdapter(agent)

    elif config.type == AgentType.LANGCHAIN:
        return LangChainAgentAdapter(config.endpoint)

    else:
        raise ValueError(f"Unsupported agent type: {config.type}")


def create_instrumented_adapter(
    adapter: BaseAgentAdapter,
    chaos_config: Any | None = None,
    replay_session: Any | None = None,
) -> BaseAgentAdapter:
    """
    Wrap an adapter with chaos injection (tool/LLM faults).

    When chaos_config is provided, the returned adapter applies faults
    when supported (match_url for HTTP, tool registry for Python/LangChain).
    For type=python with tool_faults, fails loudly if no tool callables/ToolRegistry.
    """
    from flakestorm.chaos.interceptor import ChaosInterceptor
    from flakestorm.chaos.http_transport import ChaosHttpTransport

    if chaos_config and chaos_config.tool_faults:
        # V2 spec §6.1: Python agent with tool_faults but no tools -> fail loudly
        if isinstance(adapter, PythonAgentAdapter):
            raise ValueError(
                "Tool fault injection requires explicit tool callables or ToolRegistry "
                "for type: python. Add tools to your config or use type: langchain."
            )
        # HTTP: wrap with transport that applies tool_faults (match_url or tool "*")
        if isinstance(adapter, HTTPAgentAdapter):
            call_count_ref: list[int] = [0]
            default_transport = httpx.AsyncHTTPTransport()
            chaos_transport = ChaosHttpTransport(
                default_transport, chaos_config, call_count_ref
            )
            timeout_ms = int(adapter.timeout * 1000) if adapter.timeout else 30000
            wrapped_http = HTTPAgentAdapter(
                endpoint=adapter.endpoint,
                method=adapter.method,
                request_template=adapter.request_template,
                response_path=adapter.response_path,
                query_params=adapter.query_params,
                parse_structured_input=adapter.parse_structured_input,
                timeout=timeout_ms,
                headers=adapter.headers,
                retries=adapter.retries,
                transport=chaos_transport,
            )
            return ChaosInterceptor(
                wrapped_http, chaos_config, replay_session=replay_session
            )

    return ChaosInterceptor(adapter, chaos_config, replay_session=replay_session)
