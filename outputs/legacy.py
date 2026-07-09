"""Legacy compatibility output."""

from __future__ import annotations

from typing import Any


def build_legacy(context: Any) -> dict[str, Any]:
    analysis_raw = context.stage_outputs.get("analysis", {})
    refinement_raw = context.stage_outputs.get("refinement", {})
    return {
        "analysisResult": analysis_raw,
        "refinementResult": refinement_raw,
        "timestampedActionSequence": refinement_raw.get("action_sequence")
        or refinement_raw.get("timestampedActionSequence")
        or [],
        "fineGrainedSteps": refinement_raw.get("fineGrainedSteps") or refinement_raw.get("fine_grained_steps") or [],
        "refinedInstruction": refinement_raw.get("refinedInstruction") or refinement_raw.get("refined_instruction") or "",
    }
