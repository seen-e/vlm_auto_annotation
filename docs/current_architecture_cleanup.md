# Current Architecture Cleanup

This cleanup removes historical runtime paths and leaves the current workflow
architecture as the only implementation.

## Removed Runtime Paths

- Removed the old `flows/` entrypoint package.
- Removed the old `config/` directory and constant-based `utils/config.py`.
- Removed the `annotation_pipeline/` adapter/parser/output package.
- Removed generated `outputs/artifacts/` files from the repository.
- Removed output branches that produced previous result formats.
- Removed old prompt fields such as `operation_units`, `manipulated_objects`,
  `action_steps`, and `video_summary`.

## Current Main Flow

The only main flow is:

```text
run_workflow -> WorkflowRunner -> StageRegistry -> BaseStage lifecycle -> ArtifactStore -> compose_annotation_result
```

Stages are configured by workflow YAML files and created by name through the
registry. The runner does not know scene, analysis, or refinement field
semantics.

## Stage Interfaces

Each stage consumes:

- `StageContext`
- stage media config
- prompt templates
- dynamic input variables from `context.formatted_exports`

Each stage produces:

- raw model response
- parsed JSON
- typed contract
- dynamic exports
- artifact records

## Adding A Stage

1. Add a contract model under `contracts/`.
2. Add `stages/<name>/stage.py`, `prompt.py`, `parser.py`, and `postprocess.py`.
3. Register it in `core/registry.py`.
4. Add it to a workflow YAML.
5. Add export rules for fields that later stages need.

## Configuring Prompt Inputs And Exports

Use `exports` in `configs/default.yaml` or an experiment YAML:

```yaml
exports:
  - id: analysis_actions
    source_stage: analysis
    source_path: candidate_segments
    target_name: analysis.candidate_segments
    default: []
    format: compact_json
    source_kind: contract
    enabled: true
```

Prompt templates can reference `{analysis.candidate_segments}` directly.

## Unsupported Interfaces

The package no longer supports the removed flow wrapper, constant-based config,
previous result schemas, or previous prompt field names.
