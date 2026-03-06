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

Production AI agents are **distributed systems**: they depend on LLM APIs, tools, context windows, and multi-step orchestration. Each of these can fail. Today’s tools don’t answer the questions that matter:

- **What happens when the agent’s tools fail?** — A search API returns 503. A database times out. Does the agent degrade gracefully, hallucinate, or fabricate data?
- **Does the agent always follow its rules?** — Must it always cite sources? Never return PII? Are those guarantees maintained when the environment is degraded?
- **Did we fix the production incident?** — After a failure in prod, how do we prove the fix and prevent regression?

Observability tools tell you *after* something broke. Eval libraries focus on output quality, not resilience. **No tool systematically breaks the agent’s environment to test whether it survives.** Flakestorm fills that gap.

## The Solution: Chaos Engineering for AI Agents

**Flakestorm** is a **chaos engineering platform** for production AI agents. Like Chaos Monkey for infrastructure, Flakestorm deliberately injects failures into the tools, APIs, and LLMs your agent depends on — then verifies that the agent still obeys its behavioral contract and recovers gracefully.

> **Other tools test if your agent gives good answers. Flakestorm tests if your agent survives production.**

### Three Pillars

| Pillar | What it does | Question answered |
|--------|----------------|--------------------|
| **Environment Chaos** | Inject faults into tools and LLMs (timeouts, errors, rate limits, malformed responses) | *Does the agent handle bad environments?* |
| **Behavioral Contracts** | Define invariants (rules the agent must always follow) and verify them across a matrix of chaos scenarios | *Does the agent obey its rules when the world breaks?* |
| **Replay Regression** | Import real production failure sessions and replay them as deterministic tests | *Did we fix this incident?* |

On top of that, Flakestorm still runs **adversarial prompt mutations** (24 mutation types) so you can test bad inputs and bad environments together.

**Scores at a glance**

| What you run | Score you get |
|--------------|----------------|
| `flakestorm run` | **Robustness score** (0–1): how well the agent handled adversarial prompts. |
| `flakestorm run --chaos --chaos-only` | **Chaos resilience** (same 0–1 metric): how well the agent handled a broken environment (no mutations, only chaos). |
| `flakestorm contract run` | **Resilience score** (0–100%): contract × chaos matrix, severity-weighted. |
| `flakestorm replay run …` | Per-session pass/fail; aggregate **replay regression** score when run via `flakestorm ci`. |
| `flakestorm ci` | **Overall (weighted)** score combining mutation robustness, chaos resilience, contract compliance, and replay regression — one number for CI gates. |

**Commands by scope**

| Scope | Command | What runs |
|-------|---------|-----------|
| **V1 only / mutation only** | `flakestorm run` | Just adversarial mutations → agent → invariants. No chaos, no contract matrix, no replay. Use a v1.0 config or omit `--chaos` so you get only the classic robustness score. |
| **Mutation + chaos** | `flakestorm run --chaos` | Mutations run against a fault-injected agent (tool/LLM chaos). |
| **Chaos only** | `flakestorm run --chaos --chaos-only` | No mutations; golden prompts only, with chaos. Single chaos resilience score. |
| **Contract only** | `flakestorm contract run` | Contract × chaos matrix; resilience score. |
| **Replay only** | `flakestorm replay run path/to/replay.yaml -c flakestorm.yaml` | One or more replay sessions. |
| **ALL (full CI)** | `flakestorm ci` | Mutation run + contract (if configured) + chaos-only run (if chaos configured) + all replay sessions (if configured); then **overall** weighted score. |

**Context attacks** are part of environment chaos: faults are applied to **tool responses and context** (e.g. a tool returns valid-looking content with hidden instructions), not to the user prompt. See [Context Attacks](docs/CONTEXT_ATTACKS.md).

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

*Watch Flakestorm run chaos and mutation tests against your agent in real-time*

### Test Report

![flakestorm Test Report 1](flakestorm_report1.png)

![flakestorm Test Report 2](flakestorm_report2.png)

![flakestorm Test Report 3](flakestorm_report3.png)

![flakestorm Test Report 4](flakestorm_report4.png)

![flakestorm Test Report 5](flakestorm_report5.png)

*Interactive HTML reports with detailed failure analysis and recommendations*

## How Flakestorm Works

Flakestorm supports several modes; you can use one or combine them:

- **Chaos only** — Golden prompts → agent with fault-injected tools/LLM → invariants. *Does the agent handle bad environments?*
- **Contract** — Golden prompts → agent under each chaos scenario → verify named invariants across a matrix. *Does the agent obey its rules under every failure mode?*
- **Replay** — Recorded production input + recorded tool responses → agent → contract. *Did we fix this incident?*
- **Mutation (optional)** — Golden prompts → adversarial mutations (24 types) → agent (optionally under chaos) → invariants. *Does the agent handle bad inputs (and optionally bad environments)?*

