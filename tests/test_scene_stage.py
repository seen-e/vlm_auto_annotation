from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.core.context import StageContext
from vlm_auto_annotation.stages.scene.stage import SceneStage


class FakeClient:
    def __init__(self, response: str) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.response = response

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.response))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class SceneStageTest(unittest.TestCase):
    def test_scene_stage_builds_contract(self):
        stage = SceneStage({"model": "fake", "max_tokens": 64}, client=FakeClient('{"primary_view":"front","executors":[{"executor_id":"left","description":"left arm"}],"touched_objects":[{"object_id":"cup","description":"cup"}],"scene_summary":"one arm moves cup"}'))
        stage.build_media = lambda context: ([], {"selected_views": ["front"], "source_type": "single_view"})
        context = StageContext(video_path="demo.mp4", video_id="demo", prompt_language="en", robot_type="single_arm")

        result = stage.run(context)

        self.assertTrue(result.success)
        self.assertEqual(context.stage_contracts["scene"].primary_view, "front")
        self.assertEqual(context.stage_contracts["scene"].executors[0].executor_id, "left")


if __name__ == "__main__":
    unittest.main()
