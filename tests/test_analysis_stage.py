from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.contracts.scene import SceneStageOutput, ExecutorInfo
from vlm_auto_annotation.core.context import StageContext
from vlm_auto_annotation.stages.analysis.stage import AnalysisStage


class FakeClient:
    def __init__(self, response: str) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.response = response

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.response))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class AnalysisStageTest(unittest.TestCase):
    def test_analysis_requires_scene_and_outputs_candidates(self):
        response = '{"action_steps":[{"step_id":"A001","executor":"left","action":"grasp","object":"cup","confidence":0.9}]}'
        stage = AnalysisStage({"model": "fake", "max_tokens": 64}, client=FakeClient(response))
        stage.build_media = lambda context: ([], {"selected_views": ["front"], "source_type": "single_view"})
        context = StageContext(video_path="demo.mp4", video_id="demo", prompt_language="en")
        context.stage_contracts["scene"] = SceneStageOutput(primary_view="front", executors=[ExecutorInfo(executor_id="left")])

        result = stage.run(context)

        self.assertTrue(result.success)
        self.assertEqual(context.stage_contracts["analysis"].candidate_segments[0].action, "grasp")


if __name__ == "__main__":
    unittest.main()
