# VLM Auto Annotation Architecture

This project now uses a Contract-first + Stage Plugin + Workflow Runner + Artifact Store architecture.

## Layers

- `contracts/`: typed stage contracts. A stage output is valid only after it can be represented by its contract.
- `stages/`: independent stage plugins. `scene`, `analysis`, and `refinement` each own prompt construction, parsing, and postprocessing.
- `core/`: shared runtime objects, including `StageContext`, `BaseStage`, `StageRegistry`, and `WorkflowRunner`.
- `media/`: media input, sampling, preprocessing, montage, encoding, metadata, and saving adapters.
- `llm/`: OpenAI-compatible VLM client and JSON response extraction.
- `artifacts/`: persistent store for prompts, raw responses, parsed JSON, contracts, media metadata, and optional processed media.
- `outputs/`: final output composers. Stages do not assemble the final annotation.

## Runtime Flow

1. `run_workflow` loads `configs/default.yaml` and a workflow YAML.
2. `WorkflowRunner` reads the ordered stage list.
3. `StageRegistry` creates each stage by name.
4. Each `BaseStage` runs the same lifecycle:
   `prepare_input -> build_media -> build_prompt -> call_model -> parse -> postprocess`.
5. `ArtifactStore` saves stage artifacts.
6. `outputs.composer` builds the final `AnnotationResult`.

## Stage Independence

`scene`, `analysis`, and `refinement` can be run alone or composed in a workflow. Later stages declare required previous contracts:

- `scene`: no required contract.
- `analysis`: requires `SceneStageOutput`.
- `refinement`: requires `SceneStageOutput` and `AnalysisStageOutput`.

The runner does not contain stage-specific prompt, parsing, or media logic.
