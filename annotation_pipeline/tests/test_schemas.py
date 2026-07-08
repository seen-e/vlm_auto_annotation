import unittest

from annotation_pipeline.schemas import (
    ExecutorInfo,
    FinalAnnotationOutput,
    ObjectInfo,
    RefinedSegment,
    SceneStageOutput,
)


class TestSchemas(unittest.TestCase):
    def test_scene_contract_dedupes_ids(self):
        scene = SceneStageOutput(
            primary_view="front",
            executors=[
                ExecutorInfo(executor_id="left"),
                ExecutorInfo(executor_id="left", description="duplicate"),
            ],
            touched_objects=[
                ObjectInfo(object_id="cup", role="manipulated_object"),
                ObjectInfo(object_id="cup", role="target_object"),
            ],
        )
        self.assertEqual(len(scene.executors), 1)
        self.assertEqual(len(scene.touched_objects), 1)

    def test_refined_segment_validates_confidence(self):
        segment = RefinedSegment(
            segment_id="S001",
            executor="left",
            action="grasp",
            objects=["cup"],
            confidence=0.8,
        )
        self.assertEqual(segment.confidence, 0.8)

    def test_final_output_dedupes_touched_objects(self):
        final = FinalAnnotationOutput(touched_objects=["cup", "cup", "plate"])
        self.assertEqual(final.touched_objects, ["cup", "plate"])


if __name__ == "__main__":
    unittest.main()
