# VLM Auto Annotation

This package currently implements the no-`steps_raw` part of the FineVLA-style
automatic annotation pipeline.

Prompts live in `prompts_cn/`; flow implementations live in `flows/`; shared
runtime helpers live in `utils/`.

## Implemented Flows

| Flow | Function | Use case | Stages |
|---|---|---|---|
| `single_view_no_steps_raw` | `flows/flow_analysis_refinement.py` | one main/global view, no `steps_raw` | `analysis -> refinement` |
| `multiview_no_steps_raw` | `flows/flow_analysis_refinement_detail_refinement.py` | main/global view plus wrist/detail/auxiliary view, no `steps_raw` | `analysis -> refinement -> detail_refinement` |

## Stage Meaning

`analysis` watches the full main-view trajectory and extracts a coarse
`action_sequence` plus `main_object`.

`refinement` watches the main view again and turns the coarse result into
`fineGrainedSteps` and `refinedInstruction`.

`detail_refinement` watches an auxiliary close-up view and only makes targeted
corrections to the refinement result, such as contact point, gripper state,
object identity, or spatial direction. It also records `changes_made` and keeps
the pre-detail result under `detailRefinement`.

## Basic Usage

```python
from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import (
    run_single_view_no_steps_raw,
    run_multiview_no_steps_raw,
)

client = create_openai_client()

single = run_single_view_no_steps_raw(
    client,
    video_path="main.mp4",
    initial_instruction="pick up the cup and place it on the plate",
)

multi = run_multiview_no_steps_raw(
    client,
    main_video_path="main.mp4",
    detail_video_path="wrist.mp4",
    detail_view_name="wrist",
    initial_instruction="pick up the cup and place it on the plate",
)

print(single.to_dict())
print(multi.to_dict())
```

## Output Shape

Every flow returns `AnnotationResult`:

- `flow_name`: stable flow name.
- `success`: whether every stage produced parseable JSON or a fallback.
- `output`: user-facing annotation payload, including `fineGrainedSteps` and
  `refinedInstruction`.
- `stages`: intermediate VLM stage outputs and token usage.

The old `run_standard_two_stage` name is kept as an alias of
`run_single_view_no_steps_raw` for compatibility.
