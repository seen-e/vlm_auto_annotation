# VLM Auto Annotation

This package reorganizes FineVLA-style automatic VLA annotation into four named
flows. Prompts live in `prompts_cn/`; flow implementations live in `flows/`.

## Flow Selection

| Flow | File | Use case | Core stages |
|---|---|---|---|
| 01 | `flows/flow_01_standard_two_stage.py` | single/main view, no `steps_raw` | analysis -> refinement |
| 02 | `flows/flow_02_multiview_three_stage.py` | main view + wrist/detail view, no `steps_raw` | analysis -> main refinement -> detail correction |
| 03 | `flows/flow_03_stepwise_single_view.py` | single/main view with `steps_raw` | per-step refinement -> dedup |
| 04 | `flows/flow_04_stepwise_multiview.py` | multiple synchronized views with `steps_raw` | main per-step refinement -> auxiliary-view verification -> dedup -> QC |

## Basic Usage

```python
from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import (
    run_standard_two_stage,
    run_multiview_three_stage,
    run_stepwise_single_view,
    run_stepwise_multiview,
)

client = create_openai_client()

result = run_stepwise_multiview(
    client,
    main_video_path="main.mp4",
    auxiliary_video_paths={"wrist": "wrist.mp4", "side": "side.mp4"},
    initial_instruction="stack the cups",
    steps_raw=[
        {"i": 0, "start": 0, "end": 42, "desc": "reach the cup"},
        {"i": 1, "start": 43, "end": 96, "desc": "grasp the cup"},
    ],
)

print(result.to_dict())
```

## Output Shape

Every flow returns `AnnotationResult`:

- `flow_name`: stable implementation name.
- `success`: whether every stage produced parseable JSON or a safe fallback.
- `output`: user-facing annotation payload, including `fineGrainedSteps` and `refinedInstruction`.
- `stages`: intermediate VLM stage outputs and token usage.

## Fourth Flow Design

The newly added fourth flow covers the missing combination: multi-view data with
pre-segmented `steps_raw`.

1. Use the main/global view to refine each raw step independently.
2. Use auxiliary views to verify contact points, gripper state, object identity,
   spatial direction, arm role, and action outcome for the same step range.
3. Preserve step count and order. Auxiliary views may only make small corrections.
4. Run deduplication and a final consistency QC prompt for large-scale batch safety.

The dedicated prompt file is `prompts_cn/multiview_step.py`.
