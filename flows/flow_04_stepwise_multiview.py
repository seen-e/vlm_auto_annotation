"""Flow 04: planned stepwise multi-view annotation.

Use this when the dataset already provides ``steps_raw`` and has multiple
synchronized camera views. This missing path is implemented as:

1. main-view per-step refinement;
2. auxiliary-view per-step verification/correction;
3. final dedup and consistency QC.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..config import DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..prompts_cn import (
    MULTIVIEW_STEP_QC_PROMPT_TEMPLATE,
    MULTIVIEW_STEP_QC_SYSTEM_PROMPT,
    MULTIVIEW_STEP_VERIFY_PROMPT_TEMPLATE,
    MULTIVIEW_STEP_VERIFY_SYSTEM_PROMPT,
)
from ..schemas import AnnotationResult, StageResult, StepRaw, merge_token_usage
from ..video_utils import labelled_view_parts, load_video_as_image_parts
from .flow_03_stepwise_single_view import dedup_steps, refine_steps_single_view
from .utils import (
    as_str_list,
    call_json_stage,
    instruction_from_steps,
    json_dumps,
    numbered_text,
    previous_steps_context,
)


def verify_steps_with_auxiliary_views(
    client,
    *,
    auxiliary_video_paths: Mapping[str, str | Path],
    initial_instruction: str,
    steps: list[StepRaw],
    main_refined_steps: list[str],
    model: str = DEFAULT_MODEL,
    target_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames_per_view: int = DEFAULT_MAX_FRAMES,
) -> tuple[list[str], StageResult, list[dict[str, Any]]]:
    """Use auxiliary views to verify or lightly correct each main-view step."""
    if not auxiliary_video_paths:
        stage = StageResult(
            name="multiview_verification",
            output={
                "verified_steps": main_refined_steps,
                "warning": "No auxiliary views were provided; kept main-view steps.",
            },
            success=True,
        )
        return main_refined_steps, stage, []

    verified_steps: list[str] = []
    corrections: list[dict[str, Any]] = []
    raw_responses: list[str] = []
    usage_items: list[dict[str, int]] = []

    for step, main_step in zip(steps, main_refined_steps):
        parts: list[dict[str, Any]] = []
        view_metadata: dict[str, Any] = {}
        for view_name, video_path in auxiliary_video_paths.items():
            view_parts, meta = load_video_as_image_parts(
                video_path,
                target_fps=target_fps,
                max_frames=max_frames_per_view,
                frame_start=step.start,
                frame_end=step.end,
            )
            parts.extend(labelled_view_parts(view_name, view_parts))
            view_metadata[view_name] = meta

        prompt = MULTIVIEW_STEP_VERIFY_PROMPT_TEMPLATE.format(
            initial_instruction=initial_instruction,
            step_index=step.index,
            step_description=step.description,
            main_refined_step=main_step,
            view_names=", ".join(auxiliary_video_paths.keys()),
            previous_steps_context=previous_steps_context(steps, step.index),
        )
        stage = call_json_stage(
            client,
            name=f"multiview_step_{step.index}",
            parts=parts,
            system_prompt=MULTIVIEW_STEP_VERIFY_SYSTEM_PROMPT,
            user_prompt=prompt,
            model=model,
            fallback={
                "verified_step": main_step,
                "changes_made": [],
                "view_evidence": [],
                "confidence": 0.0,
            },
        )
        verified = str(stage.output.get("verified_step", main_step)).strip() or main_step
        verified_steps.append(verified)
        raw_responses.append(stage.raw_response)
        usage_items.append(stage.token_usage)
        corrections.append(
            {
                "step_index": step.index,
                "raw_description": step.description,
                "main_refined_step": main_step,
                "verified_step": verified,
                "changes_made": as_str_list(stage.output.get("changes_made")),
                "view_evidence": stage.output.get("view_evidence", []),
                "confidence": stage.output.get("confidence"),
                "metadata": view_metadata,
            }
        )

    aggregate = StageResult(
        name="multiview_verification",
        output={"verified_steps": verified_steps, "corrections": corrections},
        raw_response=json_dumps(raw_responses),
        success=bool(verified_steps),
        token_usage=merge_token_usage(*usage_items),
    )
    return verified_steps, aggregate, corrections


def qc_multiview_steps(
    client,
    *,
    initial_instruction: str,
    original_steps: list[str],
    verified_steps: list[str],
    model: str = DEFAULT_MODEL,
) -> StageResult:
    """Run a final consistency check for the new multi-view steps_raw path."""
    prompt = MULTIVIEW_STEP_QC_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        original_steps=numbered_text(original_steps),
        verified_steps=numbered_text(verified_steps),
    )
    stage = call_json_stage(
        client,
        name="multiview_qc",
        parts=[],
        system_prompt=MULTIVIEW_STEP_QC_SYSTEM_PROMPT,
        user_prompt=prompt,
        model=model,
        fallback={
            "passed": True,
            "issues": [],
            "recommended_steps": verified_steps,
        },
    )
    recommended = as_str_list(stage.output.get("recommended_steps"))
    if recommended and len(recommended) != len(verified_steps):
        stage.output["recommended_steps"] = verified_steps
        stage.output["qc_warning"] = "QC output step count changed; kept verified steps."
    return stage


def run_stepwise_multiview(
    client,
    main_video_path: str | Path,
    auxiliary_video_paths: Mapping[str, str | Path],
    initial_instruction: str,
    steps_raw: list[dict[str, Any] | StepRaw],
    *,
    model: str = DEFAULT_MODEL,
    bimanual: bool = False,
    target_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames_per_step: int = DEFAULT_MAX_FRAMES,
    max_aux_frames_per_view: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run the fourth path: ``steps_raw`` plus multi-view correction."""
    steps, main_steps, main_stage, per_step_outputs = refine_steps_single_view(
        client,
        main_video_path,
        initial_instruction,
        steps_raw,
        model=model,
        bimanual=bimanual,
        target_fps=target_fps,
        max_frames_per_step=max_frames_per_step,
    )
    verified_steps, verify_stage, corrections = verify_steps_with_auxiliary_views(
        client,
        auxiliary_video_paths=auxiliary_video_paths,
        initial_instruction=initial_instruction,
        steps=steps,
        main_refined_steps=main_steps,
        model=model,
        target_fps=target_fps,
        max_frames_per_view=max_aux_frames_per_view,
    )
    dedup = dedup_steps(
        client,
        initial_instruction=initial_instruction,
        original_steps=[step.description for step in steps],
        refined_steps=verified_steps,
        model=model,
    )
    deduped_steps = as_str_list(dedup.output.get("deduped_steps")) or verified_steps
    qc = qc_multiview_steps(
        client,
        initial_instruction=initial_instruction,
        original_steps=[step.description for step in steps],
        verified_steps=deduped_steps,
        model=model,
    )
    final_steps = as_str_list(qc.output.get("recommended_steps")) or deduped_steps

    output: dict[str, Any] = {
        "flow": "stepwise_multiview",
        "initialInstruction": initial_instruction,
        "stepsRaw": [
            {"index": step.index, "description": step.description, "start": step.start, "end": step.end}
            for step in steps
        ],
        "mainViewSteps": main_steps,
        "fineGrainedSteps": final_steps,
        "refinedInstruction": instruction_from_steps(final_steps),
        "perStep": per_step_outputs,
        "multiViewCorrections": corrections,
        "qc": {
            "passed": qc.output.get("passed", True),
            "issues": as_str_list(qc.output.get("issues")),
        },
    }
    return AnnotationResult(
        flow_name="flow_04_stepwise_multiview",
        stages={
            "main_step_refinement": main_stage,
            "multiview_verification": verify_stage,
            "dedup": dedup,
            "multiview_qc": qc,
        },
        output=output,
    )
