"""Facade for the Search Enrichment Lab runtime."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

_SCRIPT_DIR: Final = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import search_enrichment_lab_runtime as _impl

if hasattr(_impl, "__name__"):
    # Keep imports of this facade compatible with the historic module name.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())
