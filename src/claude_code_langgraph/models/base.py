"""Base Pydantic DTOs and serialization helpers for runtime boundary contracts."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict


class RuntimeModel(BaseModel):
    """Mutable Pydantic model for validated runtime boundary payloads."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, arbitrary_types_allowed=True)


class FrozenRuntimeModel(BaseModel):
    """Immutable Pydantic model for runtime boundary DTOs."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)


ModelT = TypeVar("ModelT", bound=BaseModel)


def dump_model(model: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic boundary model into a JSON/checkpointer-safe dictionary."""

    return model.model_dump(mode="json", exclude_none=True)


def validate_list(model_cls: type[ModelT], items: list[Any] | None) -> list[ModelT]:
    """Validate every item in a list as the requested Pydantic boundary model."""

    return [model_cls.model_validate(item) for item in items or []]
