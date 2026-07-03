# =============================================================================
# Action vocabulary and shared prompt components
# =============================================================================

# English canonical action labels for English prompt mode.
ACTION_VOCABULARY = [
    "approach", "grasp", "clamp", "drag", "pick up", "place", "move", "rotate",
    "insert", "pull out", "push", "pull", "wipe", "sweep", "knock", "release",
    "press", "open", "close", "navigate", "align", "fix", "support", "handover",
]

ACTION_FINE_GRAINED_GUIDANCE = """
1. approach: Describe the target object or position being approached and the approach direction.
2. grasp: Describe the contact point, gripper/hand approach direction, and the grasped part.
3. clamp: Describe the object being clamped, the clamp location, gripper closing direction, and whether the hold is stable.
4. drag: Describe the drag direction, start point, end point, and approximate distance.
5. pick up: Describe the contact point, grasp direction, and lifting path away from the support surface.
6. place: Specify the target placement location and the final object pose, such as upright, flat, or near an edge.
7. move: Specify the moved object, movement direction, start/end positions, and approximate displacement.
8. rotate: Describe the rotated object, rotation axis, and direction, such as clockwise or counterclockwise.
9. insert: Describe the inserted object, insertion direction, target hole/container, and alignment cues.
10. pull out: Describe the object being pulled out, pull-out direction, and state after leaving the target structure.
11. push: Describe the pushing contact point, pushing direction, and displacement of the pushed object.
12. pull: Describe the pulling contact point, pulling direction, and displacement of the pulled object.
13. wipe: Describe the wiped surface area, contact mode, and sweeping direction.
14. sweep: Describe the swept area, sweeping direction, and moved objects or debris.
15. knock: Describe the impact contact point, approach direction, and object state change after impact.
16. release: Describe the release location and object pose after release, such as upright, flat, or falling from suspension.
17. press: Describe the pressing contact point, pressing direction, and visible pressing depth/force.
18. open: Describe the object being opened, contact point, opening direction, and final open state.
19. close: Describe the object being closed, contact point, closing direction, and final closed state.
20. navigate: Describe the target position approached or reached by the mobile base.
21. align: Describe the two objects being aligned, alignment direction, and final relative position.
22. fix: Describe the fixed object, fixing contact point, and purpose, such as preventing sliding or assisting another arm.
23. support: Describe the supported object, support location, and how it coordinates with another executor.
24. handover: Describe the giver, receiver, handed object, handover position, and change of object control.
"""

FEW_SHOT_EXAMPLES = """
1.
    "action_sequence": [
        {"executor": "single", "action": "pick up", "object": "ceramic bowl"},
        {"executor": "single", "action": "rotate", "object": "ceramic bowl"},
        {"executor": "single", "action": "place", "object": "ceramic bowl"}
    ],
    "main_object": "ceramic bowl",
    "Fine_Grained": [
        "Pick up the ceramic bowl from its right far edge.",
        "Rotate the bowl clockwise twice.",
        "Place the bowl in the center of the table."
    ]
2.
    "action_sequence": [
        {"executor": "single", "action": "grasp", "object": "white paper cup"},
        {"executor": "single", "action": "pick up", "object": "white paper cup"},
        {"executor": "single", "action": "move", "object": "white paper cup"},
        {"executor": "single", "action": "place", "object": "white paper cup"},
        {"executor": "single", "action": "release", "object": "white paper cup"}
    ],
    "main_object": "white paper cup",
    "Fine_Grained": [
        "Grasp the upper right rim of the white paper cup from above.",
        "Lift the paper cup vertically.",
        "Move the paper cup horizontally to the left until it aligns with the other cup.",
        "Lower the paper cup and place it into the left white paper cup to complete stacking.",
        "Release the gripper and retract the robot arm upward."
    ]
"""
