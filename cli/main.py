"""Command line interface."""

from __future__ import annotations

import argparse
import json

from ..core.runtime import load_runtime_config
from ..utils.api_client import create_openai_client
from ..app.run_workflow import run_workflow


def main() -> None:
    parser = argparse.ArgumentParser(prog="vlm-auto-annotation")
    parser.add_argument("video_path")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--video-id", default=None)
    parser.add_argument("--workflow", default="vla_phase_annotation")
    parser.add_argument("--experiment-config", default=None)
    parser.add_argument("--language", default=None)
    parser.add_argument("--robot-type", default=None)
    args = parser.parse_args()

    config = load_runtime_config()
    model_cfg = config.get("model") or {}
    client = create_openai_client(api_key=str(model_cfg.get("api_key") or ""), base_url=str(model_cfg.get("base_url") or ""))
    result = run_workflow(
        client=client,
        video_path=args.video_path,
        instruction=args.instruction,
        video_id=args.video_id,
        workflow_name=args.workflow,
        experiment_path=args.experiment_config,
        prompt_language=args.language,
        robot_type=args.robot_type,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
