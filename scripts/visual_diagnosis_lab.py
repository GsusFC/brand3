"""Facade for visual diagnosis lab runtime."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import visual_diagnosis_lab_runtime as _impl

if hasattr(_impl, "__name__"):
    # Keep compatibility with the original module import path.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

