"""Deterministic sampling helpers for the Visual Signature corpus expansion pilot."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.visual_signature.corpus_expansion.corpus_expansion_models import (
    CORPUS_EXPANSION_QUEUE_ITEM_SCHEMA_VERSION,
    CorpusExpansionQueueItem,
)


def build_default_corpus_expansion_seed() -> list[dict[str, Any]]:
    """Return a tiny, evidence-only seed queue from the current Visual Signature corpus."""

    return [
        {
            "queue_id": "queue_linear",
            "capture_id": "linear",
            "brand_name": "Linear",
            "website_url": "https://linear.app",
            "category": "SaaS",
            "queue_state": "reviewed",
            "review_outcome": "confirmed",
            "confidence_bucket": "high",
            "reviewer_id": "reviewer-01",
            "reviewed_at": "2026-05-12T10:30:00Z",
            "evidence_refs": ["examples/visual_signature/calibration_records.json"],
            "notes": ["seed-reviewed-capture"],
        },
        {
            "queue_id": "queue_verge",
            "capture_id": "the-verge",
            "brand_name": "The Verge",
            "website_url": "https://www.theverge.com",
            "category": "editorial/media",
            "queue_state": "reviewed",
            "review_outcome": "contradicted",
            "confidence_bucket": "high",
            "reviewer_id": "reviewer-02",
            "reviewed_at": "2026-05-12T10:31:00Z",
            "evidence_refs": ["examples/visual_signature/calibration_records.json"],
            "notes": ["seed-reviewed-capture"],
        },
        {
            "queue_id": "queue_openai",
            "capture_id": "openai",
            "brand_name": "OpenAI",
            "website_url": "https://openai.com",
            "category": "AI-native",
            "queue_state": "unresolved",
            "review_outcome": "unresolved",
            "confidence_bucket": "medium",
            "reviewer_id": "reviewer-03",
            "reviewed_at": "2026-05-12T10:32:00Z",
            "evidence_refs": ["examples/visual_signature/calibration_records.json"],
            "notes": ["seed-unresolved-review"],
        },
        {
            "queue_id": "queue_allbirds",
            "capture_id": "allbirds",
            "brand_name": "Allbirds",
            "website_url": "https://www.allbirds.com",
            "category": "ecommerce",
            "queue_state": "needs_additional_evidence",
            "review_outcome": None,
            "confidence_bucket": "low",
            "reviewer_id": None,
            "reviewed_at": None,
            "evidence_refs": ["examples/visual_signature/calibration_records.json"],
            "notes": ["seed-needs-more-evidence"],
        },
        {
            "queue_id": "queue_headspace",
            "capture_id": "headspace",
            "brand_name": "Headspace",
            "website_url": "https://www.headspace.com",
            "category": "wellness_lifestyle",
            "queue_state": "queued",
            "review_outcome": None,
            "confidence_bucket": "unknown",
            "reviewer_id": None,
            "reviewed_at": None,
            "evidence_refs": ["examples/visual_signature/calibration_records.json"],
            "notes": ["seed-queued-capture"],
        },
    ]


def sample_review_queue_items(
    candidates: list[dict[str, Any]],
    *,
    target_capture_count: int = 20,
) -> list[dict[str, Any]]:
    """Return a deterministic, category-balanced sample without broadening scope."""

    if target_capture_count <= 0 or not candidates:
        return []
    if len(candidates) <= target_capture_count:
        return [dict(item) for item in candidates]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        grouped[str(item.get("category") or "uncategorized")].append(item)

    sampled: list[dict[str, Any]] = []
    categories = sorted(grouped)
    cursor = 0
    while len(sampled) < target_capture_count and categories:
        category = categories[cursor % len(categories)]
        bucket = grouped[category]
        if bucket:
            sampled.append(dict(bucket.pop(0)))
        cursor += 1
        if all(not bucket for bucket in grouped.values()):
            break
    return sampled


def normalize_queue_items(items: list[dict[str, Any]]) -> list[CorpusExpansionQueueItem]:
    normalized: list[CorpusExpansionQueueItem] = []
    for item in items:
        payload = {
            "schema_version": CORPUS_EXPANSION_QUEUE_ITEM_SCHEMA_VERSION,
            "record_type": "corpus_expansion_queue_item",
            **item,
        }
        normalized.append(CorpusExpansionQueueItem.model_validate(payload))
    return normalized
