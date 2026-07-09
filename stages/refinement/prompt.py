"""Refinement prompt builder."""

from __future__ import annotations

from typing import Any

from ...flows.utils import describe_view_layout, json_dumps
from ...prompts.loader import load_prompt_package, safe_format


def _contract_dict(contract: Any) -> dict[str, Any]:
    if hasattr(contract, "model_dump"):
        return contract.model_dump()
    return dict(contract or {})


def build_refinement_prompt(context: Any, media_meta: dict[str, Any]) -> dict[str, str]:
    package = load_prompt_package(context.prompt_language)
    scene = _contract_dict(context.stage_contracts.get("scene"))
    analysis = _contract_dict(context.stage_contracts.get("analysis"))
    action_sequence = context.stage_outputs.get("analysis") or analysis
    main_object = ""
    touched = scene.get("touched_objects") if isinstance(scene, dict) else []
    if touched:
        main_object = touched[0].get("description") or touched[0].get("object_id") or ""
    user = safe_format(
        package.REFINEMENT_PROMPT_TEMPLATE,
        initial_instruction=context.instruction,
        robot_type=context.robot_type,
        robot_type_prompt=package.get_robot_type_prompt(context.robot_type),
        action_sequence=json_dumps(action_sequence),
        main_object=main_object,
        scene_context=json_dumps(scene),
        view_layout_description=describe_view_layout(media_meta, context.prompt_language),
        action_guidance=getattr(package, "ACTION_FINE_GRAINED_GUIDANCE", ""),
        FEW_SHOT_EXAMPLES=getattr(package, "FEW_SHOT_EXAMPLES", ""),
    )
    return {"system": package.REFINEMENT_SYSTEM_PROMPT, "user": user}
