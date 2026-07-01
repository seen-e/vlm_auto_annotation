"""Flow 03: FineVLA stepwise single-view annotation.

Use this when the dataset already provides ``steps_raw`` frame ranges and one
usable view. It mirrors FineVLA/Galaxea style per-step refinement plus dedup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..prompts_cn import (
    ACTION_FINE_GRAINED_GUIDANCE,
    DEDUP_STEPS_PROMPT,
    GALAXEA_STEP_PROMPT_TEMPLATE,
    GALAXEA_STEP_SYSTEM_PROMPT,
    GALAXEA_STEP_SYSTEM_PROMPT_BIMANUAL,
)
from ..schemas import AnnotationResult, StageResult, StepRaw, merge_token_usage
from ..video_utils import load_video_as_image_parts
from .utils import (
    as_str_list,
    call_json_stage,
    instruction_from_steps,
    json_dumps,
    normalize_steps_raw,
    numbered_text,
    previous_steps_context,
)


def refine_steps_single_view(
    client,
    video_path: str | Path,
    initial_instruction: str,
    steps_raw: list[dict[str, Any] | StepRaw],
    *,
    model: str = DEFAULT_MODEL,
    bimanual: bool = False,
    target_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames_per_step: int = DEFAULT_MAX_FRAMES,
    system_prompt: str | None = None,
    prompt_template: str = GALAXEA_STEP_PROMPT_TEMPLATE,
) -> tuple[list[StepRaw], list[str], StageResult, list[dict[str, Any]]]:
    """Refine every pre-segmented step on one view without final dedup."""
    steps = normalize_steps_raw(steps_raw)
    system = system_prompt or (
        GALAXEA_STEP_SYSTEM_PROMPT_BIMANUAL if bimanual else GALAXEA_STEP_SYSTEM_PROMPT
    )
    refined_steps: list[str] = []
    per_step_outputs: list[dict[str, Any]] = []
    raw_responses: list[str] = []
    usage_items: list[dict[str, int]] = []

    for step in steps:
        parts, meta = load_video_as_image_parts(
            video_path,
            target_fps=target_fps,
            max_frames=max_frames_per_step,
            frame_start=step.start,
            frame_end=step.end,
        )
        prompt = prompt_template.format(
            initial_instruction=initial_instruction,
            previous_steps_context=previous_steps_context(steps, step.index),
            step_index=step.index,
            step_description=step.description,
            action_guidance=ACTION_FINE_GRAINED_GUIDANCE,
        )
        stage = call_json_stage(
            client,
            name=f"step_{step.index}",
            parts=parts,
            system_prompt=system,
            user_prompt=prompt,
            model=model,
            fallback={"refined_step": step.description},
        )
        refined = str(stage.output.get("refined_step", step.description)).strip() or step.description
        refined_steps.append(refined)
        raw_responses.append(stage.raw_response)
        usage_items.append(stage.token_usage)
        per_step_outputs.append(
            {
                "step_index": step.index,
                "raw_description": step.description,
                "refined_step": refined,
                "model_output": stage.output,
                "metadata": meta,
            }
        )

    aggregate = StageResult(
        name="step_refinement",
        output={"fine_grained_steps": refined_steps, "steps": per_step_outputs},
        raw_response=json_dumps(raw_responses),
        success=bool(refined_steps),
        token_usage=merge_token_usage(*usage_items),
    )
    return steps, refined_steps, aggregate, per_step_outputs


def dedup_steps(
    client,
    *,
    initial_instruction: str,
    original_steps: list[str],
    refined_steps: list[str],
    model: str = DEFAULT_MODEL,
) -> StageResult:
    """Remove repeated wording while preserving step count."""
    prompt = DEDUP_STEPS_PROMPT.format(
        initial_instruction=initial_instruction,
        original_steps=numbered_text(original_steps),
        refined_steps=numbered_text(refined_steps),
    )
    stage = call_json_stage(
        client,
        name="dedup",
        parts=[],
        system_prompt="",
        user_prompt=prompt,
        model=model,
        fallback={"deduped_steps": refined_steps},
    )
    deduped = as_str_list(stage.output.get("deduped_steps"))
    if len(deduped) != len(refined_steps):
        stage.output["deduped_steps"] = refined_steps
        stage.output["dedup_warning"] = "Model output step count changed; kept pre-dedup steps."
    return stage


def run_stepwise_single_view(
    client,
    video_path: str | Path,
    initial_instruction: str,
    steps_raw: list[dict[str, Any] | StepRaw],
    *,
    model: str = DEFAULT_MODEL,
    bimanual: bool = False,
    target_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames_per_step: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run per-step refinement and dedup on one view."""
    steps, refined_steps, step_stage, per_step_outputs = refine_steps_single_view(
        client,
        video_path,
        initial_instruction,
        steps_raw,
        model=model,
        bimanual=bimanual,
        target_fps=target_fps,
        max_frames_per_step=max_frames_per_step,
    )
    dedup = dedup_steps(
        client,
        initial_instruction=initial_instruction,
        original_steps=[step.description for step in steps],
        refined_steps=refined_steps,
        model=model,
    )
    final_steps = as_str_list(dedup.output.get("deduped_steps")) or refined_steps

    output: dict[str, Any] = {
        "flow": "stepwise_single_view",
        "initialInstruction": initial_instruction,
        "stepsRaw": [
            {"index": step.index, "description": step.description, "start": step.start, "end": step.end}
            for step in steps
        ],
        "fineGrainedSteps": final_steps,
        "refinedInstruction": instruction_from_steps(final_steps),
        "perStep": per_step_outputs,
    }
    return AnnotationResult(
        flow_name="flow_03_stepwise_single_view",
        stages={"step_refinement": step_stage, "dedup": dedup},
        output=output,
    )
