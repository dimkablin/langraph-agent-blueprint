"""Slash-command module for parsing, registering, or executing user-facing control commands."""

from .builtin import _doctor as handler

__all__ = ["handler"]

