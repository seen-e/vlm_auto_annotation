"""Refinement stage plugin."""

from __future__ import annotations

from typing import Any

from ...core.stage import BaseStage
from .parser import parse_refinement
from .postprocess import postprocess_refinement
from .prompt import build_refinement_prompt


class RefinementStage(BaseStage):
    name = "refinement"
    required_contracts = ("scene", "analysis")

    def build_prompt(self, context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
        return build_refinement_prompt(context, media_meta)

    def parse(self, raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
        return parse_refinement(raw_json, context, media_meta)

    def postprocess(self, parse_result: Any, context: Any, media_meta: dict[str, Any]):
        return postprocess_refinement(parse_result, context, media_meta)
