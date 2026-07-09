"""Debug output."""

from __future__ import annotations

from typing import Any


def build_debug(context: Any, run_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_warnings": list(context.validation_warnings),
        "stages": {
            name: {
                "elapsed_seconds": result.elapsed_seconds,
                "usage": result.usage,
                "warnings": result.warnings,
                "errors": result.errors,
                "media_meta": result.media_meta,
            }
            for name, result in run_results.items()
        },
    }
