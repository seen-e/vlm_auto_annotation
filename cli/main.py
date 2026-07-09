"""Command line interface."""

from __future__ import annotations

import argparse
import json

from ..llm.client import create_openai_client
from ..app.run_workflow import run_workflow


def main() -> None:
    parser = argparse.ArgumentParser(prog="vlm-auto-annotation")
    parser.add_argument("video_path")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--video-id", default=None)
    parser.add_argument("--workflow", default="vla_phase_annotation")
    parser.add_argument("--language", default=None)
    parser.add_argument("--robot-type", default=None)
    args = parser.parse_args()

    client = create_openai_client()
    result = run_workflow(
        client=client,
        video_path=args.video_path,
        instruction=args.instruction,
        video_id=args.video_id,
        workflow_name=args.workflow,
        prompt_language=args.language,
        robot_type=args.robot_type,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
