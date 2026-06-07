#!/usr/bin/env python3
"""Capture lab-only computed-style snapshots for Visual Diagnosis."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_diagnosis.style_capture import capture_computed_style_snapshot


DEFAULT_OUTPUT_ROOT = Path("out") / "visual_diagnosis_computed_styles"


def capture_manifest(manifest_path: str | Path, *, output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    rows = _load_rows(Path(manifest_path))
    output_dir = Path(output_root) / _timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for row in rows:
        brand_name = str(row["brand_name"])
        website_url = str(row["website_url"])
        result_path = output_dir / f"{_slug(brand_name)}.computed-style.json"
        try:
            snapshot = capture_computed_style_snapshot(website_url)
            _write_json(result_path, snapshot)
            results.append(
                {
                    "brand_name": brand_name,
                    "website_url": website_url,
                    "status": "captured",
                    "computed_style_snapshot_path": str(result_path),
                    "element_count": snapshot.get("element_count"),
                    "color_count": len(snapshot.get("colors") or []),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "brand_name": brand_name,
                    "website_url": website_url,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    manifest = {
        "schema_version": "computed-style-capture-manifest-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_manifest_path": str(manifest_path),
        "output_dir": str(output_dir),
        "total": len(results),
        "ok": sum(1 for item in results if item.get("status") == "captured"),
        "error": sum(1 for item in results if item.get("status") == "failed"),
        "results": results,
    }
    _write_json(output_dir / "capture_manifest.json", manifest)
    return manifest


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("manifest must be a JSON array or an object with a brands array")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each manifest row must be a JSON object")
        if not str(row.get("brand_name") or "").strip():
            raise ValueError("each manifest row requires brand_name")
        if not str(row.get("website_url") or "").strip():
            raise ValueError("each manifest row requires website_url")
        result.append(row)
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in normalized.split("-") if part) or "brand"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to a visual diagnosis lab manifest JSON.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory for generated snapshots.")
    args = parser.parse_args()
    result = capture_manifest(args.manifest, output_root=args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
