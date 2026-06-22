from __future__ import annotations

from src.reports import brand_audit_analyst_orchestration as _orchestration
import sys

# Keep module identity stable while avoiding an additional shim layer.
sys.modules[__name__] = _orchestration
