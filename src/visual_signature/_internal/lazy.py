"""Helpers for lazy re-export packages."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable


def make_lazy_getattr(namespace: dict[str, Any], exports: dict[str, tuple[str, str]]) -> Callable[[str], Any]:
    def __getattr__(name: str) -> Any:
        target = exports.get(name)
        if target is None:
            raise AttributeError(f"module {namespace.get('__name__', '<unknown>')!r} has no attribute {name!r}")
        module_name, attr_name = target
        value = getattr(import_module(module_name), attr_name)
        namespace[name] = value
        return value

    return __getattr__


def make_lazy_dir(namespace: dict[str, Any], exports: dict[str, tuple[str, str]]) -> Callable[[], list[str]]:
    def __dir__() -> list[str]:
        return sorted(set(namespace) | set(exports))

    return __dir__
