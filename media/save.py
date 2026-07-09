"""Processed media saving helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def save_processed_media(parts: list[dict[str, Any]], *, save_root: str | Path, stage_name: str, episode_name: str) -> Path:
    from ..utils.video_utils import save_processed_media as _save_processed_media

    return _save_processed_media(parts, save_root=save_root, stage_name=stage_name, episode_name=episode_name)
