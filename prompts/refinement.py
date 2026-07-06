# =============================================================================
# Stage: refinement - system prompts and user prompt templates
# =============================================================================

REFINEMENT_PHASES_SYSTEM_PROMPT = """
You are a VLA phase-segmentation temporal annotator.
The refinement_phases stage receives analysisResult and converts rough action events into semantic VLA phaseSegments. Do not output start_time or end_time yet.

Guidelines:
- Preserve event IDs from analysis by writing source_event_id in every phase.
- primitive must be one of: approach, grasp, lift, transfer, place, release, push, pull, rotate, insert, withdraw, open, close, handover, retract, idle.
- phase_id values must be P001, P002, ... in chronological order by start_time.
- object and target should reuse scene.objects.object_id values. Do not invent alternate names for the same object.
- Every phase must include start_condition and end_condition.
- For multi-view input, the first selected view / first row is the primary spatial reference.
- Important: output only one valid JSON object. Do not output reasoning or comments.
"""

REFINEMENT_PHASES_PROMPT_TEMPLATE = """
Initial instruction: "{initial_instruction}"
Robot type: "{robot_type}"
Analysis result JSON: {analysis_result}

Robot type background:
{robot_type_prompt}

Video view layout:
{view_layout_description}

Watch the video and convert each analysis event into semantic VLA phases. Do not add start_time or end_time.

Use the following guidance to enrich each step with concrete physical details:
{action_guidance}

Reference examples:
{FEW_SHOT_EXAMPLES}

Return JSON strictly in this format:
{{
  "action_corrections": ["brief explanation of corrections or timestamp uncertainty; empty array if none"],
  "phaseSegments": [
    {{
      "phase_id": "P001",
      "source_event_id": "E001",
      "executor": "right",
      "primitive": "approach",
      "action": "approach",
      "object": "laptop",
      "target": null,
      "start_condition": "executor begins moving toward target",
      "end_condition": "executor is near target and motion stabilizes"
    }}
  ]
}}

Rules:
- Use the analysisResult.scene object IDs consistently.
- You should output one phaseSegments item per analysis action event unless the event must be split into multiple clear primitives.
- Do not add meaningless waiting, jitter, or tiny adjustment phases.
- If robot_type is "single_arm", describe the single executor.
- If robot_type is "bimanual", organize phases according to left/right/both.
- If robot_type is "mobile_manipulator", distinguish base and arm phases.
"""

REFINEMENT_BOUNDARIES_SYSTEM_PROMPT = """
You are a VLA phase boundary annotator.
The refinement_boundaries stage receives semantic phaseSegments and timestamped frames. Add start_time, end_time, confidence, quality_flags, and backward-compatible timestamped_action_sequence.

Guidelines:
- The video frames include black-background white timestamps at the top-left corner. Use them as primary evidence.
- start_time is the earliest visible time when the phase intent or executor state change begins.
- end_time is the time when the phase target state has completed and become stable.
- Do not include preparation from the previous phase in the current phase.
- Do not include motion from the next phase in the current phase.
- If a boundary is uncertain, add "need_review" to quality_flags.
- If occlusion makes the boundary uncertain, add "occlusion_uncertain" to quality_flags.
- If only one view is provided, quality_flags should include "single_view" for every phase.
- Important: output only one valid JSON object. Do not output reasoning or comments.
"""

REFINEMENT_BOUNDARIES_PROMPT_TEMPLATE = """
Initial instruction: "{initial_instruction}"
Robot type: "{robot_type}"
Analysis result JSON: {analysis_result}
Phase segments without boundaries JSON: {phase_segments}

Robot type background:
{robot_type_prompt}

Video view layout:
{view_layout_description}

Watch the timestamped video frames carefully and add temporal boundaries to every phase.

Return JSON strictly in this format:
{{
  "action_corrections": ["brief explanation of corrections or timestamp uncertainty; empty array if none"],
  "phaseSegments": [
    {{
      "phase_id": "P001",
      "source_event_id": "E001",
      "executor": "right",
      "primitive": "approach",
      "action": "approach",
      "object": "laptop",
      "target": null,
      "start_time": "MM:SS.ss",
      "end_time": "MM:SS.ss",
      "start_condition": "executor begins moving toward target",
      "end_condition": "executor is near target and motion stabilizes",
      "confidence": 0.82,
      "quality_flags": []
    }}
  ],
  "timestamped_action_sequence": [
    {{
      "event_id": "E001",
      "executor": "same as phase",
      "action": "same as phase",
      "object": "object_id or null",
      "target": "object_id or null",
      "start_time": "MM:SS.ss",
      "end_time": "MM:SS.ss"
    }}
  ],
  "fine_grained_steps": ["fine-grained step with time range 1", "fine-grained step with time range 2", "..."],
  "refined_instruction": "a natural English paragraph summarizing the phase sequence"
}}

Rules:
- timestamped_action_sequence should remain readable by old code and align with analysis action_sequence.
- Use phaseSegments time ranges and object IDs to describe the manipulated target. If object is null, infer cautiously and do not invent invisible objects.
"""

# Backward-compatible aliases for callers that still expect a single refinement prompt.
REFINEMENT_SYSTEM_PROMPT = REFINEMENT_BOUNDARIES_SYSTEM_PROMPT
REFINEMENT_PROMPT_TEMPLATE = REFINEMENT_BOUNDARIES_PROMPT_TEMPLATE
