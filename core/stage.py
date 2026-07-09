"""Base stage lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from .context import StageContext


@dataclass
class StageRunResult:
    name: str
    prompt: dict[str, str]
    raw_response: str
    parsed_output: dict[str, Any]
    contract: Any
    media_meta: dict[str, Any]
    media_parts: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return not self.errors


class BaseStage:
    """Contract-first VLM stage.

    Subclasses only implement prompt construction and parsing. The lifecycle is
    consistent for scene, analysis, refinement, and future plugin stages.
    """

    name = ""
    required_contracts: tuple[str, ...] = ()

    def __init__(self, config: dict[str, Any], client: Any = None) -> None:
        self.config = config
        self.client = client

    def prepare_input(self, context: StageContext) -> None:
        missing = [stage for stage in self.required_contracts if stage not in context.stage_contracts]
        if missing:
            raise ValueError(f"stage '{self.name}' requires previous contract(s): {missing}")

    def build_media(self, context: StageContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        loader = self.config.get("_media_loader")
        if loader is not None:
            return loader(
                context.video_path,
                input_mode=self.config.get("input_mode", "image_sequence"),
                target_fps=float(self.config.get("fps", 1.0) or 1.0),
                max_frames=int(self.config.get("max_frames", 128) or 128),
                resize_width=int(self.config.get("resize_width", 336) or 336),
                jpeg_quality=int(self.config.get("jpeg_quality", 85) or 85),
                min_api_frames=int(self.config.get("min_api_frames", 2) or 2),
                draw_timestamps=bool(self.config.get("draw_timestamps", False)),
                draw_viewposition=bool(self.config.get("draw_viewposition", False)),
                merge_length=int(self.config.get("merge_length", 0) or 0),
                merge_view_names=self.config.get("merge_view_names"),
                merge_views=bool(self.config.get("merge_views", True)),
                merge_mode=str(self.config.get("merge_mode", "per_frame") or "per_frame"),
            )
        from ..media.input import build_media_parts

        return build_media_parts(context.video_path, self.config)

    def build_prompt(self, context: StageContext, media_meta: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError

    def call_model(self, media_parts: list[dict[str, Any]], prompt: dict[str, str]) -> tuple[str, dict[str, int]]:
        from ..llm.json_call import call_json

        return call_json(
            self.client,
            media_parts=media_parts,
            system_prompt=prompt.get("system", ""),
            user_prompt=prompt.get("user", ""),
            model=self.config.get("model", ""),
            max_tokens=int(self.config.get("max_tokens", 0) or 0),
            temperature=float(self.config.get("temperature", 0.0) or 0.0),
            top_p=float(self.config.get("top_p", 0.95) or 0.95),
            top_k=int(self.config.get("top_k", 0) or 0),
        )

    def parse(self, raw_json: dict[str, Any] | None, context: StageContext, media_meta: dict[str, Any]):
        raise NotImplementedError

    def postprocess(self, parse_result: Any, context: StageContext, media_meta: dict[str, Any]):
        return parse_result

    def run(self, context: StageContext) -> StageRunResult:
        start = time.perf_counter()
        self.prepare_input(context)
        media_parts, media_meta = self.build_media(context)
        prompt = self.build_prompt(context, media_meta)
        raw_response, usage = self.call_model(media_parts, prompt)

        from ..llm.json_call import extract_json

        parsed = extract_json(raw_response) or {}
        parse_result = self.parse(parsed, context, media_meta)
        contract = self.postprocess(parse_result.output, context, media_meta)
        warnings = list(getattr(parse_result, "warnings", []) or [])
        errors = list(getattr(parse_result, "errors", []) or [])
        result = StageRunResult(
            name=self.name,
            prompt=prompt,
            raw_response=raw_response,
            parsed_output=parsed,
            contract=contract,
            media_meta=media_meta,
            media_parts=media_parts,
            usage=usage,
            warnings=warnings,
            errors=errors,
            elapsed_seconds=time.perf_counter() - start,
        )
        context.stage_outputs[self.name] = parsed
        context.stage_contracts[self.name] = contract
        context.validation_warnings.extend(warnings)
        context.stage_artifacts[self.name] = {
            "media_meta": media_meta,
            "usage": usage,
            "elapsed_seconds": result.elapsed_seconds,
        }
        return result
