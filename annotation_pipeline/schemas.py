"""Typed stage contracts for VLA/VLM video annotation.

All public fields use snake_case. The models are intentionally compact: each
stage only carries the information produced by that stage and consumed by later
stages.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RobotType = Literal["single_arm", "bimanual", "mobile_manipulator", "unknown"]
ChangeType = Literal["keep", "split", "merge", "trim", "remove", "add"]


def _clip(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def timestamp_to_seconds(value: str | None) -> float | None:
    """Convert MM:SS.ss timestamp to seconds; return None if invalid."""
    text = str(value or "").strip()
    match = re.match(r"^(\d+):(\d{2}(?:\.\d+)?)$", text)
    if not match:
        return None
    return int(match.group(1)) * 60 + float(match.group(2))


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FrameSample(ContractModel):
    """One sampled frame metadata item.

    Produced by sampling code; consumed by all VLM stages when frame metadata is
    available. frame_index and timestamp are optional because some callers only
    pass image parts.
    """

    frame_index: int | None = Field(default=None, description="0-based source frame index.")
    timestamp: str | None = Field(default=None, description="MM:SS.ss timestamp for the sampled frame.")
    timestamp_seconds: float | None = Field(default=None, ge=0, description="Timestamp in seconds.")
    view_name: str | None = Field(default=None, description="Camera/view name for this frame.")


class VideoSample(ContractModel):
    """Video-level input metadata shared by all stages."""

    video_id: str | None = Field(default=None, description="Stable episode/video identifier.")
    video_path: str | list[str] | dict[str, str] | None = Field(default=None, description="Input video path(s).")
    robot_type: RobotType = Field(default="unknown", description="Configured robot profile.")
    primary_view: str | None = Field(default=None, description="Primary view used for spatial names.")
    views: list[str] = Field(default_factory=list, description="Selected camera/view names.")
    sampled_frames: list[FrameSample] = Field(default_factory=list, description="Optional sampled frame metadata.")


class ExecutorInfo(ContractModel):
    """Execution subject defined by Scene and reused by later stages."""

    executor_id: str = Field(description="Required stable executor id, e.g. left/right/single/base/arm.")
    description: str = Field(default="", description="Short visual description from primary view.")
    main_workspace: str | None = Field(default=None, description="Main operation area.")
    best_observation_views: list[str] = Field(default_factory=list, description="Best views for this executor.")

    @field_validator("executor_id", "description", "main_workspace", mode="before")
    @classmethod
    def _clean_short_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _clip(value, 80)


class ObjectInfo(ContractModel):
    """Object defined by Scene and referenced by later stages."""

    object_id: str = Field(description="Required stable snake_case object id.")
    description: str = Field(default="", description="Short object description.")
    role: str = Field(default="", description="manipulated_object/target_object/tool/container/support/background.")

    @field_validator("object_id", "description", "role", mode="before")
    @classmethod
    def _clean_object_text(cls, value: Any) -> str:
        return _clip(value, 80)


class SceneStageInput(ContractModel):
    """Input contract for Scene stage.

    Scene consumes video/frame/view metadata and robot profile. It must not
    consume analysis or refinement results.
    """

    video_id: str | None = None
    sampled_frames: list[FrameSample] = Field(default_factory=list)
    views: list[str] = Field(default_factory=list)
    primary_view: str | None = None
    robot_profile: RobotType = "unknown"
    state_action_summary: str | None = None


class SceneStageOutput(ContractModel):
    """Scene output.

    Responsibility: establish global context only. It must not contain action
    sequences or temporal boundaries.
    """

    primary_view: str | None = Field(default=None, description="Primary spatial reference view.")
    executors: list[ExecutorInfo] = Field(default_factory=list, description="Visible execution subjects.")
    touched_objects: list[ObjectInfo] = Field(default_factory=list, description="Objects likely to be manipulated.")
    background_objects: list[ObjectInfo] = Field(default_factory=list, description="Visible non-operated objects.")
    executor_object_map: dict[str, list[str]] = Field(default_factory=dict, description="executor_id -> object_ids.")
    best_observation_views: dict[str, list[str]] = Field(default_factory=dict, description="executor_id -> view names.")
    scene_summary: str = Field(default="", description="At most two short sentences.")

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
    """Candidate action segment produced by Analysis.

    Time fields are optional candidates. If both frame and time are present,
    downstream code should prefer frame index for exact video alignment and use
    timestamp for human-readable output.
    """

    segment_id: str = Field(description="Required stable segment id, e.g. S001.")
    start_time: str | None = Field(default=None, description="Optional MM:SS.ss start boundary.")
    end_time: str | None = Field(default=None, description="Optional MM:SS.ss end boundary.")
    start_frame: int | None = Field(default=None, ge=0, description="Optional inclusive start frame.")
    end_frame: int | None = Field(default=None, ge=0, description="Optional inclusive end frame.")
    executor: str = Field(description="Must come from Scene executors.")
    action: str = Field(description="Short action phrase.")
    objects: list[str] = Field(default_factory=list, description="Stable object_ids touched/targeted.")
    evidence: str = Field(default="", description="One short evidence sentence.")
    confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Confidence in [0, 1].")

    @field_validator("segment_id", "executor", "action", "evidence", mode="before")
    @classmethod
    def _clean_segment_text(cls, value: Any) -> str:
        return _clip(value, 80)


class AnalysisStageInput(ContractModel):
    """Input contract for Analysis stage."""

    scene_output: SceneStageOutput = Field(description="Structured Scene output.")
    sampled_frames: list[FrameSample] = Field(default_factory=list)
    state_action_data: dict[str, Any] | None = None
    phase_granularity: Literal["atomic", "subtask", "task"] = "atomic"


class AnalysisStageOutput(ContractModel):
    """Analysis output.

    Responsibility: produce candidate action segments only. It should not repeat
    scene descriptions or final captions.
    """

    candidate_segments: list[SegmentCandidate] = Field(default_factory=list)
    uncertain_regions: list[dict[str, str]] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)

    @field_validator("analysis_notes", mode="before")
    @classmethod
    def _trim_notes(cls, value: Any) -> list[str]:
        items = value if isinstance(value, list) else ([] if value is None else [value])
        return [_clip(item, 30) for item in items if _clip(item, 30)][:3]


class RefinedSegment(ContractModel):
    """Finalized temporal segment produced by Refinement."""

    segment_id: str = Field(description="Segment id, usually inherited from Analysis.")
    start_time: str | None = Field(default=None, description="MM:SS.ss start boundary.")
    end_time: str | None = Field(default=None, description="MM:SS.ss end boundary.")
    start_frame: int | None = Field(default=None, ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    executor: str = Field(description="Must come from Scene executors.")
    action: str = Field(description="Short action phrase.")
    objects: list[str] = Field(default_factory=list)
    boundary_reason: str = Field(default="", description="Short reason for boundary choice.")
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)

    @field_validator("segment_id", "executor", "action", "boundary_reason", mode="before")
    @classmethod
    def _clean_refined_text(cls, value: Any) -> str:
        return _clip(value, 80)


class SegmentChange(ContractModel):
    """How Refinement changed an Analysis candidate."""

    original_segment_id: str = Field(description="Source candidate segment id.")
    change_type: ChangeType = Field(default="keep", description="keep/split/merge/trim/remove/add.")
    reason: str = Field(default="", description="Short reason, max 30 chars.")

    @field_validator("reason", mode="before")
    @classmethod
    def _clean_reason(cls, value: Any) -> str:
        return _clip(value, 30)


class RefinementStageInput(ContractModel):
    """Input contract for Refinement stage."""

    candidate_segments: list[SegmentCandidate] = Field(default_factory=list)
    timestamps: list[str] = Field(default_factory=list)
    frame_index: list[int] = Field(default_factory=list)
    state_action_change_points: list[dict[str, Any]] = Field(default_factory=list)
    refinement_rules: list[str] = Field(default_factory=list)


class RefinementStageOutput(ContractModel):
    """Refinement output.

    Responsibility: fix boundaries, split/merge/trim/remove candidates only.
    """

    refined_segments: list[RefinedSegment] = Field(default_factory=list)
    changes: list[SegmentChange] = Field(default_factory=list)


class FinalAnnotationOutput(ContractModel):
    """Compact final annotation output produced by the label/caption adapter."""

    video_id: str | None = Field(default=None)
    task_summary: str = Field(default="", description="One-sentence task summary.")
    action_sequence: list[dict[str, Any]] = Field(default_factory=list, description="Time-ordered compact actions.")
    touched_objects: list[str] = Field(default_factory=list, description="Actually manipulated object_ids.")
    final_caption: str = Field(default="", description="Concise natural-language final label.")
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
