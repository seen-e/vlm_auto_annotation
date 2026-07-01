# =============================================================================
# 动作词表与通用提示词组件
# =============================================================================

# 保持英文规范动作标签，避免破坏后续 action_sequence / guidance 的兼容性。
ACTION_VOCABULARY = [
    "Grasp", "Grab", "Drag", "Pick up", "Place", "Move", "Rotate",
    "Insert", "Push", "Wipe", "Sweep", "Knock", "Release", "Press"
]

ACTION_FINE_GRAINED_GUIDANCE = """
1. Grasp: 说明接触点以及夹爪接近方向（从上方、左侧、右侧、前方、后方）。
2. Grab: 指明被抓取的具体部位以及接近方向。
3. Drag: 描述拖拽方向和大致距离。
4. Pick up: 说明接触点、抓取方向（从上方、左侧、右侧、前方、后方）以及抬起路径。
5. Place: 指明目标放置位置以及物体最终姿态（例如直立、平放）。
6. Move: 明确移动方向和大致位移。
7. Rotate: 说明旋转轴和旋转方向（顺时针/逆时针）。
8. Insert: 描述插入方向和对齐线索。
9. Push: 说明推动接触点和推动方向。
10. Wipe: 描述擦拭的表面区域和扫动方向。
11. Sweep: 描述被扫过的区域和运动方向。
12. Knock: 指明撞击接触点和接近方向。
13. Release: 说明释放位置以及释放后物体姿态（例如直立、平放）。
14. Press: 指明按压接触点、按压方向以及可见的按压深度/力度。
"""

FEW_SHOT_EXAMPLES = """
1.
    "action_sequence": ["Pick up", "Rotate", "Place"],
    "main_object": "ceramic bowl",
    "Fine_Grained": [
        "从右侧远端边缘拿起陶瓷碗。",
        "将碗顺时针旋转两圈。",
        "把碗放到桌面中央。"
    ]
2.
    "action_sequence": ["Grasp", "Lift", "Move", "Stack", "Release"],
    "main_object": "white paper cup",
    "Fine_Grained": [
        "从上方抓住右侧白色纸杯的右上边缘。",
        "将纸杯垂直抬起。",
        "水平向左移动纸杯，使其与另一个纸杯对齐。",
        "将纸杯降低并套入左侧白色纸杯中完成堆叠。",
        "松开夹爪并向上撤回机械臂。"
    ]
"""
