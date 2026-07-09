"""Analysis stage plugin."""

from __future__ import annotations

from typing import Any

from ...core.stage import BaseStage
from .parser import parse_analysis
from .postprocess import postprocess_analysis
from .prompt import build_analysis_prompt


class AnalysisStage(BaseStage):
    name = "analysis"
    required_contracts = ("scene",)

    def build_prompt(self, context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
        return build_analysis_prompt(context, media_meta)

    def parse(self, raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
        return parse_analysis(raw_json, context, media_meta)

    def postprocess(self, parse_result: Any, context: Any, media_meta: dict[str, Any]):
        return postprocess_analysis(parse_result, context, media_meta)
