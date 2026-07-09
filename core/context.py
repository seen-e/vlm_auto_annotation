"""Shared stage context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageContext:
    """Mutable context passed between independent stages."""

    video_path: Any
    instruction: str = ""
    video_id: str | None = None
    robot_type: str = "unknown"
    prompt_language: str = "cn"
    model: str = ""
    workflow_name: str = ""
    experiment_name: str = "default"
    stage_raw_responses: dict[str, str] = field(default_factory=dict)
    stage_parsed_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    stage_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    stage_contracts: dict[str, Any] = field(default_factory=dict)
    stage_artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    exports: dict[str, Any] = field(default_factory=dict)
    formatted_exports: dict[str, Any] = field(default_factory=dict)
    export_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    validation_warnings: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def episode_name(self) -> str:
        if self.video_id:
            return str(self.video_id)
        if isinstance(self.video_path, dict) and self.video_path:
            from pathlib import Path

            return Path(str(next(iter(self.video_path.values())))).stem or "episode"
        if isinstance(self.video_path, (list, tuple)) and self.video_path:
            from pathlib import Path

            return Path(str(self.video_path[0])).stem or "episode"
        from pathlib import Path

        return Path(str(self.video_path)).stem or "episode"
