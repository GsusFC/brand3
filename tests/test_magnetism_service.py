from __future__ import annotations

from pathlib import Path

from src.services.magnetism_service import run_magnetism_from_url
from src.storage.sqlite_store import SQLiteStore


def test_run_magnetism_from_url_uses_brand_audit_snapshot(tmp_path: Path):
    db_path = str(tmp_path / "brand3.sqlite3")
    store = SQLiteStore(db_path)
    try:
        brand_id = store.upsert_brand("Canonical Service", "https://service.test")
        run_id = store.create_run(
            brand_id,
            "Canonical Service",
            "https://service.test",
            use_llm=True,
            use_social=True,
        )
        store.save_raw_input(
            run_id,
            "web",
            {
                "markdown_content": (
                    "Canonical Service is a workflow platform for finance teams "
                    "that helps reduce reconciliation time."
                )
            },
        )
        store.save_evidence_items(
            run_id,
            [
                {
                    "source": "context",
                    "url": "https://service.test",
                    "quote": (
                        "Canonical Service is a workflow platform for finance teams "
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
        assert url == "https://service.test"
        return {"run_id": run_id}

    result = run_magnetism_from_url(
        "https://service.test",
        audit_runner=fake_audit_runner,
        db_path=db_path,
    )

    assert result["source"] == "brand_audit_snapshot"
    assert result["extraction_mode"] == "canonical_snapshot"
    assert result["canonical_evidence_source"] == "brand_audit_snapshot"
    assert result["source_run_id"] == run_id
    assert "deprecation" not in result
    assert result["evidence_packet_summary"]["source"] == "brand_audit_snapshot"
    assert result["tldr_brand3"]["value_proposition"]["detected"] is True
