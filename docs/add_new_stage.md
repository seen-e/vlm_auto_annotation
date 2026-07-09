# Add A New Stage

1. Define or reuse a contract in `contracts/`.
2. Create a package under `stages/<stage_name>/`.
3. Implement:
   - `prompt.py`
   - `parser.py`
   - `postprocess.py`
   - `stage.py`
4. Subclass `BaseStage` and set:

```python
class MyStage(BaseStage):
    name = "my_stage"
    required_contracts = ("scene",)
```

5. Register the stage in `core/registry.py`.
6. Add the stage to a workflow YAML.
7. Add tests for prompt building, parsing, postprocessing, artifact saving, and workflow execution.

The stage should not assemble final outputs. Final JSON views belong in `outputs/`.

## Add Stage Exports

Expose fields to later stages by adding export rules to a workflow or experiment
config:

```yaml
exports:
  - id: my_stage_objects
    source_stage: my_stage
    source_path: objects[*].name
    target_name: my_stage.object_names
    default: []
    format: bullet
    source_kind: contract
    enabled: true
```

Later prompt templates can reference `{my_stage.object_names}`. No runner change
is required.
