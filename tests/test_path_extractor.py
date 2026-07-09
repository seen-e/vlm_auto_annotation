from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.utils.path_extractor import extract_path


class PathExtractorTest(unittest.TestCase):
    def test_dotted_path_and_wildcard(self):
        data = {"analysis": {"actions": [{"action": "grasp"}, {"action": "place"}]}}

        value, success = extract_path(data, "analysis.actions[*].action", [])

        self.assertTrue(success)
        self.assertEqual(value, ["grasp", "place"])

    def test_missing_path_returns_default(self):
        value, success = extract_path({"a": {}}, "a.b.c", "empty")

        self.assertFalse(success)
        self.assertEqual(value, "empty")


if __name__ == "__main__":
    unittest.main()
