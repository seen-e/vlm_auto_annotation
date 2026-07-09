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
