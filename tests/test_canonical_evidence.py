from __future__ import annotations

from src.reports import canonical_evidence
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
                "source": "web",
                "payload": {
                    "canonical_url": "https://canonical.test/product",
                    "markdown_content": "Product platform details for finance teams." * 80,
                },
            },
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://canonical.test/about",
                    "markdown_content": "About Canonical Brand and its operating model." * 80,
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
                "quote": (
                    "Canonical Brand is a workflow platform for finance teams "
                    "that helps reduce reconciliation time."
                ),
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
    assert summary["raw_input_count"] == 4
    assert summary["evidence_item_count"] == 1
    assert summary["web_page_roles"] == ["homepage", "product", "about"]
    assert summary["extraction_quality_report"]["status"] == "strong"
    assert summary["extraction_quality_report"]["homepage_detected"] is True
    assert summary["extraction_quality_report"]["product_page_detected"] is True
    assert summary["extraction_quality_report"]["about_page_detected"] is True
    assert summary["data_quality"] == "partial"
    assert summary["strategic_group_counts"]["product_offer"] >= 1
    assert isinstance(summary["strategic_rejected_reason_counts"], dict)
    assert summary["evidence_quality"]["status"] == "strong"
    assert summary["evidence_quality"]["missing_key_groups"] == []
    assert summary["evidence_quality"]["owned_source_count"] >= 1
    assert summary["evidence_quality"]["visual_semantics_detected"] is True


def test_canonical_brand_evidence_reuses_collected_evidences_for_fallback(monkeypatch):
    calls = 0

    def fake_collect_evidences(snapshot):
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(canonical_evidence, "collect_evidences", fake_collect_evidences)
    snapshot = {
        "run": {
            "id": 902,
            "brand_name": "Fallback Brand",
            "url": "https://fallback.test",
        },
        "features": [],
        "evidence_items": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Fallback web copy for downstream interpreters.",
                },
            }
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)

    assert calls == 1
    assert evidence.interpreter_text == "Fallback web copy for downstream interpreters."


def test_canonical_brand_evidence_quality_marks_missing_strategy_groups():
    snapshot = {
        "run": {
            "id": 903,
            "brand_name": "Weak Canonical",
            "url": "https://weak.test",
        },
        "features": [],
        "evidence_items": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Trusted worldwide. Privacy and security first.",
                },
            }
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    quality = evidence.to_summary()["evidence_quality"]

    assert quality["status"] == "weak"
    assert quality["missing_key_groups"] == ["product_offer", "audience", "outcome"]
    assert "no_product_offer" in quality["reasons"]


def test_canonical_brand_evidence_quality_marks_empty_packet_insufficient(monkeypatch):
    def fake_collect_evidences(snapshot):
        return []

    monkeypatch.setattr(canonical_evidence, "collect_evidences", fake_collect_evidences)
    snapshot = {
        "run": {
            "id": 904,
            "brand_name": "Empty Canonical",
            "url": "https://empty.test",
        },
        "features": [],
        "evidence_items": [],
        "raw_inputs": [],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    quality = evidence.to_summary()["evidence_quality"]

    assert quality["status"] == "insufficient"
    assert "no_interpreter_text" in quality["reasons"]
    assert "no_raw_inputs" in quality["reasons"]
    assert "no_strategic_groups" in quality["reasons"]


def test_canonical_brand_evidence_treats_localized_root_as_homepage():
    snapshot = {
        "run": {"id": 908, "brand_name": "Localized", "url": "https://localized.test/es/"},
        "features": [],
        "evidence_items": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://localized.test/es/",
                    "markdown_content": "# Localized homepage\nPrimary localized page evidence. " * 80,
                    "owned_fallback_urls": [
                        "https://localized.test/es/features/product-video",
                        "https://localized.test/es/pricing",
                    ],
                },
            }
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    report = evidence.to_summary()["extraction_quality_report"]

    assert report["homepage_detected"] is True
    assert report["product_page_detected"] is True
    assert report["pricing_page_detected"] is True
    assert "homepage" not in report["missing_core_roles"]
    assert report["owned_page_roles"] == ["homepage", "product", "pricing"]


def test_canonical_brand_evidence_reports_owned_page_role_coverage():
    snapshot = {
        "run": {
            "id": 905,
            "brand_name": "Role Coverage",
            "url": "https://roles.test",
        },
        "features": [],
        "evidence_items": [],
        "raw_inputs": [
            {"source": "web", "payload": {"canonical_url": "https://roles.test/", "markdown_content": "Home copy " * 120}},
            {"source": "web", "payload": {"canonical_url": "https://roles.test/pricing", "markdown_content": "Pricing copy " * 80}},
            {"source": "web", "payload": {"canonical_url": "https://roles.test/customers", "markdown_content": "Customer proof " * 80}},
            {"source": "web", "payload": {"canonical_url": "https://roles.test/security", "markdown_content": "Security and trust " * 80}},
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    report = evidence.to_summary()["extraction_quality_report"]

    assert report["owned_page_count"] == 4
    assert report["owned_page_roles"] == ["homepage", "pricing", "customers", "trust"]
    assert report["homepage_detected"] is True
    assert report["customers_page_detected"] is True
    assert report["trust_or_security_page_detected"] is True
    assert report["pricing_page_detected"] is True
    assert report["likely_failure_cause"] == "partial_owned_page_coverage"
    assert "missing_product_or_solution_page" in report["reasons"]


def test_canonical_brand_evidence_reads_embedded_owned_subpages_as_page_roles():
    snapshot = {
        "run": {
            "id": 907,
            "brand_name": "Embedded Pages",
            "url": "https://embedded.test",
        },
        "features": [],
        "evidence_items": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://embedded.test",
                    "markdown_content": (
                        "# Embedded Pages\nHomepage evidence. " * 80
                        + "\n\n---\n## Subpage: https://embedded.test/product\n"
                        + "Product platform evidence. " * 80
                        + "\n\n---\n## Subpage: https://embedded.test/about\n"
                        + "About the company evidence. " * 80
                    ),
                },
            }
        ],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    report = evidence.to_summary()["extraction_quality_report"]

    assert evidence.to_summary()["web_page_roles"] == ["homepage", "product", "about"]
    assert report["owned_page_count"] == 3
    assert report["owned_page_roles"] == ["homepage", "product", "about"]
    assert report["product_page_detected"] is True
    assert report["about_page_detected"] is True
    assert report["owned_text_chars"] >= len("Product platform evidence. " * 80)


def test_canonical_brand_evidence_reports_capture_gap_without_owned_web_pages():
    snapshot = {
        "run": {"id": 906, "brand_name": "No Pages", "url": "https://nopages.test"},
        "features": [],
        "evidence_items": [],
        "raw_inputs": [],
    }

    evidence = build_canonical_brand_evidence(snapshot)
    report = evidence.to_summary()["extraction_quality_report"]

    assert report["status"] == "capture_gap"
    assert report["likely_failure_cause"] == "no_owned_web_pages"
    assert "no_owned_web_pages" in report["reasons"]
