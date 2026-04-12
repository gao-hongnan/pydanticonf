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


def varargs_function(*args: int, k: int = 0) -> tuple[int, ...]:
    """Function accepting variable positional args for _args_ replacement tests."""
    return args + (k,)


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

        result = locate("tests.unit.test_instantiate.OuterClass.InnerClass")
        assert result is OuterClass.InnerClass

    def test_resolves_deeply_nested_class(self) -> None:
        """_locate resolves deeply nested class."""
        from pydanticonf.instantiate._locate import locate

        result = locate("tests.unit.test_instantiate.OuterClass.DeepInner.Leaf")
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


# ---------------------------------------------------------------------------
# ABC-001-1B Tests: DynamicConfig rewrite
# ---------------------------------------------------------------------------


class TestDynamicConfig:
    """Tests for DynamicConfig after stripping dead methods (AC-008, EC-007)."""

    def test_auto_injects_target_from_generic(self) -> None:
        """DynamicConfig[T].model_validate auto-injects _target_ from T."""
        from pydanticonf.instantiate.base import DynamicConfig

        class FooConfig(DynamicConfig[SimpleTarget]):
            pass

        cfg = FooConfig.model_validate({"x": 1})
        assert cfg.target_ == f"{SimpleTarget.__module__}.{SimpleTarget.__qualname__}"

    def test_explicit_target_preserved(self) -> None:
        """DynamicConfig with explicit _target_ keeps it."""
        from pydanticonf.instantiate.base import DynamicConfig

        class FooConfig(DynamicConfig[SimpleTarget]):
            pass

        cfg = FooConfig.model_validate({"_target_": "custom.path.Foo", "x": 1})
        assert cfg.target_ == "custom.path.Foo"

    def test_extra_fields_allowed(self) -> None:
        """DynamicConfig allows extra fields."""
        from pydanticonf.instantiate.base import DynamicConfig

        class FooConfig(DynamicConfig[SimpleTarget]):
            pass

        cfg = FooConfig.model_validate({"x": 1, "y": 2, "z": 3})
        assert cfg.x == 1
        data = cfg.model_dump()
        assert data["y"] == 2
        assert data["z"] == 3

    def test_no_get_target_parts_method(self) -> None:
        """get_target_parts() must not exist after rewrite."""
        from pydanticonf.instantiate.base import DynamicConfig

        assert not hasattr(DynamicConfig, "get_target_parts")

    def test_no_get_kwargs_method(self) -> None:
        """get_kwargs() must not exist after rewrite."""
        from pydanticonf.instantiate.base import DynamicConfig

        assert not hasattr(DynamicConfig, "get_kwargs")

    def test_no_frostbound_imports(self) -> None:
        """base.py must not import from frostbound."""
        from pathlib import Path

        import pydanticonf.instantiate.base as base_module

        source = Path(base_module.__file__).read_text()
        assert "frostbound" not in source


# ---------------------------------------------------------------------------
# ABC-001-2A Tests: Core instantiate() recursive walker
# ---------------------------------------------------------------------------

# Target string constants for test configs
_SIMPLE_TARGET = f"{__name__}.SimpleTarget"
_WRAPPER_TARGET = f"{__name__}.Wrapper"
_INNER_TARGET = f"{__name__}.Inner"
_LAYER_TARGET = f"{__name__}.Layer"
_GROUP_TARGET = f"{__name__}.Group"
_FUNCTION_TARGET = f"{__name__}.simple_function"
_VARARGS_TARGET = f"{__name__}.varargs_function"


