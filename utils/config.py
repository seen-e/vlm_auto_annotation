"""Runtime defaults for VLM auto annotation."""

from __future__ import annotations

import os

# 默认使用的视觉语言模型名称，可通过 ANNOTATE_MODEL 覆盖。
DEFAULT_MODEL = os.environ.get("ANNOTATE_MODEL", "Qwen3-VL-30B-A3B-Instruct")
# OpenAI 兼容接口的基础地址，可通过 ANNOTATE_BASE_URL 覆盖。
DEFAULT_BASE_URL = os.environ.get(
    "ANNOTATE_BASE_URL",
    "http://localhost:8002/v1",
)

# 初始分析阶段的视频采样帧率，控制送入模型做粗分析的帧密度。
DEFAULT_ANALYSIS_FPS = float(os.environ.get("ANNOTATE_ANALYSIS_FPS", "5.0"))
# 细化阶段的视频采样帧率，控制对候选片段进一步复核时的帧密度。
DEFAULT_REFINEMENT_FPS = float(os.environ.get("ANNOTATE_REFINEMENT_FPS", "5.0"))

# 标注时使用的机器人类型，可选 single_arm、bimanual、mobile_manipulator、unknown。
DEFAULT_ROBOT_TYPE = os.environ.get("ANNOTATE_ROBOT_TYPE", "bimanual")
# 提示词语言，可选 cn/en；cn 使用 prompts_cn，en 使用 prompts。
DEFAULT_PROMPT_LANGUAGE = os.environ.get("ANNOTATE_PROMPT_LANGUAGE", "en")

# analysis 阶段模型回复的最大 token 数；设为 0 表示使用模型服务默认限制。
DEFAULT_ANALYSIS_MAX_TOKENS = int(os.environ.get("ANNOTATE_ANALYSIS_MAX_TOKENS", "512"))
# refinement 阶段模型回复的最大 token 数；设为 0 表示使用模型服务默认限制。
DEFAULT_REFINEMENT_MAX_TOKENS = int(os.environ.get("ANNOTATE_REFINEMENT_MAX_TOKENS", "2048"))
# detail_refinement 阶段模型回复的最大 token 数；设为 0 表示使用模型服务默认限制。
DEFAULT_DETAIL_REFINEMENT_MAX_TOKENS = int(os.environ.get("ANNOTATE_DETAIL_REFINEMENT_MAX_TOKENS", "2048"))

# VLM 输出采样温度，数值越低越稳定，越高越随机。
DEFAULT_VLM_TEMPERATURE = float(os.environ.get("ANNOTATE_VLM_TEMPERATURE", "0.0"))
# VLM nucleus sampling 参数，控制候选 token 的累计概率范围。
DEFAULT_VLM_TOP_P = float(os.environ.get("ANNOTATE_VLM_TOP_P", "0.95"))
# VLM top-k sampling 参数；设为 0 表示不显式传 top_k，使用模型服务默认值。
DEFAULT_VLM_TOP_K = int(os.environ.get("ANNOTATE_VLM_TOP_K", "0"))

# 单次处理最多抽取的视频帧数，用于限制请求体大小和推理耗时。
DEFAULT_MAX_FRAMES = int(os.environ.get("ANNOTATE_MAX_FRAMES", "128"))
# 送入模型前将视频帧缩放到的目标宽度，用于控制图像尺寸和显存占用。
DEFAULT_RESIZE_WIDTH = int(os.environ.get("ANNOTATE_RESIZE_WIDTH", "224"))
# 编码视频帧为 JPEG 时使用的质量参数，数值越高图像越清晰但体积越大。
DEFAULT_JPEG_QUALITY = int(os.environ.get("ANNOTATE_JPEG_QUALITY", "75"))
# 调用模型接口时至少提供的帧数，避免片段过短导致模型输入不足。
MIN_API_FRAMES = int(os.environ.get("ANNOTATE_MIN_API_FRAMES", "2"))
# 并行执行步骤的最大工作线程数，用于限制并发量和本机资源占用。
MAX_STEP_WORKERS = int(os.environ.get("ANNOTATE_MAX_STEP_WORKERS", "8"))
