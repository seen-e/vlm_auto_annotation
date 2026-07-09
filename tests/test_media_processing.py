from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vlm_auto_annotation.media.input import build_media_parts


class MediaProcessingTest(unittest.TestCase):
    def test_build_media_parts_image_sequence_from_video(self):
        cv2 = __import__("cv2")
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "demo.mp4"
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (32, 32))
            for index in range(8):
                frame = np.full((32, 32, 3), index * 20, dtype=np.uint8)
                writer.write(frame)
            writer.release()

            parts, meta = build_media_parts(
                str(video_path),
                {
                    "input_mode": "image_sequence",
                    "fps": 1.0,
                    "max_frames": 4,
                    "resize_width": 32,
                    "jpeg_quality": 70,
                    "min_api_frames": 1,
                    "draw_timestamps": False,
                    "draw_viewposition": False,
                    "merge_views": False,
                    "merge_mode": "per_frame",
                    "merge_length": 0,
                    "merge_view_names": ["front"],
                },
            )

            self.assertGreaterEqual(len(parts), 1)
            self.assertEqual(meta["input_mode"], "image_sequence")
            self.assertLessEqual(meta["sampled_frame_count"], 4)


if __name__ == "__main__":
    unittest.main()
