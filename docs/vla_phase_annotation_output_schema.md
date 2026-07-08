# VLA Phase Annotation 输出结构说明

## 1. 背景

`vla_phase_annotation` 流程处理单个 VLA episode，经过三个阶段生成最终标注结果：

```
scene -> analysis -> refinement -> build_final_annotation -> output
```

本次重构之前，默认 `output` dict 将最终结果与中间阶段结果混排在一起，存在以下问题：

- **默认输出冗余**：`scene_context`、`candidate_segments`、`refined_segments`、`changes`
  全部序列化到同一个 dict 中，尽管其中很多字段可从最终的 `action_sequence` 推导或已被其替代。
- **`AnnotationResult.stages` 总是保存完整 `StageResult` 对象**（包含原始 VLM 响应），
  导致序列化结果体积过大。
- **`debug=True` 时的 `debug.legacy` 块** 与 `output` 和 `stages` 中已有的字段大量重复。

本次重构将输出拆分为四个清晰的层级：

| 层级 | 用途 | 默认开启 |
|------|------|:---:|
| **轻量输出 (lightweight)** | 下游训练、评估、数据集构建 | 是 |
| **调试输出 (debug)** | 单次运行排查（校验警告、耗时、阶段元数据） | 否 |
| **追溯输出 (trace)** | 完整流程复现（原始输出、解析后合约） | 否 |
| **兼容输出 (legacy)** | 旧下游代码兼容（已弃用） | 否 |

## 2. 整体流程不变

以下内容保持不变：

- **阶段执行顺序**：scene → analysis → refinement（不变）
- **模型调用逻辑**：`call_json_stage` / `call_vlm` 逻辑未修改
- **Prompt 构造**：prompt 模板未做语义性修改
- **解析器与适配器**：`parse_scene_output`、`parse_analysis_output`、`parse_refinement_output`、
  `old_*_output_to_new` 未修改
- **视频加载**：`load_video_or_views_as_media_parts` 未修改
- **处理后媒体保存**：`save_processed_stages` + `save_processed_dir` 行为不变

## 3. 默认轻量输出

默认对所有调用生效，适用于：

- 批量 VLA episode 标注
- 下游训练 / 评估
- 数据集构建

**结构示例：**

```json
{
  "schema_version": "v2",
  "video_id": "episode_001",
  "flow_name": "vla_phase_annotation",
  "task": {
    "initial_instruction": "抓取杯子",
    "refined_instruction": "抓取桌子上的红色杯子",
    "summary": "左机械臂抓取红色杯子"
  },
  "scene": {
    "primary_view": "camera_front",
    "executors": [
      {
        "executor_id": "left",
        "description": "左机械臂",
        "main_workspace": "桌面"
      }
    ],
    "touched_objects": [
      {
        "object_id": "red_cup",
        "description": "桌上的红色杯子",
        "role": "target_object"
      }
    ],
    "background_objects": []
  },
  "segments": [
    {
      "segment_id": "S001",
      "start_time": "00:00.00",
      "end_time": "00:02.50",
      "executor": "left",
      "action": "grasp",
      "objects": ["red_cup"],
      "confidence": 0.92,
      "boundary_reason": "夹爪闭合"
    }
  ],
  "metadata": {
    "model": "Qwen3.6-27B",
    "prompt_language": "cn",
    "robot_type": "bimanual",
    "elapsed_seconds": 12.345
  },
  "validation": {
    "warnings": []
  }
}
```

**默认输出中不再保存的字段**（与旧 v1 格式对比）：

| 移除字段 | 如需获取 |
|----------|----------|
| `candidate_segments` | 设置 `include_intermediate_contracts=True`，见 `intermediate_contracts.analysis` |
| `refined_segments` | 设置 `include_intermediate_contracts=True`，见 `intermediate_contracts.refinement` |
| `changes` | 设置 `include_intermediate_contracts=True`，见 `intermediate_contracts.refinement` |
| 完整 `scene_context` | 设置 `include_intermediate_contracts=True`，见 `intermediate_contracts.scene` |
| `validation_warnings`（顶层 list） | 默认在 `validation.warnings` 中，`include_validation=True`（默认开启） |
| 完整 `AnnotationResult.stages`（含原始 VLM 输出） | 设置 `include_stage_objects=True` 或 `include_trace=True` |
| 旧 `debug.legacy` 字段 | 设置 `include_legacy_fields=True`，见 `legacy_output` |
| 原始 VLM 响应文本 | 设置 `include_trace=True`，见 `trace.stage_outputs` |

## 4. 调试输出

用途：排查单次运行，不收集原始 VLM 文本。

**开启方式：**

```python
result = run_vla_phase_annotation(..., include_debug=True)
# 或使用旧参数：
result = run_vla_phase_annotation(..., debug=True)
```

也可以通过配置开启：

```yaml
# config/config.yaml
output:
  include_debug: true
```

或环境变量：

```bash
set ANNOTATE_OUTPUT_INCLUDE_DEBUG=true
```

**包含内容：**

