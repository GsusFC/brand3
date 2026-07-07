from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.services.scanner_stability_audit import (
    StabilityAuditOptions,
    analyze_scanner_stability,
    render_stability_markdown,
)


def test_stability_audit_flags_interpretation_variance_with_same_inputs(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    payload_a = _payload(
        raw_inputs={"homepage": "same"},
        research_pack={"claims": ["same"]},
        analyst_tldr={"magnetism": {"answer": "A"}},
        version="SV9",
    )
    payload_b = _payload(
        raw_inputs={"homepage": "same"},
        research_pack={"claims": ["same"]},
        analyst_tldr={"magnetism": {"answer": "B"}},
        version="SV9",
    )
    _insert_scan(db_path, 1, "Example", "https://example.com", 62, 70, payload_a)
    _insert_scan(db_path, 2, "Example", "https://www.example.com/", 72, 70, payload_b)

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(version="SV9"))

    assert report["repeated_group_count"] == 1
    group = report["groups"][0]
    assert group["diagnosis_stage"] == "interpretation_drift"
    assert group["numeric_stats"]["magnetism_score"]["range"] == 10
    assert "analyst_tldr_hash" in group["changing_hashes"]
    assert "raw_inputs_hash" not in group["changing_hashes"]
    assert "research_pack_hash" not in group["changing_hashes"]


def test_stability_audit_prioritizes_acquisition_when_raw_inputs_change(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    _insert_scan(
        db_path,
        1,
        "Example",
        "https://example.com",
        61,
        70,
        _payload(raw_inputs={"homepage": "first"}, research_pack={"claims": ["first"]}, version="SV9"),
    )
    _insert_scan(
        db_path,
        2,
        "Example",
        "https://example.com",
        81,
        72,
        _payload(raw_inputs={"homepage": "second"}, research_pack={"claims": ["second"]}, version="SV9"),
    )

    report = analyze_scanner_stability(db_path)

    group = report["groups"][0]
    assert group["diagnosis_stage"] == "acquisition_drift"
    assert group["max_numeric_range"] == 20
    assert "raw_inputs_hash" in group["changing_hashes"]


def test_stability_audit_uses_sv9_component_scores_when_available(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    _create_sv9_schema(db_path)
    base_payload = _payload(raw_inputs={"homepage": "same"}, research_pack={"claims": ["same"]}, version="SV9")
    _insert_scan(db_path, 1, "Example", "https://example.com", 70, 70, base_payload, source_run_id=101)
    _insert_scan(db_path, 2, "Example", "https://example.com", 70, 70, base_payload, source_run_id=102)
    _insert_sv9(db_path, 1, 101, 70, "clarity", 5)
    _insert_sv9(db_path, 2, 102, 70, "clarity", 8)

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(version="SV9"))

    group = report["groups"][0]
    assert group["diagnosis_stage"] == "scoring_drift"
    assert "sv9_component_scores_hash" in group["changing_hashes"]


def test_stability_audit_hashes_persisted_raw_inputs_by_source_run(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    _create_raw_inputs_schema(db_path)
    payload = _payload(raw_inputs={}, research_pack={"claims": ["same"]}, version="SV9")
    _insert_scan(db_path, 1, "Example", "https://example.com", 70, 70, payload, source_run_id=101)
    _insert_scan(db_path, 2, "Example", "https://example.com", 60, 70, payload, source_run_id=102)
    _insert_raw_input(db_path, 101, "web", {"html": "first"})
    _insert_raw_input(db_path, 102, "web", {"html": "second"})

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(version="SV9"))

    group = report["groups"][0]
    assert group["diagnosis_stage"] == "acquisition_drift"
    assert "raw_inputs_hash" in group["changing_hashes"]


def test_stability_audit_separates_runs_by_exa_strategy(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    _create_raw_inputs_schema(db_path)
    payload = _payload(raw_inputs={}, research_pack={"claims": ["same"]}, version="SV9")
    _insert_scan(db_path, 1, "Example", "https://example.com", 80, 90, payload, source_run_id=101)
    _insert_scan(db_path, 2, "Example", "https://example.com", 60, 70, payload, source_run_id=102)
    _insert_raw_input(db_path, 101, "exa", {"diagnostics": {"strategy": "precision_vnext_v1"}})
    _insert_raw_input(db_path, 102, "exa", {"diagnostics": {"strategy": "precision_vnext_v2"}})

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(version="SV9"))

    assert report["repeated_group_count"] == 0


def test_stability_audit_flags_storage_payload_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    payload = _payload(raw_inputs={}, research_pack={"claims": ["same"]}, version="SV9")
    payload["magnetism_score"] = 70
    payload["coherence_score"] = 80
    payload["quadrant"] = "payload quadrant"
    _insert_scan(db_path, 1, "Example", "https://example.com", 70, 80, payload)
    _insert_scan(db_path, 2, "Example", "https://example.com", 0, 40, payload)

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(version="SV9"))

    group = report["groups"][0]
    assert group["diagnosis_stage"] == "persistence_drift"
    assert "storage_payload_mismatch" in group["changing_fields"]


