"""Slash-command module for parsing, registering, or executing user-facing control commands."""

from .builtin import _resume as handler

__all__ = ["handler"]

