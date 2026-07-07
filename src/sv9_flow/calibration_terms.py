"""Loader for calibration-derived keyword policies.

These lists are calibration data, not architecture: they accreted from
specific cohort brands during shadow batches and carry overfit risk. They
live in policy_data/calibration_terms.json so changing them is a reviewable
data change with provenance instead of silent code drift.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_TERMS_PATH = Path(__file__).parent / "policy_data" / "calibration_terms.json"


@lru_cache(maxsize=1)
def _terms() -> dict[str, Any]:
    return json.loads(_TERMS_PATH.read_text(encoding="utf-8"))


def provenance() -> str:
    return str(_terms()["provenance"])


def block_detection_policy() -> dict[str, Any]:
    # Deep copies keep the lru_cache safe from consumer mutation.
    return copy.deepcopy(_terms()["block_detection"])


def block_evidence_policy() -> dict[str, Any]:
    return copy.deepcopy(_terms()["block_evidence"])


def magnetism_families() -> dict[str, frozenset[str]]:
    return {key: frozenset(values) for key, values in _terms()["magnetism_families"].items()}


def magnetism_direct_pull_gap_markers() -> tuple[str, ...]:
    return tuple(_terms()["magnetism_direct_pull_gap_markers"])


def core_purpose_heuristics() -> dict[str, Any]:
    return copy.deepcopy(_terms()["core_purpose_heuristics"])
