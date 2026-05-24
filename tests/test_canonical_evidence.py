from __future__ import annotations

from src.reports.canonical_evidence import build_canonical_brand_evidence


def test_canonical_brand_evidence_groups_snapshot_for_downstream_lenses():
    snapshot = {
        "run": {
            "id": 901,
            "brand_name": "Canonical Brand",
            "url": "https://canonical.test",
            "audit": {"data_quality": "partial"},
        },
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://canonical.test",
                    "markdown_content": (
                        "Canonical Brand is a workflow platform for finance teams "
                        "that helps reduce reconciliation time."
                    ),
                },
            },
            {
                "source": "visual_signature",
                "payload": {"semantics": {"aesthetic_style": "minimalist brutalism"}},
            },
        ],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://canonical.test",
                "quote": "Canonical Brand is a workflow platform for finance teams that helps reduce reconciliation time.",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.9,
            }
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)

    assert evidence.brand_name == "Canonical Brand"
    assert evidence.run_id == 901
    assert "workflow platform" in evidence.interpreter_text
    assert evidence.visual_semantics["status"] == "detected"
    assert evidence.visual_semantics["data"]["aesthetic_style"] == "minimalist brutalism"
    summary = evidence.to_summary()
    assert summary["source"] == "brand_audit_snapshot"
    assert summary["source_label"] == "Canonical Brand Audit evidence"
    assert summary["raw_input_count"] == 2
    assert summary["evidence_item_count"] == 1
    assert summary["data_quality"] == "partial"
    assert summary["strategic_group_counts"]["product_offer"] >= 1
