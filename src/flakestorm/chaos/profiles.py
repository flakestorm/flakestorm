"""
Load built-in chaos profiles by name.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from flakestorm.core.config import ChaosConfig


def get_profiles_dir() -> Path:
    """Return the directory containing built-in profile YAML files."""
    return Path(__file__).resolve().parent / "profiles"


def load_chaos_profile(name: str) -> ChaosConfig:
    """
    Load a built-in chaos profile by name (e.g. api_outage, degraded_llm).
    Raises FileNotFoundError if the profile does not exist.
    """
    profiles_dir = get_profiles_dir()
    # Try name.yaml then name with .yaml
    path = profiles_dir / f"{name}.yaml"
    if not path.exists():
        path = profiles_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"Chaos profile not found: {name}. "
                f"Looked in {profiles_dir}. "
                f"Available: {', '.join(p.stem for p in profiles_dir.glob('*.yaml'))}"
            )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    chaos_data = data.get("chaos") if isinstance(data, dict) else None
    if not chaos_data:
        return ChaosConfig()
    return ChaosConfig.model_validate(chaos_data)


def list_profile_names() -> list[str]:
    """Return list of built-in profile names (without .yaml)."""
    profiles_dir = get_profiles_dir()
    if not profiles_dir.exists():
        return []
    return [p.stem for p in profiles_dir.glob("*.yaml")]
