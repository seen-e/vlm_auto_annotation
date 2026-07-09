"""Scene prompt builder."""

from __future__ import annotations

from typing import Any

from ...prompts.loader import load_prompt_package
from ...utils.prompt_context import describe_view_layout
from ...utils.prompt_renderer import render_prompt_template


def build_scene_prompt(context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
    package = load_prompt_package(context.prompt_language)
    view_layout = describe_view_layout(media_meta, context.prompt_language)
    user = render_prompt_template(
        package.SCENE_PROMPT_TEMPLATE,
        context=context,
        stage_config=getattr(context, "extras", {}).get("stage_config", {}),
        extra_variables={
            "view_layout_description": view_layout,
            "action_vocabulary": getattr(package, "ACTION_VOCABULARY", ""),
            "robot_type": context.robot_type,
        },
    )
    return {"system": package.SCENE_SYSTEM_PROMPT, "user": user}
