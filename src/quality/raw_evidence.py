"""Shared helpers for parsing raw feature evidence.

The repository stores `raw_value` in a loose shape for traceability. This
module normalizes the common cases for downstream explainability code without
changing the persisted shape itself.
"""

from __future__ import annotations

import ast
import json
from typing import Any


def parse_raw_feature_value(raw_value: Any) -> Any:
    """Return the best-effort parsed representation of a raw feature value."""

    if isinstance(raw_value, (dict, list)):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        return json.loads(raw_value)
    except Exception:
        pass
    try:
        return ast.literal_eval(raw_value)
    except Exception:
        return raw_value
