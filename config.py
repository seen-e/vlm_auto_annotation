"""Runtime defaults for VLM auto annotation."""

from __future__ import annotations

import os

DEFAULT_MODEL = os.environ.get("ANNOTATE_MODEL", "qwen-vl-plus")
DEFAULT_BASE_URL = os.environ.get(
    "ANNOTATE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)

DEFAULT_ANALYSIS_FPS = float(os.environ.get("ANNOTATE_ANALYSIS_FPS", "4.0"))
DEFAULT_REFINEMENT_FPS = float(os.environ.get("ANNOTATE_REFINEMENT_FPS", "3.0"))
DEFAULT_MAX_FRAMES = int(os.environ.get("ANNOTATE_MAX_FRAMES", "512"))
DEFAULT_RESIZE_WIDTH = int(os.environ.get("ANNOTATE_RESIZE_WIDTH", "512"))
DEFAULT_JPEG_QUALITY = int(os.environ.get("ANNOTATE_JPEG_QUALITY", "85"))
MIN_API_FRAMES = int(os.environ.get("ANNOTATE_MIN_API_FRAMES", "2"))
MAX_STEP_WORKERS = int(os.environ.get("ANNOTATE_MAX_STEP_WORKERS", "8"))
