from __future__ import annotations

from pathlib import Path

from src.services.magnetism_service import run_magnetism_from_audit_snapshot, run_magnetism_from_url
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


def test_run_magnetism_from_url_maps_audit_progress_to_scanner_phases(monkeypatch) -> None:
    phases: list[str] = []

    def fake_audit_runner(url: str, *, progress_cb=None) -> dict[str, int]:
        assert url == "https://service.test"
        for phase in ("extracting", "scoring", "finalizing"):
            progress_cb(phase)
        return {"run_id": 123}

    def fake_magnetism_from_run(run_id: int, *, llm=None, db_path=None):
        assert run_id == 123
        return {"source": "brand_audit_snapshot", "source_run_id": run_id}

    monkeypatch.setattr(
        "src.services.magnetism_service.run_magnetism_from_audit_run",
        fake_magnetism_from_run,
    )

    result = run_magnetism_from_url(
        "https://service.test",
        audit_runner=fake_audit_runner,
        progress_cb=phases.append,
    )

    assert result["source_run_id"] == 123
    assert phases == [
        "collecting",
        "extracting",
        "interpreting",
        "interpreting",
        "interpreting",
    ]


def test_run_magnetism_from_audit_snapshot_builds_default_llm_when_available(monkeypatch) -> None:
    captured = {}

    class FakeLLM:
        def __init__(self, model=None):
            self.api_key = "test-key"
            self.model = model

    class FakeExtractor:
        def __init__(self, llm=None):
            captured["llm"] = llm

        def extract_from_audit_snapshot(self, snapshot):
            return {"source": "brand_audit_snapshot", "snapshot": snapshot}

    monkeypatch.setattr("src.services.magnetism_service.LLMAnalyzer", FakeLLM)
    monkeypatch.setattr("src.services.magnetism_service.MagnetismExtractor", FakeExtractor)
    monkeypatch.setattr("src.services.magnetism_service.LLM_PREMIUM_MODEL", "premium-model")

    result = run_magnetism_from_audit_snapshot({"run": {"id": 1}})

    assert result["source"] == "brand_audit_snapshot"
    assert captured["llm"].api_key == "test-key"
    assert captured["llm"].model == "premium-model"
