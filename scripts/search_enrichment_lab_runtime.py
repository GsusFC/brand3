"""Runtime facade for Search Enrichment Lab.

Keep historical module path stable while moving heavy implementation into
`search_enrichment_lab_runtime_impl.py`.
"""

from __future__ import annotations

import sys

import search_enrichment_lab_runtime_impl as _impl

if hasattr(_impl, "__name__"):
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())
