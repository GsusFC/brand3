"""Corpus calibration helpers for Visual Signature annotations."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.visual_signature.annotations.types import ANNOTATION_TARGETS


def load_annotation_overlays(path: str | Path) -> list[dict[str, Any]]:
    root = Path(path)
    overlays: list[dict[str, Any]] = []
    for item in sorted(root.glob("*.json")):
        payload = json.loads(item.read_text(encoding="utf-8"))
        annotation = payload.get("annotations") if isinstance(payload, dict) else None
        if isinstance(annotation, dict):
            overlays.append(payload)
    return overlays


def build_annotation_audit(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    target_completion: Counter[str] = Counter()
    target_unknown: Counter[str] = Counter()
    confidence_values: dict[str, list[float]] = defaultdict(list)
    category_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for payload in payloads:
        annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
        status = str(annotations.get("status") or "missing")
        status_counts[status] += 1
        category = _category(payload)
        category_counts[category][status] += 1
        targets = annotations.get("targets") if isinstance(annotations.get("targets"), dict) else {}
        for target in ANNOTATION_TARGETS:
            value = targets.get(target) if isinstance(targets, dict) else None
            if not isinstance(value, dict):
                continue
            target_completion[target] += 1
            if str(value.get("label") or "unknown") == "unknown":
                target_unknown[target] += 1
            confidence_values[target].append(_float(value.get("confidence")))
    total = len(payloads)
    return {
        "version": "visual-signature-annotation-audit-1",
        "total": total,
        "status_counts": dict(sorted(status_counts.items())),
        "target_completion": {
            target: {
                "count": target_completion[target],
                "rate": _rate(target_completion[target], total),
                "unknown_count": target_unknown[target],
                "unknown_rate": _rate(target_unknown[target], target_completion[target]),
                "avg_confidence": _average(confidence_values[target]),
            }
            for target in ANNOTATION_TARGETS
        },
        "per_category_status": {
            category: dict(sorted(counts.items()))
            for category, counts in sorted(category_counts.items())
        },
        "notes": [
            "Annotation audit is calibration-only.",
            "Mock provider outputs are not semantic ground truth.",
            "No scoring or rubric dimensions are modified.",
        ],
    }


def annotation_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Annotation Audit",
        "",
        "Calibration-only annotation overlay summary. This does not affect scoring, rubric dimensions, reports, or UI.",
        "",
        f"- Total overlays: {audit.get('total', 0)}",
        f"- Status counts: {_distribution(audit.get('status_counts') or {})}",
        "",
        "| Target | Completion | Unknown | Avg confidence |",
        "| --- | ---: | ---: | ---: |",
    ]
    for target, row in (audit.get("target_completion") or {}).items():
        lines.append(
            f"| {target} | {row['rate']:.0%} | {row['unknown_rate']:.0%} | {_num(row['avg_confidence'])} |"
        )
    lines.extend(["", "## Category Status", ""])
    for category, counts in (audit.get("per_category_status") or {}).items():
        lines.append(f"- `{category}`: {_distribution(counts)}")
    return "\n".join(lines).rstrip()


def _category(payload: dict[str, Any]) -> str:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    return str(calibration.get("expected_category") or payload.get("category") or "uncategorized")


def _float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _distribution(values: dict[str, int]) -> str:
    return ", ".join(f"{key}:{value}" for key, value in sorted(values.items())) or "-"


def _num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"
