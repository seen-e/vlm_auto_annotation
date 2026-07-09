"""Workflow runner."""

from __future__ import annotations

import logging
from typing import Any

from .context import StageContext
from .registry import StageRegistry, default_registry

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """Execute configured stages without hard-coding stage logic."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        client: Any = None,
        registry: StageRegistry | None = None,
        artifact_store: Any = None,
    ) -> None:
        self.config = config
        self.client = client
        self.registry = registry or default_registry()
        if artifact_store is None:
            from ..artifacts.store import ArtifactStore

            artifacts_cfg = config.get("artifacts", {})
            artifact_store = ArtifactStore(
                root_dir=artifacts_cfg.get("root_dir", "outputs/artifacts"),
                enabled=bool(artifacts_cfg.get("enabled", True)),
                config=artifacts_cfg,
            )
        self.artifact_store = artifact_store

    def _workflow_stage_names(self) -> list[str]:
        workflow = self.config.get("workflow") or {}
        return list(workflow.get("stages") or ["scene", "analysis", "refinement"])

    def _stage_config(self, name: str) -> dict[str, Any]:
        stage_cfg = dict((self.config.get("stages") or {}).get(name) or {})
        model_cfg = self.config.get("model") or {}
        sampling_cfg = self.config.get("vlm_sampling") or {}
        stage_cfg.setdefault("model", model_cfg.get("name", ""))
        stage_cfg.setdefault("temperature", sampling_cfg.get("temperature", 0.0))
        stage_cfg.setdefault("top_p", sampling_cfg.get("top_p", 0.95))
        stage_cfg.setdefault("top_k", sampling_cfg.get("top_k", 0))
        return stage_cfg

    def load_outputs(self, context: StageContext, load_outputs: dict[str, str] | None = None) -> None:
        if not load_outputs:
            return
        for stage_name, path in load_outputs.items():
            contract = self.artifact_store.load_contract_file(path, stage_name)
            context.stage_contracts[stage_name] = contract
            logger.info("Loaded stage contract stage=%s path=%s", stage_name, path)

    def run(
        self,
        context: StageContext,
        *,
        stages: list[str] | None = None,
        load_outputs: dict[str, str] | None = None,
    ):
        self.load_outputs(context, load_outputs)
        stage_names = stages or self._workflow_stage_names()
        run_results = {}
        for name in stage_names:
            if name in context.stage_contracts and name in (load_outputs or {}):
                continue
            stage = self.registry.create(name, self._stage_config(name), client=self.client)
            logger.info("Workflow stage start name=%s video_id=%s", name, context.video_id or context.episode_name)
            result = stage.run(context)
            run_results[name] = result
            self.artifact_store.save_stage_result(context, result)
            logger.info("Workflow stage done name=%s elapsed=%.2fs", name, result.elapsed_seconds)

        from ..outputs.composer import compose_annotation_result

        return compose_annotation_result(context, run_results, self.config)
