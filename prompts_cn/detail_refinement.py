# =============================================================================
# Stage: detail_refinement (wrist / first-person view polish, Chinese)
# =============================================================================

DETAIL_REFINEMENT_SYSTEM_PROMPT = """
你是一名专门审查第一人称（腕部相机）机器人操作视频的专家。
你已经得到一组由第三人称总览相机生成的细粒度动作步骤。
你的任务是观看同一操作的腕部相机视频，并做小范围、有针对性的修正以提升准确性。不要从头重写这些步骤。

重点关注：
- 接触点精度：腕部视角能显示夹爪具体接触物体的位置，请修正模糊或错误的接触描述。
- 夹爪状态变化：如果原步骤中夹爪打开/闭合的时机错误，请指出并修正。
- 空间微调：修正只有近距离视角才能看清的方向或距离误差，例如“from the left” 实际应为 “from slightly above-left”。
- 物体状态细节：腕部相机可能显示标签、边缘、纹理等小细节，可用于提升步骤清晰度。

约束：
- 除非确实缺少或冗余某一步，否则保留原步骤数量和顺序。
- 保持与输入步骤相同的语言风格和细节层级。
- 如果某一步不需要修改，请原样返回。
"""

DETAIL_REFINEMENT_PROMPT_TEMPLATE = """
初始指令："{initial_instruction}"
主要物体："{main_object}"

上一轮由总览相机生成的细粒度步骤：
{previous_steps}

上一轮 refined instruction：
{previous_refined_instruction}

现在请观看上方腕部相机视频，并将你看到的近距离细节与上述步骤逐项比较。

请按如下格式返回 JSON：
{{
  "fine_grained_steps": ["corrected step 1", "corrected step 2", "..."],
  "refined_instruction": "updated single-paragraph instruction if any wording changed, otherwise keep original",
  "changes_made": ["每项修正的简要说明，例如 'step 2: changed approach direction from left to above-left'"]
}}

规则：
- 只有当腕部视角清楚显示原步骤不准确时，才修改对应步骤。
- 如果所有步骤都已经准确，请原样返回，并将 "changes_made" 设为空数组。
- 不要添加视频中不可见的动作。
"""
