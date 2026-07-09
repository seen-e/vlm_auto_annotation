from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.utils.value_formatter import format_value


class ValueFormatterTest(unittest.TestCase):
    def test_formats_without_mutating_raw_type(self):
        value = [{"action": "grasp"}]

        self.assertEqual(format_value(value, "compact_json"), '[{"action":"grasp"}]')
        self.assertIn("- {", format_value(value, "bullet"))
        self.assertIs(format_value(value, "raw"), value)


if __name__ == "__main__":
    unittest.main()
