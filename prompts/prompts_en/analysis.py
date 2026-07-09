"""English analysis-stage prompt."""

ANALYSIS_SYSTEM_PROMPT = """
You are the Analysis stage for robot manipulation video annotation.
Return only one JSON object that matches the current AnalysisStageOutput contract.
Use the dynamic context variables provided in the prompt. Do not invent executor or object names when scene context is available.
Do not output final temporal boundaries unless the contract field is explicitly present.
"""

ANALYSIS_PROMPT_TEMPLATE = """
Instruction:
{initial_instruction}

View layout:
{view_layout_description}

Action vocabulary:
{action_vocabulary}

Scene context:
{scene}

Task:
Split the visible manipulation into ordered candidate action segments.

Return JSON with this exact structure:
{{
  "candidate_segments": [
    {{
      "segment_id": "S001",
      "start_time": null,
      "end_time": null,
      "start_frame": null,
      "end_frame": null,
      "executor": "executor_id from scene context",
      "action": "short action phrase",
      "objects": ["object_id"],
      "evidence": "short visual evidence",
      "confidence": 0.6
    }}
  ],
  "uncertain_regions": [],
  "analysis_notes": []
}}
"""
