from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.contracts.analysis import AnalysisStageOutput, SegmentCandidate
from vlm_auto_annotation.contracts.scene import SceneStageOutput, ExecutorInfo
from vlm_auto_annotation.core.context import StageContext
from vlm_auto_annotation.stages.refinement.stage import RefinementStage


class FakeClient:
    def __init__(self, response: str) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.response = response

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.response))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class RefinementStageTest(unittest.TestCase):
    def test_refinement_outputs_timed_segments(self):
        response = '{"refined_segments":[{"segment_id":"S001","start_time":"00:00.00","end_time":"00:01.00","executor":"left","action":"grasp","objects":["cup"],"confidence":0.8}]}'
        stage = RefinementStage({"model": "fake", "max_tokens": 64}, client=FakeClient(response))
        stage.build_media = lambda context: ([], {"selected_views": ["front"], "source_type": "single_view"})
        context = StageContext(video_path="demo.mp4", video_id="demo", prompt_language="en")
        context.stage_contracts["scene"] = SceneStageOutput(primary_view="front", executors=[ExecutorInfo(executor_id="left")])
        context.stage_contracts["analysis"] = AnalysisStageOutput(
            candidate_segments=[SegmentCandidate(segment_id="S001", executor="left", action="grasp")]
        )

        result = stage.run(context)

        self.assertTrue(result.success)
        self.assertEqual(context.stage_contracts["refinement"].refined_segments[0].start_time, "00:00.00")


if __name__ == "__main__":
    unittest.main()
