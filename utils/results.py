"""Runtime result containers for VLA phase annotation flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#twesterf 
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
    """Complete flow result returned by public flow functions."""

    flow_name: str
    stages: dict[str, StageResult] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return bool(self.stages) and all(stage.success for stage in self.stages.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_name": self.flow_name,
            "success": self.success,
            "output": self.output,
            "stages": {
                name: {
                    "success": stage.success,
                    "output": stage.output,
                    "error": stage.error,
                    "token_usage": stage.token_usage,
                }
                for name, stage in self.stages.items()
            },
        }


def merge_token_usage(*items: dict[str, int]) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for item in items:
        for key in usage:
            usage[key] += int(item.get(key, 0) or 0)
    return usage
