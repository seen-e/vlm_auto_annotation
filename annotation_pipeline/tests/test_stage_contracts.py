import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import vlm_auto_annotation.flows.flow_analysis_refinement as flow_module
from vlm_auto_annotation.flows import run_vla_phase_annotation
from vlm_auto_annotation.utils.video_utils import save_processed_media


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


def _fake_loader(*args, **kwargs):
    return (
        [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AA=="}}],
        {
            "input_mode": kwargs.get("input_mode", "image_sequence"),
            "source_type": "single_view",
            "selected_views": ["front"],
            "merge_view_names": ["front"],
            "sampled_frames": 1,
            "sampled_frame_count": 1,
            "media_part_count": 1,
        },
    )


def _run_flow(**extra_kwargs):
    """Run the flow with the fake loader, returning the result."""
    original_loader = flow_module.load_video_or_views_as_media_parts
    flow_module.load_video_or_views_as_media_parts = _fake_loader
    try:
        return run_vla_phase_annotation(
            _Client(),
            "x.mp4",
            "grasp cup",
            prompt_language="en",
            video_id="ep001",
            **extra_kwargs,
        )
    finally:
        flow_module.load_video_or_views_as_media_parts = original_loader


class TestSceneResult(unittest.TestCase):
    def test_scene_result_for_analysis_is_compact(self):
        scene_result = flow_module._scene_result_for_analysis(
            {
                "primary_view": "camera_front",
                "spatial_reference_rule": "left/right use camera_front",
                "operation_units": [{"unit_id": "left"}],
                "manipulated_objects": [{"object_id": "cup", "description": "cup"}],
                "video_summary": "The video shows one robot arm, and the moved object is a cup.",
            }
        )
        self.assertEqual(
            sorted(scene_result),
            ["manipulated_objects", "operation_units", "primary_view", "spatial_reference_rule", "video_summary"],
        )
        self.assertEqual(scene_result["primary_view"], "camera_front")
        self.assertEqual(scene_result["operation_units"][0]["unit_id"], "left")
        self.assertEqual(scene_result["manipulated_objects"][0]["description"], "cup")


class TestLightweightOutput(unittest.TestCase):
    """Verify the default v2 lightweight output structure."""

    def test_default_output_contains_core_fields(self):
        result = _run_flow()
        data = result.output

        self.assertIn("schema_version", data)
        self.assertEqual(data["schema_version"], "v2")
        self.assertIn("video_id", data)
        self.assertEqual(data["video_id"], "ep001")
        self.assertIn("flow_name", data)
        self.assertIn("task", data)
        self.assertIn("initial_instruction", data["task"])
        self.assertIn("refined_instruction", data["task"])
        self.assertIn("summary", data["task"])
        self.assertIn("scene", data)
        self.assertIn("primary_view", data["scene"])
        self.assertIn("executors", data["scene"])
        self.assertIn("touched_objects", data["scene"])
        self.assertIn("segments", data)
        self.assertIn("metadata", data)
        self.assertIn("model", data["metadata"])
        self.assertIn("prompt_language", data["metadata"])
        self.assertIn("robot_type", data["metadata"])
        self.assertIn("elapsed_seconds", data["metadata"])

    def test_default_output_excludes_intermediate_fields(self):
        result = _run_flow()
        data = result.output

        self.assertNotIn("scene_context", data)
        self.assertNotIn("candidate_segments", data)
        self.assertNotIn("refined_segments", data)
        self.assertNotIn("changes", data)

    def test_default_output_excludes_debug_and_trace(self):
        result = _run_flow()
        data = result.output

        self.assertNotIn("debug", data)
        self.assertNotIn("trace", data)
        self.assertNotIn("legacy_output", data)

    def test_default_output_excludes_intermediate_contracts(self):
        result = _run_flow()
        data = result.output

        self.assertNotIn("intermediate_contracts", data)

    def test_default_output_stages_is_empty(self):
        result = _run_flow()

        self.assertEqual(result.stages, {})

    def test_segments_contain_confidence(self):
        result = _run_flow()
        segments = result.output["segments"]

        self.assertGreater(len(segments), 0)
        self.assertIn("confidence", segments[0])
        self.assertEqual(segments[0]["confidence"], 0.9)

    def test_validation_is_included_by_default(self):
        result = _run_flow()
        data = result.output

        self.assertIn("validation", data)
        self.assertIn("warnings", data["validation"])


class TestDebugOutput(unittest.TestCase):
    """Verify debug output when include_debug=True or debug=True."""

    def test_include_debug_adds_debug_section(self):
        result = _run_flow(include_debug=True)
        data = result.output

        self.assertIn("debug", data)
        self.assertIn("timing", data["debug"])
        self.assertIn("stage_metadata", data["debug"])
        self.assertIn("validation", data["debug"])

    def test_legacy_debug_param_still_works(self):
        result = _run_flow(debug=True)
        data = result.output

        self.assertIn("debug", data)
        self.assertIn("timing", data["debug"])

    def test_include_debug_does_not_add_trace(self):
        result = _run_flow(include_debug=True)
        data = result.output

        self.assertNotIn("trace", data)

    def test_include_debug_does_not_add_legacy(self):
        result = _run_flow(include_debug=True)
        data = result.output

        self.assertNotIn("legacy_output", data)

    def test_debug_timing_has_all_stages(self):
        result = _run_flow(include_debug=True)
        timing = result.output["debug"]["timing"]

        self.assertIn("scene_load_seconds", timing)
        self.assertIn("scene_postprocess_seconds", timing)
        self.assertIn("analysis_load_seconds", timing)
        self.assertIn("analysis_postprocess_seconds", timing)
        self.assertIn("refinement_load_seconds", timing)
        self.assertIn("refinement_postprocess_seconds", timing)
        self.assertIn("total_seconds", timing)

    def test_debug_stage_metadata_has_all_stages(self):
        result = _run_flow(include_debug=True)
        meta = result.output["debug"]["stage_metadata"]

        self.assertIn("scene", meta)
        self.assertIn("analysis", meta)
        self.assertIn("refinement", meta)


class TestTraceOutput(unittest.TestCase):
    """Verify trace output when include_trace=True."""

    def test_include_trace_adds_trace_section(self):
        result = _run_flow(include_trace=True)
        data = result.output

        self.assertIn("trace", data)
        trace = data["trace"]
        self.assertIn("stage_outputs", trace)
        self.assertIn("stage_contracts", trace)
        self.assertIn("scene", trace["stage_outputs"])
        self.assertIn("analysis", trace["stage_outputs"])
        self.assertIn("refinement", trace["stage_outputs"])
        self.assertIn("scene", trace["stage_contracts"])
        self.assertIn("analysis", trace["stage_contracts"])
        self.assertIn("refinement", trace["stage_contracts"])

    def test_include_trace_populates_stages(self):
        result = _run_flow(include_trace=True)

        self.assertIn("scene", result.stages)
        self.assertIn("analysis", result.stages)
        self.assertIn("refinement", result.stages)

    def test_include_trace_does_not_duplicate_legacy(self):
        result = _run_flow(include_trace=True)
        data = result.output

        self.assertNotIn("legacy_output", data)


class TestLegacyOutput(unittest.TestCase):
    """Verify legacy compatibility output."""

    def test_include_legacy_adds_legacy_output(self):
        result = _run_flow(include_legacy_fields=True)
        data = result.output

        self.assertIn("legacy_output", data)
        legacy = data["legacy_output"]
        self.assertIn("analysisResult", legacy)
        self.assertIn("sceneContext", legacy)
        self.assertIn("timestampedActionSequence", legacy)
        self.assertIn("fineGrainedSteps", legacy)
        self.assertIn("refinedInstruction", legacy)

    def test_legacy_not_included_by_default(self):
        result = _run_flow()
        data = result.output

        self.assertNotIn("legacy_output", data)

    def test_legacy_not_included_with_debug_only(self):
        result = _run_flow(include_debug=True)
        data = result.output

        self.assertNotIn("legacy_output", data)


class TestIntermediateContracts(unittest.TestCase):
    """Verify intermediate_contracts optional output."""

    def test_include_intermediate_contracts(self):
        result = _run_flow(include_intermediate_contracts=True)
        data = result.output

        self.assertIn("intermediate_contracts", data)
        ics = data["intermediate_contracts"]
        self.assertIn("scene", ics)
        self.assertIn("analysis", ics)
        self.assertIn("refinement", ics)

    def test_analysis_contract_has_candidate_segments(self):
        result = _run_flow(include_intermediate_contracts=True)
        ics = result.output["intermediate_contracts"]

        self.assertIn("candidate_segments", ics["analysis"])

    def test_refinement_contract_has_refined_segments_and_changes(self):
        result = _run_flow(include_intermediate_contracts=True)
        ics = result.output["intermediate_contracts"]

        self.assertIn("refined_segments", ics["refinement"])
        self.assertIn("changes", ics["refinement"])

    def test_intermediate_not_included_by_default(self):
        result = _run_flow()
        data = result.output

        self.assertNotIn("intermediate_contracts", data)


class TestStageObjects(unittest.TestCase):
    """Verify configurable stages population."""

    def test_include_stage_objects_populates_stages(self):
        result = _run_flow(include_stage_objects=True)

        self.assertIn("scene", result.stages)
        self.assertIn("analysis", result.stages)
        self.assertIn("refinement", result.stages)

    def test_stage_objects_default_empty(self):
        result = _run_flow()

        self.assertEqual(result.stages, {})

    def test_stage_objects_with_debug(self):
        result = _run_flow(include_stage_objects=True, include_debug=True)

        self.assertIn("scene", result.stages)
        self.assertIn("debug", result.output)


class TestSaveProcessedMedia(unittest.TestCase):
    def test_save_processed_media_writes_stage_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = save_processed_media(
                [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}}],
                save_root=tmp,
                stage_name="scene",
                episode_name="episode:001",
            )
            self.assertEqual(len(saved), 1)
            self.assertEqual(Path(saved[0]).name, "frame_000000.jpg")
            self.assertIn("episode_001", saved[0])

            saved_video = save_processed_media(
                [{"type": "video_url", "video_url": {"url": "data:video/mp4;base64,QUJD"}}],
                save_root=tmp,
                stage_name="analysis",
                episode_name="episode:001",
            )
            self.assertEqual(Path(saved_video[0]).name, "episode_001.mp4")


class TestAnnotationResultToDict(unittest.TestCase):
    """Verify to_dict() schema versioning."""

    def test_to_dict_v2_excludes_raw_stage_output(self):
        result = _run_flow(include_stage_objects=True)
        d = result.to_dict(schema_version="v2")

        self.assertIn("stages", d)
        for stage_name, stage_dict in d["stages"].items():
            self.assertNotIn("output", stage_dict, f"v2 should not include raw output in stage '{stage_name}'")

    def test_to_dict_v1_includes_raw_stage_output(self):
        result = _run_flow(include_stage_objects=True)
        d = result.to_dict(schema_version="v1")

        self.assertIn("stages", d)
        for stage_name, stage_dict in d["stages"].items():
            self.assertIn("output", stage_dict, f"v1 should include raw output in stage '{stage_name}'")

    def test_to_dict_default_is_v2(self):
        """Default to_dict() should behave like v2 (no raw stage output exposed)."""
        result = _run_flow(include_stage_objects=True)
        d = result.to_dict()

        self.assertIn("stages", d)
        for stage_name, stage_dict in d["stages"].items():
            self.assertNotIn("output", stage_dict, f"default to_dict should not include raw output in stage '{stage_name}'")


if __name__ == "__main__":
    unittest.main()
