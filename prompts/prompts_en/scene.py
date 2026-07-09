"""English scene-stage prompt."""

SCENE_SYSTEM_PROMPT = """
You are the Scene stage for a robot manipulation video annotation workflow.
Return only one JSON object that matches the current SceneStageOutput contract.
Do not output action sequences, start times, end times, or frame boundaries.
Use the primary view as the reference for left/right/front/back names.
"""

SCENE_PROMPT_TEMPLATE = """
View layout:
{view_layout_description}

Task:
Identify the stable scene context before action analysis.

Return JSON with this exact structure:
{{
  "primary_view": "primary view name",
  "executors": [
    {{
      "executor_id": "left | right | both | single | base | arm | arm_1 | arm_2 | unknown",
      "description": "short visual description",
      "main_workspace": "short workspace description or null",
      "best_observation_views": ["view names useful for this executor"]
    }}
  ],
  "touched_objects": [
    {{
      "object_id": "stable_snake_case_id",
      "description": "short object name",
      "role": "manipulated_object | target_object | tool | container | support"
    }}
  ],
  "background_objects": [
    {{
      "object_id": "stable_snake_case_id",
      "description": "short object name",
      "role": "background"
    }}
  ],
  "executor_object_map": {{"executor_id": ["object_id"]}},
  "best_observation_views": {{"executor_id": ["view_name"]}},
  "scene_summary": "one or two short sentences"
}}
"""