- `debug.validation` — 校验警告
- `debug.timing` — 各阶段加载和后处理耗时 + 总耗时
- `debug.stage_metadata` — 媒体加载参数（fps、resize_width、selected_views 等）

**结构示例：**

```json
{
  "debug": {
    "validation": {
      "warnings": [
        "video_id=ep001 stage=analysis: object 'unknown_obj' not in scene"
      ]
    },
    "timing": {
      "scene_load_seconds": 0.512,
      "scene_postprocess_seconds": 0.012,
      "analysis_load_seconds": 0.489,
      "analysis_postprocess_seconds": 0.008,
      "refinement_load_seconds": 0.501,
      "refinement_postprocess_seconds": 0.015,
      "total_seconds": 12.345
    },
    "stage_metadata": {
      "scene": {
        "input_mode": "image_sequence",
        "target_fps": 1.0,
        "sampled_frames": 24,
        "resize_width": 224,
        "selected_views": ["camera_front", "camera_top"],
        "draw_timestamps": true,
        "load_elapsed_seconds": 0.512,
        "postprocess_elapsed_seconds": 0.012
      },
      "analysis": { /* 同上结构 */ },
      "refinement": { /* 同上结构 */ }
    }
  }
}
```

**调试输出不包含：**

- 原始 VLM 响应文本
- prompt 全文
- media parts / base64
- legacy 兼容字段

## 5. 追溯输出

用途：完整流程复现和深度排查。

**开启方式：**

```python
result = run_vla_phase_annotation(..., include_trace=True)
```

也可以通过配置开启：

```yaml
# config/config.yaml
output:
  include_trace: true
```

或环境变量：

```bash
set ANNOTATE_OUTPUT_INCLUDE_TRACE=true
```

开启 `include_trace=True` 时，`include_stage_objects` 自动生效（`AnnotationResult.stages` 会包含完整 `StageResult` 对象）。

**包含内容：**

- `trace.stage_outputs` — 每个 VLM 阶段解析后的 JSON 输出
- `trace.stage_contracts` — 每个阶段序列化后的 Pydantic 合约

**结构示例：**

```json
{
  "trace": {
    "stage_outputs": {
      "scene": { "scene_context": { ... } },
      "analysis": { "candidate_segments": [ ... ] },
      "refinement": { "refined_segments": [ ... ], "changes": [ ... ] }
    },
    "stage_contracts": {
      "scene": { "primary_view": "camera_front", "executors": [ ... ] },
      "analysis": { "candidate_segments": [ ... ] },
      "refinement": { "refined_segments": [ ... ], "changes": [ ... ] }
    }
  }
}
```

**追溯输出不包含：**

- media parts / base64
- 完整二进制图像数据

## 6. 兼容输出

用途：**临时**兼容旧下游代码。已弃用，不建议新代码使用。

**开启方式：**

```python
result = run_vla_phase_annotation(..., include_legacy_fields=True)
```

也可以通过配置开启：

```yaml
# config/config.yaml
output:
  include_legacy_fields: true
```

或环境变量：

```bash
set ANNOTATE_OUTPUT_INCLUDE_LEGACY=true
```

**结构示例：**

```json
{
  "legacy_output": {
    "analysisResult": {
      "robot_type": "bimanual",
      "sceneContext": { ... },
      "action_sequence": [ ... ],
      "main_object": "red_cup"
    },
    "sceneContext": { ... },
    "timestampedActionSequence": [ ... ],
    "fineGrainedSteps": [ ... ],
    "refinedInstruction": "..."
  }
}
```

> **已弃用。** 新下游代码应使用轻量输出中的 `segments`、`scene`、`task` 字段。

## 7. 中间合约

**开启方式：**

```python
result = run_vla_phase_annotation(..., include_intermediate_contracts=True)
```

也可以通过配置开启：

```yaml
# config/config.yaml
output:
  include_intermediate_contracts: true
```

或环境变量：

```bash
set ANNOTATE_OUTPUT_INCLUDE_INTERMEDIATE_CONTRACTS=true
```

这会在输出中追加三个阶段的完整序列化 Pydantic 合约：

```json
{
  "intermediate_contracts": {
    "scene": { ... },
    "analysis": { ... },
    "refinement": { ... }
  }
}
```

适用于：

- parser 调试
- contract schema 对齐
- 对比 analysis 候选段与 refinement 精炼结果

不建议在批量标注流水线中开启。

## 8. `AnnotationResult.stages` 保存策略

| 配置 | `stages` 内容 |
|------|------|
| 默认（`include_stage_objects=False`） | 空 dict `{}` |
| `include_stage_objects=True` | 完整的 scene / analysis / refinement `StageResult` 对象 |
| `include_trace=True` | 同 `include_stage_objects=True`（自动启用） |

原因：`stages` 包含原始 VLM 输出和内部上下文，下游训练几乎不需要，
且会显著增加序列化体积。

## 9. 处理后媒体保存策略

与之前版本保持一致。

```python
result = run_vla_phase_annotation(
    ...,
    save_processed_stages=["scene", "analysis"],
    save_processed_dir="outputs/processed_media",
)
```

