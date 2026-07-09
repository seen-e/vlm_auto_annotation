"""Prompt package loader."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def normalize_prompt_language(value: Any) -> str:
    text = str(value or "cn").strip().lower().replace("-", "_")
    aliases = {"zh": "cn", "zh_cn": "cn", "chinese": "cn", "english": "en"}
    text = aliases.get(text, text)
    return text if text in {"cn", "en"} else "cn"


def load_prompt_package(language: Any):
    lang = normalize_prompt_language(language)
    package_name = ".prompts_cn" if lang == "cn" else ".prompts_en"
    return import_module(package_name, package=__package__)


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def safe_format(template: str, **kwargs: Any) -> str:
    return template.format_map(SafeFormatDict(kwargs))
