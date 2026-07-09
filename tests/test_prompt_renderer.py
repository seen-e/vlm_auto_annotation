from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.core.context import StageContext
from vlm_auto_annotation.utils.prompt_renderer import render_prompt_template


class PromptRendererTest(unittest.TestCase):
    def test_nested_prompt_variable(self):
        context = StageContext(video_path="demo.mp4")
        context.formatted_exports["analysis"] = {"action": "grasp cup"}

        text = render_prompt_template("Action: {analysis.action}", context=context)

        self.assertEqual(text, "Action: grasp cup")

    def test_missing_nested_variable_is_empty(self):
        context = StageContext(video_path="demo.mp4")

        text = render_prompt_template("Action: {analysis.action}", context=context)

        self.assertEqual(text, "Action: ")


if __name__ == "__main__":
    unittest.main()
