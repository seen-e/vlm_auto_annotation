"""Artifact path layout."""

from __future__ import annotations

from pathlib import Path


def stage_dir(root: str | Path, episode_name: str, stage_name: str) -> Path:
    return Path(root) / str(episode_name) / str(stage_name)
