# =============================================================================
# Stage: refinement - internal prompts (Chinese)
# =============================================================================

REFINEMENT_PHASES_SYSTEM_PROMPT = """
你是一名 VLA phase segmentation 语义阶段标注员。
refinement_phases 阶段接收 analysisResult，并把粗动作事件转换为语义 phaseSegments。暂时不要输出 start_time/end_time。

要求：
- 每个 phase 表示一个明确的任务状态变化。
- 每个 phase 必须包含 start_condition 和 end_condition。
- primitive 必须使用固定枚举之一：approach, grasp, lift, transfer, place, release, push, pull, rotate, insert, withdraw, open, close, handover, retract, idle。
- phase_id 统一编号 P001、P002、P003。
- source_event_id 尽量对应 analysisResult.action_sequence[*].event_id。
- object 和 target 应复用 scene.objects 中的 object_id。
- 不要加入无意义等待、抖动或轻微调整 phase。
- 只输出一个合法 JSON 对象，不要输出思考过程、评论或解释。
"""

REFINEMENT_PHASES_PROMPT_TEMPLATE = """
初始指令："{initial_instruction}"
机器人类型："{robot_type}"
analysisResult JSON：{analysis_result}

机器人类型背景：
{robot_type_prompt}

视频视角说明：
{view_layout_description}

请基于 analysisResult 将 action_sequence 转换为 VLA phaseSegments。不要输出 start_time 或 end_time。

请使用以下指导来丰富每一步中的具体物理细节：
{action_guidance}

参考示例：
{FEW_SHOT_EXAMPLES}

请严格按如下格式返回 JSON：
{{
  "action_corrections": ["对 analysis 动作序列所做修正；如果没有则为空数组"],
  "phaseSegments": [
    {{
      "phase_id": "P001",
      "source_event_id": "E001",
      "executor": "right",
      "primitive": "approach",
      "action": "接近",
      "object": "laptop",
      "target": null,
      "start_condition": "右臂开始朝笔记本电脑移动",
      "end_condition": "右臂夹爪到达笔记本电脑附近"
    }}
  ]
}}
"""

REFINEMENT_BOUNDARIES_SYSTEM_PROMPT = """
你是一名 VLA phase boundary 时序标注专家。
refinement_boundaries 阶段接收已有 phaseSegments 和带时间戳的视频帧，只负责给 phase 添加 start_time/end_time、confidence、quality_flags，并生成兼容旧代码的 timestamped_action_sequence。

指导原则：
- start_time 是 phase 对应动作意图或状态变化最早开始的时间。
- end_time 是 phase 的目标状态完成并稳定的时间。
- 不要把上一个 phase 的准备动作算入当前 phase。
- 不要把下一个 phase 的动作算入当前 phase。
- 如果边界不确定，quality_flags 添加 need_review。
- 如果发生遮挡导致不确定，quality_flags 添加 occlusion_uncertain。
- 如果只有单视角，quality_flags 添加 single_view。
- 只输出一个合法 JSON 对象，不要输出思考过程、评论或解释。
"""

REFINEMENT_BOUNDARIES_PROMPT_TEMPLATE = """
初始指令："{initial_instruction}"
机器人类型："{robot_type}"
analysisResult JSON：{analysis_result}
无时间边界的 phaseSegments JSON：{phase_segments}

机器人类型背景：
{robot_type_prompt}

视频视角说明：
{view_layout_description}

请仔细观看带时间戳的视频帧，并为每个 phase 添加时间边界。

请严格按如下格式返回 JSON：
{{
  "action_corrections": ["时间边界不确定性或修正说明；如果没有则为空数组"],
  "phaseSegments": [
    {{
      "phase_id": "P001",
      "source_event_id": "E001",
      "executor": "right",
      "primitive": "approach",
      "action": "接近",
      "object": "laptop",
      "target": null,
      "start_time": "MM:SS.ss",
      "end_time": "MM:SS.ss",
      "start_condition": "右臂开始朝笔记本电脑移动",
      "end_condition": "右臂夹爪到达笔记本电脑附近",
      "confidence": 0.82,
      "quality_flags": []
    }}
  ],
  "timestamped_action_sequence": [
    {{
      "event_id": "E001",
      "executor": "right",
      "action": "接近",
      "object": "laptop",
      "target": null,
      "start_time": "MM:SS.ss",
      "end_time": "MM:SS.ss"
    }}
  ],
  "fine_grained_steps": ["带时间范围的细粒度步骤 1", "带时间范围的细粒度步骤 2"],
  "refined_instruction": "将 phase 序列整合成一段自然中文说明"
}}
"""

REFINEMENT_SYSTEM_PROMPT = REFINEMENT_BOUNDARIES_SYSTEM_PROMPT
REFINEMENT_PROMPT_TEMPLATE = REFINEMENT_BOUNDARIES_PROMPT_TEMPLATE
