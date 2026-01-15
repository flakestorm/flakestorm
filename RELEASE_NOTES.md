# Release Notes

## Version 0.9.1 - 24 Mutation Types Update

### 🎯 Major Update: Comprehensive Mutation Coverage

Flakestorm now supports **24 mutation types** for comprehensive robustness testing, expanding from the original 8 core types to cover advanced prompt-level attacks and system/network-level vulnerabilities.

### ✨ What's New

#### Expanded Mutation Types (24 Total)

**Core Prompt-Level Attacks (8 types):**
- Paraphrase - Semantic rewrites preserving intent
- Noise - Typos and spelling errors
- Tone Shift - Aggressive/impatient phrasing
- Prompt Injection - Basic adversarial attacks
- Encoding Attacks - Base64, Unicode, URL encoding
- Context Manipulation - Adding/removing/reordering context
- Length Extremes - Empty, minimal, or very long inputs
- Custom - User-defined mutation templates

**Advanced Prompt-Level Attacks (7 new types):**
- Multi-Turn Attack - Fake conversation history with contradictory turns
- Advanced Jailbreak - Sophisticated injection techniques (DAN, role-playing, hypothetical scenarios)
- Semantic Similarity Attack - Adversarial examples that look similar but have different meanings
- Format Poisoning - Structured data injection (JSON, XML, markdown, YAML)
- Language Mixing - Multilingual inputs, code-switching, mixed scripts
- Token Manipulation - Tokenizer edge cases, special tokens, boundary attacks
- Temporal Attack - Impossible dates, outdated references, temporal confusion

**System/Network-Level Attacks (9 new types):**
- HTTP Header Injection - Header manipulation and injection attacks
- Payload Size Attack - Extremely large payloads, memory exhaustion
- Content-Type Confusion - MIME type manipulation and format confusion
- Query Parameter Poisoning - Parameter pollution and query-based injection
- Request Method Attack - HTTP method confusion and manipulation
- Protocol-Level Attack - Request smuggling, chunked encoding, protocol confusion
- Resource Exhaustion - CPU/memory exhaustion, infinite loops, DoS patterns
- Concurrent Request Pattern - Race conditions, concurrent state manipulation
- Timeout Manipulation - Slow processing, timeout-inducing patterns

### 🔧 Improvements

- **Comprehensive Testing Coverage**: All 24 mutation types are fully implemented with templates and default weights
- **Updated Documentation**: README and Usage Guide now reflect all 24 mutation types
- **Enhanced Test Suite**: Test coverage expanded to validate all 24 mutation types
- **Production Status**: Updated development status to Production/Stable

### 📚 Documentation Updates

- README.md updated to reflect 24 mutation types with clear categorization
- Usage Guide includes detailed explanations of all mutation types
- Test suite (`tests/test_mutations.py`) now validates all 24 types

### 🐛 Bug Fixes

- Fixed mutation type count inconsistencies in documentation
- Updated test assertions to cover all mutation types

### 📦 Technical Details

- All 24 mutation types have:
  - Complete template definitions in `src/flakestorm/mutations/templates.py`
  - Default weights configured in `src/flakestorm/mutations/types.py`
  - Display names and descriptions
  - Full test coverage

### 🚀 Migration Guide

No breaking changes. Existing configurations continue to work. The default mutation types remain the original 8 core types. To use the new advanced types, add them to your `flakestorm.yaml`:

```yaml
mutations:
  types:
    - paraphrase
    - noise
    - tone_shift
    - prompt_injection
    - encoding_attacks
    - context_manipulation
    - length_extremes
    - custom
    # Add new types as needed:
    - multi_turn_attack
    - advanced_jailbreak
    - semantic_similarity_attack
    # ... and more
```

### 📊 Impact

This update significantly expands Flakestorm's ability to test agent robustness across:
- **Security vulnerabilities** (advanced jailbreaks, protocol attacks)
- **Input parsing edge cases** (format poisoning, token manipulation)
- **System-level attacks** (resource exhaustion, timeout manipulation)
- **Internationalization** (language mixing, character set handling)

### 🙏 Acknowledgments

Thank you to all contributors and users who have helped shape Flakestorm into a comprehensive chaos engineering tool for AI agents.

---

**Full Changelog**: See [GitHub Releases](https://github.com/flakestorm/flakestorm/releases) for detailed commit history.
