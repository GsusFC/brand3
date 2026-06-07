#!/usr/bin/env python3
"""Run lab-only Brand3 visual diagnosis over local evidence files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_diagnosis import build_visual_diagnosis


DEFAULT_OUTPUT_ROOT = Path("out") / "visual_diagnosis_lab"


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(Path(path))
    if isinstance(payload, dict) and isinstance(payload.get("brands"), list):
        rows = payload["brands"]
    elif isinstance(payload, list):
        rows = payload
    else:
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


def run_lab(manifest_path: str | Path, *, output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    rows = load_manifest(manifest_path)
    output_dir = Path(output_root) / _timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for row in rows:
        diagnosis = build_visual_diagnosis(
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
            screenshot_capture=_row_payload(row, "screenshot_capture"),
            visual_signature_payload=_row_payload(row, "visual_signature"),
            coherence_breakdown=_coherence_breakdown_for_row(row),
            category_hint=str(row.get("category_hint") or ""),
        )
        result = {
            "brand_name": row["brand_name"],
            "website_url": row["website_url"],
            "category_hint": row.get("category_hint") or "",
            "diagnosis": diagnosis.to_dict(),
        }
        results.append(result)
        _write_json(output_dir / f"{_slug(str(row['brand_name']))}.json", result)

    summary = {
        "schema_version": "visual-diagnosis-lab-run-1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest_path": str(manifest_path),
        "brand_count": len(results),
        "results": results,
    }
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(_summary_markdown(summary) + "\n", encoding="utf-8")
    return {"output_dir": str(output_dir), "summary": summary}


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Visual Diagnosis Lab Summary",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Brand count: {summary['brand_count']}",
        "",
        "| Brand | Status | Profile | Identity read | Confidence | Anti-patterns |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary["results"]:
        diagnosis = row["diagnosis"]
        read = diagnosis["diagnosis"]
        signals = diagnosis["signals"]
        antipatterns = ", ".join(signals.get("antipatterns") or []) or "-"
        lines.append(
            f"| {row['brand_name']} | {diagnosis['status']} | {read['reference_profile']} | "
            f"{read['identity_read']} | {diagnosis['confidence']} | {antipatterns} |"
        )
    return "\n".join(lines)


def _load_optional_json(value: Any) -> dict[str, Any] | None:
    if not value:
        return None
    payload = _load_json(Path(str(value)))
    if not isinstance(payload, dict):
        raise ValueError(f"{value} must contain a JSON object")
    return payload


def _row_payload(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    inline = row.get(key)
    if isinstance(inline, dict):
        return inline
    return _load_optional_json(row.get(f"{key}_path"))


def _coherence_breakdown_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    explicit = _row_payload(row, "coherence_breakdown")
    magnetism_payload = _row_payload(row, "magnetism_payload")
    extracted = extract_coherence_breakdown(magnetism_payload or {})
    if explicit and extracted:
        return {**explicit, **extracted}
    return extracted or explicit


def extract_coherence_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract Magnetism coherence breakdown from known local lab payload shapes."""
    if not isinstance(payload, dict):
        return {}

    scanner = payload.get("scanner") if isinstance(payload.get("scanner"), dict) else {}
    normalized = scanner.get("score_coherence_breakdown")
    if isinstance(normalized, dict) and normalized:
        return dict(normalized)

    methodology = payload.get("methodology") if isinstance(payload.get("methodology"), dict) else {}
    score_breakdown = methodology.get("score_breakdown") if isinstance(methodology.get("score_breakdown"), dict) else {}
    coherence = score_breakdown.get("coherence")
    if isinstance(coherence, dict) and coherence:
        return dict(coherence)

    raw_score_breakdown = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
    raw_coherence = raw_score_breakdown.get("coherence")
    if isinstance(raw_coherence, dict) and raw_coherence:
        return dict(raw_coherence)

    coherence_score = payload.get("coherence_score")
    if coherence_score is not None:
        return {"visual_identity": coherence_score, "source": "coherence_score_fallback"}

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    if scores.get("coherence") is not None:
        return {"visual_identity": scores.get("coherence"), "source": "scores.coherence_fallback"}
    return {}


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in normalized.split("-") if part) or "brand"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to lab manifest JSON.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory for generated lab output.")
    args = parser.parse_args()
    result = run_lab(args.manifest, output_root=args.output_root)
    print(result["output_dir"])


if __name__ == "__main__":
    main()
