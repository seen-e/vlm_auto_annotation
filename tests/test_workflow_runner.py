from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.app.run_workflow import run_workflow
from vlm_auto_annotation.core.stage import BaseStage


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        response = self.responses.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class WorkflowRunnerTest(unittest.TestCase):
    def test_workflow_runs_all_stages(self):
        old_build_media = BaseStage.build_media
        BaseStage.build_media = lambda self, context: ([], {"selected_views": ["front"], "source_type": "single_view"})
        try:
            client = FakeClient(
                [
                    '{"primary_view":"front","operation_units":[{"unit_id":"left","unit_type":"arm","is_active":true}],"manipulated_objects":[{"object_id":"cup","description":"cup"}],"video_summary":"one arm moves cup"}',
                    '{"action_steps":[{"step_id":"A001","executor":"left","action":"grasp","object":"cup","confidence":0.9}]}',
                    '{"refined_segments":[{"segment_id":"S001","start_time":"00:00.00","end_time":"00:01.00","executor":"left","action":"grasp","objects":["cup"],"confidence":0.8}]}',
                ]
            )
            result = run_workflow(
                client=client,
                video_path="demo.mp4",
                instruction="pick up the cup",
                video_id="demo",
                prompt_language="en",
                config_overrides={"artifacts": {"enabled": False}},
            )
        finally:
            BaseStage.build_media = old_build_media

        self.assertTrue(result.success)
        self.assertEqual(set(result.stages), {"scene", "analysis", "refinement"})
        self.assertEqual(result.output["segments"][0]["action"], "grasp")


if __name__ == "__main__":
    unittest.main()
