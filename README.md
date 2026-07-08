# VLM Auto Annotation

This package implements a FineVLA-style automatic annotation pipeline for robot
manipulation videos. It supports Chinese and English prompts, configurable robot
types, multi-view frame merging, stage-specific sampling, and compact VLA phase
annotation output.

Prompts live in `prompts/prompts_cn/` and `prompts/prompts_en/`; the official
flow lives in `flows/`; shared runtime helpers live in `utils/`; normalized
stage contracts, parsers, and adapters live in `annotation_pipeline/`.

## Configuration

Runtime defaults are configured in [config/config.yaml](config/config.yaml).
`utils/config.py` loads YAML and keeps the existing `DEFAULT_*`, `MIN_*`, and
`MAX_*` constants for compatibility.

Use another YAML file with:

```powershell
$env:ANNOTATE_CONFIG="C:\path\to\config.yaml"
```

Environment variables with the `ANNOTATE_*` prefix still override YAML values.
Examples:

```powershell
$env:ANNOTATE_PROMPT_LANGUAGE="cn"
$env:ANNOTATE_ROBOT_TYPE="bimanual"
$env:ANNOTATE_ANALYSIS_MERGE_VIEWS="true"
$env:ANNOTATE_ANALYSIS_MERGE_MODE="timeline_grid"
$env:ANNOTATE_MERGE_VIEW_NAMES="observation.rgb_images.camera_front,observation.rgb_images.camera_top"
```

## Official Flow

| Flow | Function | Stages |
|---|---|---|
| `vla_phase_annotation` | `run_vla_phase_annotation` in `flows/flow_analysis_refinement.py` | `scene -> analysis -> refinement` |

## Stage Contracts

The official flow entry point is `run_vla_phase_annotation`. Internally, VLM
JSON is normalized through Pydantic contracts and legacy adapters in
`annotation_pipeline/`.

| Stage | Responsibility | Main Input | Main Output |
|---|---|---|---|
| `scene` | Establish stable scene context only | video frames, views, robot profile | `scene_context.executors`, `touched_objects`, `background_objects`, `executor_object_map`, `best_observation_views`, `scene_summary` |
| `analysis` | Propose candidate action segments | `scene_context`, sampled frames, optional state-action data | `candidate_segments`, `uncertain_regions`, `analysis_notes` |
| `refinement` | Fix segment boundaries and segment structure | `candidate_segments`, timestamped frames, refinement rules | `refined_segments`, `changes` |
| label adapter | Build compact final annotation | `scene_summary`, `refined_segments` | `task_summary`, `action_sequence`, `touched_objects`, `final_caption`, `metadata` |

`analysis` does not repeat scene background. `refinement` does not write final
long-form descriptions by default. Old fields such as `sceneContext`,
`action_sequence`, `timestamped_action_sequence`, `fineGrainedSteps`, and
`refinedInstruction` are accepted by adapters. When `debug=True`, legacy
intermediate fields are placed under `output.debug`.

Normalized refined segment example:

```json
{
  "segment_id": "S001",
  "start_time": "00:01.00",
  "end_time": "00:02.20",
  "executor": "left",
  "action": "grasp",
  "objects": ["cup"],
  "boundary_reason": "gripper closes on cup",
  "confidence": 0.82
}
```

## Output Shape

`AnnotationResult.output` is now the compact user-facing payload:

```json
{
  "video_id": "episode_001",
  "task_summary": "left arm manipulates a cup",
  "action_sequence": [
    {
      "segment_id": "S001",
      "start_time": "00:01.00",
      "end_time": "00:02.20",
      "executor": "left",
      "action": "grasp",
      "objects": ["cup"]
    }
  ],
  "touched_objects": ["cup"],
  "final_caption": "00:01.00-00:02.20 left grasp cup",
  "scene_context": {},
  "candidate_segments": [],
  "refined_segments": [],
  "changes": [],
  "validation_warnings": [],
  "metadata": {}
}
```

`AnnotationResult.stages` still contains raw per-stage VLM outputs and token
usage for compatibility and debugging.

## Multi-View Input

`video_path` may be a string, a list, or a dict. For dict input, keys are view
names and values are video paths. Each stage has its own
`stages.<stage>.merge_view_names` list selecting which views are merged.

Each stage has its own `input_mode`, `max_frames`, `merge_view_names`,
`jpeg_quality`, `min_api_frames`, and `merge_views` settings. `input_mode:
image_sequence` keeps the existing behavior and sends sampled frames as
`image_url` parts. `input_mode: video` uses the same preprocessing path, then
re-encodes the processed frame sequence and sends it as a `video_url` part.

When `merge_views` is `false`,
multi-view input is not concatenated and that stage uses only the primary view,
i.e. the first path/view in `video_path`.

When a stage's `merge_views` is `true`, `merge_mode` controls the layout:

- `per_frame`: frames at the same timestamp are vertically concatenated. Each
  sampled timestamp is sent as a separate image.
- `timeline_grid`: views are arranged vertically and sampled times horizontally
  in one large image. The left side labels view names, the top labels time
  columns, and each cell may still include an in-frame timestamp according to
  that stage's `draw_timestamps`.

The first selected view is always the primary view. Spatial descriptions such as
left/right/front/back/far/close use the first view as reference; other views only
help confirm occlusion, contact, and depth.

## Processed Media Debugging

`config/config.yaml` can save the final visual inputs that each stage sends to
the VLM:

```yaml
processed_media:
  save_processed_stages: []
  save_processed_dir: ""
```

`save_processed_stages` accepts `scene`, `analysis`, and `refinement`. Empty,
null, or missing means no processed media is saved. When it is non-empty,
`save_processed_dir` must be set. Image-sequence stages are saved as
`{save_processed_dir}/{stage}/{episode}/frame_000000.jpg`; video stages are
saved as `{save_processed_dir}/{stage}/{episode}.mp4`.

## Basic Usage

```python
from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import run_vla_phase_annotation

client = create_openai_client()

result = run_vla_phase_annotation(
    client,
    video_path={
        "observation.rgb_images.camera_front": r"C:\path\front.mp4",
        "observation.rgb_images.camera_top": r"C:\path\top.mp4",
    },
    initial_instruction="place the laptop onto the laptop stand",
    prompt_language="cn",
    video_id="episode_001",
    debug=False,
)

print(result.output)
```

## Example CLI

Run the default batch:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py
```

Useful overrides:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py `
  --analysis-fps 1 `
  --scene-resize-width 224 `
  --analysis-merge-mode timeline_grid `
  --refinement-fps 5 `
  --analysis-resize-width 224 `
  --refinement-resize-width 448 `
  --no-merge-views `
  --no-analysis-draw-timestamps `
  --refinement-draw-timestamps `
  --log-level INFO
```

## Debug Frames

To inspect the frames sent to the VLM:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py
```

Use stage defaults explicitly:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage analysis
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage refinement
```

## Tests

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' -m compileall annotation_pipeline flows prompts utils example
& 'C:\Users\34927\.conda\envs\py3115\python.exe' -m unittest discover -s annotation_pipeline/tests
```
