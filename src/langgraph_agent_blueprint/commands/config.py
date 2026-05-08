"""Typed runtime configuration loaded from environment, CLI overrides, and project settings."""

from .builtin import _config as handler

__all__ = ["handler"]

