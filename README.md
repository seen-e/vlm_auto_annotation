# VLM Auto Annotation

This package implements a VLA phase segmentation annotation pipeline for robot
manipulation videos. The public flow remains:

```text
single_view_no_steps_raw: analysis -> refinement
```

The flow name, function signature, and `AnnotationResult` return type are kept
for compatibility. `video_path` can still be a string, list, or dict. Dict/list
multi-view inputs are merged vertically according to `video.merge_view_names`;
no separate multiview flow is used.

Internally, the two public stages are split into four VLM calls:

```text
analysis:
  analysis_scene
  analysis_events

refinement:
  refinement_phases
  refinement_boundaries
```

## Configuration

Runtime defaults are configured in [config/config.yaml](config/config.yaml).
[utils/config.py](utils/config.py) only loads YAML and exports compatibility
constants such as `DEFAULT_MODEL`.

Important defaults:

```yaml
stages:
  analysis:
    fps: 1.0
    max_tokens: 1024
    resize_width: 224
    draw_timestamps: false
  refinement:
    fps: 5.0
    max_tokens: 3072
    resize_width: 448
    draw_timestamps: true

video:
  max_frames: 128
  merge_view_names:
    - observation.rgb_images.camera_front
    - observation.rgb_images.camera_top
```

Environment variables with the `ANNOTATE_*` prefix can still override YAML
values temporarily. `ANNOTATE_CONFIG` can point to a different YAML file.

## Analysis Output

`analysis` produces a stable scene model plus a rough event sequence. It does
not output timestamps.

```json
{
  "analysisResult": {
    "scene": {
      "robot_type": "bimanual",
      "arms": [
        {
          "arm_id": "left",
          "description": "left arm stabilizes the stand",
          "best_view": "observation.rgb_images.camera_front"
        }
      ],
      "objects": [
        {
          "object_id": "laptop",
          "description": "笔记本电脑",
          "category": "manipulated_object"
        }
      ]
    },
    "main_object": "laptop",
    "action_sequence": [
      {
        "event_id": "E001",
        "executor": "right",
        "action": "接近",
        "object": "laptop",
        "target": null,
        "rough_order": 1
      }
    ]
  }
}
```

Executor IDs are stable:

- `bimanual`: `left`, `right`, `both`
- `single_arm`: `single`
- `mobile_manipulator`: `base`, `arm`

Objects should be defined once in `analysisResult.scene.objects`, then reused
by `object` and `target` fields.

## Refinement Output

`refinement` receives the full `analysisResult`, watches timestamped frames,
and outputs both backward-compatible timestamps and VLA phase segments.

```json
{
  "timestampedActionSequence": [
    {
      "event_id": "E001",
      "executor": "right",
      "action": "接近",
      "object": "laptop",
      "target": null,
      "start_time": "00:01.00",
      "end_time": "00:02.20"
    }
  ],
  "phaseSegments": [
    {
      "phase_id": "P001",
      "source_event_id": "E001",
      "executor": "right",
      "primitive": "approach",
      "action": "接近",
      "object": "laptop",
      "target": null,
      "start_time": "00:01.00",
      "end_time": "00:02.20",
      "start_condition": "右臂开始接近笔记本电脑",
      "end_condition": "右臂到达笔记本电脑附近并稳定",
      "confidence": 0.82,
      "quality_flags": []
    }
  ]
}
```

Allowed `primitive` values are:

```text
approach, grasp, lift, transfer, place, release, push, pull, rotate, insert,
withdraw, open, close, handover, retract, idle
```

If the VLM omits `phaseSegments`, the flow creates them from
`timestampedActionSequence` and adds
`fallback_from_timestampedActionSequence` to `quality_flags`. Missing
confidence defaults to `0.6`; missing time boundaries add `need_review`.
Single-view inputs add `single_view` to each phase.

`AnnotationResult.stages` records each internal call for debugging:

```text
analysis_scene
analysis_events
refinement_phases
refinement_boundaries
```

## Multi-View Rule

For multi-view input, frames at the same timestamp are vertically concatenated.
The first selected view is the primary view for left/right/front/back spatial
language. Other views only help confirm occlusion, contact, and depth.

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

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py --limit 1 --log-level INFO
```

The CLI logs stage timing, frame loading time, VLM request time, token usage,
and per-record batch runtime. Logs are also saved locally by default under
`logs/` with a timestamped filename. You can override this per run:

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\example\main.py `
  --limit 1 `
  --log-level INFO `
  --log-dir logs `
  --log-to-file
```

Use `--no-log-to-file` to keep console-only logs.

## Debug Frames

```powershell
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage analysis
& 'C:\Users\34927\.conda\envs\py3115\python.exe' .\utils\video_utils.py --stage refinement
```

Debug frames are written under `debug_frames/`.