class TestInstantiate:
    """Tests for the public instantiate() function (AC-003 through AC-007)."""

    def test_basic_instantiation(self) -> None:
        """instantiate creates an instance from a config dict."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"_target_": _SIMPLE_TARGET, "x": 42})
        assert isinstance(result, SimpleTarget)
        assert result.x == 42

    def test_partial_flag_returns_functools_partial(self) -> None:
        """_partial_=True returns functools.partial instead of calling."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"_target_": _SIMPLE_TARGET, "x": 1}, _partial_=True)
        assert isinstance(result, functools.partial)
        assert result.func is SimpleTarget
        assert result.keywords == {"x": 1}
        assert result.args == ()

    def test_args_key_passed_as_positional(self) -> None:
        """_args_ key passes values as positional args to target."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"_target_": _FUNCTION_TARGET, "_args_": [1, 2], "k": 3})
        assert result == (1, 2, 3)

    def test_call_time_positional_replaces_config_args(self) -> None:
        """Call-time *args REPLACE config's _args_ (AC-005, EC-006)."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"_target_": _VARARGS_TARGET, "_args_": [1, 2]}, 7, 8, 9)
        assert result == (7, 8, 9, 0)  # args replaced, k=0 default

    def test_call_time_kwargs_override_wins(self) -> None:
        """Call-time **overrides MERGE OVER config kwargs (AC-005, EC-009)."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"_target_": _SIMPLE_TARGET, "x": 1}, x=99)
        assert isinstance(result, SimpleTarget)
        assert result.x == 99

    def test_recursive_false_passes_nested_dict_unchanged(self) -> None:
        """_recursive_=False passes nested _target_ dicts as plain dicts."""
        from pydanticonf.instantiate.instantiate import instantiate

        cfg = {
            "_target_": _WRAPPER_TARGET,
            "_recursive_": False,
            "inner": {"_target_": _INNER_TARGET, "x": 1},
        }
        result = instantiate(cfg)
        assert isinstance(result, Wrapper)
        assert isinstance(result.inner, dict)
        assert result.inner["_target_"] == _INNER_TARGET

    def test_recursive_true_instantiates_nested(self) -> None:
        """_recursive_=True (default) instantiates nested configs."""
        from pydanticonf.instantiate.instantiate import instantiate

        cfg = {
            "_target_": _WRAPPER_TARGET,
            "inner": {"_target_": _INNER_TARGET, "x": 1},
        }
        result = instantiate(cfg)
        assert isinstance(result, Wrapper)
        assert isinstance(result.inner, Inner)
        assert result.inner.x == 1

    def test_error_full_key_for_bad_nested_kwarg(self) -> None:
        """Error carries full_key with bracket notation for list index."""
        from pydanticonf.instantiate.errors import InstantiationError
        from pydanticonf.instantiate.instantiate import instantiate

        cfg = {
            "_target_": _GROUP_TARGET,
            "items": [{"_target_": _LAYER_TARGET, "warmpu": 0.1}],
        }
        with pytest.raises(InstantiationError) as exc_info:
            instantiate(cfg)
        err = exc_info.value
        assert err.full_key == "items[0]"
        assert _LAYER_TARGET in (err.target or "")
        assert err.__cause__ is not None

    def test_error_full_key_uses_bracket_index(self) -> None:
        """Error full_key uses bracket notation for second list item."""
        from pydanticonf.instantiate.errors import InstantiationError
        from pydanticonf.instantiate.instantiate import instantiate

        cfg = {
            "_target_": _GROUP_TARGET,
            "items": [
                {"_target_": _LAYER_TARGET, "warmup": 0.1},
                {"_target_": _LAYER_TARGET, "warmpu": 0.2},
            ],
        }
        with pytest.raises(InstantiationError) as exc_info:
            instantiate(cfg)
        assert exc_info.value.full_key == "items[1]"

    def test_error_chained_cause_is_original(self) -> None:
        """InstantiationError.__cause__ is the original TypeError."""
        from pydanticonf.instantiate.errors import InstantiationError
        from pydanticonf.instantiate.instantiate import instantiate

        cfg = {
            "_target_": _GROUP_TARGET,
            "items": [{"_target_": _LAYER_TARGET, "warmpu": 0.1}],
        }
        with pytest.raises(InstantiationError) as exc_info:
            instantiate(cfg)
        assert isinstance(exc_info.value.__cause__, TypeError)
        msg = str(exc_info.value)
        assert "Error in call to target" in msg

    def test_partial_with_failed_locate_raises_error(self) -> None:
        """_partial_=True with nonexistent target still raises error (EC-008)."""
        from pydanticonf.instantiate.errors import InstantiationError
        from pydanticonf.instantiate.instantiate import instantiate

        with pytest.raises(InstantiationError):
            instantiate({"_target_": "nonexistent.Bad", "_partial_": True})

    def test_target_not_found_raises_instantiation_error(self) -> None:
        """Nonexistent _target_ raises InstantiationError."""
        from pydanticonf.instantiate.errors import InstantiationError
        from pydanticonf.instantiate.instantiate import instantiate

        with pytest.raises(InstantiationError) as exc_info:
            instantiate({"_target_": "nonexistent.module.Class"})
        assert exc_info.value.target == "nonexistent.module.Class"

    def test_instantiate_with_dynamic_config(self) -> None:
        """instantiate works with DynamicConfig instances."""
        from pydanticonf.instantiate.base import DynamicConfig
        from pydanticonf.instantiate.instantiate import instantiate

        class FooConfig(DynamicConfig[SimpleTarget]):
            pass

        cfg = FooConfig.model_validate({"x": 42})
        result = instantiate(cfg)
        assert isinstance(result, SimpleTarget)
        assert result.x == 42

    def test_instantiate_dict_without_target_returns_dict(self) -> None:
        """Dict without _target_ returns recursively walked dict."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate({"a": 1, "b": {"c": 2}})
        assert result == {"a": 1, "b": {"c": 2}}

    def test_instantiate_list_returns_list(self) -> None:
        """List input returns recursively walked list."""
        from pydanticonf.instantiate.instantiate import instantiate

        result = instantiate([1, {"_target_": _SIMPLE_TARGET, "x": 5}, 3])
        assert result[0] == 1
        assert isinstance(result[1], SimpleTarget)
        assert result[1].x == 5
        assert result[2] == 3

    def test_instantiate_scalar_returns_scalar(self) -> None:
        """Scalar input returns the scalar unchanged."""
        from pydanticonf.instantiate.instantiate import instantiate

        assert instantiate(42) == 42
        assert instantiate("hello") == "hello"
        assert instantiate(None) is None
