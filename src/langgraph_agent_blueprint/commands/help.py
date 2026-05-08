"""Slash-command module for parsing, registering, or executing user-facing control commands."""

from .builtin import _help as handler

__all__ = ["handler"]

