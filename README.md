# VLM Auto Annotation

VLM Auto Annotation is a contract-first stage workflow for robot manipulation
video annotation. The only runtime path is:

```text
configs/default.yaml + workflow yaml -> WorkflowRunner -> Stage plugins -> ArtifactStore -> current output
```

## Main Entry Points

- Python workflow: `vlm_auto_annotation.app.run_workflow.run_workflow`
- Python single stage: `vlm_auto_annotation.app.run_stage.run_stage`
- CLI: `python -m vlm_auto_annotation.cli.main`

## Configuration

Runtime configuration lives under `configs/`.

- `configs/default.yaml`: model, prompt, artifact, output, exports, and stage defaults.
- `configs/workflows/*.yaml`: ordered stage lists.
- `configs/experiments/*.yaml`: experiment-level export rules.

The old `config/` directory is not part of the current architecture.

## Stages

Current built-in stages:

- `scene`
- `analysis`
- `refinement`

Stages are registered through `core/registry.py` and executed by
`core/workflow.py`. A stage owns prompt rendering, model call parsing, and
contract validation. The runner only schedules stages by name.

## Dynamic Exports

Stage-to-stage variables are controlled by `exports` config rules:

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
```

Raw exported values keep their original type in `context.exports`. Prompt-ready
values are written to `context.formatted_exports`.

Prompt templates can reference nested variables:

```text
Scene executors:
{scene.executors}
```

## Minimal Python Usage

```python
from vlm_auto_annotation.app.run_workflow import run_workflow
from vlm_auto_annotation.utils.api_client import create_openai_client

client = create_openai_client(api_key="EMPTY", base_url="http://localhost:8002/v1")

result = run_workflow(
    client=client,
    video_path="demo.mp4",
    instruction="pick up the cup",
    video_id="demo",
    workflow_name="vla_phase_annotation",
    prompt_language="cn",
    robot_type="bimanual",
)
```

## Tests

```powershell
python -B -m unittest discover -s tests -v
```
