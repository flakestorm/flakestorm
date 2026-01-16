# Flakestorm

<p align="center">
  <strong>The Agent Reliability Engine</strong><br>
  <em>Chaos Engineering for Production AI Agents</em>
</p>

<p align="center">
  <a href="https://github.com/flakestorm/flakestorm/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License">
  </a>
  <a href="https://github.com/flakestorm/flakestorm">
    <img src="https://img.shields.io/github/stars/flakestorm/flakestorm?style=social" alt="GitHub Stars">
  </a>
  <a href="https://pypi.org/project/flakestorm/">
    <img src="https://img.shields.io/pypi/v/flakestorm.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/flakestorm/">
    <img src="https://img.shields.io/pypi/dm/flakestorm.svg" alt="PyPI downloads">
  </a>
  <a href="https://github.com/flakestorm/flakestorm/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/flakestorm/flakestorm/ci.yml?branch=main" alt="Build Status">
  </a>
  <a href="https://github.com/flakestorm/flakestorm/releases">
    <img src="https://img.shields.io/github/v/release/flakestorm/flakestorm" alt="Latest Release">
  </a>
</p>

---

## The Problem

**The "Happy Path" Fallacy**: Current AI development tools focus on getting an agent to work *once*. Developers tweak prompts until they get a correct answer, declare victory, and ship.

**The Reality**: LLMs are non-deterministic. An agent that works on Monday with `temperature=0.7` might fail on Tuesday. Production agents face real users who make typos, get aggressive, and attempt prompt injections. Real traffic exposes failures that happy-path testing misses.

**The Void**:
- **Observability Tools** (LangSmith) tell you *after* the agent failed in production
- **Eval Libraries** (RAGAS) focus on academic scores rather than system reliability
- **CI Pipelines** lack chaos testing — agents ship untested against adversarial inputs
- **Missing Link**: A tool that actively *attacks* the agent to prove robustness before deployment

## The Solution

**Flakestorm** is a chaos testing layer for production AI agents. It applies **Chaos Engineering** principles to systematically test how your agents behave under adversarial inputs before real users encounter them.

Instead of running one test case, Flakestorm takes a single "Golden Prompt", generates adversarial mutations (semantic variations, noise injection, hostile tone, prompt injections), runs them against your agent, and calculates a **Robustness Score**. Run it before deploy, in CI, or against production-like environments.

> **"If it passes Flakestorm, it won't break in Production."**

## Production-First by Design

Flakestorm is designed for teams already running AI agents in production. Most production agents use cloud LLM APIs (OpenAI, Gemini, Claude, Perplexity, etc.) and face real traffic, real users, and real abuse patterns.

**Why local LLMs exist in the open source version:**
- Fast experimentation and proofs-of-concept
- CI-friendly testing without external dependencies
- Transparent, extensible chaos engine

**Why production chaos should mirror production reality:**
Production agents run on cloud infrastructure, process real user inputs, and scale dynamically. Chaos testing should reflect this reality—testing against the same infrastructure, scale, and patterns your agents face in production.

The cloud version removes operational friction: no local model setup, no environment configuration, scalable mutation runs, shared dashboards, and team collaboration. Open source proves the value; cloud delivers production-grade chaos engineering.

## Who Flakestorm Is For

- **Teams shipping AI agents to production** — Catch failures before users do
- **Engineers running agents behind APIs** — Test against real-world abuse patterns
- **Teams already paying for LLM APIs** — Reduce regressions and production incidents
- **CI/CD pipelines** — Automated reliability gates before deployment

Flakestorm is built for production-grade agents handling real traffic. While it works great for exploration and hobby projects, it's designed to catch the failures that matter when agents are deployed at scale.




#
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

## How Flakestorm Works

Flakestorm follows a simple but powerful workflow:

1. **You provide "Golden Prompts"** — example inputs that should always work correctly
2. **Flakestorm generates mutations** — using a local LLM, it creates adversarial variations across 24 mutation types:
   - **Core prompt-level (8)**: Paraphrase, noise, tone shift, prompt injection, encoding attacks, context manipulation, length extremes, custom
   - **Advanced prompt-level (7)**: Multi-turn attacks, advanced jailbreaks, semantic similarity attacks, format poisoning, language mixing, token manipulation, temporal attacks
   - **System/Network-level (9)**: HTTP header injection, payload size attacks, content-type confusion, query parameter poisoning, request method attacks, protocol-level attacks, resource exhaustion, concurrent patterns, timeout manipulation
3. **Your agent processes each mutation** — Flakestorm sends them to your agent endpoint
4. **Invariants are checked** — responses are validated against rules you define (latency, content, safety)
5. **Robustness Score is calculated** — weighted by mutation difficulty and importance
6. **Report is generated** — interactive HTML showing what passed, what failed, and why

The result: You know exactly how your agent will behave under stress before users ever see it.

