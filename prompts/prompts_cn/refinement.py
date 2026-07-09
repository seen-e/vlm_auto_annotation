"""中文 Refinement 阶段提示词。"""

REFINEMENT_SYSTEM_PROMPT = """
你是机器人操作视频标注流程中的 Refinement 阶段。
只返回一个符合当前 RefinementStageOutput 契约的 JSON 对象。
使用提示词中的 scene 和 analysis 上下文变量，不要添加视频中不可见的动作。
start_time 是 phase 意图或状态变化开始的最早可见时间。
end_time 是目标状态完成并稳定的时间。
"""

REFINEMENT_PROMPT_TEMPLATE = """
初始指令：
{initial_instruction}

视角说明：
{view_layout_description}

Scene 上下文：
{scene}

Analysis 候选片段：
{analysis.candidate_segments}

任务：
将候选动作片段修正为最终带时间边界的动作片段。

严格返回如下 JSON 结构：
{{
  "refined_segments": [
    {{
      "segment_id": "S001",
      "start_time": "MM:SS.ss 或 null",
      "end_time": "MM:SS.ss 或 null",
      "start_frame": null,
      "end_frame": null,
      "executor": "executor_id",
      "action": "简短动作短语",
      "objects": ["object_id"],
      "boundary_reason": "简短边界依据",
      "confidence": 0.6
    }}
  ],
  "changes": [
    {{
      "original_segment_id": "S001",
      "change_type": "keep | split | merge | trim | remove | add",
      "reason": "简短原因"
    }}
  ]
}}
"""