def test_stability_audit_exposes_strict_group_dimensions_and_day_bucket(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)
    payload = _payload(raw_inputs={"homepage": "same"}, research_pack={"claims": ["same"]}, version="scanner-v1")
    payload["lang"] = "es"
    payload["visual_signature_version"] = "visual-v1"
    payload["tldr_prompt_version"] = "tldr-v1"
    payload["research_pack_builder_version"] = "pack-v1"
    payload["capture_strategy"] = "playwright"
    _insert_scan(db_path, 1, "Example", "https://example.com", 70, 80, payload, created_at="2026-06-29T01:00:00+00:00")
    _insert_scan(db_path, 2, "Example", "https://example.com", 70, 80, payload, created_at="2026-06-29T02:00:00+00:00")

    report = analyze_scanner_stability(db_path, options=StabilityAuditOptions(group_by_day=True))

    dimensions = report["groups"][0]["group_dimensions"]
    assert dimensions["normalized_brand_or_url"] == "example.com"
    assert dimensions["scanner_version"] == "scanner-v1"
    assert dimensions["lang"] == "es"
    assert dimensions["visual_signature_version"] == "visual-v1"
    assert dimensions["tldr_prompt_version"] == "tldr-v1"
    assert dimensions["research_pack_builder_version"] == "pack-v1"
    assert dimensions["exa_strategy"] == "unknown"
    assert dimensions["capture_strategy"] == "playwright"
    assert dimensions["created_day_bucket"] == "2026-06-29"


def test_stability_markdown_handles_empty_report(tmp_path: Path) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    _create_magnetism_schema(db_path)

    report = analyze_scanner_stability(db_path)
    markdown = render_stability_markdown(report)

    assert "No repeated scanner groups found" in markdown


def _create_magnetism_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE magnetism_scans (
                id INTEGER PRIMARY KEY,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                magnetism_score INTEGER NOT NULL,
                coherence_score INTEGER NOT NULL,
                quadrant TEXT NOT NULL,
                raw_payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                source_run_id INTEGER
            )
            """
        )


def _create_sv9_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE sv9_scans (
                id INTEGER PRIMARY KEY,
                brand_name TEXT,
                url TEXT,
                source_run_id INTEGER,
                rubric_version TEXT,
                brand3_score INTEGER,
                model TEXT,
                evaluator_model TEXT,
                reliability_status TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE sv9_component_scores (
                id INTEGER PRIMARY KEY,
                scan_id INTEGER,
                component TEXT,
                status TEXT,
                score INTEGER,
                scale INTEGER,
                points INTEGER,
                confidence TEXT,
                veredicto TEXT,
                evidence_json TEXT
            )
            """
        )


def _create_raw_inputs_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE raw_inputs (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def _payload(
    *,
    raw_inputs: dict,
    research_pack: dict,
    analyst_tldr: dict | None = None,
    version: str,
) -> dict:
    return {
        "scanner_version": version,
        "debug": {
            "raw_inputs": raw_inputs,
            "normalized_payload": {
                "research_pack": research_pack,
                "analyst_tldr_validated": analyst_tldr or {"magnetism": {"answer": "same"}},
            },
        },
        "tldr_brand3": analyst_tldr or {"magnetism": {"answer": "same"}},
    }


def _insert_scan(
    db_path: Path,
    scan_id: int,
    brand_name: str,
    url: str,
    magnetism_score: int,
    coherence_score: int,
    payload: dict,
    *,
    source_run_id: int | None = None,
    created_at: str = "2026-06-29T00:00:00+00:00",
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO magnetism_scans (
                id, brand_name, url, magnetism_score, coherence_score, quadrant,
                raw_payload, created_at, status, source_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?)
            """,
            (
                scan_id,
                brand_name,
                url,
                magnetism_score,
                coherence_score,
                "steady quadrant",
                json.dumps(payload),
                created_at,
                source_run_id,
            ),
        )


def _insert_raw_input(db_path: Path, run_id: int, source: str, payload: dict) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, source, json.dumps(payload), "2026-06-29T00:00:00+00:00"),
        )


def _insert_sv9(
    db_path: Path,
    scan_id: int,
    source_run_id: int,
    brand3_score: int,
    component: str,
    component_score: int,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sv9_scans (
                id, brand_name, url, source_run_id, rubric_version, brand3_score,
                model, evaluator_model, reliability_status, created_at
            ) VALUES (?, 'Example', 'https://example.com', ?, 'SV9', ?, 'sv9-model', 'eval-model', 'ok', ?)
            """,
            (scan_id, source_run_id, brand3_score, "2026-06-29T00:00:00+00:00"),
        )
        conn.execute(
            """
            INSERT INTO sv9_component_scores (
                scan_id, component, status, score, scale, points, confidence, veredicto, evidence_json
            ) VALUES (?, ?, 'ok', ?, 10, ?, 'high', 'ok', '{}')
            """,
            (scan_id, component, component_score, component_score),
        )
