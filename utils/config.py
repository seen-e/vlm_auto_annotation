"""Compatibility constants loaded from ``config/config.yaml``.

``config/config.yaml`` is the single source of default runtime parameters.
This Python module exists so existing imports such as
``from utils.config import DEFAULT_MODEL`` keep working.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
CONFIG_PATH = Path(os.environ.get("ANNOTATE_CONFIG", DEFAULT_CONFIG_PATH))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML object: {path}")
    return data


def _required(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for key in dotted_key.split("."):
        if not isinstance(current, dict) or key not in current:
            raise KeyError(f"Missing required config key '{dotted_key}' in {CONFIG_PATH}")
        current = current[key]
    return current


def _optional(data: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    current: Any = data
    for key in dotted_key.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _env_str(name: str, value: Any) -> str:
    return str(os.environ.get(name, value))


def _env_int(name: str, value: Any) -> int:
    return int(os.environ.get(name, value))


def _env_float(name: str, value: Any) -> float:
    return float(os.environ.get(name, value))


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _env_bool(name: str, value: Any) -> bool:
    return _to_bool(os.environ.get(name, value))


def _env_list(name: str, value: Any) -> list[str]:
    raw = os.environ.get(name)
    if raw is not None:
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise TypeError(f"Expected list or comma-separated string for {name}, got {type(value).__name__}")


def _env_merge_mode(name: str, value: Any) -> str:
    mode = _env_str(name, value).strip().lower().replace("-", "_")
    aliases = {
        "frame": "per_frame",
        "frames": "per_frame",
        "vertical": "per_frame",
        "grid": "timeline_grid",
        "timeline": "timeline_grid",
        "time_grid": "timeline_grid",
    }
    mode = aliases.get(mode, mode)
    if mode not in {"per_frame", "timeline_grid"}:
        raise ValueError(f"{name} must be 'per_frame' or 'timeline_grid', got: {mode}")
    return mode


_CONFIG = _load_yaml(CONFIG_PATH)

DEFAULT_MODEL = _env_str("ANNOTATE_MODEL", _required(_CONFIG, "model.name"))
DEFAULT_BASE_URL = _env_str("ANNOTATE_BASE_URL", _required(_CONFIG, "model.base_url"))

DEFAULT_SCENE_FPS = _env_float("ANNOTATE_SCENE_FPS", _required(_CONFIG, "stages.scene.fps"))
DEFAULT_ANALYSIS_FPS = _env_float("ANNOTATE_ANALYSIS_FPS", _required(_CONFIG, "stages.analysis.fps"))
DEFAULT_REFINEMENT_FPS = _env_float("ANNOTATE_REFINEMENT_FPS", _required(_CONFIG, "stages.refinement.fps"))

DEFAULT_ROBOT_TYPE = _env_str("ANNOTATE_ROBOT_TYPE", _required(_CONFIG, "prompt.robot_type"))
DEFAULT_PROMPT_LANGUAGE = _env_str("ANNOTATE_PROMPT_LANGUAGE", _required(_CONFIG, "prompt.language"))

DEFAULT_SCENE_MAX_TOKENS = _env_int(
    "ANNOTATE_SCENE_MAX_TOKENS",
    _required(_CONFIG, "stages.scene.max_tokens"),
)
DEFAULT_ANALYSIS_MAX_TOKENS = _env_int(
    "ANNOTATE_ANALYSIS_MAX_TOKENS",
    _required(_CONFIG, "stages.analysis.max_tokens"),
)
DEFAULT_REFINEMENT_MAX_TOKENS = _env_int(
    "ANNOTATE_REFINEMENT_MAX_TOKENS",
    _required(_CONFIG, "stages.refinement.max_tokens"),
)

_fallback_max_frames = os.environ.get("ANNOTATE_MAX_FRAMES")
DEFAULT_SCENE_MAX_FRAMES = _env_int(
    "ANNOTATE_SCENE_MAX_FRAMES",
    _fallback_max_frames or _optional(_CONFIG, "stages.scene.max_frames", _required(_CONFIG, "video.max_frames")),
)
DEFAULT_ANALYSIS_MAX_FRAMES = _env_int(
    "ANNOTATE_ANALYSIS_MAX_FRAMES",
    _fallback_max_frames or _optional(_CONFIG, "stages.analysis.max_frames", _required(_CONFIG, "video.max_frames")),
)
DEFAULT_REFINEMENT_MAX_FRAMES = _env_int(
    "ANNOTATE_REFINEMENT_MAX_FRAMES",
    _fallback_max_frames or _optional(_CONFIG, "stages.refinement.max_frames", _required(_CONFIG, "video.max_frames")),
)
_fallback_merge_views = os.environ.get("ANNOTATE_MERGE_VIEWS")
_fallback_merge_mode = os.environ.get("ANNOTATE_MERGE_MODE")
DEFAULT_SCENE_MERGE_VIEWS = _env_bool(
    "ANNOTATE_SCENE_MERGE_VIEWS",
    _fallback_merge_views or _required(_CONFIG, "stages.scene.merge_views"),
)
DEFAULT_ANALYSIS_MERGE_VIEWS = _env_bool(
    "ANNOTATE_ANALYSIS_MERGE_VIEWS",
    _fallback_merge_views or _required(_CONFIG, "stages.analysis.merge_views"),
)
DEFAULT_REFINEMENT_MERGE_VIEWS = _env_bool(
    "ANNOTATE_REFINEMENT_MERGE_VIEWS",
    _fallback_merge_views or _required(_CONFIG, "stages.refinement.merge_views"),
)
DEFAULT_SCENE_MERGE_MODE = _env_merge_mode(
    "ANNOTATE_SCENE_MERGE_MODE",
    _fallback_merge_mode or _required(_CONFIG, "stages.scene.merge_mode"),
)
DEFAULT_ANALYSIS_MERGE_MODE = _env_merge_mode(
    "ANNOTATE_ANALYSIS_MERGE_MODE",
    _fallback_merge_mode or _required(_CONFIG, "stages.analysis.merge_mode"),
)
DEFAULT_REFINEMENT_MERGE_MODE = _env_merge_mode(
    "ANNOTATE_REFINEMENT_MERGE_MODE",
    _fallback_merge_mode or _required(_CONFIG, "stages.refinement.merge_mode"),
)
DEFAULT_VLM_TEMPERATURE = _env_float("ANNOTATE_VLM_TEMPERATURE", _required(_CONFIG, "vlm_sampling.temperature"))
DEFAULT_VLM_TOP_P = _env_float("ANNOTATE_VLM_TOP_P", _required(_CONFIG, "vlm_sampling.top_p"))
DEFAULT_VLM_TOP_K = _env_int("ANNOTATE_VLM_TOP_K", _required(_CONFIG, "vlm_sampling.top_k"))

DEFAULT_MAX_FRAMES = DEFAULT_REFINEMENT_MAX_FRAMES
DEFAULT_MERGE_VIEWS = DEFAULT_ANALYSIS_MERGE_VIEWS
DEFAULT_MERGE_MODE = DEFAULT_ANALYSIS_MERGE_MODE

_fallback_resize_width = os.environ.get("ANNOTATE_RESIZE_WIDTH")
DEFAULT_SCENE_RESIZE_WIDTH = _env_int(
    "ANNOTATE_SCENE_RESIZE_WIDTH",
    _fallback_resize_width or _required(_CONFIG, "stages.scene.resize_width"),
)
DEFAULT_ANALYSIS_RESIZE_WIDTH = _env_int(
    "ANNOTATE_ANALYSIS_RESIZE_WIDTH",
    _fallback_resize_width or _required(_CONFIG, "stages.analysis.resize_width"),
)
DEFAULT_REFINEMENT_RESIZE_WIDTH = _env_int(
    "ANNOTATE_REFINEMENT_RESIZE_WIDTH",
    _fallback_resize_width or _required(_CONFIG, "stages.refinement.resize_width"),
)
DEFAULT_RESIZE_WIDTH = DEFAULT_REFINEMENT_RESIZE_WIDTH

_fallback_merge_view_names = os.environ.get("ANNOTATE_MERGE_VIEW_NAMES")
DEFAULT_SCENE_MERGE_VIEW_NAMES = _env_list(
    "ANNOTATE_SCENE_MERGE_VIEW_NAMES",
    _fallback_merge_view_names or _optional(_CONFIG, "stages.scene.merge_view_names", _required(_CONFIG, "video.merge_view_names")),
)
DEFAULT_ANALYSIS_MERGE_VIEW_NAMES = _env_list(
    "ANNOTATE_ANALYSIS_MERGE_VIEW_NAMES",
    _fallback_merge_view_names or _optional(_CONFIG, "stages.analysis.merge_view_names", _required(_CONFIG, "video.merge_view_names")),
)
DEFAULT_REFINEMENT_MERGE_VIEW_NAMES = _env_list(
    "ANNOTATE_REFINEMENT_MERGE_VIEW_NAMES",
    _fallback_merge_view_names or _optional(_CONFIG, "stages.refinement.merge_view_names", _required(_CONFIG, "video.merge_view_names")),
)
DEFAULT_MERGE_VIEW_NAMES = DEFAULT_REFINEMENT_MERGE_VIEW_NAMES

_fallback_jpeg_quality = os.environ.get("ANNOTATE_JPEG_QUALITY")
DEFAULT_SCENE_JPEG_QUALITY = _env_int(
    "ANNOTATE_SCENE_JPEG_QUALITY",
    _fallback_jpeg_quality or _optional(_CONFIG, "stages.scene.jpeg_quality", _required(_CONFIG, "video.jpeg_quality")),
)
DEFAULT_ANALYSIS_JPEG_QUALITY = _env_int(
    "ANNOTATE_ANALYSIS_JPEG_QUALITY",
    _fallback_jpeg_quality or _optional(_CONFIG, "stages.analysis.jpeg_quality", _required(_CONFIG, "video.jpeg_quality")),
)
DEFAULT_REFINEMENT_JPEG_QUALITY = _env_int(
    "ANNOTATE_REFINEMENT_JPEG_QUALITY",
    _fallback_jpeg_quality or _optional(_CONFIG, "stages.refinement.jpeg_quality", _required(_CONFIG, "video.jpeg_quality")),
)
DEFAULT_JPEG_QUALITY = DEFAULT_REFINEMENT_JPEG_QUALITY

DEFAULT_SCENE_DRAW_TIMESTAMPS = _env_bool(
    "ANNOTATE_SCENE_DRAW_TIMESTAMPS",
    _required(_CONFIG, "stages.scene.draw_timestamps"),
)
DEFAULT_ANALYSIS_DRAW_TIMESTAMPS = _env_bool(
    "ANNOTATE_ANALYSIS_DRAW_TIMESTAMPS",
    _required(_CONFIG, "stages.analysis.draw_timestamps"),
)
DEFAULT_REFINEMENT_DRAW_TIMESTAMPS = _env_bool(
    "ANNOTATE_REFINEMENT_DRAW_TIMESTAMPS",
    os.environ.get("ANNOTATE_DRAW_TIMESTAMPS", _required(_CONFIG, "stages.refinement.draw_timestamps")),
)
DEFAULT_DRAW_TIMESTAMPS = DEFAULT_REFINEMENT_DRAW_TIMESTAMPS

_fallback_min_api_frames = os.environ.get("ANNOTATE_MIN_API_FRAMES")
DEFAULT_SCENE_MIN_API_FRAMES = _env_int(
    "ANNOTATE_SCENE_MIN_API_FRAMES",
    _fallback_min_api_frames or _optional(_CONFIG, "stages.scene.min_api_frames", _required(_CONFIG, "video.min_api_frames")),
)
DEFAULT_ANALYSIS_MIN_API_FRAMES = _env_int(
    "ANNOTATE_ANALYSIS_MIN_API_FRAMES",
    _fallback_min_api_frames or _optional(_CONFIG, "stages.analysis.min_api_frames", _required(_CONFIG, "video.min_api_frames")),
)
DEFAULT_REFINEMENT_MIN_API_FRAMES = _env_int(
    "ANNOTATE_REFINEMENT_MIN_API_FRAMES",
    _fallback_min_api_frames or _optional(_CONFIG, "stages.refinement.min_api_frames", _required(_CONFIG, "video.min_api_frames")),
)
MIN_API_FRAMES = DEFAULT_REFINEMENT_MIN_API_FRAMES
MAX_STEP_WORKERS = _env_int("ANNOTATE_MAX_STEP_WORKERS", _required(_CONFIG, "workers.max_step_workers"))

DEFAULT_LOG_LEVEL = _env_str("ANNOTATE_LOG_LEVEL", _required(_CONFIG, "logging.level"))
DEFAULT_LOG_FORMAT = _env_str("ANNOTATE_LOG_FORMAT", _required(_CONFIG, "logging.format"))