这会将预处理后的图像序列或 mp4 文件按阶段和 episode 名称保存到磁盘。
它与 JSON 输出各层是**正交**的——处理后媒体永远不会嵌入到 `output` / `debug` / `trace` 中。

配置方式：

```yaml
# config/config.yaml
processed_media:
  save_processed_stages: ["scene", "analysis"]
  save_processed_dir: "outputs/processed_media"
```

## 10. 参数与配置对照表

所有输出控制开关支持三层覆盖：**函数参数 > 环境变量 > config.yaml**。

| 函数参数 | 默认值（来自 config） | 环境变量 | config.yaml 路径 |
|----------|:---:|------|------|
| `output_schema_version` | `"v2"` | `ANNOTATE_OUTPUT_SCHEMA_VERSION` | `output.schema_version` |
| `include_validation` | `True` | `ANNOTATE_OUTPUT_INCLUDE_VALIDATION` | `output.include_validation` |
| `include_debug` | `False` | `ANNOTATE_OUTPUT_INCLUDE_DEBUG` | `output.include_debug` |
| `include_trace` | `False` | `ANNOTATE_OUTPUT_INCLUDE_TRACE` | `output.include_trace` |
| `include_intermediate_contracts` | `False` | `ANNOTATE_OUTPUT_INCLUDE_INTERMEDIATE_CONTRACTS` | `output.include_intermediate_contracts` |
| `include_legacy_fields` | `False` | `ANNOTATE_OUTPUT_INCLUDE_LEGACY` | `output.include_legacy_fields` |
| `include_stage_objects` | `False` | `ANNOTATE_OUTPUT_INCLUDE_STAGE_OBJECTS` | `output.include_stage_objects` |
| `debug` | `False` | —（无独立环境变量，旧参数） | — |

**config.yaml 中的 `output` section：**

```yaml
output:
  schema_version: v2
  include_validation: true
  include_debug: false
  include_trace: false
  include_intermediate_contracts: false
  include_legacy_fields: false
  include_stage_objects: false
```

## 11. 推荐使用方式

### 默认批量标注

```python
result = run_vla_phase_annotation(
    client=client,
    video_path="episode_001.mp4",
    initial_instruction="抓取杯子",
)
# result.output 是轻量 JSON
# result.stages 为空（轻量模式）
```

### 单次调试

```python
result = run_vla_phase_annotation(
    client=client,
    video_path="episode_001.mp4",
    initial_instruction="抓取杯子",
    include_debug=True,   # 或 debug=True
)
# result.output.debug 包含 timing、metadata、validation
```

### 完整追溯（复现）

```python
result = run_vla_phase_annotation(
    client=client,
    video_path="episode_001.mp4",
    initial_instruction="抓取杯子",
    include_trace=True,
)
# result.output.trace 包含各阶段原始输出和解析后合约
# result.stages 包含完整 StageResult 对象
```

### 兼容旧下游

```python
result = run_vla_phase_annotation(
    client=client,
    video_path="episode_001.mp4",
    initial_instruction="抓取杯子",
    include_legacy_fields=True,
)
# result.output.legacy_output 包含旧字段名
```

### 保存处理后媒体 + 标注

```python
result = run_vla_phase_annotation(
    client=client,
    video_path="episode_001.mp4",
    initial_instruction="抓取杯子",
    save_processed_stages=["scene", "analysis"],
    save_processed_dir="outputs/processed_media",
)
```

## 12. 迁移指南

### 旧代码

```python
output = result.output
segments = output["refined_segments"]
candidates = output["candidate_segments"]
scene = output["scene_context"]
warnings = output["validation_warnings"]
```

### 新代码

```python
output = result.output
segments = output["segments"]
candidates = output.get("intermediate_contracts", {}).get("analysis", {}).get("candidate_segments", [])
scene = output["scene"]
warnings = output.get("validation", {}).get("warnings", [])
```

### 临时过渡

如果无法立即迁移，可临时开启 legacy 字段：

```python
result = run_vla_phase_annotation(..., include_legacy_fields=True)
# 旧字段名在 result.output["legacy_output"] 下
```

或开启中间合约：

```python
result = run_vla_phase_annotation(..., include_intermediate_contracts=True)
# 完整解析后合约在 result.output["intermediate_contracts"] 下
```

## 13. 注意事项

- 默认轻量输出**不适合**做 prompt/debug 复现，如需复现请使用 `include_trace=True`。
- 追溯输出适合复现，但**不适合**大规模长期存储（体积较大）。
- 处理后媒体可能体积很大，只在必要阶段开启。
- base64 media parts **永远不会**写入 `output`、`debug` 或 `trace`。
- 批量跑几十万 episode 时，推荐只使用默认轻量输出。
- 所有开关默认值继承自 `config/config.yaml` 中的 `output` section，修改该文件即可全局生效。
- 环境变量可以在不修改代码和配置文件的情况下临时覆盖（如 `ANNOTATE_OUTPUT_INCLUDE_DEBUG=true`）。
