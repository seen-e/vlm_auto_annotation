"""Config-driven extraction of stage outputs into context variables."""

from __future__ import annotations

import logging
from typing import Any

from .path_extractor import extract_path
from .value_formatter import format_value

logger = logging.getLogger(__name__)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def normalize_export_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize global ``exports`` and grouped ``stage_exports`` into one list."""
    rules: list[dict[str, Any]] = []
    for item in config.get("exports") or []:
        if isinstance(item, dict):
            rules.append(dict(item))
    grouped = config.get("stage_exports") or {}
    if isinstance(grouped, dict):
        for stage_name, items in grouped.items():
            for item in items or []:
                if isinstance(item, dict):
                    rule = dict(item)
                    rule.setdefault("source_stage", stage_name)
                    rules.append(rule)
    return rules


class StageExporter:
    """Apply export rules after one stage completes."""

    def __init__(self, rules: list[dict[str, Any]], *, experiment_name: str = "default") -> None:
        self.rules = [rule for rule in rules if rule.get("enabled", True)]
        self.experiment_name = experiment_name

    @staticmethod
    def _set_target(container: dict[str, Any], target_name: str, value: Any) -> None:
        keys = [part for part in str(target_name or "").split(".") if part]
        if not keys:
            return
        current = container
        for key in keys[:-1]:
            next_value = current.get(key)
            if not isinstance(next_value, dict):
                next_value = {}
                current[key] = next_value
            current = next_value
        current[keys[-1]] = value

    def export_stage(
        self,
        *,
        context: Any,
        stage_name: str,
        parsed_output: dict[str, Any],
        contract: Any,
    ) -> list[str]:
        warnings: list[str] = []
        parsed_data = _to_jsonable(parsed_output or {})
        contract_data = _to_jsonable(contract)
        for rule in self.rules:
            if str(rule.get("source_stage") or "").strip() != stage_name:
                continue
            source_path = str(rule.get("source_path") or "").strip()
            target_name = str(rule.get("target_name") or "").strip()
            if not source_path or not target_name:
                continue
            default = rule.get("default")
            source_kind = str(rule.get("source_kind") or "contract").strip().lower()
            source = parsed_data if source_kind == "parsed" else contract_data
            if source_kind == "auto":
                value, success = extract_path(parsed_data, source_path, default)
                if not success:
                    value, success = extract_path(contract_data, source_path, default)
            else:
                value, success = extract_path(source, source_path, default)
            used_default = not success
            if used_default:
                value = default
                warning = (
                    f"experiment={self.experiment_name} stage={stage_name} "
                    f"source_path={source_path} target_name={target_name}: used default"
                )
                warnings.append(warning)
            else:
                warning = ""
            fmt = str(rule.get("format") or "json")
            self._set_target(context.exports, target_name, value)
            self._set_target(context.formatted_exports, target_name, format_value(value, fmt))
            context.export_status[target_name] = {
                "experiment": self.experiment_name,
                "source_stage": stage_name,
                "source_path": source_path,
                "target_name": target_name,
                "success": bool(success),
                "used_default": used_default,
                "format": fmt,
                "source_kind": source_kind,
                "warning": warning,
            }
            logger.info(
                "Stage export experiment=%s stage=%s source_path=%s target_name=%s success=%s used_default=%s value_type=%s",
                self.experiment_name,
                stage_name,
                source_path,
                target_name,
                bool(success),
                used_default,
                type(value).__name__,
            )
        return warnings
