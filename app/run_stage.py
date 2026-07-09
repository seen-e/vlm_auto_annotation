"""Programmatic single-stage entrypoint."""

from __future__ import annotations

from typing import Any

from .run_workflow import run_workflow


def run_stage(*, stage_name: str, client: Any, video_path: Any, instruction: str = "", **kwargs: Any):
    return run_workflow(
        client=client,
        video_path=video_path,
        instruction=instruction,
        workflow_name=f"{stage_name}_only",
        stages=[stage_name],
        **kwargs,
    )
