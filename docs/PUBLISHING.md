# Publishing flakestorm to PyPI

This guide explains how to publish flakestorm so users can install it with `pip install flakestorm`.

---

## Table of Contents

1. [Understanding PyPI](#understanding-pypi)
2. [Prerequisites](#prerequisites)
3. [Project Structure for Publishing](#project-structure-for-publishing)
4. [Step-by-Step Publishing Guide](#step-by-step-publishing-guide)
5. [Automated Publishing with GitHub Actions](#automated-publishing-with-github-actions)
6. [Publishing the Rust Extension](#publishing-the-rust-extension)
7. [Version Management](#version-management)
8. [Testing Before Publishing](#testing-before-publishing)
9. [Common Issues](#common-issues)

---

## Understanding PyPI

### What is PyPI?

**PyPI** (Python Package Index) is the official repository for Python packages. When users run:

```bash
pip install flakestorm
```

pip downloads the package from PyPI (https://pypi.org).

### What Gets Published?

A Python package is distributed as either:
- **Source Distribution (sdist)**: `.tar.gz` file with source code
- **Wheel (bdist_wheel)**: `.whl` file, pre-built for specific platforms

For flakestorm:
- **Pure Python code**: Published as universal wheel (works everywhere)
- **Rust extension**: Published as platform-specific wheels (separate process)

---

## Prerequisites

### 1. PyPI Account

Create accounts on:
- **Test PyPI**: https://test.pypi.org/account/register/ (for testing)
- **PyPI**: https://pypi.org/account/register/ (for production)

### 2. API Tokens

Generate API tokens (more secure than username/password):

1. Go to https://pypi.org/manage/account/token/
2. Create a token with scope "Entire account" or project-specific
3. Save the token securely (you'll only see it once!)

### 3. Install Build Tools

```bash
pip install build twine hatch
```

---

## Project Structure for Publishing

flakestorm is already set up correctly. Here's what makes it publishable:

### pyproject.toml (Key Sections)

```toml
[build-system]
requires = ["hatchling", "hatch-fancy-pypi-readme"]
build-backend = "hatchling.build"

[project]
name = "flakestorm"                    # Package name on PyPI
version = "0.1.0"                    # Version number
description = "The Agent Reliability Engine"
readme = "README.md"                 # Shown on PyPI page
license = "Apache-2.0"
requires-python = ">=3.10"
dependencies = [                     # Auto-installed with package
    "typer>=0.9.0",
    "rich>=13.0.0",
    # ...
]

[project.scripts]
flakestorm = "flakestorm.cli.main:app"  # Creates `flakestorm` command

[tool.hatch.build.targets.wheel]
packages = ["src/flakestorm"]         # What to include in wheel
```

### Directory Structure

```
flakestorm/
├── pyproject.toml      # Package metadata (required)
├── README.md           # PyPI description
├── LICENSE             # License file
├── src/
│   └── flakestorm/       # Your package code
│       ├── __init__.py # Must exist for package
│       ├── core/
│       ├── mutations/
│       └── ...
└── tests/              # Not included in package
```

### `src/flakestorm/__init__.py` (Package Entry Point)

```python
"""flakestorm - The Agent Reliability Engine"""

__version__ = "0.1.0"

from flakestorm.core.config import load_config, FlakeStormConfig
from flakestorm.core.runner import FlakeStormRunner

__all__ = ["load_config", "FlakeStormConfig", "FlakeStormRunner", "__version__"]
```

---

## Step-by-Step Publishing Guide

### Step 1: Verify Package Metadata

```bash
# Check pyproject.toml is valid
python -m pip install .

# Verify the package works
flakestorm --version
```

### Step 2: Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# You should see:
# dist/
#   flakestorm-0.1.0.tar.gz      (source)
#   flakestorm-0.1.0-py3-none-any.whl  (wheel)
```

### Step 3: Check the Build

```bash
# Verify the package contents
twine check dist/*

# List files in the wheel
unzip -l dist/*.whl

# Ensure it contains:
# - flakestorm/__init__.py
# - flakestorm/core/*.py
# - flakestorm/mutations/*.py
# - etc.
```

### Step 4: Test on Test PyPI (Recommended)

```bash
# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: pypi-your-test-token-here

# Install from Test PyPI to verify
pip install --index-url https://test.pypi.org/simple/ flakestorm
```

### Step 5: Publish to Production PyPI

```bash
# Upload to real PyPI
twine upload dist/*

# Username: __token__
# Password: pypi-your-real-token-here
```

### Step 6: Verify Installation

```bash
# In a fresh virtual environment
python -m venv test_env
source test_env/bin/activate

pip install flakestorm
flakestorm --version
```

🎉 **Congratulations!** Users can now `pip install flakestorm`!

---

## Automated Publishing with GitHub Actions

Set up automatic publishing when you create a release:

### `.github/workflows/publish.yml`

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install build tools
        run: pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

### Setting Up the Secret

1. Go to your GitHub repo → Settings → Secrets → Actions
2. Add a new secret named `PYPI_TOKEN`
3. Paste your PyPI API token as the value

### Creating a Release

1. Go to GitHub → Releases → Create new release
2. Create a new tag (e.g., `v0.1.0`)
3. Add release notes
4. Publish release
5. GitHub Actions will automatically publish to PyPI

---

## Publishing the Rust Extension

The Rust extension (if implemented) would be published separately because it requires platform-specific binaries.

### Using `maturin`

```bash
cd rust/

# Build wheels for your current platform
maturin build --release

# The wheel would be in: ../target/wheels/flakestorm_rust-0.1.0-cp39-*.whl
```

### Multi-Platform Publishing with GitHub Actions

```yaml
# .github/workflows/rust-publish.yml
name: Publish Rust Extension

on:
  release:
    types: [published]

jobs:
  linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          manylinux: auto
          command: build
          args: --release --manifest-path rust/Cargo.toml -o dist
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-linux
          path: dist

  macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          command: build
          args: --release --manifest-path rust/Cargo.toml -o dist
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-macos
          path: dist

  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          command: build
          args: --release --manifest-path rust/Cargo.toml -o dist
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-windows
          path: dist

  publish:
    needs: [linux, macos, windows]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist
          merge-multiple: true
      - name: Publish to PyPI
        uses: PyO3/maturin-action@v1
        with:
          command: upload
          args: --skip-existing dist/*
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

---

## Version Management

### Semantic Versioning

Follow [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

0.1.0 - Initial release
0.1.1 - Bug fixes
0.2.0 - New features (backward compatible)
1.0.0 - Stable release / Breaking changes
```

### Where Version is Defined

Update version in TWO places:

1. **`pyproject.toml`**:
   ```toml
   [project]
   version = "0.2.0"
   ```

2. **`src/flakestorm/__init__.py`**:
   ```python
   __version__ = "0.2.0"
   ```

### Automating Version Sync (Optional)

Use `hatch-vcs` to automatically get version from git tags:

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"
```

Then just create a git tag and the version is set automatically:

```bash
git tag v0.2.0
git push --tags
```

---

## Testing Before Publishing

### Local Testing

```bash
# Create a fresh virtual environment
python -m venv test_install
source test_install/bin/activate

# Install from local build
pip install dist/flakestorm-0.1.0-py3-none-any.whl

# Test it works
flakestorm --help
flakestorm init
python -c "from flakestorm import load_config; print('OK')"
```

### Test PyPI

Always test on Test PyPI first:

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            flakestorm
```

The `--extra-index-url` is needed because Test PyPI may not have all dependencies.

---

## Common Issues

### "Package name already taken"

Package names on PyPI are unique. If `flakestorm` is taken:
- Check https://pypi.org/project/flakestorm/
- Choose a different name: `flakestorm-cli`, `py-flakestorm`, etc.

### "Invalid distribution file"

```bash
# Check what's wrong
twine check dist/*

# Common fixes:
# - Ensure README.md is valid markdown
# - Ensure LICENSE file exists
# - Ensure version is valid format
```

### "Missing files in wheel"

```bash
# List wheel contents
unzip -l dist/*.whl

# If files are missing, check pyproject.toml:
[tool.hatch.build.targets.wheel]
packages = ["src/flakestorm"]  # Make sure path is correct
```

### "Command not found after install"

Ensure `project.scripts` is set in pyproject.toml:

```toml
[project.scripts]
flakestorm = "flakestorm.cli.main:app"
```

---

## Quick Reference

### One-Time Setup

```bash
# Install tools
pip install build twine

# Create PyPI account and token
# Store token securely
```

### Each Release

```bash
# 1. Update version in pyproject.toml and __init__.py
# 2. Commit and push
git add -A && git commit -m "Release 0.2.0" && git push

# 3. Build
python -m build

# 4. Check
twine check dist/*

# 5. Test (optional but recommended)
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ flakestorm

# 6. Publish
twine upload dist/*

# 7. Tag release
git tag v0.2.0
git push --tags
```

### With GitHub Actions

Just create a release on GitHub and everything happens automatically!

---

## Next Steps After Publishing

1. **Announce**: Post on social media, Reddit, Hacker News
2. **Documentation**: Update docs with install instructions
3. **Monitor**: Watch for issues and PyPI download stats
4. **Iterate**: Fix bugs, add features, release new versions

---

*Happy publishing! 🚀*
