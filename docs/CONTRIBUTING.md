# Contributing to flakestorm

Thank you for your interest in contributing to flakestorm! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/flakestorm/flakestorm.git
   cd flakestorm
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Install Ollama** (for mutation generation)
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull qwen3:8b
   ```

4. **Set up Rust** (optional, for performance module)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   cd rust && cargo build --release
   ```

5. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/flakestorm --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestEntropixConfig::test_create_default_config
```

### Code Style

We use:
- **black** for Python formatting
- **ruff** for linting
- **mypy** for type checking

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Project Structure

```
flakestorm/
├── src/flakestorm/           # Main package
│   ├── cli/                # CLI commands
│   ├── core/               # Core logic
│   ├── mutations/          # Mutation engine
│   ├── assertions/         # Invariant checkers
│   ├── reports/            # Report generators
│   └── integrations/       # External integrations
├── rust/                   # Rust performance module
├── tests/                  # Test suite
├── docs/                   # Documentation
└── examples/               # Example configurations
```

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Include:
   - flakestorm version
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the use case
3. Explain why existing features don't meet the need
4. If possible, outline an implementation approach

### Submitting Pull Requests

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make your changes**
   - Write clear, documented code
   - Add tests for new functionality
   - Update documentation as needed

4. **Run checks locally**
   ```bash
   black src tests
   ruff check src tests
   mypy src
   pytest
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "feat: Add new mutation type for XXX"
   ```
   
   Use conventional commits:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Tests
   - `refactor:` Code refactoring
   - `chore:` Maintenance

6. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

7. **PR Description should include**
   - What the change does
   - Why it's needed
   - How it was tested
   - Any breaking changes

## Development Guidelines

### Adding a New Mutation Type

1. Add to `MutationType` enum in `mutations/types.py`
2. Add template in `mutations/templates.py`
3. Add weight in `core/config.py`
4. Add tests in `tests/test_mutations.py`
5. Update documentation

### Adding a New Invariant Checker

1. Create checker class in `assertions/` (deterministic, semantic, or safety)
2. Implement `check(response, latency_ms) -> CheckResult`
3. Register in `assertions/verifier.py` CHECKER_REGISTRY
4. Add to `InvariantType` enum if new type
5. Add tests
6. Document in CONFIGURATION_GUIDE.md

### Adding a New Agent Adapter

1. Create adapter class implementing `AgentProtocol`
2. Add to `core/protocol.py`
3. Add to `AgentType` enum if new type
4. Update `create_agent_adapter()` factory
5. Add tests
6. Document usage

## Testing Guidelines

### Test Structure

```python
class TestMyFeature:
    """Tests for MyFeature."""
    
    def test_happy_path(self):
        """Test normal operation."""
        ...
    
    def test_edge_case(self):
        """Test edge case handling."""
        ...
    
    def test_error_handling(self):
        """Test error conditions."""
        ...
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mocking Ollama

```python
from unittest.mock import AsyncMock, patch

@patch('flakestorm.mutations.engine.AsyncClient')
async def test_mutation_generation(mock_client):
    mock_client.return_value.generate = AsyncMock(
        return_value={"response": "mutated text"}
    )
    # Test code...
```

## Documentation

### Docstring Format

```python
def function_name(param1: str, param2: int = 10) -> bool:
    """
    Brief description of function.
    
    Longer description if needed. Explain what the function
    does, not how it does it.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        
    Example:
        >>> result = function_name("test")
        >>> print(result)
        True
    """
```

### Updating Documentation

- README.md: High-level overview and quick start
- CONFIGURATION_GUIDE.md: Detailed config reference
- API_SPECIFICATION.md: Python SDK reference
- ARCHITECTURE_SUMMARY.md: System design

## Release Process

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag release
5. CI automatically publishes to PyPI

## Getting Help

- Open an issue for questions
- Join Discord community (coming soon)
- Check existing documentation

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md
- Release notes
- GitHub contributors page

Thank you for contributing to flakestorm!

