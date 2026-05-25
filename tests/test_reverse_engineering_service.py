from __future__ import annotations

from pathlib import Path

from src.services.reverse_engineering_service import (
    run_legacy_reverse_engineering,
    run_reverse_engineering_from_url,
)
from src.storage.sqlite_store import SQLiteStore


def test_run_reverse_engineering_from_url_uses_brand_audit_snapshot(tmp_path: Path):
    db_path = str(tmp_path / "brand3.sqlite3")
    store = SQLiteStore(db_path)
    try:
        brand_id = store.upsert_brand("Canonical Reverse", "https://reverse.test")
        run_id = store.create_run(
            brand_id,
            "Canonical Reverse",
            "https://reverse.test",
            use_llm=True,
            use_social=True,
        )
        store.save_raw_input(
            run_id,
            "web",
            {
                "markdown_content": (
                    "Canonical Reverse is a workflow platform for finance teams "
                    "that helps reduce reconciliation time. It provides API "
                    "integrations and developer documentation."
                )
            },
        )
        store.save_evidence_items(
            run_id,
            [
                {
                    "source": "context",
                    "url": "https://reverse.test",
                    "quote": (
                        "Canonical Reverse is a workflow platform for finance teams "
                        "that helps reduce reconciliation time."
                    ),
                    "feature_name": "positioning",
                    "dimension_name": "coherencia",
                    "confidence": 0.9,
                }
            ],
        )
    finally:
        store.close()

    def fake_audit_runner(url: str) -> dict[str, int]:
        assert url == "https://reverse.test"
        return {"run_id": run_id}

    result = run_reverse_engineering_from_url(
        "https://reverse.test",
        audit_runner=fake_audit_runner,
        db_path=db_path,
    )

    assert result["source"] == "brand_audit_snapshot"
    assert result["extraction_mode"] == "canonical_snapshot"
    assert result["canonical_evidence_source"] == "brand_audit_snapshot"
    assert result["source_run_id"] == run_id
    assert "deprecation" not in result
    assert result["canonical_evidence_summary"]["source"] == "brand_audit_snapshot"
    assert result["layers"]["netspace"]["status"] == "detected"


def test_run_legacy_reverse_engineering_marks_direct_path_deprecated():
    result = run_legacy_reverse_engineering(
        "Legacy Reverse has a moral mission and an API for teams.",
        brand_name="Legacy Reverse",
    )

    assert result["source"] == "direct_reverse_engineering_legacy"
    assert result["extraction_mode"] == "legacy_direct"
    assert result["canonical_evidence_source"] is None
    assert result["deprecation"]["status"] == "deprecated"
    assert result["deprecation"]["replacement"] == (
        "run_reverse_engineering_from_audit_snapshot"
    )
