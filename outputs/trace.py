"""Trace output."""

from __future__ import annotations

from typing import Any


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def build_trace(context: Any, run_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage_outputs": context.stage_outputs,
        "stage_contracts": {name: _dump(contract) for name, contract in context.stage_contracts.items()},
        "stage_artifacts": context.stage_artifacts,
        "raw_responses": {name: result.raw_response for name, result in run_results.items()},
    }
