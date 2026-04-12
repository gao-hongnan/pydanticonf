"""InstantiationError with Hydra-compatible error formatting.

Defines a single InstantiationError(Exception) class carrying target,
full_key, and chained __cause__. The rendered str(err) matches Hydra's
three context-specific format strings.
"""

from __future__ import annotations

CALL_PREAMBLE = "Error in call to target"
PARTIAL_PREAMBLE = "Error in creating partial"
ARGS_PREAMBLE = "Error in collecting args and kwargs for"

_PREAMBLE_TEMPLATES: dict[str, str] = {
    "call": "Error in call to target '{target}':",
    "partial": "Error in creating partial({target}, ...) object:",
    "args": "Error in collecting args and kwargs for '{target}':",
}


class InstantiationError(Exception):
    """Error raised during instantiation with Hydra-compatible formatting.

    Attributes:
        target: The _target_ string being resolved, or None.
        full_key: Dotted config path to the offending node with bracket
            notation for list indices (e.g. "layers[0]").
    """

    def __init__(
        self,
        target: str | None = None,
        full_key: str = "",
        preamble_type: str = "call",
    ) -> None:
        self.target = target
        self.full_key = full_key
        self._preamble_type = preamble_type
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        target_str = self.target or ""
        template = _PREAMBLE_TEMPLATES.get(self._preamble_type, _PREAMBLE_TEMPLATES["call"])
        preamble_line = template.format(target=target_str)

        cause_repr = repr(self.__cause__) if self.__cause__ else ""

        parts = [preamble_line]
        if cause_repr:
            parts.append(cause_repr)
        if self.full_key:
            parts.append(f"full_key: {self.full_key}")

        return "\n".join(parts)

    def __str__(self) -> str:
        return self._build_message()
