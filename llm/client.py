"""VLM client factory."""

from __future__ import annotations

from pathlib import Path

from ..core.runtime import load_runtime_config
from ..utils.api_client import create_openai_client


def create_client_from_config(config_path: str | Path | None = None):
    config = load_runtime_config(default_path=config_path)
    model_cfg = config.get("model") or {}
    return create_openai_client(api_key=str(model_cfg.get("api_key") or ""), base_url=str(model_cfg.get("base_url") or ""))


__all__ = ["create_client_from_config", "create_openai_client"]
