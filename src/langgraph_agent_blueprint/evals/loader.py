"""Scenario loading and validation for eval/replay files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from langgraph_agent_blueprint.models.evals import EvalScenario


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_scenarios_dir() -> Path:
    return repo_root() / "evals" / "scenarios"


def default_fixtures_dir() -> Path:
    return repo_root() / "evals" / "fixtures"


def load_scenario(path: str | Path) -> EvalScenario:
    scenario_path = Path(path)
    try:
        raw = _read_mapping(scenario_path)
        return EvalScenario.model_validate(raw)
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        raise ValueError(f"Invalid eval scenario {scenario_path}: {exc}") from exc


def load_scenarios(directory: str | Path | None = None) -> list[EvalScenario]:
    root = Path(directory) if directory is not None else default_scenarios_dir()
    paths = sorted([*root.glob("*.yaml"), *root.glob("*.yml"), *root.glob("*.json")])
    scenarios = [load_scenario(path) for path in paths]
    return sorted(scenarios, key=lambda scenario: scenario.id)


def scenario_path_for_id(scenario_id: str, directory: str | Path | None = None) -> Path:
    root = Path(directory) if directory is not None else default_scenarios_dir()
    for suffix in [".yaml", ".yml", ".json"]:
        candidate = root / f"{scenario_id}{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Eval scenario not found: {scenario_id}")


def load_scenario_by_id(scenario_id: str, directory: str | Path | None = None) -> EvalScenario:
    return load_scenario(scenario_path_for_id(scenario_id, directory))


def _read_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        parsed = json.loads(path.read_text(encoding="utf-8"))
    else:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("scenario file must contain an object")
    return parsed
