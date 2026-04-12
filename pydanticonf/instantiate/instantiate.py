"""Recursive walker for Hydra-style instantiate().

Stateless pure-function implementation following Decision 3 (NFR-004 compliant).
The public ``instantiate()`` function delegates to the internal ``_walk()``
recursive helper which threads ``path`` through every call for full_key
construction.

Special keys recognized: ``_target_``, ``_args_``, ``_partial_``, ``_recursive_``.
"""

from __future__ import annotations

import functools
from typing import Any

from pydantic import BaseModel

from pydanticonf.instantiate._locate import locate as _locate
from pydanticonf.instantiate.errors import InstantiationError

_EXCLUDE_KEYS: frozenset[str] = frozenset({"_target_", "_args_", "_partial_", "_recursive_"})


def _format_full_key(path: tuple[str | int, ...]) -> str:
    """Format a path tuple into a dotted key with bracket notation for ints.

    Examples::

        _format_full_key(("model", "encoder", "layers", 0))
            -> "model.encoder.layers[0]"
        _format_full_key(("layers", 0))
            -> "layers[0]"
    """
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        else:
            if parts and not parts[-1].endswith("]"):
                parts.append(".")
            parts.append(segment)
    return "".join(parts)


def _walk(
    node: Any,
    path: tuple[str | int, ...],
    recursive: bool,
    partial_flag: bool,
    call_args: tuple[Any, ...],
    call_kwargs: dict[str, Any],
) -> Any:
    """Internal recursive walker implementing the instantiate contract.

    Normalizes BaseModel/DynamicConfig inputs via ``model_dump(by_alias=True)``
    at entry. For nodes without ``_target_``: descends into dict/list
    recursively or returns scalars unchanged.
    """
    # Normalize BaseModel / DynamicConfig to plain dict
    if isinstance(node, BaseModel):
        node = node.model_dump(by_alias=True)

    # Non-dict nodes: recurse into lists or return scalars
    if not isinstance(node, dict):
        if isinstance(node, list):
            return [_walk(item, path + (i,), recursive, False, (), {}) for i, item in enumerate(node)]
        return node

    # Dict without _target_: recursively walk values
    if "_target_" not in node:
        if recursive:
            return {k: _walk(v, path + (k,), recursive, False, (), {}) for k, v in node.items()}
        return node

    # --- Node has _target_: extract special keys ---
    target_str: str = node["_target_"]
    args_in: list[Any] = list(node.get("_args_", ()))
    partial_node: bool = node.get("_partial_", False)
    recursive_node: bool = node.get("_recursive_", True)

    # Build kwargs dict (exclude special keys)
    kwargs_in: dict[str, Any] = {k: v for k, v in node.items() if k not in _EXCLUDE_KEYS}

    # Apply call-time overrides only at ROOT (path == ())
    if path == ():
        if len(call_args) > 0:
            args_in = list(call_args)  # positional REPLACES
        kwargs_in.update(call_kwargs)  # call-time MERGES OVER

    effective_recursive = recursive_node if path == () else recursive

    # Resolve target
    try:
        target = _locate(target_str)
    except Exception as e:
        raise InstantiationError(
            target=target_str,
            full_key=_format_full_key(path),
            preamble_type="call",
        ) from e

    # Recursively walk children if effective_recursive
    if effective_recursive:
        args_in = [_walk(a, path + (i,), effective_recursive, False, (), {}) for i, a in enumerate(args_in)]
        kwargs_in = {k: _walk(v, path + (k,), effective_recursive, False, (), {}) for k, v in kwargs_in.items()}

    # Call target or build partial
    effective_partial = partial_flag if path == () else partial_node
    try:
        if effective_partial:
            return functools.partial(target, *args_in, **kwargs_in)
        return target(*args_in, **kwargs_in)
    except Exception as e:
        preamble_type = "partial" if effective_partial else "call"
        raise InstantiationError(
            target=target_str,
            full_key=_format_full_key(path),
            preamble_type=preamble_type,
        ) from e


def instantiate(
    cfg: Any,
    *args: Any,
    _partial_: bool = False,
    _recursive_: bool = True,
    **overrides: Any,
) -> Any:
    """Instantiate an object from a config dict, DynamicConfig, or list.

    Supports four Hydra-compatible special keys:
        ``_target_`` (required dotted path), ``_args_`` (positional args),
        ``_partial_`` (return functools.partial), ``_recursive_`` (default True).

    Call-time positional ``*args`` REPLACE the config's ``_args_``.
    Call-time ``**overrides`` MERGE OVER config kwargs (call-time wins).

    Args:
        cfg: Config dict, DynamicConfig, BaseModel, list, or scalar.
        *args: Call-time positional args replacing config's ``_args_``.
        _partial_: Return functools.partial instead of calling.
        _recursive_: Recursively instantiate nested configs.
        **overrides: Call-time kwargs that merge over config kwargs.

    Returns:
        Instantiated object, functools.partial, or walked data structure.

    Raises:
        InstantiationError: On target resolution or call failures.
    """
    return _walk(
        cfg,
        path=(),
        recursive=_recursive_,
        partial_flag=_partial_,
        call_args=args,
        call_kwargs=overrides,
    )
