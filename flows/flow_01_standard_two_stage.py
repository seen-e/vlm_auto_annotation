"""Flow 01: FineVLA standard two-stage annotation.

Use this when a task has one usable global-view video and no pre-segmented
``steps_raw``. It mirrors FineVLA's analysis -> refinement path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import DEFAULT_ANALYSIS_FPS, DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..prompts_cn import (
    ACTION_FINE_GRAINED_GUIDANCE,
    ACTION_VOCABULARY,
    ANALYSIS_PROMPT_TEMPLATE,
    ANALYSIS_SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES,
    REFINEMENT_PROMPT_TEMPLATE,
    REFINEMENT_SYSTEM_PROMPT,
)
from ..schemas import AnnotationResult
from ..video_utils import load_video_as_image_parts
from .utils import as_str_list, call_json_stage, instruction_from_steps


def run_standard_two_stage(
    client,
    video_path: str | Path,
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run global analysis followed by fine-grained refinement."""
    analysis_parts, analysis_meta = load_video_as_image_parts(
        video_path,
        target_fps=analysis_fps,
        max_frames=max_frames,
    )
    analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        action_vocabulary=ACTION_VOCABULARY,
    )
    analysis = call_json_stage(
        client,
        name="analysis",
        parts=analysis_parts,
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        user_prompt=analysis_prompt,
        model=model,
        fallback={"action_sequence": [], "main_object": ""},
    )

    action_sequence = as_str_list(analysis.output.get("action_sequence"))
    main_object = str(analysis.output.get("main_object", "")).strip()

    refinement_parts, refinement_meta = load_video_as_image_parts(
        video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
    )
    refinement_prompt = REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        action_sequence=action_sequence,
        main_object=main_object,
        action_guidance=ACTION_FINE_GRAINED_GUIDANCE,
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
    )
    refinement = call_json_stage(
        client,
        name="refinement",
        parts=refinement_parts,
        system_prompt=REFINEMENT_SYSTEM_PROMPT,
        user_prompt=refinement_prompt,
        model=model,
        fallback={"fine_grained_steps": [], "refined_instruction": ""},
    )

    steps = as_str_list(refinement.output.get("fine_grained_steps"))
    refined_instruction = str(refinement.output.get("refined_instruction", "")).strip()
    if steps and not refined_instruction:
        refined_instruction = instruction_from_steps(steps)

    output: dict[str, Any] = {
        "flow": "standard_two_stage",
        "initialInstruction": initial_instruction,
        "analysisResult": {
            "action_sequence": action_sequence,
            "main_object": main_object,
        },
        "fineGrainedSteps": steps,
        "refinedInstruction": refined_instruction,
        "metadata": {
            "analysis": analysis_meta,
            "refinement": refinement_meta,
        },
    }
    return AnnotationResult(
        flow_name="flow_01_standard_two_stage",
        stages={"analysis": analysis, "refinement": refinement},
        output=output,
    )
