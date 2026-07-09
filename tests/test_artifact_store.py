from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.artifacts.store import ArtifactStore
from vlm_auto_annotation.contracts.scene import SceneStageOutput
from vlm_auto_annotation.core.context import StageContext


class ArtifactStoreTest(unittest.TestCase):
    def test_saves_and_loads_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(tmp, enabled=True)
            context = StageContext(video_path="demo.mp4", video_id="episode_1")
            result = SimpleNamespace(
                name="scene",
                prompt={"system": "sys", "user": "user"},
                raw_response="{}",
                parsed_output={},
                contract=SceneStageOutput(primary_view="front"),
                media_meta={"selected_views": ["front"]},
                usage={},
                success=True,
                warnings=[],
                errors=[],
                elapsed_seconds=0.1,
            )
            store.save_stage_result(context, result)
            contract_path = Path(tmp) / "episode_1" / "scene" / "contract.json"

            self.assertTrue(contract_path.exists())
            self.assertEqual(json.loads(contract_path.read_text(encoding="utf-8"))["primary_view"], "front")
            self.assertEqual(store.load_contract_file(contract_path, "scene").primary_view, "front")


if __name__ == "__main__":
    unittest.main()
