import unittest

from annotation_pipeline.parsers import parse_analysis_output, parse_refinement_output, parse_scene_output


class TestParsers(unittest.TestCase):
    def test_old_scene_context_maps_to_new_contract(self):
        result = parse_scene_output(
            {
                "sceneContext": {
                    "primary_view": "front",
                    "arms": [{"arm_id": "left", "handled_objects": ["cup"]}],
                    "task_objects": [{"object_id": "cup", "description": "red cup"}],
                }
            },
            video_id="ep001",
        )
        self.assertFalse(result.errors)
        self.assertEqual(result.output.executors[0].executor_id, "left")
        self.assertEqual(result.output.touched_objects[0].object_id, "cup")

    def test_old_analysis_sequence_maps_to_candidate_segments(self):
        scene = parse_scene_output(
            {
                "scene_context": {
                    "primary_view": "front",
                    "executors": [{"executor_id": "left"}],
                    "touched_objects": [{"object_id": "cup"}],
                }
            }
        ).output
        result = parse_analysis_output(
            {"action_sequence": [{"executor": "left", "action": "grasp", "object": "cup"}]},
            scene=scene,
        )
        self.assertEqual(result.output.candidate_segments[0].segment_id, "S001")
        self.assertEqual(result.output.candidate_segments[0].objects, ["cup"])

    def test_refinement_swaps_invalid_time_boundary(self):
        scene = parse_scene_output(
            {
                "scene_context": {
                    "primary_view": "front",
                    "executors": [{"executor_id": "left"}],
                    "touched_objects": [{"object_id": "cup"}],
                }
            }
        ).output
        analysis = parse_analysis_output(
            {"candidate_segments": [{"segment_id": "S001", "executor": "left", "action": "grasp", "objects": ["cup"]}]},
            scene=scene,
        ).output
        result = parse_refinement_output(
            {
                "refined_segments": [
                    {
                        "segment_id": "S001",
                        "executor": "left",
                        "action": "grasp",
                        "objects": ["cup"],
                        "start_time": "00:02.00",
                        "end_time": "00:01.00",
                    }
                ]
            },
            analysis=analysis,
            scene=scene,
        )
        self.assertEqual(result.output.refined_segments[0].start_time, "00:01.00")
        self.assertTrue(result.warnings)

    def test_refinement_action_sequence_with_times_maps_to_segments(self):
        scene = parse_scene_output(
            {
                "scene_context": {
                    "primary_view": "front",
                    "executors": [{"executor_id": "left"}],
                    "touched_objects": [{"object_id": "cup"}],
                }
            }
        ).output
        analysis = parse_analysis_output(
            {"action_sequence": [{"executor": "left", "action": "grasp", "object": "cup"}]},
            scene=scene,
        ).output
        result = parse_refinement_output(
            {
                "action_sequence": [
                    {
                        "executor": "left",
                        "action": "grasp",
                        "object": "cup",
                        "start_time": "00:00.50",
                        "end_time": "00:01.20",
                    }
                ],
                "fine_grained_steps": ["00:00.50-00:01.20 left arm grasps the cup."],
                "refined_instruction": "The left arm grasps the cup.",
            },
            analysis=analysis,
            scene=scene,
        )
        segment = result.output.refined_segments[0]
        self.assertEqual(segment.start_time, "00:00.50")
        self.assertEqual(segment.end_time, "00:01.20")
        self.assertEqual(segment.objects, ["cup"])


if __name__ == "__main__":
    unittest.main()
