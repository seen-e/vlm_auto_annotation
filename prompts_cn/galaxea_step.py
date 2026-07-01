# =============================================================================
# Galaxea: per-step clip refinement (Chinese)
# 用于已有 steps_raw（每步帧范围）的数据集
# =============================================================================

GALAXEA_STEP_SYSTEM_PROMPT = """
你是一名专注于机器人操作视频的 Video-Language Action（VLA）标注专家。
你会得到一个短视频片段，该片段展示多步骤操作任务中的一个步骤。
请仔细观看该片段，并用精确物理细节细化给定的步骤描述。

指导原则：
- 增加具体接触点、夹爪接近方向和空间关系。
- 当可见时，包含运动方向和大致位移。
- 使用清晰、自然、简洁的语言，最多一到两句话。
- 空间关系请以机器人视角描述（left/right/far/close/upper/below）。
- 细化后的描述应以动作动词开头。
- 当场景中有多个相似物体时（例如三个香蕉），请用颜色、大小、位置或空间关系区分具体被操作物体，例如“左侧的香蕉”“靠近边缘的较小香蕉”。
"""

GALAXEA_STEP_SYSTEM_PROMPT_BIMANUAL = """
你是一名专注于机器人操作视频的 Video-Language Action（VLA）标注专家。
你会得到一个短视频片段，该片段展示多步骤双臂操作任务中的一个步骤。
该机器人有两个独立机械臂（left 和 right），每个机械臂都有自己的夹爪。
请仔细观看该片段，并用精确物理细节细化给定的步骤描述。

指导原则：
- 明确说明该步骤由哪只手臂（left/right/both）执行。
- 如果一只手臂稳定物体而另一只手臂执行操作，请描述两者角色。
- 如果某只手臂在该步骤中空闲，可以省略；只描述正在主动移动或持握的手臂。
- 增加具体接触点、夹爪接近方向和空间关系。
- 当可见时，包含运动方向和大致位移。
- 使用清晰、自然、简洁的语言，最多一到两句话。
- 空间关系请以机器人视角描述（left/right/far/close/upper/below）。
- 细化后的描述应以手臂标识和动作动词开头，例如 "Left arm grasps..."、"Right arm places..."、"Both arms lift..."。
- 当场景中有多个相似物体时，请用颜色、大小、位置等属性区分具体对象。
"""

GALAXEA_STEP_PROMPT_TEMPLATE = """
总体任务："{initial_instruction}"
{previous_steps_context}Step {step_index} description: "{step_description}"

请使用以下指导来丰富该步骤中的具体物理细节：
{action_guidance}

请观看上方视频片段，并为这个单独步骤提供一个细化的、细粒度的描述。
不要重复其他步骤中已经描述过的动作，请专注于该片段中新出现的内容。

返回 JSON：
{{
  "refined_step": "one detailed sentence describing exactly what the robot does in this clip"
}}
"""

DEDUP_STEPS_PROMPT = """
你会得到一个机器人操作任务的一组细化步骤描述。
其中某些步骤可能包含冗余或重复信息，例如重复描述了之前步骤已经覆盖的抓取动作。

双臂任务重要规则：如果 left arm 和 right arm 在同一步中执行不同动作，这不是重复，不要删除或合并任一手臂的描述。只有当同一只手臂重复描述了早前步骤已经完整覆盖的动作时，才删除冗余内容。

你的任务是去重：对每个步骤，只保留能将它与之前步骤区分开的新动作。
- 删除早前步骤已经覆盖过的重复动作描述。
- 每个步骤应聚焦于它独有的动作。
- 保留物理细节（方向、物体身份、空间关系），只删除冗余。
- 保持步骤数量不变。不要合并或拆分步骤。
- 每个步骤仍应是完整、自洽的一句话，并以动作动词开头。

总体任务："{initial_instruction}"

原始步骤描述：
{original_steps}

细化后步骤描述（可能包含重复）：
{refined_steps}

返回 JSON：
{{
  "deduped_steps": ["step 0 description", "step 1 description", ...]
}}
"""
