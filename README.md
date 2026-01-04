# Flakestorm

<p align="center">
  <strong>The Agent Reliability Engine</strong><br>
  <em>Chaos Engineering for AI Agents</em>
</p>

<p align="center">
  <a href="https://github.com/flakestorm/flakestorm/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License">
  </a>
  <a href="https://github.com/flakestorm/flakestorm">
    <img src="https://img.shields.io/github/stars/flakestorm/flakestorm?style=social" alt="GitHub Stars">
  </a>
</p>

---

## The Problem

**The "Happy Path" Fallacy**: Current AI development tools focus on getting an agent to work *once*. Developers tweak prompts until they get a correct answer, declare victory, and ship.

**The Reality**: LLMs are non-deterministic. An agent that works on Monday with `temperature=0.7` might fail on Tuesday. Users don't follow "Happy Paths" — they make typos, they're aggressive, they lie, and they attempt prompt injections.

**The Void**:
- **Observability Tools** (LangSmith) tell you *after* the agent failed in production
- **Eval Libraries** (RAGAS) focus on academic scores rather than system reliability
- **Missing Link**: A tool that actively *attacks* the agent to prove robustness before deployment

## The Solution

**Flakestorm** is a local-first testing engine that applies **Chaos Engineering** principles to AI Agents.

Instead of running one test case, Flakestorm takes a single "Golden Prompt", generates adversarial mutations (semantic variations, noise injection, hostile tone, prompt injections), runs them against your agent, and calculates a **Robustness Score**.

> **"If it passes Flakestorm, it won't break in Production."**

## What You Get in Minutes

Within minutes of setup, Flakestorm gives you:

- **Robustness Score**: A single number (0.0-1.0) that quantifies your agent's reliability
- **Failure Analysis**: Detailed reports showing exactly which mutations broke your agent and why
- **Security Insights**: Discover prompt injection vulnerabilities before attackers do
- **Edge Case Discovery**: Find boundary conditions that would cause production failures
- **Actionable Reports**: Interactive HTML reports with specific recommendations for improvement

No more guessing if your agent is production-ready. Flakestorm tells you exactly what will break and how to fix it.

## Demo

### flakestorm in Action

![flakestorm Demo](flakestorm_demo.gif)

*Watch flakestorm generate mutations and test your agent in real-time*

### Test Report

![flakestorm Test Report 1](flakestorm_report1.png)

![flakestorm Test Report 2](flakestorm_report2.png)

![flakestorm Test Report 3](flakestorm_report3.png)

![flakestorm Test Report 4](flakestorm_report4.png)

![flakestorm Test Report 5](flakestorm_report5.png)

*Interactive HTML reports with detailed failure analysis and recommendations*

## Try Flakestorm in ~60 Seconds

Want to see Flakestorm in action immediately? Here's the fastest path:

1. **Install flakestorm** (if you have Python 3.10+):
   ```bash
   pip install flakestorm
   ```

2. **Initialize a test configuration**:
   ```bash
   flakestorm init
   ```

3. **Point it at your agent** (edit `flakestorm.yaml`):
   ```yaml
   agent:
     endpoint: "http://localhost:8000/invoke"  # Your agent's endpoint
     type: "http"
   ```

4. **Run your first test**:
   ```bash
   flakestorm run
   ```

That's it! You'll get a robustness score and detailed report showing how your agent handles adversarial inputs.

> **Note**: For full local execution (including mutation generation), you'll need Ollama installed. See the [Local Execution](#local-execution-advanced--power-users) section below or the [Usage Guide](docs/USAGE_GUIDE.md) for complete setup instructions.

## How Flakestorm Works

Flakestorm follows a simple but powerful workflow:

