import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import vlm_auto_annotation.flows.flow_analysis_refinement as flow_module
from vlm_auto_annotation.flows import run_vla_phase_annotation


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Usage:
    prompt_tokens = 1
    completion_tokens = 1
    total_tokens = 2


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class _Completions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        payloads = [
            {
                "scene_context": {
                    "primary_view": "front",
                    "executors": [{"executor_id": "left", "description": "left arm"}],
                    "touched_objects": [{"object_id": "cup", "description": "cup"}],
                    "scene_summary": "left arm manipulates a cup",
                }
            },
            {
                "candidate_segments": [
                    {
                        "segment_id": "S001",
                        "executor": "left",
                        "action": "grasp",
                        "objects": ["cup"],
                        "confidence": 0.9,
                    }
                ]
            },
            {
                "refined_segments": [
                    {
                        "segment_id": "S001",
                        "executor": "left",
                        "action": "grasp",
                        "objects": ["cup"],
                        "start_time": "00:00.00",
                        "end_time": "00:01.00",
                        "confidence": 0.9,
                    }
                ],
                "changes": [{"original_segment_id": "S001", "change_type": "keep", "reason": ""}],
            },
        ]
        return _Response(json.dumps(payloads[self.calls - 1]))


class _Client:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _Completions()})()


class TestStageContracts(unittest.TestCase):
    def test_flow_returns_compact_output(self):
        original_loader = flow_module.load_video_or_views_as_image_parts

        def fake_loader(*args, **kwargs):
            return (
                [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AA=="}}],
                {"selected_views": ["front"], "input_mode": "single_view", "sampled_frames": 1},
            )

        flow_module.load_video_or_views_as_image_parts = fake_loader
        try:
            result = run_vla_phase_annotation(_Client(), "x.mp4", "grasp cup", prompt_language="en", video_id="ep001")
        finally:
            flow_module.load_video_or_views_as_image_parts = original_loader

        data = result.output
        self.assertIn("scene_context", data)
        self.assertIn("candidate_segments", data)
        self.assertIn("refined_segments", data)
        self.assertNotIn("fineGrainedSteps", data)
        self.assertEqual(data["action_sequence"][0]["objects"], ["cup"])


if __name__ == "__main__":
    unittest.main()
