"""Shared constants and helpers for the Visual Signature web lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .visual_signature_artifact_data_support import ARTIFACTS
from .visual_signature_artifact_data_support import HUMAN_REVIEW_DESIGN_PATH
from .visual_signature_artifact_data_support import REVIEW_SEMANTICS_PATH
from .visual_signature_artifact_data_support import artifact_file_response_payload
from .visual_signature_artifact_data_support import artifact_path
from .visual_signature_artifact_data_support import screenshot_file_response_payload
from .visual_signature_artifact_data_support import _is_under_root
from .visual_signature_artifact_data_support import visual_signature_root
from .visual_signature_section_data_support import artifacts_for_section as _artifacts_for_section_impl
from .visual_signature_section_data_support import cards_for_section as _cards_for_section_impl
from .visual_signature_section_data_support import items_for_section as _items_for_section_impl
from .visual_signature_section_data_support import status_for as _status_for_impl
from .visual_signature_section_data_support import summary_for as _summary_for_impl


def _related_variant_payload(variant: dict[str, Any], selected_filename: str) -> dict[str, Any]:
    payload = dict(variant)
    payload["is_current"] = payload.get("filename") == selected_filename
    return payload


def _artifact_payload(key: str) -> dict[str, Any]:
    spec = ARTIFACTS[key]
    path = artifact_path(key)
    exists = bool(path and path.exists())
    payload = _load_json(path) if exists and spec["type"] == "json" else None
    return {
        "key": key,
        "label": spec["label"],
        "type": spec["type"],
        "section": spec["section"],
        "exists": exists,
        "path": str(path) if path else "",
        "source_href": f"/visual-signature/artifacts/{key}",
        "status": _status_for_impl(payload, exists=exists),
        "summary": _summary_for_impl(payload, spec["type"], exists=exists),
        "raw_json": _pretty_json(payload) if payload is not None else "",
    }


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else {"items": value}


def _cards_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return _cards_for_section_impl(section, artifacts)


def _artifacts_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return _artifacts_for_section_impl(section, artifacts)


def _items_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    del artifacts
    return _items_for_section_impl(
        section,
        load_json=_load_json,
        artifact_path=artifact_path,
        as_list=_as_list,
    )




def _pretty_json(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _nested(payload: dict[str, Any], key: str, nested_key: str) -> Any:
    value = payload.get(key)
    return value.get(nested_key) if isinstance(value, dict) else None


def _find_manifest_row(payload: dict[str, Any], brand_name: str) -> dict[str, Any] | None:
    target = brand_name.lower()
    for row in _as_list(payload.get("results")):
        if isinstance(row, dict) and str(row.get("brand_name") or "").lower() == target:
            return row
    return None


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in normalized.split("-") if part)
