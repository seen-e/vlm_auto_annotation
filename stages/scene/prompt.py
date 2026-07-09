"""Scene prompt builder."""

from __future__ import annotations

from typing import Any

from ...flows.utils import describe_view_layout
from ...prompts.loader import load_prompt_package, safe_format


def build_scene_prompt(context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
    package = load_prompt_package(context.prompt_language)
    view_layout = describe_view_layout(media_meta, context.prompt_language)
    user = safe_format(
        package.SCENE_PROMPT_TEMPLATE,
        view_layout_description=view_layout,
        action_vocabulary=getattr(package, "ACTION_VOCABULARY", ""),
        robot_type=context.robot_type,
    )
    return {"system": package.SCENE_SYSTEM_PROMPT, "user": user}
