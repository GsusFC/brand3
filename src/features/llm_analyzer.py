"""Facade for LLM analyzer implementation.

This keeps the previous public import path (`src.features.llm_analyzer`) while
allowing tests and callers to patch helpers on the facade module. Runtime method
calls are synchronized so patched helpers are used by the actual implementation
logic.
"""

from __future__ import annotations

from src.features import llm_analyzer_impl as _impl

import sys

sys.modules[__name__] = _impl
