"""Tests for pydanticonf.instantiate — Hydra-style instantiate() rewrite.

Target class fixtures are defined at module level so they are importable
as _target_ strings (e.g. "tests.unit.test_instantiate.OuterClass.InnerClass").
"""

from __future__ import annotations

import functools
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Module-level target fixtures (used as _target_ strings in tests)
# ---------------------------------------------------------------------------


class OuterClass:
    """Outer class with nested inner class for _locate nested-class tests."""

    class InnerClass:
        def __init__(self, value: int = 0) -> None:
            self.value = value

    class DeepInner:
        class Leaf:
            def __init__(self, x: int = 0) -> None:
                self.x = x


class SimpleTarget:
    """Simple target class with one kwarg."""

    def __init__(self, x: int = 0) -> None:
        self.x = x


def simple_function(a: int, b: int, *, k: int = 0) -> tuple[int, int, int]:
    """Simple target function for _args_ tests."""
    return (a, b, k)


class Wrapper:
    """Wrapper class for _recursive_ tests."""

    def __init__(self, inner: Any = None) -> None:
        self.inner = inner


class Inner:
    """Inner class for _recursive_ tests."""

    def __init__(self, x: int = 0) -> None:
        self.x = x


class Layer:
    """Layer class for error-path tests."""

    def __init__(self, warmup: float = 0.0) -> None:
        self.warmup = warmup


class Group:
    """Group class for error-path tests with list items."""

    def __init__(self, items: list[Any] | None = None) -> None:
        self.items = items or []


# ---------------------------------------------------------------------------
# ABC-001-1A Tests: InstantiationError and _locate
# ---------------------------------------------------------------------------


class TestInstantiationError:
    """Tests for InstantiationError (AC-007, NFR-007)."""

    def test_message_format_call_preamble(self) -> None:
        """InstantiationError __str__ produces three-line Hydra format."""
        from pydanticonf.instantiate.errors import InstantiationError

        cause = TypeError("bad kwarg")
        err = InstantiationError(
            target="pkg.Layer",
            full_key="layers[0]",
            preamble_type="call",
        )
        try:
            raise err from cause
        except InstantiationError as e:
            msg = str(e)
            assert "Error in call to target 'pkg.Layer':" in msg
            assert "TypeError('bad kwarg')" in msg
            assert "full_key: layers[0]" in msg
            assert e.__cause__ is cause

    def test_message_format_partial_preamble(self) -> None:
        """InstantiationError with partial preamble."""
        from pydanticonf.instantiate.errors import InstantiationError

        cause = ValueError("bad partial")
        err = InstantiationError(
            target="pkg.Fn",
            full_key="",
            preamble_type="partial",
        )
        try:
            raise err from cause
        except InstantiationError as e:
            msg = str(e)
            assert "Error in creating partial(pkg.Fn, ...) object:" in msg
            assert "ValueError('bad partial')" in msg
            assert "full_key" not in msg  # empty full_key should not appear

    def test_message_format_args_preamble(self) -> None:
        """InstantiationError with args preamble."""
        from pydanticonf.instantiate.errors import InstantiationError

        cause = AttributeError("missing")
        err = InstantiationError(
            target="pkg.Collector",
            full_key="items[1]",
            preamble_type="args",
        )
        try:
            raise err from cause
        except InstantiationError as e:
            msg = str(e)
            assert "Error in collecting args and kwargs for 'pkg.Collector':" in msg
            assert "full_key: items[1]" in msg

    def test_chained_cause_preserved(self) -> None:
        """InstantiationError chains __cause__ from original exception."""
        from pydanticonf.instantiate.errors import InstantiationError

        original = TypeError("original error")
        err = InstantiationError(
            target="pkg.Mod",
            full_key="cfg",
            preamble_type="call",
        )
        try:
            raise err from original
        except InstantiationError as e:
            assert e.__cause__ is original
            assert e.target == "pkg.Mod"
            assert e.full_key == "cfg"


class TestLocate:
    """Tests for vendored _locate (AC-002, EC-001, EC-002)."""

    def test_resolves_nested_class(self) -> None:
        """_locate resolves nested class via segment walking."""
        from pydanticonf.instantiate._locate import locate

        result = locate(
            "tests.unit.test_instantiate.OuterClass.InnerClass"
        )
        assert result is OuterClass.InnerClass

    def test_resolves_deeply_nested_class(self) -> None:
        """_locate resolves deeply nested class."""
        from pydanticonf.instantiate._locate import locate

        result = locate(
            "tests.unit.test_instantiate.OuterClass.DeepInner.Leaf"
        )
        assert result is OuterClass.DeepInner.Leaf

    def test_empty_path_raises_import_error(self) -> None:
        """_locate raises ImportError for empty path."""
        from pydanticonf.instantiate._locate import locate

        with pytest.raises(ImportError, match="Empty path"):
            locate("")

    def test_leading_dot_raises_error(self) -> None:
        """_locate raises error for path with leading dot."""
        from pydanticonf.instantiate._locate import locate

        with pytest.raises((ImportError, ValueError)):
            locate(".foo")

    def test_resolves_module_attribute(self) -> None:
        """_locate resolves a standard library module attribute."""
        from pydanticonf.instantiate._locate import locate

        result = locate("os.path.join")
        import os.path

        assert result is os.path.join

    def test_nonexistent_module_raises_import_error(self) -> None:
        """_locate raises ImportError for nonexistent module."""
        from pydanticonf.instantiate._locate import locate

        with pytest.raises(ImportError):
            locate("nonexistent_module_xyz.Foo")
