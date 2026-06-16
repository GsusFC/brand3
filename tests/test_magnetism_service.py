from __future__ import annotations

from pathlib import Path

from src.features.magnetism.extractor import MagnetismExtractor
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


def test_run_magnetism_from_url_forwards_run_input_sources_to_audit_runner(monkeypatch) -> None:
    captured = {}

    def fake_audit_runner(url: str, *, progress_cb=None, run_input_sources=None) -> dict[str, int]:
        captured["url"] = url
        captured["run_input_sources"] = run_input_sources
        if progress_cb is not None:
            progress_cb("extracting")
        return {
            "run_id": 200,
        }

    def fake_magnetism_from_run(run_id: int, *, llm=None, db_path=None):
        assert run_id == 200
        return {"source": "brand_audit_snapshot", "source_run_id": run_id}

    monkeypatch.setattr(
        "src.services.magnetism_service.run_magnetism_from_audit_run",
        fake_magnetism_from_run,
    )

    phases: list[str] = []
    result = run_magnetism_from_url(
        "https://service.test",
        audit_runner=fake_audit_runner,
        run_input_sources={"hyperbrowser", "context"},
        progress_cb=phases.append,
    )

    assert captured["url"] == "https://service.test"
    assert captured["run_input_sources"] == {"hyperbrowser", "context"}
    assert result["source_run_id"] == 200
    assert "interpreting" in phases


def test_run_magnetism_from_audit_snapshot_builds_default_llm_when_available(monkeypatch) -> None:
    captured = {}

    class FakeLLM:
        def __init__(self, model=None):
            self.api_key = "test-key"
            self.model = model

    class FakeExtractor:
        def __init__(self, llm=None, *, analyst_llm=None, system_reading_llm=None):
            captured["llm"] = llm
            captured["analyst_llm"] = analyst_llm
            captured["system_reading_llm"] = system_reading_llm

        def extract_from_audit_snapshot(self, snapshot):
            return {"source": "brand_audit_snapshot", "snapshot": snapshot}

    monkeypatch.setattr("src.services.magnetism_service.LLMAnalyzer", FakeLLM)
    monkeypatch.setattr("src.services.magnetism_service.MagnetismExtractor", FakeExtractor)
    monkeypatch.setattr("src.services.magnetism_service.MAGNETISM_EXTRACTOR_MODEL", "extract-model")
    monkeypatch.setattr("src.services.magnetism_service.MAGNETISM_ANALYST_MODEL", "analyst-model")
    monkeypatch.setattr("src.services.magnetism_service.MAGNETISM_SYSTEM_READING_MODEL", "system-model")

    result = run_magnetism_from_audit_snapshot({"run": {"id": 1}})

    assert result["source"] == "brand_audit_snapshot"
    assert captured["llm"].api_key == "test-key"
    assert captured["llm"].model == "extract-model"
    assert captured["analyst_llm"].model == "analyst-model"
    assert captured["system_reading_llm"].model == "system-model"


def test_run_magnetism_from_audit_snapshot_preserves_explicit_single_llm(monkeypatch) -> None:
    captured = {}

    class FakeExtractor:
        def __init__(self, llm=None, *, analyst_llm=None, system_reading_llm=None):
            captured["llm"] = llm
            captured["analyst_llm"] = analyst_llm
            captured["system_reading_llm"] = system_reading_llm

        def extract_from_audit_snapshot(self, snapshot):
            return {"source": "brand_audit_snapshot", "snapshot": snapshot}

    explicit_llm = object()
    monkeypatch.setattr("src.services.magnetism_service.MagnetismExtractor", FakeExtractor)

    result = run_magnetism_from_audit_snapshot({"run": {"id": 1}}, llm=explicit_llm)

    assert result["source"] == "brand_audit_snapshot"
    assert captured["llm"] is explicit_llm
    assert captured["analyst_llm"] is None
    assert captured["system_reading_llm"] is None


def test_magnetism_extractor_uses_separate_analyst_llm(monkeypatch) -> None:
    class FakeLLM:
        api_key = "test-key"

    extraction_llm = FakeLLM()
    analyst_llm = FakeLLM()
    system_llm = FakeLLM()
    captured = {}

    def fake_run_analyst_tldr_pass(**kwargs):
        captured["llm"] = kwargs["llm"]
        return {
            "raw": {},
            "validated": {
                "prompt_version": "test",
                "tldr_brand3": {"mission": {"detected": True}},
            },
            "analysis_error": None,
        }

    monkeypatch.setattr(
        "src.features.magnetism.extractor.run_analyst_tldr_pass",
        fake_run_analyst_tldr_pass,
    )

    result = {"tldr_brand3": {"mission": {"detected": True}}}
    extractor = MagnetismExtractor(
        llm=extraction_llm,
        analyst_llm=analyst_llm,
        system_reading_llm=system_llm,
    )

    extractor._apply_research_pack_tldr(
        result=result,
        brand_name="Acme",
        url="https://acme.test",
        packet_dict={},
        brand_context_brief={},
    )

    assert captured["llm"] is analyst_llm
    assert result["tldr_generation_mode"] == "analyst_pass_validated"


def test_magnetism_extractor_uses_separate_system_reading_llm(monkeypatch) -> None:
    class FakeLLM:
        api_key = "test-key"

    extraction_llm = FakeLLM()
    analyst_llm = FakeLLM()
    system_llm = FakeLLM()
    captured = {}

    def fake_maybe_build_system_reading(**kwargs):
        captured["llm"] = kwargs["llm"]
        return {"diagnosis": "LLM system reading."}

    monkeypatch.setattr(
        "src.features.magnetism.extractor.maybe_build_system_reading",
        fake_maybe_build_system_reading,
    )

    extractor = MagnetismExtractor(
        llm=extraction_llm,
        analyst_llm=analyst_llm,
        system_reading_llm=system_llm,
    )
    reading = extractor._build_system_reading(
        tldr={},
        layers={},
        metrics={},
        url="https://acme.test",
        brand_name="Acme",
    )

    assert captured["llm"] is system_llm
    assert reading == {"diagnosis": "LLM system reading."}


def test_magnetism_extractor_records_llm_model_roles() -> None:
    class FakeLLM:
        api_key = "test-key"

        def __init__(self, model: str):
            self.model = model

    extractor = MagnetismExtractor(
        llm=FakeLLM("extract-tier"),
        analyst_llm=FakeLLM("analyst-tier"),
        system_reading_llm=FakeLLM("system-tier"),
    )

    assert extractor._llm_model_roles() == {
        "magnetism_extractor": "extract-tier",
        "magnetism_analyst": "analyst-tier",
        "magnetism_system_reading": "system-tier",
    }
