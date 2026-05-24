"""Review queue helpers for the Visual Signature corpus expansion pilot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.corpus_expansion.corpus_expansion_models import (
    CORPUS_EXPANSION_REVIEW_QUEUE_SCHEMA_VERSION,
    CorpusExpansionReviewQueue,
    validate_corpus_expansion_review_queue_payload,
)
from src.visual_signature.corpus_expansion.corpus_sampling import build_default_corpus_expansion_seed, normalize_queue_items


def build_corpus_expansion_review_queue(
    *,
    pilot_run_id: str,
    generated_at: datetime | None = None,
    target_capture_count: int = 20,
    seed_items: list[dict[str, Any]] | None = None,
) -> CorpusExpansionReviewQueue:
    candidate_items = seed_items or build_default_corpus_expansion_seed()
    items = sample_review_queue_items(candidate_items, target_capture_count=target_capture_count)
    items = normalize_queue_items(items)
    queue_state_distribution = _count_distribution(str(item.queue_state) for item in items)
    category_distribution = _count_distribution(item.category for item in items)
    confidence_distribution = _count_distribution(item.confidence_bucket for item in items)
    reviewed_count = sum(1 for item in items if item.queue_state == "reviewed")
    return CorpusExpansionReviewQueue(
        schema_version=CORPUS_EXPANSION_REVIEW_QUEUE_SCHEMA_VERSION,
        record_type="corpus_expansion_review_queue",
        pilot_run_id=pilot_run_id,
        generated_at=generated_at or datetime.now(timezone.utc),
        target_capture_count=target_capture_count,
        current_capture_count=len(items),
        reviewed_capture_count=reviewed_count,
        category_distribution=category_distribution,
        confidence_distribution=confidence_distribution,
        queue_state_distribution=queue_state_distribution,
        queue_items=items,
        readiness_scope="human_review_scaling",
        readiness_status="not_ready",
        notes=[
            "Evidence-only review queue scaffold.",
            "Not enabled for scoring, runtime behavior, or model training.",
        ],
    )


def review_queue_items_to_dicts(queue: CorpusExpansionReviewQueue) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in queue.queue_items]


def validate_corpus_expansion_review_queue(payload: dict[str, Any]) -> list[str]:
    return validate_corpus_expansion_review_queue_payload(payload)


def write_review_queue(
    queue: CorpusExpansionReviewQueue,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _count_distribution(values: list[str] | Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def sample_review_queue_items(
    candidates: list[dict[str, Any]],
    *,
    target_capture_count: int = 20,
) -> list[dict[str, Any]]:
    from src.visual_signature.corpus_expansion.corpus_sampling import sample_review_queue_items as _sample_review_queue_items

    return _sample_review_queue_items(candidates, target_capture_count=target_capture_count)
