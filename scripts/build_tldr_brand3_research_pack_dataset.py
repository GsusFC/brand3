"""Facade for the TL;DR Brand3 research pack dataset builder runtime."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import build_tldr_brand3_research_pack_dataset_runtime as _impl

if hasattr(_impl, "__name__"):
    # Preserve imports against the historic module entrypoint.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

