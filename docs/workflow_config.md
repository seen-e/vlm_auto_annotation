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
  include_contracts: false
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

## Dynamic Stage Exports

Stage-to-stage prompt variables are configured through export rules. The raw
export keeps its original type, such as `dict`, `list`, string, number, or
`null`. A separate formatted copy is generated for prompt injection.

```yaml
exports:
  - id: scene_executors
    source_stage: scene
    source_path: executors
    target_name: scene.executors
    default: []
    format: json
    source_kind: contract
    enabled: true

  - id: analysis_actions
    source_stage: analysis
    source_path: candidate_segments[*].action
    target_name: analysis.action_names
    default: []
    format: bullet
    source_kind: contract
    enabled: true
```

Fields:

- `source_stage`: stage that produced the data.
- `source_path`: dotted path inside the parsed output or contract. Supports `a.b`, `items[0]`, and `items[*].name`.
- `target_name`: variable path written into `StageContext`, such as `analysis.action`.
- `default`: value used when extraction fails.
- `format`: `json`, `compact_json`, `bullet`, `text`, or `raw`.
- `source_kind`: `contract`, `parsed`, or `auto`.
- `enabled`: disable a rule without deleting it.

Prompt templates can reference nested target names:

```text
Scene executors:
{scene.executors}

Previous actions:
{analysis.action_names}
```

Missing variables render as empty strings, so experiment prompts can be swapped
without changing Python code.

## Experiment Overrides

Experiment YAML files can replace, append, or merge export rules:

```yaml
experiment:
  name: experiment_action_sequence

exports_mode: replace
exports:
  - id: analysis_actions
    source_stage: analysis
    source_path: candidate_segments
    target_name: analysis.action_sequence
    default: []
    format: compact_json
    source_kind: contract
    enabled: true
```

Supported `exports_mode` values:

- `replace`: experiment exports replace the default list.
- `append`: experiment exports append to the default list.
- `merge_by_id`: experiment exports override default rules with the same `id`.