1. **You provide "Golden Prompts"** — example inputs that should always work correctly
2. **Flakestorm generates mutations** — using a local LLM, it creates adversarial variations:
   - Paraphrases (same meaning, different words)
   - Typos and noise (realistic user errors)
   - Tone shifts (frustrated, urgent, aggressive users)
   - Prompt injections (security attacks)
   - Encoding attacks (Base64, URL encoding)
   - Context manipulation (noisy, verbose inputs)
   - Length extremes (empty, very long inputs)
3. **Your agent processes each mutation** — Flakestorm sends them to your agent endpoint
4. **Invariants are checked** — responses are validated against rules you define (latency, content, safety)
5. **Robustness Score is calculated** — weighted by mutation difficulty and importance
6. **Report is generated** — interactive HTML showing what passed, what failed, and why

The result: You know exactly how your agent will behave under stress before users ever see it.

## Features

- ✅ **8 Core Mutation Types**: Comprehensive robustness testing covering semantic, input, security, and edge cases
- ✅ **Invariant Assertions**: Deterministic checks, semantic similarity, basic safety
- ✅ **Local-First**: Uses Ollama with Qwen 3 8B for free testing
- ✅ **Beautiful Reports**: Interactive HTML reports with pass/fail matrices

## Local Execution (Advanced / Power Users)

For full local execution with mutation generation, you'll need to set up Ollama and configure your Python environment. This section covers the complete setup process for users who want to run everything locally without external dependencies.

> **Quick Setup**: For detailed installation instructions, troubleshooting, and configuration options, see the [Usage Guide](docs/USAGE_GUIDE.md). The guide includes step-by-step instructions for Ollama installation, Python environment setup, model selection, and advanced configuration.

## Toward a Zero-Setup Path

We're working on making Flakestorm even easier to use. Future improvements include:

- **Cloud-hosted mutation generation**: No need to install Ollama locally
- **One-command setup**: Automated installation and configuration
- **Docker containers**: Pre-configured environments for instant testing
- **CI/CD integrations**: Native GitHub Actions, GitLab CI, and more
- **Comprehensive Reporting**: Dashboard and reports with team collaboration.

The goal: Test your agent's robustness with a single command, no local dependencies required.

For now, the local execution path gives you full control and privacy. As we build toward zero-setup, you'll always have the option to run everything locally.


## Documentation

### Getting Started
- [📖 Usage Guide](docs/USAGE_GUIDE.md) - Complete end-to-end guide
- [⚙️ Configuration Guide](docs/CONFIGURATION_GUIDE.md) - All configuration options
- [🔌 Connection Guide](docs/CONNECTION_GUIDE.md) - How to connect FlakeStorm to your agent
- [🧪 Test Scenarios](docs/TEST_SCENARIOS.md) - Real-world examples with code
- [🔗 Integrations Guide](docs/INTEGRATIONS_GUIDE.md) - HuggingFace models & semantic similarity

### For Developers
- [🏗️ Architecture & Modules](docs/MODULES.md) - How the code works
- [❓ Developer FAQ](docs/DEVELOPER_FAQ.md) - Q&A about design decisions
- [📦 Publishing Guide](docs/PUBLISHING.md) - How to publish to PyPI
- [🤝 Contributing](docs/CONTRIBUTING.md) - How to contribute

### Troubleshooting
- [🔧 Fix Installation Issues](FIX_INSTALL.md) - Resolve `ModuleNotFoundError: No module named 'flakestorm.reports'`
- [🔨 Fix Build Issues](BUILD_FIX.md) - Resolve `pip install .` vs `pip install -e .` problems

### Reference
- [📋 API Specification](docs/API_SPECIFICATION.md) - API reference
- [🧪 Testing Guide](docs/TESTING_GUIDE.md) - How to run and write tests
- [✅ Implementation Checklist](docs/IMPLEMENTATION_CHECKLIST.md) - Development progress

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Tested with Flakestorm</strong><br>
  <img src="https://img.shields.io/badge/tested%20with-flakestorm-brightgreen" alt="Tested with Flakestorm">
</p>
