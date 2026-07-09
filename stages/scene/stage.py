"""Scene stage plugin."""

from __future__ import annotations

from typing import Any

from ...core.stage import BaseStage
from .parser import parse_scene
from .postprocess import postprocess_scene
from .prompt import build_scene_prompt


class SceneStage(BaseStage):
    name = "scene"
    required_contracts: tuple[str, ...] = ()

    def build_prompt(self, context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
        return build_scene_prompt(context, media_meta)

    def parse(self, raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
        return parse_scene(raw_json, context, media_meta)

    def postprocess(self, parse_result: Any, context: Any, media_meta: dict[str, Any]):
        return postprocess_scene(parse_result, context, media_meta)
