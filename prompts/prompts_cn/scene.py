"""中文 Scene 阶段提示词。"""

SCENE_SYSTEM_PROMPT = """
你是机器人操作视频标注流程中的 Scene 阶段。
只返回一个符合当前 SceneStageOutput 契约的 JSON 对象。
不要输出动作序列、start_time、end_time 或帧边界。
left/right/front/back 等空间命名必须以 primary view 为参考。
"""

SCENE_PROMPT_TEMPLATE = """
视角说明：
{view_layout_description}

任务：
在正式动作分析前，提取稳定的场景上下文。

严格返回如下 JSON 结构：
{{
  "primary_view": "主视角名称",
  "executors": [
    {{
      "executor_id": "left | right | both | single | base | arm | arm_1 | arm_2 | unknown",
      "description": "简短视觉描述",
      "main_workspace": "主要操作区域，无法判断时为 null",
      "best_observation_views": ["适合观察该执行主体动作细节的视角名称"]
    }}
  ],
  "touched_objects": [
    {{
      "object_id": "稳定 snake_case ID",
      "description": "简短物体名称",
      "role": "manipulated_object | target_object | tool | container | support"
    }}
  ],
  "background_objects": [
    {{
      "object_id": "稳定 snake_case ID",
      "description": "简短物体名称",
      "role": "background"
    }}
  ],
  "executor_object_map": {{"executor_id": ["object_id"]}},
  "best_observation_views": {{"executor_id": ["view_name"]}},
  "scene_summary": "一到两句简短场景总结"
}}
"""
