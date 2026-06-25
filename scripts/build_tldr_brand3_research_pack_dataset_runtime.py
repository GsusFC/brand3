"""Runtime facade for TL;DR research pack dataset builder.

The heavy implementation now lives in
`build_tldr_brand3_research_pack_dataset_runtime_impl.py`.
"""

from __future__ import annotations

import sys

import build_tldr_brand3_research_pack_dataset_runtime_impl as _impl

if hasattr(_impl, "__name__"):
    # Preserve imports through historical module path.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())
