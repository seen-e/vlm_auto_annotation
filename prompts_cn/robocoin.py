# =============================================================================
# RoboCOIN-specific prompt variants (Chinese)
# 这些 prompt 扩展通用双臂 prompt，加入：
#   1. Fold / Zip 动作词表和细节指导
#   2. Static / End 步骤处理
#   3. 双臂协作 few-shot 示例
#   4. 更强的 no-repeat 要求
# 不要用于其他数据集。
# =============================================================================

from .vocabulary import ACTION_FINE_GRAINED_GUIDANCE

ACTION_FINE_GRAINED_GUIDANCE_ROBOCOIN = ACTION_FINE_GRAINED_GUIDANCE + """
15. Fold: 描述折叠轴（例如沿长边、沿中心线）、折叠方向（向内/向外/朝向机器人）以及大致结果（例如“对折”“折成三折”）。
16. Zip: 指明拉链起点、拉动方向（向上/向下/向左/向右）以及移动距离或终点（例如“从底部止点拉到拉链顶部”）。
"""

GALAXEA_STEP_SYSTEM_PROMPT_BIMANUAL_ROBOCOIN = """
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

特殊步骤类型请按如下方式处理：
- "Static" / holding steps：手臂没有明显净运动。描述哪只手臂保持哪个物体，以及它保持的位置/姿态。不要编造不可见运动。例如："Left arm holds the open bag upright near the table edge, keeping the opening stable."
- "End" / retract steps：手臂释放物体并撤回到中立/休息位置。描述释放动作和撤回方向。例如："Right arm releases the cloth from its gripper and retracts upward to resting position."
- 非常短且几乎没有可见运动的片段：只描述清楚可见的内容；不要幻觉补充不可见细节。

Few-shot examples:
[Static step]  "Left arm holds the unzipped storage bag open by pressing both gripper fingers against the rim, keeping the opening stable while the right arm loads items inside."
[End step]     "Right arm releases the folded cloth and retracts upward and backward away from the basket to its resting position above the workspace."
[Single-arm]   "Left arm grasps the hamburger patty from above at its center using a top-down grip and lifts it vertically off the tray."
[Bimanual]     "Both arms simultaneously grasp opposite ends of the shirt - left arm at the left sleeve cuff and right arm at the right sleeve cuff - and stretch it taut horizontally before beginning the fold."
"""

GALAXEA_STEP_PROMPT_TEMPLATE_ROBOCOIN = (
    '总体任务："{initial_instruction}"\n'
    '{previous_steps_context}'
    'Step {step_index} description: "{step_description}"\n\n'
    '请使用以下指导来丰富该步骤中的具体物理细节：\n'
    + ACTION_FINE_GRAINED_GUIDANCE_ROBOCOIN +
    '\n请观看上方视频片段，并为这个单独步骤提供一个细化的、细粒度的描述。\n'
    '**重要**：不要重新描述 previous steps 中已经列出的任何动作，'
    '只关注该片段中新出现且有区分度的内容。\n\n'
    '返回 JSON：\n'
    '{{\n'
    '  "refined_step": "one detailed sentence describing exactly what the robot does in this clip"\n'
    '}}\n'
)
