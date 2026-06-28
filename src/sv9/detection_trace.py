"""Pass 1 detection fingerprints and diffs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def detection_fingerprint(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return stable hash metadata for a Pass 1 payload."""
    payload = payload if isinstance(payload, dict) else {}
    tldr = payload.get("tldr_brand3")
    if not isinstance(tldr, dict):
        tldr = {}
    return {
        "schema_version": "sv9-pass1-fingerprint-v1",
        "tldr_hash": _json_hash(tldr),
        "block_hashes": {
            str(block_name): _json_hash(block_payload)
            for block_name, block_payload in sorted(tldr.items())
        },
        "block_keys": sorted(tldr.keys()),
    }


def diff_tldr_brand3(
    left_payload: dict[str, Any] | None,
    right_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return field-by-field diffs across two Pass 1 payloads."""
    left = _extract_tldr(left_payload)
    right = _extract_tldr(right_payload)
    diffs: list[dict[str, Any]] = []
    for path in sorted(set(_flatten_paths(left)) | set(_flatten_paths(right))):
        left_value = _read_path(left, path)
        right_value = _read_path(right, path)
        if left_value == right_value:
            continue
        diffs.append(
            {
                "path": path,
                "left": left_value,
                "right": right_value,
            }
        )
    return diffs


def _extract_tldr(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    tldr = payload.get("tldr_brand3")
    return tldr if isinstance(tldr, dict) else {}


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _flatten_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        if prefix:
            paths.add(prefix)
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths |= _flatten_paths(child, child_prefix)
        return paths
    if isinstance(value, list):
        if prefix:
            paths.add(prefix)
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths |= _flatten_paths(child, child_prefix)
        return paths
    if prefix:
        paths.add(prefix)
    return paths


def _read_path(value: Any, path: str) -> Any:
    if not path:
        return value
    current = value
    token = ""
    index_mode = False
    tokens: list[str] = []
    for char in path:
        if char == "." and not index_mode:
            if token:
                tokens.append(token)
                token = ""
            continue
        if char == "[":
            if token:
                tokens.append(token)
                token = ""
            index_mode = True
            continue
        if char == "]":
            if token:
                tokens.append(f"[{token}]")
                token = ""
            index_mode = False
            continue
        token += char
    if token:
        tokens.append(token if not index_mode else f"[{token}]")

    for token in tokens:
        if token.startswith("[") and token.endswith("]"):
            try:
                idx = int(token[1:-1])
            except ValueError:
                return None
            if not isinstance(current, list) or idx >= len(current):
                return None
            current = current[idx]
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(token)
    return current
