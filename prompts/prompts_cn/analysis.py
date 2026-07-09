"""中文 Analysis 阶段提示词。"""

ANALYSIS_SYSTEM_PROMPT = """
你是机器人操作视频标注流程中的 Analysis 阶段。
只返回一个符合当前 AnalysisStageOutput 契约的 JSON 对象。
优先使用提示词中提供的动态上下文变量，不要在已有 scene 上下文时重新发明执行主体或物体名称。
除非契约字段明确需要，否则不要输出最终时间边界。
"""

ANALYSIS_PROMPT_TEMPLATE = """
初始指令：
{initial_instruction}

视角说明：
{view_layout_description}

动作词表：
{action_vocabulary}

Scene 上下文：
{scene}

任务：
将可见操作按照真实时间顺序拆分为候选动作片段。

严格返回如下 JSON 结构：
{{
  "candidate_segments": [
    {{
      "segment_id": "S001",
      "start_time": null,
      "end_time": null,
      "start_frame": null,
      "end_frame": null,
      "executor": "scene 上下文中的 executor_id",
      "action": "简短动作短语",
      "objects": ["object_id"],
      "evidence": "简短视觉依据",
      "confidence": 0.6
    }}
  ],
  "uncertain_regions": [],
  "analysis_notes": []
}}
"""
