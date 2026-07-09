"""Contract models for the current stage workflow."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RobotType = Literal["single_arm", "bimanual", "mobile_manipulator", "unknown"]
ChangeType = Literal["keep", "split", "merge", "trim", "remove", "add"]


def _clip(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def timestamp_to_seconds(value: str | None) -> float | None:
    text = str(value or "").strip()
    match = re.match(r"^(\d+):(\d{2}(?:\.\d+)?)$", text)
    if not match:
        return None
    return int(match.group(1)) * 60 + float(match.group(2))


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FrameSample(ContractModel):
    frame_index: int | None = Field(default=None)
    timestamp: str | None = Field(default=None)
    timestamp_seconds: float | None = Field(default=None, ge=0)
    view_name: str | None = Field(default=None)


class VideoSample(ContractModel):
    video_id: str | None = None
    video_path: str | list[str] | dict[str, str] | None = None
    robot_type: RobotType = "unknown"
    primary_view: str | None = None
    views: list[str] = Field(default_factory=list)
    sampled_frames: list[FrameSample] = Field(default_factory=list)


class ExecutorInfo(ContractModel):
    executor_id: str
    description: str = ""
    main_workspace: str | None = None
    best_observation_views: list[str] = Field(default_factory=list)

    @field_validator("executor_id", "description", "main_workspace", mode="before")
    @classmethod
    def _clean_short_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _clip(value, 80)


class ObjectInfo(ContractModel):
    object_id: str
    description: str = ""
    role: str = ""

    @field_validator("object_id", "description", "role", mode="before")
    @classmethod
    def _clean_object_text(cls, value: Any) -> str:
        return _clip(value, 80)


class SceneStageInput(ContractModel):
    video_id: str | None = None
    sampled_frames: list[FrameSample] = Field(default_factory=list)
    views: list[str] = Field(default_factory=list)
    primary_view: str | None = None
    robot_profile: RobotType = "unknown"


class SceneStageOutput(ContractModel):
    primary_view: str | None = None
    executors: list[ExecutorInfo] = Field(default_factory=list)
    touched_objects: list[ObjectInfo] = Field(default_factory=list)
    background_objects: list[ObjectInfo] = Field(default_factory=list)
    executor_object_map: dict[str, list[str]] = Field(default_factory=dict)
    best_observation_views: dict[str, list[str]] = Field(default_factory=dict)
    scene_summary: str = ""

    @field_validator("scene_summary", mode="before")
    @classmethod
    def _clean_summary(cls, value: Any) -> str:
        return _clip(value, 200)

    @model_validator(mode="after")
    def _dedupe(self) -> "SceneStageOutput":
        self.executors = _dedupe_by(self.executors, "executor_id")
        self.touched_objects = _dedupe_by(self.touched_objects, "object_id")
        self.background_objects = _dedupe_by(self.background_objects, "object_id")
        return self


class SegmentCandidate(ContractModel):
    segment_id: str
    start_time: str | None = None
    end_time: str | None = None
    start_frame: int | None = Field(default=None, ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    executor: str
    action: str
    objects: list[str] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)

    @field_validator("segment_id", "executor", "action", "evidence", mode="before")
    @classmethod
    def _clean_segment_text(cls, value: Any) -> str:
        return _clip(value, 80)


class AnalysisStageInput(ContractModel):
    scene_output: SceneStageOutput
    sampled_frames: list[FrameSample] = Field(default_factory=list)
    phase_granularity: Literal["atomic", "subtask", "task"] = "atomic"


class AnalysisStageOutput(ContractModel):
    candidate_segments: list[SegmentCandidate] = Field(default_factory=list)
    uncertain_regions: list[dict[str, str]] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)

    @field_validator("analysis_notes", mode="before")
    @classmethod
    def _trim_notes(cls, value: Any) -> list[str]:
        items = value if isinstance(value, list) else ([] if value is None else [value])
        return [_clip(item, 30) for item in items if _clip(item, 30)][:3]


class RefinedSegment(ContractModel):
    segment_id: str
    start_time: str | None = None
    end_time: str | None = None
    start_frame: int | None = Field(default=None, ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    executor: str
    action: str
    objects: list[str] = Field(default_factory=list)
    boundary_reason: str = ""
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)

    @field_validator("segment_id", "executor", "action", "boundary_reason", mode="before")
    @classmethod
    def _clean_refined_text(cls, value: Any) -> str:
        return _clip(value, 80)


class SegmentChange(ContractModel):
    original_segment_id: str
    change_type: ChangeType = "keep"
    reason: str = ""

    @field_validator("reason", mode="before")
    @classmethod
    def _clean_reason(cls, value: Any) -> str:
        return _clip(value, 30)


class RefinementStageInput(ContractModel):
    candidate_segments: list[SegmentCandidate] = Field(default_factory=list)
    timestamps: list[str] = Field(default_factory=list)
    frame_index: list[int] = Field(default_factory=list)
    refinement_rules: list[str] = Field(default_factory=list)


class RefinementStageOutput(ContractModel):
    refined_segments: list[RefinedSegment] = Field(default_factory=list)
    changes: list[SegmentChange] = Field(default_factory=list)


class FinalAnnotationOutput(ContractModel):
    video_id: str | None = None
    task_summary: str = ""
    action_sequence: list[dict[str, Any]] = Field(default_factory=list)
    touched_objects: list[str] = Field(default_factory=list)
    final_caption: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dedupe_objects(self) -> "FinalAnnotationOutput":
        seen: set[str] = set()
        self.touched_objects = [item for item in self.touched_objects if not (item in seen or seen.add(item))]
        return self


def _dedupe_by(items: list[Any], attr: str) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for item in items:
        key = str(getattr(item, attr, "") or "")
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out
