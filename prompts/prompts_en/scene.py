"""Scene-stage prompt templates."""

SCENE_SYSTEM_PROMPT = """
You are the Scene stage for robot manipulation video annotation.
Your only responsibility is to define stable scene context for later stages.

Rules:
- Output JSON only. Do not use Markdown.
- Do not output action sequences, start_time, end_time, start_frame, or end_frame.
- Define executors and objects once so later stages can reuse the same IDs.
- Spatial names such as left/right/front/back must use the primary view as reference.
- For multiple arms, prefer spatial executor IDs such as left/right/center rather than arm_1/arm_2 when visually clear.
- If information is missing, use null or [] instead of guessing.
"""

SCENE_PROMPT_TEMPLATE = """
Initial instruction: "{initial_instruction}"
Configured robot_type: "{robot_type}"

Robot type background:
{robot_type_prompt}

Video view layout:
{view_layout_description}

Return one JSON object with this schema:
{{
  "scene_context": {{
    "primary_view": "view name or null",
    "executors": [
      {{
        "executor_id": "left | right | center | single | base | arm | unknown",
        "description": "short primary-view visual description",
        "main_workspace": "short workspace description or null",
        "best_observation_views": ["view_name"]
      }}
    ],
    "touched_objects": [
      {{
        "object_id": "stable_snake_case_id",
        "description": "short object description",
        "role": "manipulated_object | target_object | tool | container | support"
      }}
    ],
    "background_objects": [
      {{
        "object_id": "stable_snake_case_id",
        "description": "short background object description",
        "role": "background"
      }}
    ],
    "executor_object_map": {{
      "executor_id": ["object_id"]
    }},
    "best_observation_views": {{
      "executor_id": ["view_name"]
    }},
    "scene_summary": "maximum two short sentences"
  }}
}}
"""
