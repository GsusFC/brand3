"""Facade for Brand3 CLI entrypoint and public API."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("main_runtime")
_RUNTIME_NAMES = {name for name in _runtime.__dict__ if not name.startswith("__")}
_RUNTIME_BASELINE = {name: _runtime.__dict__.get(name) for name in _RUNTIME_NAMES}


def _sync_runtime_overrides() -> None:
    """Keep runtime values aligned with façade monkeypatches."""
    for name in _RUNTIME_NAMES:
        runtime_value = _runtime.__dict__.get(name)
        if name in globals():
            facade_value = globals()[name]
            if runtime_value is not facade_value:
                setattr(_runtime, name, facade_value)
            continue
        baseline_value = _RUNTIME_BASELINE.get(name)
        if runtime_value is not baseline_value:
            setattr(_runtime, name, baseline_value)


def __getattr__(name: str):
    if name in _RUNTIME_NAMES:
        value = _runtime.__dict__[name]
        if callable(value):
            def _proxy(*args, **kwargs):
                _sync_runtime_overrides()
                return getattr(_runtime, name)(*args, **kwargs)

            _proxy.__name__ = name
            _proxy.__doc__ = getattr(value, "__doc__", None)
            return _proxy
        return value
    raise AttributeError(f"module 'main' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | {_k for _k in _runtime.__dict__ if not _k.startswith("__")})


__all__ = [name for name in _RUNTIME_NAMES if not name.startswith("_")]