> **Note**: The open source version uses local LLMs (Ollama) for mutation generation. The cloud version (in development) uses production-grade infrastructure to mirror real-world chaos testing at scale.

## Features

- ✅ **24 Mutation Types**: Comprehensive robustness testing covering:
  - **Core prompt-level attacks (8)**: Paraphrase, noise, tone shift, prompt injection, encoding attacks, context manipulation, length extremes, custom
  - **Advanced prompt-level attacks (7)**: Multi-turn attacks, advanced jailbreaks, semantic similarity attacks, format poisoning, language mixing, token manipulation, temporal attacks
  - **System/Network-level attacks (9)**: HTTP header injection, payload size attacks, content-type confusion, query parameter poisoning, request method attacks, protocol-level attacks, resource exhaustion, concurrent patterns, timeout manipulation
- ✅ **Invariant Assertions**: Deterministic checks, semantic similarity, basic safety
- ✅ **Beautiful Reports**: Interactive HTML reports with pass/fail matrices
- ✅ **Open Source Core**: Full chaos engine available locally for experimentation and CI

## Open Source vs Cloud

**Open Source (Always Free):**
- Core chaos engine with all 24 mutation types (no artificial feature gating)
- Local execution for fast experimentation
- CI-friendly usage without external dependencies
- Full transparency and extensibility
- Perfect for proofs-of-concept and development workflows

**Cloud (In Progress / Waitlist):**
- Zero-setup chaos testing (no Ollama, no local models)
- Scalable runs (thousands of mutations)
- Shared dashboards & reports
- Team collaboration
- Scheduled & continuous chaos runs
- Production-grade reliability workflows

**Our Philosophy:** We do not cripple the OSS version. Cloud exists to remove operational pain, not to lock features. Open source proves the value; cloud delivers production-grade chaos engineering at scale.

# Try Flakestorm in ~60 Seconds

This is the fastest way to try Flakestorm locally. Production teams typically use the cloud version (waitlist). Here's the local quickstart:

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

> **Note**: For full local execution (including mutation generation), you'll need Ollama installed. See the [Usage Guide](docs/USAGE_GUIDE.md) for complete setup instructions.



## Roadmap

See what's coming next! Check out our [Roadmap](ROADMAP.md) for upcoming features including:
- 🚀 Pattern Engine Upgrade with 110+ Prompt Injection Patterns and 52+ PII Detection Patterns
- ☁️ Cloud Version enhancements (scalable runs, team collaboration, continuous testing)
- 🏢 Enterprise features (on-premise deployment, custom patterns, compliance certifications)

## Documentation

### Getting Started
- [📖 Usage Guide](docs/USAGE_GUIDE.md) - Complete end-to-end guide (includes local setup)
- [⚙️ Configuration Guide](docs/CONFIGURATION_GUIDE.md) - All configuration options
- [🔌 Connection Guide](docs/CONNECTION_GUIDE.md) - How to connect FlakeStorm to your agent
- [🧪 Test Scenarios](docs/TEST_SCENARIOS.md) - Real-world examples with code
- [🔗 Integrations Guide](docs/INTEGRATIONS_GUIDE.md) - HuggingFace models & semantic similarity

### For Developers
- [🏗️ Architecture & Modules](docs/MODULES.md) - How the code works
- [❓ Developer FAQ](docs/DEVELOPER_FAQ.md) - Q&A about design decisions
- [🤝 Contributing](docs/CONTRIBUTING.md) - How to contribute

### Troubleshooting
- [🔧 Fix Installation Issues](FIX_INSTALL.md) - Resolve `ModuleNotFoundError: No module named 'flakestorm.reports'`
- [🔨 Fix Build Issues](BUILD_FIX.md) - Resolve `pip install .` vs `pip install -e .` problems

### Support
- [🐛 Issue Templates](https://github.com/flakestorm/flakestorm/tree/main/.github/ISSUE_TEMPLATE) - Use our issue templates to report bugs, request features, or ask questions

### Reference
- [📋 API Specification](docs/API_SPECIFICATION.md) - API reference
- [🧪 Testing Guide](docs/TESTING_GUIDE.md) - How to run and write tests
- [✅ Implementation Checklist](docs/IMPLEMENTATION_CHECKLIST.md) - Development progress

## Cloud Version (Early Access)

For teams running production AI agents, the cloud version removes operational friction: zero-setup chaos testing without local model configuration, scalable mutation runs that mirror production traffic, shared dashboards for team collaboration, and continuous chaos runs integrated into your reliability workflows.

The cloud version is currently in early access. [Join the waitlist](https://flakestorm.com) to get access as we roll it out.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Tested with Flakestorm</strong><br>
  <img src="https://img.shields.io/badge/tested%20with-flakestorm-brightgreen" alt="Tested with Flakestorm">
</p>



<iframe src="https://github.com/sponsors/flakestorm/card" title="Sponsor flakestorm" height="225" width="600" style="border: 0;"></iframe>
