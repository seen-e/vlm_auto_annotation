# VLM Auto Annotation

This package implements a FineVLA-style automatic annotation pipeline for robot
manipulation videos. It supports Chinese and English prompts, configurable robot
types, multi-view frame merging, stage-specific frame sampling, and timestamped
refinement outputs.

Prompts live in `prompts_cn/` and `prompts/`; flow implementations live in
`flows/`; shared runtime helpers live in `utils/`.

## Configuration

Runtime defaults are configured in [config/config.yaml](config/config.yaml). This
YAML file is the single source of default parameters. The Python module
[utils/config.py](utils/config.py) only loads YAML and exports the existing
`DEFAULT_*`, `MIN_*`, and `MAX_*` constants for compatibility; it does not keep
its own hidden defaults.

You can also point to another YAML file:

```powershell
$env:ANNOTATE_CONFIG="C:\path\to\config.yaml"
```

Environment variables with the `ANNOTATE_*` prefix still override YAML values.
For example:

```powershell
$env:ANNOTATE_ANALYSIS_RESIZE_WIDTH="224"
$env:ANNOTATE_REFINEMENT_RESIZE_WIDTH="448"
$env:ANNOTATE_MERGE_VIEW_NAMES="observation.rgb_images.camera_front,observation.rgb_images.camera_top"
```

If `ANNOTATE_CONFIG` points to a custom YAML file, that file must contain the
same required keys. Missing keys fail fast during import.

Complete YAML structure:

```yaml
model:
  name: Qwen3.5-27B
  base_url: http://localhost:8002/v1

prompt:
  language: cn
  robot_type: bimanual

stages:
  analysis:
    fps: 1.0
    max_tokens: 512
    resize_width: 224
    draw_timestamps: false
  refinement:
    fps: 5.0
    max_tokens: 2048
    resize_width: 448
    draw_timestamps: true

vlm_sampling:
  temperature: 0.0
  top_p: 0.95
  top_k: 0

video:
  max_frames: 128
  merge_view_names:
    - observation.rgb_images.camera_front
    - observation.rgb_images.camera_top
  jpeg_quality: 75
  min_api_frames: 2

workers:
  max_step_workers: 8

logging:
  level: INFO
  format: "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
```

`analysis` normally does not need timestamps, so `draw_timestamps` is disabled
by default. `refinement` uses timestamps to add `start_time` and `end_time` for
each action.

## Implemented Flows

| Flow | Function | Stages |
|---|---|---|
| `single_view_no_steps_raw` | `flows/flow_analysis_refinement.py` | `analysis -> refinement` |

## Stage Meaning

`analysis` watches sampled frames, uses the configured `robot_type`, and
extracts a coarse `action_sequence` plus `main_object`. The action sequence is
a chronological list of objects:

```json
{
  "executor": "left",
  "action": "抓住",
  "object": "笔记本电脑"
}
```

For bimanual robots, `executor` should be `left`, `right`, or `both`. For mobile
manipulators, use `base` for navigation and `arm` for manipulation. Actions are
ordered by their start time: the action that starts earlier appears earlier,
even if actions overlap.

`refinement` watches the video again, with timestamp overlays enabled by
default, and adds a timestamped sequence:

```json
{
  "executor": "right",
  "action": "接近",
  "object": "笔记本电脑",
  "start_time": "00:01.00",
  "end_time": "00:02.20"
}
```

It also outputs `fineGrainedSteps` and `refinedInstruction`.

## Multi-View Input

`video_path` may be a string, a list, or a dict. For dict input, keys are view
names and values are video paths. The configured `video.merge_view_names`
selects which views are merged.

For multi-view input, frames at the same timestamp are vertically concatenated.
The first selected view is the primary view. Spatial descriptions such as
left/right/front/back/far/close use the first view as reference; other views
only help confirm occlusion, contact, and depth.

## Basic Usage

```python
from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import run_single_view_no_steps_raw

client = create_openai_client()

result = run_single_view_no_steps_raw(
    client,
    video_path={
        "observation.rgb_images.camera_front": r"C:\path\front.mp4",
        "observation.rgb_images.camera_top": r"C:\path\top.mp4",
    },
    initial_instruction="place the laptop onto the laptop stand",
)

print(result.to_dict())
```

## Example CLI

Run the default batch:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py
```

Useful CLI overrides:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py `
  --analysis-fps 1 `
  --refinement-fps 5 `
  --analysis-resize-width 224 `
  --refinement-resize-width 448 `
  --no-analysis-draw-timestamps `
  --refinement-draw-timestamps `
  --log-level INFO
```

The CLI logs stage timing, frame loading time, VLM request time, token usage,
and per-record batch runtime. Set `logging.level` in `config/config.yaml`, or
override it with `--log-level DEBUG`.

## Debug Frames

To inspect the actual frames sent to the VLM, run:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py
```

By default this uses `example/robot_mind2_camera_top_tasks.json`, task index 0,
the configured merge views, and writes sampled images to
`debug_frames/multiview_timestamp_default`.

Use stage defaults explicitly:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage analysis
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage refinement
```

## Output Shape

Every flow returns `AnnotationResult`:

- `flow_name`: stable flow name.
- `success`: whether every stage produced parseable JSON or a fallback.
- `output`: user-facing annotation payload.
- `output.analysisResult.action_sequence`: coarse chronological actions.
- `output.timestampedActionSequence`: refinement actions with `start_time` and
  `end_time`.
- `output.fineGrainedSteps`: detailed natural-language steps.
- `output.refinedInstruction`: final refined instruction.
- `stages`: intermediate VLM stage outputs and token usage.

The old `run_standard_two_stage` name is kept as an alias of
`run_single_view_no_steps_raw` for compatibility.
