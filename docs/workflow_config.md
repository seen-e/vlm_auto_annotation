# Workflow Configuration

Default runtime values live in `configs/default.yaml`.

Workflow files live in `configs/workflows/`. A workflow only defines stage order and output options:

```yaml
name: vla_phase_annotation
stages:
  - scene
  - analysis
  - refinement
output:
  include_lightweight: true
  include_debug: false
```

## Stage Media Parameters

Each stage has independent media parameters:

- `input_mode`: `image_sequence` or `video`
- `fps`
- `max_frames`
- `resize_width`
- `jpeg_quality`
- `min_api_frames`
- `draw_timestamps`
- `draw_viewposition`
- `merge_views`
- `merge_mode`: `per_frame` or `timeline_grid`
- `merge_length`
- `merge_view_names`

`merge_view_names` is the only source for selecting and ordering multi-view inputs. The first selected view is the primary view for left/right/front/back language.

## Artifacts

`artifacts` controls saved stage data:

```yaml
artifacts:
  root_dir: outputs/artifacts
  enabled: true
  save_prompt: true
  save_raw_response: true
  save_parsed: true
  save_contract: true
  save_media_meta: true
  save_processed_media: false
```

Contracts saved as `contract.json` can be loaded by later runs through `load_outputs`.
