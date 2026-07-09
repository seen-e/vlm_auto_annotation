"""Runtime result containers for VLA phase annotation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    """Result from one VLM stage."""

    name: str
    output: dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    success: bool = False
    error: str | None = None
    token_usage: dict[str, int] = field(default_factory=dict)


@dataclass
class AnnotationResult:
    """Complete workflow result returned by public entrypoints.

    ``stages`` may be empty when stage objects are excluded from output.
    """

    workflow_name: str
    stages: dict[str, StageResult] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return bool(self.stages) and all(stage.success for stage in self.stages.values())

    def to_dict(self, *, schema_version: str | None = None) -> dict[str, Any]:
        """Serialize to plain dict.

        ``schema_version`` controls whether parsed stage output is included.
        """
        version = (schema_version or "").strip() or "v2"
        if version == "debug":
            stages_serialized = {
                name: {
                    "success": stage.success,
                    "output": stage.output,
                    "error": stage.error,
                    "token_usage": stage.token_usage,
                }
                for name, stage in self.stages.items()
            }
        else:
            stages_serialized = {
                name: {
                    "success": stage.success,
                    "error": stage.error,
                    "token_usage": stage.token_usage,
                }
                for name, stage in self.stages.items()
            }
        return {
            "workflow_name": self.workflow_name,
            "success": self.success,
            "output": self.output,
            "stages": stages_serialized,
        }


def merge_token_usage(*items: dict[str, int]) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for item in items:
        for key in usage:
            usage[key] += int(item.get(key, 0) or 0)
    return usage