You define **golden prompts**, **invariants** (or a full **contract** with severity and chaos matrix), and optionally **chaos** (tool/LLM faults) and **replay** sessions. Flakestorm runs the chosen mode(s), checks responses against your rules, and produces a **robustness score** (mutation or chaos-only runs) or **resilience score** (contract run), plus HTML report. Use `flakestorm run`, `flakestorm contract run`, `flakestorm replay run`, or `flakestorm ci` for the combined overall score.

> **Note**: Mutation generation uses a local LLM (Ollama) or cloud APIs (OpenAI, Claude, Gemini). API keys via environment variables only. See [LLM Providers](docs/LLM_PROVIDERS.md).

## Features

### Chaos engineering pillars

- **Environment Chaos** — Inject faults into tools and LLMs (timeouts, errors, rate limits, malformed responses, built-in profiles). [→ Environment Chaos](docs/ENVIRONMENT_CHAOS.md)
- **Behavioral Contracts** — Named invariants × chaos matrix; severity-weighted resilience score; optional reset for stateful agents. [→ Behavioral Contracts](docs/BEHAVIORAL_CONTRACTS.md)
- **Replay Regression** — Import production failures (manual or LangSmith), replay deterministically, verify against contracts. [→ Replay Regression](docs/REPLAY_REGRESSION.md)

### Supporting capabilities

- **Adversarial mutations** — 24 mutation types (prompt-level and system/network-level) when you want to test bad inputs alone or combined with chaos. [→ Test Scenarios](docs/TEST_SCENARIOS.md)
- **Invariants & assertions** — Deterministic checks, semantic similarity, safety (PII, refusal); configurable per contract.
- **Robustness score** — For mutation runs: a single weighted score (0–1) of how well the agent handled adversarial prompts. Reported in HTML/JSON and CLI (`results.statistics.robustness_score`).
- **Unified resilience score** — For full CI: weighted combination of **mutation robustness**, chaos resilience, contract compliance, and replay regression; configurable in YAML.
- **Context attacks** — Indirect injection and memory poisoning (e.g. via tool responses). [→ Context Attacks](docs/CONTEXT_ATTACKS.md)
- **LLM providers** — Ollama, OpenAI, Anthropic, Google (Gemini); API keys via env only. [→ LLM Providers](docs/LLM_PROVIDERS.md)
- **Reports** — Interactive HTML and JSON; contract matrix and replay reports.

**Try it:** [Working example](examples/v2_research_agent/README.md) with chaos, contracts, and replay from the CLI.

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
   With a [v2 config](examples/v2_research_agent/README.md) you can also run `flakestorm run --chaos`, `flakestorm contract run`, `flakestorm replay run`, or `flakestorm ci` to exercise all pillars.

That's it! You get a **robustness score** (for mutation runs) or a **resilience score** (when using chaos/contract/replay), plus a report showing how your agent handles chaos and adversarial inputs.

> **Note**: For full local execution (including mutation generation), you'll need Ollama installed. See the [Usage Guide](docs/USAGE_GUIDE.md) for complete setup instructions.



## Roadmap

See [Roadmap](ROADMAP.md) for the full plan. Highlights:

- **V3 — Multi-agent chaos** — Chaos engineering for systems of multiple agents: fault injection across agent-to-agent and tool boundaries, contract verification for multi-agent workflows, and replay of multi-agent production incidents.
- **Pattern engine** — 110+ prompt-injection and 52+ PII detection patterns; Rust-backed, sub-50ms.
- **Cloud** — Scalable runs, team dashboards, scheduled chaos, CI integrations.
- **Enterprise** — On-premise, audit logging, compliance certifications.

## Documentation

### Getting Started
- [📖 Usage Guide](docs/USAGE_GUIDE.md) - Complete end-to-end guide (includes local setup)
- [⚙️ Configuration Guide](docs/CONFIGURATION_GUIDE.md) - All configuration options
- [🔌 Connection Guide](docs/CONNECTION_GUIDE.md) - How to connect FlakeStorm to your agent
- [🧪 Test Scenarios](docs/TEST_SCENARIOS.md) - Real-world examples with code
- [📂 Example: chaos, contracts & replay](examples/v2_research_agent/README.md) - Working agent and config you can run
- [🔗 Integrations Guide](docs/INTEGRATIONS_GUIDE.md) - HuggingFace models & semantic similarity
- [🤖 LLM Providers](docs/LLM_PROVIDERS.md) - OpenAI, Claude, Gemini (env-only API keys)
- [🌪️ Environment Chaos](docs/ENVIRONMENT_CHAOS.md) - Tool/LLM fault injection
- [📜 Behavioral Contracts](docs/BEHAVIORAL_CONTRACTS.md) - Contract × chaos matrix
- [🔄 Replay Regression](docs/REPLAY_REGRESSION.md) - Import and replay production failures
- [🛡️ Context Attacks](docs/CONTEXT_ATTACKS.md) - Indirect injection, memory poisoning
- [📐 V2 Spec](docs/V2_SPEC.md) - Score formula, reset, Python tools

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

---

<p align="center">
  ❤️ <a href="https://github.com/sponsors/flakestorm">Sponsor Flakestorm on GitHub</a>
</p>
 