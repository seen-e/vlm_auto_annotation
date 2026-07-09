"""English refinement-stage prompt."""

REFINEMENT_SYSTEM_PROMPT = """
You are the Refinement stage for robot manipulation video annotation.
Return only one JSON object that matches the current RefinementStageOutput contract.
Use scene and analysis context variables from the prompt. Do not add actions that are not visible.
start_time is the earliest visible start of the phase intention or state change.
end_time is when the target state is completed and stable.
"""

REFINEMENT_PROMPT_TEMPLATE = """
Instruction:
{initial_instruction}

View layout:
{view_layout_description}

Scene context:
{scene}

Analysis candidates:
{analysis.candidate_segments}

Task:
Refine candidate segments into final temporal segments.

Return JSON with this exact structure:
{{
  "refined_segments": [
    {{
      "segment_id": "S001",
      "start_time": "MM:SS.ss or null",
      "end_time": "MM:SS.ss or null",
      "start_frame": null,
      "end_frame": null,
      "executor": "executor_id",
      "action": "short action phrase",
      "objects": ["object_id"],
      "boundary_reason": "short boundary evidence",
      "confidence": 0.6
    }}
  ],
  "changes": [
    {{
      "original_segment_id": "S001",
      "change_type": "keep | split | merge | trim | remove | add",
      "reason": "short reason"
    }}
  ]
}}
"""
