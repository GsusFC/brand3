"""Facade for local deploy pipeline compare runtime."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import compare_local_deploy_pipeline_runtime as _impl

if hasattr(_impl, "__name__"):
    # Preserve imports through the historical module path.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

