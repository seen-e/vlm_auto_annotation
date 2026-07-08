"""Stage contracts and adapters for VLA/VLM video annotation."""

from .schemas import (
    AnalysisStageInput,
    AnalysisStageOutput,
    ExecutorInfo,
    FinalAnnotationOutput,
    FrameSample,
    ObjectInfo,
    RefinedSegment,
    RefinementStageInput,
    RefinementStageOutput,
    SceneStageInput,
    SceneStageOutput,
    SegmentCandidate,
    SegmentChange,
    VideoSample,
)

__all__ = [
    "VideoSample",
    "FrameSample",
    "ExecutorInfo",
    "ObjectInfo",
    "SceneStageInput",
    "SceneStageOutput",
    "SegmentCandidate",
    "AnalysisStageInput",
    "AnalysisStageOutput",
    "RefinedSegment",
    "SegmentChange",
    "RefinementStageInput",
    "RefinementStageOutput",
    "FinalAnnotationOutput",
]
