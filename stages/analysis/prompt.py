"""Analysis prompt builder."""

from __future__ import annotations

from typing import Any

from ...prompts.loader import load_prompt_package
from ...utils.prompt_context import describe_view_layout, json_dumps
from ...utils.prompt_renderer import render_prompt_template


def _contract_dict(contract: Any) -> dict[str, Any]:
    if hasattr(contract, "model_dump"):
        return contract.model_dump()
    return dict(contract or {})


def build_analysis_prompt(context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
    package = load_prompt_package(context.prompt_language)
    scene_contract = context.stage_contracts.get("scene")
    scene_result = _contract_dict(scene_contract)
    if context.stage_outputs.get("scene"):
        scene_result = context.stage_outputs["scene"]
    user = render_prompt_template(
        package.ANALYSIS_PROMPT_TEMPLATE,
        context=context,
        stage_config=getattr(context, "extras", {}).get("stage_config", {}),
        extra_variables={
            "initial_instruction": context.instruction,
            "robot_type": context.robot_type,
            "robot_type_prompt": package.get_robot_type_prompt(context.robot_type),
            "action_vocabulary": getattr(package, "ACTION_VOCABULARY", ""),
            "view_layout_description": describe_view_layout(media_meta, context.prompt_language),
            "scene_result": json_dumps(scene_result),
            "scene_context": json_dumps(scene_result),
        },
    )
    return {"system": package.ANALYSIS_SYSTEM_PROMPT, "user": user}
