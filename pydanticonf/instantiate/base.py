from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

InstanceT = TypeVar("InstanceT")


def _find_generic_target(cls: type) -> type | None:
    """Walk the MRO to find the DynamicConfig[T] parameterization.

    Pydantic v2's metaclass replaces ``__orig_bases__`` with processed
    bases.  The resolved generic arguments are stored in
    ``__pydantic_generic_metadata__`` on the parameterized parent class
    in the MRO.
    """
    for parent in cls.__mro__:
        meta: dict[str, Any] | None = getattr(parent, "__pydantic_generic_metadata__", None)
        if meta is None:
            continue
        origin = meta.get("origin")
        if origin is DynamicConfig:
            args = meta.get("args", ())
            if args and isinstance(args[0], type):
                return args[0]
    return None


class DynamicConfig(BaseModel, Generic[InstanceT]):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )

    target_: str = Field(..., alias="_target_")

    @classmethod
    def model_validate(
        cls,
        obj: object,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, object] | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> DynamicConfig[InstanceT]:
        if isinstance(obj, dict) and "_target_" not in obj and "target_" not in obj:
            target_type = _find_generic_target(cls)
            if target_type is not None:
                module = getattr(target_type, "__module__", "")
                name = getattr(target_type, "__qualname__", "")
                if module and name:
                    obj["_target_"] = f"{module}.{name}"
        return super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )
