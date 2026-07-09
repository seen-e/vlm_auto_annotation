"""Configuration loading and merging."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_runtime_config(
    *,
    default_path: str | Path | None = None,
    workflow_path: str | Path | None = None,
    experiment_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    default_file = Path(default_path) if default_path else PACKAGE_ROOT / "configs" / "default.yaml"
    config = load_yaml(default_file)
    if workflow_path:
        workflow = load_yaml(workflow_path)
        config["workflow"] = workflow
    if experiment_path:
        experiment = load_yaml(experiment_path)
        mode = str(experiment.get("exports_mode") or "replace").strip().lower()
        if "exports" in experiment and mode == "replace":
            config["exports"] = experiment.get("exports") or []
            experiment = {key: value for key, value in experiment.items() if key != "exports"}
        elif "exports" in experiment and mode == "append":
            config["exports"] = [*(config.get("exports") or []), *(experiment.get("exports") or [])]
            experiment = {key: value for key, value in experiment.items() if key != "exports"}
        elif "exports" in experiment and mode == "merge_by_id":
            merged = {str(item.get("id") or item.get("target_name")): item for item in config.get("exports") or [] if isinstance(item, dict)}
            for item in experiment.get("exports") or []:
                if isinstance(item, dict):
                    merged[str(item.get("id") or item.get("target_name"))] = item
            config["exports"] = list(merged.values())
            experiment = {key: value for key, value in experiment.items() if key != "exports"}
        config = deep_merge(config, experiment)
    if overrides:
        config = deep_merge(config, overrides)
    return config


def workflow_config_path(name: str) -> Path:
    return PACKAGE_ROOT / "configs" / "workflows" / f"{name}.yaml"
