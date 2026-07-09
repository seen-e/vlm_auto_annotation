"""Stage plugin registry."""

from __future__ import annotations

from typing import Any


class StageRegistry:
    def __init__(self) -> None:
        self._items: dict[str, type] = {}

    def register(self, name: str, stage_cls: type) -> None:
        if not name:
            raise ValueError("stage name must be non-empty")
        self._items[name] = stage_cls

    def create(self, name: str, config: dict[str, Any], client: Any = None):
        try:
            stage_cls = self._items[name]
        except KeyError as exc:
            raise KeyError(f"unknown stage '{name}', registered={sorted(self._items)}") from exc
        return stage_cls(config=config, client=client)

    def names(self) -> list[str]:
        return sorted(self._items)


def default_registry() -> StageRegistry:
    from ..stages.analysis.stage import AnalysisStage
    from ..stages.refinement.stage import RefinementStage
    from ..stages.scene.stage import SceneStage

    registry = StageRegistry()
    registry.register("scene", SceneStage)
    registry.register("analysis", AnalysisStage)
    registry.register("refinement", RefinementStage)
    return registry
