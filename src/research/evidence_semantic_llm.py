from __future__ import annotations

from src.research import evidence_semantic_llm_impl as _impl
import sys

sys.modules[__name__] = _impl
