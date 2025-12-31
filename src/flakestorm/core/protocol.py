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


def extract_response(data: dict | list, path: str | None) -> str:
    """
    Extract response from JSON using JSONPath or dot notation.

    Supports:
    - JSONPath: "$.data.result"
    - Dot notation: "data.result"
    - Simple key: "result"

    Args:
        data: JSON data (dict or list)
        path: JSONPath or dot notation path

    Returns:
        Extracted response as string
    """
    if path is None:
        # Fallback to default fields
        if isinstance(data, dict):
            return data.get("output") or data.get("response") or str(data)
        return str(data)

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
                except (ValueError, IndexError):
                    return str(data)
            else:
                return str(data)

            if current is None:
                return str(data)

        return str(current) if current is not None else str(data)
    except (KeyError, TypeError, AttributeError):
        # Fallback to default extraction
        if isinstance(data, dict):
            return data.get("output") or data.get("response") or str(data)
        return str(data)


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

    async def invoke(self, input: str) -> AgentResponse:
        """Send request to HTTP endpoint."""
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                    data = response.json()

                    # 4. Extract response using response_path
                    output = extract_response(data, self.response_path)

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
