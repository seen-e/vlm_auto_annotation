"""Artifact store for stage prompts, responses, contracts, and media."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .layout import stage_dir

logger = logging.getLogger(__name__)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


class ArtifactStore:
    def __init__(self, root_dir: str | Path, *, enabled: bool = True, config: dict[str, Any] | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.enabled = enabled
        self.config = config or {}

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _write_json(self, path: Path, data: Any) -> None:
        self._write_text(path, json.dumps(_to_jsonable(data), ensure_ascii=False, indent=2))

    def save_stage_result(self, context: Any, result: Any) -> None:
        if not self.enabled:
            return
        base = stage_dir(self.root_dir, context.episode_name, result.name)
        selected_processed_stages = set(self.config.get("save_processed_stages") or [])
        try:
            if self.config.get("save_prompt", True):
                self._write_text(base / "system_prompt.txt", result.prompt.get("system", ""))
                self._write_text(base / "user_prompt.txt", result.prompt.get("user", ""))
            if self.config.get("save_raw_response", True):
                self._write_text(base / "raw_response.txt", result.raw_response)
            if self.config.get("save_parsed", True):
                self._write_json(base / "parsed.json", result.parsed_output)
            if self.config.get("save_contract", True):
                self._write_json(base / "contract.json", result.contract)
            if self.config.get("save_media_meta", True):
                self._write_json(base / "media_meta.json", result.media_meta)
            if self.config.get("save_processed_media", False) and (
                not selected_processed_stages or result.name in selected_processed_stages
            ):
                from ..media.save import save_processed_media

                save_processed_media(
                    result.media_parts,
                    save_root=base / "processed_media",
                    stage_name=result.name,
                    episode_name=context.episode_name,
                )
            self._write_json(
                base / "run_meta.json",
                {
                    "success": result.success,
                    "warnings": result.warnings,
                    "errors": result.errors,
                    "usage": result.usage,
                    "elapsed_seconds": result.elapsed_seconds,
                },
            )
            self._write_json(base / "exports.json", getattr(context, "exports", {}))
            self._write_json(base / "formatted_exports.json", getattr(context, "formatted_exports", {}))
            self._write_json(base / "export_status.json", getattr(context, "export_status", {}))
            logger.info("Saved stage artifacts stage=%s dir=%s", result.name, base)
        except Exception:
            logger.exception("Failed to save stage artifacts stage=%s dir=%s", result.name, base)
            raise

    def load_contract_file(self, path: str | Path, stage_name: str):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if stage_name == "scene":
            from ..contracts.scene import SceneStageOutput

            return SceneStageOutput(**data)
        if stage_name == "analysis":
            from ..contracts.analysis import AnalysisStageOutput

            return AnalysisStageOutput(**data)
        if stage_name == "refinement":
            from ..contracts.refinement import RefinementStageOutput

            return RefinementStageOutput(**data)
        raise KeyError(f"unknown contract stage '{stage_name}'")
