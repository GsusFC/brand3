"""Runtime facade for local deploy pipeline comparison.

Keep public module path stable while moving implementation to
`compare_local_deploy_pipeline_runtime_impl.py`.
"""

from __future__ import annotations

import sys

import compare_local_deploy_pipeline_runtime_impl as _impl

if hasattr(_impl, "__name__"):
    # Preserve imports through the historical module path.
    sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())
