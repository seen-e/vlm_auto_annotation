from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.contracts.analysis import AnalysisStageOutput, SegmentCandidate
from vlm_auto_annotation.core.context import StageContext
from vlm_auto_annotation.utils.stage_exporter import StageExporter


class StageExporterTest(unittest.TestCase):
    def test_nested_target_preserves_raw_dict_or_list(self):
        context = StageContext(video_path="demo.mp4", experiment_name="exp")
        contract = AnalysisStageOutput(
            candidate_segments=[
                SegmentCandidate(segment_id="S001", executor="left", action="grasp", objects=["cup"])
            ]
        )
        exporter = StageExporter(
            [
                {
                    "source_stage": "analysis",
                    "source_path": "candidate_segments",
                    "target_name": "analysis.action",
                    "default": [],
                    "format": "compact_json",
                    "source_kind": "contract",
                    "enabled": True,
                }
            ],
            experiment_name="exp",
        )

        exporter.export_stage(context=context, stage_name="analysis", parsed_output={}, contract=contract)

        self.assertIsInstance(context.exports["analysis"]["action"], list)
        self.assertEqual(context.exports["analysis"]["action"][0]["action"], "grasp")
        self.assertEqual(context.formatted_exports["analysis"]["action"], '[{"segment_id":"S001","start_time":null,"end_time":null,"start_frame":null,"end_frame":null,"executor":"left","action":"grasp","objects":["cup"],"evidence":"","confidence":0.6}]')

    def test_missing_field_uses_nested_default(self):
        context = StageContext(video_path="demo.mp4")
        exporter = StageExporter(
            [
                {
                    "source_stage": "scene",
                    "source_path": "missing.path",
                    "target_name": "scene.objects",
                    "default": [],
                    "format": "json",
                    "enabled": True,
                }
            ]
        )

        warnings = exporter.export_stage(context=context, stage_name="scene", parsed_output={}, contract={})

        self.assertEqual(context.exports["scene"]["objects"], [])
        self.assertTrue(warnings)
        self.assertTrue(context.export_status["scene.objects"]["used_default"])


if __name__ == "__main__":
    unittest.main()
