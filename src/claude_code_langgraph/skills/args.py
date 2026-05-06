"""Typed Pydantic argument schemas and prompt formatting for skill invocations."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


MAX_SKILL_TEXT_CHARS = 12000
MAX_SKILL_LIST_ITEMS = 50
MAX_SKILL_LIST_ITEM_CHARS = 1000


class BaseSkillArgs(BaseModel):
    """Base class for typed skill arguments."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GenericSkillArgs(BaseSkillArgs):
    """Fallback arguments for file-based skills without a specific schema."""

    text: str = Field(default="", max_length=MAX_SKILL_TEXT_CHARS)
    data: dict[str, Any] = Field(default_factory=dict)


class RememberSkillArgs(BaseSkillArgs):
    """Arguments for the durable memory skill."""

    text: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    scope: Literal["user", "project", "session"] = "session"


class VerifySkillArgs(BaseSkillArgs):
    """Arguments for verification workflows."""

    task: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    commands: list[str] = Field(default_factory=list, max_length=MAX_SKILL_LIST_ITEMS)

    @field_validator("commands")
    @classmethod
    def commands_must_fit_budget(cls, value: list[str]) -> list[str]:
        return _validate_string_list(value, "commands")


class SimplifySkillArgs(BaseSkillArgs):
    """Arguments for code/text simplification."""

    content: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    preserve_behavior: bool = True


class SkillifySkillArgs(BaseSkillArgs):
    """Arguments for generating a reusable SKILL.md workflow."""

    workflow: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    target_name: str | None = Field(default=None, max_length=120)


class DebugSkillArgs(BaseSkillArgs):
    """Arguments for systematic debugging."""

    problem: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    context: str | None = Field(default=None, max_length=MAX_SKILL_TEXT_CHARS)


class StuckSkillArgs(BaseSkillArgs):
    """Arguments for blocked-progress recovery."""

    situation: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    attempted_steps: list[str] = Field(default_factory=list, max_length=MAX_SKILL_LIST_ITEMS)

    @field_validator("attempted_steps")
    @classmethod
    def attempted_steps_must_fit_budget(cls, value: list[str]) -> list[str]:
        return _validate_string_list(value, "attempted_steps")


class BatchSkillArgs(BaseSkillArgs):
    """Arguments for batched multi-step coordination."""

    task: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    steps: list[str] = Field(default_factory=list, max_length=MAX_SKILL_LIST_ITEMS)

    @field_validator("steps")
    @classmethod
    def steps_must_fit_budget(cls, value: list[str]) -> list[str]:
        return _validate_string_list(value, "steps")


class UpdateConfigSkillArgs(BaseSkillArgs):
    """Arguments for safe configuration changes."""

    change_request: str = Field(min_length=1, max_length=MAX_SKILL_TEXT_CHARS)
    dry_run: bool = True


class SkillArgumentValidationError(ValueError):
    """Structured validation error raised before a skill is executed."""

    def __init__(self, skill_name: str, errors: list[dict[str, Any]]) -> None:
        self.skill_name = skill_name
        self.errors = errors
        super().__init__(f"Invalid arguments for skill {skill_name}: {errors}")


BUILTIN_SKILL_ARG_SCHEMAS: dict[str, type[BaseSkillArgs]] = {
    "batch": BatchSkillArgs,
    "debug": DebugSkillArgs,
    "remember": RememberSkillArgs,
    "simplify": SimplifySkillArgs,
    "skillify": SkillifySkillArgs,
    "stuck": StuckSkillArgs,
    "update-config": UpdateConfigSkillArgs,
    "verify": VerifySkillArgs,
}

STRING_ARG_FIELD_BY_SKILL: dict[str, str] = {
    "batch": "task",
    "debug": "problem",
    "remember": "text",
    "simplify": "content",
    "skillify": "workflow",
    "stuck": "situation",
    "update-config": "change_request",
    "verify": "task",
}


def args_schema_for_skill(skill_name: str) -> type[BaseSkillArgs]:
    """Return the configured argument schema for a built-in skill name."""

    return BUILTIN_SKILL_ARG_SCHEMAS.get(skill_name, GenericSkillArgs)


def validate_skill_args(skill_name: str, raw_args: Any, schema: type[BaseSkillArgs]) -> BaseSkillArgs:
    """Validate raw skill args using the skill's typed Pydantic schema."""

    try:
        if isinstance(raw_args, schema):
            return raw_args
        data = _coerce_raw_args(skill_name, raw_args, schema)
        return schema.model_validate(data)
    except ValidationError as exc:
        raise SkillArgumentValidationError(skill_name, exc.errors(include_url=False)) from exc


def format_skill_args_for_prompt(skill_name: str, typed_args: BaseSkillArgs) -> str:
    """Format validated typed args for SKILL.md prompt interpolation."""

    if isinstance(typed_args, GenericSkillArgs):
        if typed_args.data:
            return json.dumps(typed_args.data, ensure_ascii=False, sort_keys=True)
        return typed_args.text
    data = typed_args.model_dump(exclude_none=True)
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _coerce_raw_args(skill_name: str, raw_args: Any, schema: type[BaseSkillArgs]) -> dict[str, Any]:
    if schema is GenericSkillArgs:
        if raw_args is None:
            return {}
        if isinstance(raw_args, str):
            return {"text": raw_args}
        if isinstance(raw_args, dict):
            if set(raw_args).issubset({"text", "data"}):
                return raw_args
            return {"data": raw_args}
        return {"text": json.dumps(raw_args, ensure_ascii=False) if isinstance(raw_args, list) else str(raw_args)}
    if isinstance(raw_args, str):
        if skill_name == "remember":
            return _coerce_remember_string(raw_args)
        return {STRING_ARG_FIELD_BY_SKILL[skill_name]: raw_args}
    if isinstance(raw_args, dict):
        return raw_args
    return {"__invalid__": raw_args}


def _validate_string_list(value: list[str], field_name: str) -> list[str]:
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must contain only strings")
        if len(item) > MAX_SKILL_LIST_ITEM_CHARS:
            raise ValueError(f"{field_name} item exceeds {MAX_SKILL_LIST_ITEM_CHARS} characters")
    return value


def _coerce_remember_string(raw_args: str) -> dict[str, str]:
    stripped = raw_args.strip()
    if ":" in stripped:
        maybe_scope, text = stripped.split(":", 1)
        scope = maybe_scope.strip().lower()
        if scope in {"user", "project", "session"}:
            return {"scope": scope, "text": text.strip()}
    return {"text": raw_args}
