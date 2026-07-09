"""Prompt rendering with dynamic context variables."""

from __future__ import annotations

from typing import Any


class MissingPromptValue:
    def __getattr__(self, name: str) -> "MissingPromptValue":
        return self

    def __getitem__(self, key: Any) -> "MissingPromptValue":
        return self

    def __str__(self) -> str:
        return ""

    def __format__(self, spec: str) -> str:
        return ""


MISSING = MissingPromptValue()


class AttrDict(dict):
    def __getattr__(self, name: str) -> Any:
        return self.get(name, MISSING)

    def __getitem__(self, key: Any) -> Any:
        return self.get(key, MISSING)


class PromptVariables(dict):
    def __missing__(self, key: str) -> MissingPromptValue:
        return MISSING


def _wrap(value: Any) -> Any:
    if isinstance(value, dict):
        return AttrDict({key: _wrap(val) for key, val in value.items()})
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    return value


def render_prompt_template(
    template: str,
    *,
    context: Any,
    stage_config: dict[str, Any] | None = None,
    extra_variables: dict[str, Any] | None = None,
) -> str:
    """Render a prompt from context exports, stage defaults, and extra variables."""
    stage_config = stage_config or {}
    variables = PromptVariables()
    variables.update(_wrap(stage_config.get("input_variables") or {}))
    variables.update(_wrap(getattr(context, "formatted_exports", {}) or {}))
    variables.update(_wrap(extra_variables or {}))
    return str(template).format_map(variables)
