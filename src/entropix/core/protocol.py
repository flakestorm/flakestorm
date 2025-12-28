"""
Agent Protocol and Adapters for Entropix

Defines the interface that all agents must implement and provides
built-in adapters for common agent types (HTTP, Python callable, LangChain).
"""

from __future__ import annotations

import asyncio
import importlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

import httpx

from entropix.core.config import AgentConfig, AgentType


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
    
    All agents must implement this interface to be tested with Entropix.
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
    
    Expects the endpoint to accept POST requests with JSON body:
    {"input": "user prompt"}
    
    And return JSON response:
    {"output": "agent response"}
    """
    
    def __init__(
        self,
        endpoint: str,
        timeout: int = 30000,
        headers: dict[str, str] | None = None,
        retries: int = 2,
    ):
        """
        Initialize the HTTP adapter.
        
        Args:
            endpoint: The HTTP endpoint URL
            timeout: Request timeout in milliseconds
            headers: Optional custom headers
            retries: Number of retry attempts
        """
        self.endpoint = endpoint
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
                    response = await client.post(
                        self.endpoint,
                        json={"input": input},
                        headers=self.headers,
                    )
                    response.raise_for_status()
                    
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    data = response.json()
                    
                    # Handle different response formats
                    output = data.get("output") or data.get("response") or str(data)
                    
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

