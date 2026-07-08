SINGLE_ARM_ROBOT_PROMPT = """
The robot is a fixed-base single-arm manipulation robot. It consists of one robot arm and one gripper or dexterous hand, while the base remains stationary. All manipulation is performed by the arm.
The robot can approach targets, adjust pose, grasp, lift, transport, place, push, pull, rotate, insert, pull out, open, close, and release objects. Complex tasks are usually composed of multiple consecutive primitive operations.
When analyzing a video, focus on the robot's task intent, object interaction process, contact events, and object state changes, rather than low-level joint trajectories or tiny end-effector motions.
For action_sequence, use "single" as the executor. The action field should record the high-level action performed by the arm in chronological order. The object field should record the direct target of the action, such as the object being grasped, moved, placed, or approached; use an empty string "" if there is no clear object.
"""


BIMANUAL_ROBOT_PROMPT = """
The robot is a fixed-base bimanual manipulation robot with left and right arms. The two arms can operate independently or cooperate on the same task.
The robot can perform bimanual approach, synchronized grasping, two-hand carrying, object handover, object fixing, folding, assembly, opening/closing containers, and other coordinated manipulation tasks. Many tasks require the two arms to divide roles and cooperate toward a shared goal.
When analyzing a video, treat the two arms as a coordinated system. Focus on the collaboration between the arms, object handover, contact events, object state changes, and task goal changes, rather than separately describing low-level arm trajectories.
For action_sequence, use "left", "right", or "both" as the executor. If the two arms perform different actions in the same time span, output separate records in chronological order. If both arms synchronously perform the same action, use "both". The action field records the high-level action for that executor. The object field records the direct target or destination of the action; use an empty string "" if there is no clear object.
"""


MOBILE_MANIPULATOR_PROMPT = """
The robot is a mobile manipulator composed of a mobile base and one or more robot arms. The full task often contains both navigation and manipulation phases.
The robot can navigate, localize, approach targets, grasp, carry, transport, place, push, pull, open/close doors, open/close drawers, insert, and retrieve objects. It can move between different locations to complete long-horizon manipulation tasks.
When analyzing a video, understand the behavior as a continuous process combining mobility and manipulation. Distinguish the navigation phase from the manipulation phase, and focus on when object interaction begins, how the operation goal is completed, how object states change, and how task phases switch.
For action_sequence, use "base" as the executor for mobile-base navigation or approach phases, and "arm" as the executor for manipulation phases. The action field records high-level actions such as navigate, approach, grasp, carry, and place in chronological order. For navigation actions, object should be the target position or target area; for manipulation actions, object should be the manipulated object. Use an empty string "" if there is no clear object.
"""


ROBOT_TYPE_PROMPTS = {
    "single_arm": SINGLE_ARM_ROBOT_PROMPT,
    "bimanual": BIMANUAL_ROBOT_PROMPT,
    "mobile_manipulator": MOBILE_MANIPULATOR_PROMPT,
}


def get_robot_type_prompt(robot_type: str) -> str:
    prompt = ROBOT_TYPE_PROMPTS.get(robot_type)
    if prompt:
        return prompt.strip()
    return (
        'The current robot_type is "unknown". Do not guess the robot category; annotate only visible actions. '
        'Use "unknown" as the executor, record high-level visible actions in chronological order, and set object '
        'to the clear target object or an empty string "".'
    )
