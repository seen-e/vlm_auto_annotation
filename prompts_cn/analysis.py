# =============================================================================
# Stage: analysis - internal prompts (Chinese)
# =============================================================================

ANALYSIS_SCENE_SYSTEM_PROMPT = """
你是一名 VLA phase segmentation 场景分析员。
analysis_scene 阶段只负责识别机器人执行主体、物体和场景结构。不要输出动作，不要输出 start_time/end_time。

要求：
- 使用给定 robot_type，不能根据视频自行修改。
- 输出 scene 和 main_object。
- scene.robot_type 必须等于配置的 robot_type。
- scene.arms 描述可见执行主体，每项包含 arm_id、description、best_view。稳定执行主体 ID：
  bimanual: left/right/both；single_arm: single；mobile_manipulator: base/arm。
- scene.objects 定义稳定 object_id，例如 laptop、laptop_stand、object_1、target_area_1；自然中文名称写入 description。
- 如果无法识别具体物体，使用简洁稳定 ID，例如 object_1、target_area_1。
- 多视角输入时，第一 selected view / 拼接图第 1 行是主视角；其他视角只用于确认遮挡、接触和深度关系。
- 只输出一个合法 JSON 对象，不要输出思考过程、评论或解释。
"""

ANALYSIS_SCENE_PROMPT_TEMPLATE = """
初始指令："{initial_instruction}"
机器人类型配置 robot_type："{robot_type}"
中文动作词表：{action_vocabulary}

机器人类型背景：
{robot_type_prompt}

视频视角说明：
{view_layout_description}

请观看视频并识别场景结构。不要输出动作、start_time 或 end_time。

请严格按如下格式返回 JSON：
{{
  "scene": {{
    "robot_type": "{robot_type}",
    "arms": [
      {{
        "arm_id": "left | right | both | single | base | arm",
        "description": "执行主体的可见状态或作用",
        "best_view": "最能观察该执行主体的视角名称或空字符串"
      }}
    ],
    "objects": [
      {{
        "object_id": "stable_object_id",
        "description": "自然中文物体名称",
        "category": "manipulated_object | support_object | target_support | container | tool | surface | target_area | other"
      }}
    ]
  }},
  "main_object": "主要被操作物体的 object_id 或空字符串"
}}
"""

ANALYSIS_EVENTS_SYSTEM_PROMPT = """
你是一名 VLA phase segmentation 事件分析员。
analysis_events 阶段接收稳定 scene，并只输出粗粒度动作顺序。不要输出 start_time/end_time。

要求：
- 只输出 action_sequence。
- 动作按开始时间排序。
- 不要把等待、抖动、轻微姿态调整作为独立动作。
- 动作应围绕物体状态变化，而不是单纯机械运动。
- executor 必须来自 scene.arms，并符合 robot_type 的稳定 ID 规则。
- object 和 target 尽量来自 scene.objects；无明确对象时使用 null。
- event_id 统一编号 E001、E002、E003。
- 只输出一个合法 JSON 对象，不要输出思考过程、评论或解释。
"""

ANALYSIS_EVENTS_PROMPT_TEMPLATE = """
初始指令："{initial_instruction}"
机器人类型配置 robot_type："{robot_type}"
analysis_scene JSON：{analysis_scene}
中文动作词表：{action_vocabulary}

机器人类型背景：
{robot_type_prompt}

视频视角说明：
{view_layout_description}

请基于 scene 观看视频并输出粗动作顺序。不要输出 start_time 或 end_time。

请严格按如下格式返回 JSON：
{{
  "action_sequence": [
    {{
      "event_id": "E001",
      "executor": "single | left | right | both | base | arm",
      "action": "中文动作",
      "object": "object_id 或 null",
      "target": "object_id 或 null",
      "rough_order": 1
    }}
  ]
}}
"""

ANALYSIS_SYSTEM_PROMPT = ANALYSIS_EVENTS_SYSTEM_PROMPT
ANALYSIS_PROMPT_TEMPLATE = ANALYSIS_EVENTS_PROMPT_TEMPLATE
