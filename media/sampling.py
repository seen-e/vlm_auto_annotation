"""Sampling helpers.

The implementation delegates to the compatibility media backend while the
public API is now split by responsibility.
"""

from .input import build_media_parts

__all__ = ["build_media_parts"]
