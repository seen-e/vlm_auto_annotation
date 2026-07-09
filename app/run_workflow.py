"""Programmatic workflow entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.context import StageContext
from ..core.runtime import load_runtime_config, workflow_config_path
from ..core.workflow import WorkflowRunner


def run_workflow(
    *,
    client: Any,
    video_path: Any,
    instruction: str = "",
    video_id: str | None = None,
    workflow_name: str = "vla_phase_annotation",
    prompt_language: str | None = None,
    robot_type: str | None = None,
    config_path: str | Path | None = None,
    workflow_path: str | Path | None = None,
    experiment_path: str | Path | None = None,
    config_overrides: dict[str, Any] | None = None,
    stages: list[str] | None = None,
    load_outputs: dict[str, str] | None = None,
):
    wf_path = Path(workflow_path) if workflow_path else workflow_config_path(workflow_name)
    config = load_runtime_config(
        default_path=config_path,
        workflow_path=wf_path,
        experiment_path=experiment_path,
        overrides=config_overrides,
    )
    prompt_cfg = config.get("prompt") or {}
    model_cfg = config.get("model") or {}
    context = StageContext(
        video_path=video_path,
        instruction=instruction,
        video_id=video_id,
        robot_type=robot_type or prompt_cfg.get("robot_type", "unknown"),
        prompt_language=prompt_language or prompt_cfg.get("language", "cn"),
        model=model_cfg.get("name", ""),
        workflow_name=(config.get("workflow") or {}).get("name", workflow_name),
        experiment_name=(config.get("experiment") or {}).get("name", "default"),
    )
    return WorkflowRunner(config, client=client).run(context, stages=stages, load_outputs=load_outputs)
