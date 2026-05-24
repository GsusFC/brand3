"""Aggregate human review reports for annotation calibration."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.visual_signature.annotations.review.persistence import load_review_records, validate_review_record
from src.visual_signature.annotations.review.types import ReviewRecord


def build_review_reports(records: list[ReviewRecord]) -> dict[str, Any]:
    valid_records = [record for record in records if validate_review_record(record)["valid"]]
    return {
        "version": "visual-signature-human-review-reports-1",
        "record_count": len(records),
        "valid_record_count": len(valid_records),
        "reviewer_agreement_report": reviewer_agreement_report(valid_records),
        "target_quality_summary": target_quality_summary(valid_records),
        "hallucination_summary": hallucination_summary(valid_records),
        "annotation_usefulness_summary": annotation_usefulness_summary(valid_records),
        "notes": [
            "Human review reports are evidence-only calibration artifacts.",
            "They do not affect scoring, rubric dimensions, reports, or UI.",
        ],
    }


def build_review_reports_from_path(path: str | Path) -> dict[str, Any]:
    return build_review_reports(load_review_records(path))


def write_review_reports(output_dir: str | Path, reports: dict[str, Any]) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for key in (
        "reviewer_agreement_report",
        "target_quality_summary",
        "hallucination_summary",
        "annotation_usefulness_summary",
    ):
        json_path = destination / f"{key}.json"
        md_path = destination / f"{key}.md"
        _write_json(json_path, reports.get(key) or {})
        md_path.write_text(_report_markdown(key, reports.get(key) or {}) + "\n", encoding="utf-8")
        written[f"{key}_json"] = str(json_path)
        written[f"{key}_md"] = str(md_path)
    _write_json(destination / "review_reports_manifest.json", reports)
    written["manifest_json"] = str(destination / "review_reports_manifest.json")
    return written


def reviewer_agreement_report(records: list[ReviewRecord]) -> dict[str, Any]:
    by_annotation_target: dict[tuple[str, str], list[str]] = defaultdict(list)
    reviewers: set[str] = set()
    for record in records:
        reviewers.add(record.reviewer_id)
        for target, review in record.target_reviews.items():
            by_annotation_target[(record.annotation_id, target)].append(review.decision)
    comparable = 0
    agreed = 0
    conflicts: list[dict[str, Any]] = []
    for (annotation_id, target), decisions in sorted(by_annotation_target.items()):
        if len(decisions) < 2:
            continue
        comparable += 1
        counts = Counter(decisions)
        top_count = counts.most_common(1)[0][1]
        if top_count == len(decisions):
            agreed += 1
        else:
            conflicts.append(
                {
                    "annotation_id": annotation_id,
                    "target": target,
                    "decisions": dict(sorted(counts.items())),
                }
            )
    return {
        "reviewer_count": len(reviewers),
        "review_record_count": len(records),
        "comparable_annotation_targets": comparable,
        "full_agreement_count": agreed,
        "full_agreement_rate": _rate(agreed, comparable),
        "conflicts": conflicts,
    }


def target_quality_summary(records: list[ReviewRecord]) -> dict[str, Any]:
    by_target: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        for target, review in record.target_reviews.items():
            by_target[target].append(review)
    return {
        target: {
            "review_count": len(reviews),
            "agreement_rate": _rate(sum(1 for item in reviews if item.decision == "agree"), len(reviews)),
            "disagreement_rate": _rate(sum(1 for item in reviews if item.decision == "disagree"), len(reviews)),
            "uncertain_rate": _rate(sum(1 for item in reviews if item.decision == "uncertain"), len(reviews)),
            "hallucination_rate": _rate(sum(1 for item in reviews if item.hallucination), len(reviews)),
            "avg_usefulness": _average([item.usefulness for item in reviews]),
            "high_uncertainty_rate": _rate(sum(1 for item in reviews if item.uncertainty == "high"), len(reviews)),
        }
        for target, reviews in sorted(by_target.items())
    }


def hallucination_summary(records: list[ReviewRecord]) -> dict[str, Any]:
    total_reviews = 0
    hallucinations = 0
    by_target: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for record in records:
        for target, review in record.target_reviews.items():
            total_reviews += 1
            if not review.hallucination:
                continue
            hallucinations += 1
            by_target[target] += 1
            examples.append(
                {
                    "annotation_id": record.annotation_id,
                    "brand_name": record.brand_name,
                    "target": target,
                    "decision": review.decision,
                    "notes": review.notes,
                }
            )
    return {
        "target_review_count": total_reviews,
        "hallucination_count": hallucinations,
        "hallucination_rate": _rate(hallucinations, total_reviews),
        "by_target": dict(sorted(by_target.items())),
        "examples": examples[:25],
    }


def annotation_usefulness_summary(records: list[ReviewRecord]) -> dict[str, Any]:
    overall_scores = [record.overall_usefulness for record in records if record.overall_usefulness is not None]
    target_scores: list[int] = []
    uncertainty: Counter[str] = Counter()
    for record in records:
        for review in record.target_reviews.values():
            target_scores.append(review.usefulness)
            uncertainty[review.uncertainty] += 1
    return {
        "record_count": len(records),
        "avg_overall_usefulness": _average(overall_scores),
        "avg_target_usefulness": _average(target_scores),
        "uncertainty_distribution": dict(sorted(uncertainty.items())),
        "high_uncertainty_rate": _rate(uncertainty["high"], sum(uncertainty.values())),
    }


def _report_markdown(title: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {title.replace('_', ' ').title()}",
        "",
        "Offline human review calibration output. This does not affect scoring, rubric dimensions, reports, or UI.",
        "",
    ]
    if title == "target_quality_summary":
        lines.extend(["| Target | Reviews | Agree | Disagree | Uncertain | Hallucination | Usefulness |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for target, row in payload.items():
            lines.append(
                f"| {target} | {row['review_count']} | {row['agreement_rate']:.0%} | "
                f"{row['disagreement_rate']:.0%} | {row['uncertain_rate']:.0%} | "
                f"{row['hallucination_rate']:.0%} | {_num(row['avg_usefulness'])} |"
            )
    else:
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                lines.append(f"- `{key}`: `{json.dumps(value, sort_keys=True)}`")
            else:
                lines.append(f"- `{key}`: {value}")
    return "\n".join(lines).rstrip()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _average(values: list[int | float | None]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 3)


def _num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"
