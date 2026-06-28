import json
import subprocess
import sys

from src.sv9_flow import (
    BRAND_EVIDENCE_PACK_VERSION,
    BRAND_INTERPRETATION_VERSION,
    SV9_FLOW_CANDIDATE_VERSION,
    SV9_TILE_SIGNALS_VERSION,
)
from src.sv9_flow.adapters import build_flow_candidate_from_current_outputs
from src.sv9_flow.reporting import SV9_FLOW_REPORT_VERSION, build_flow_report
from src.sv9_flow.surface import (
    CURRENT_SURFACE_INVENTORY,
    legacy_score_artifacts,
    pre_sv9_authority_violations,
    worker_artifacts,
)


def test_flow_candidate_builds_evidence_interpretation_and_tile_signals_without_score() -> None:
    snapshot = {
        "run": {"brand_name": "Acme", "url": "https://acme.example"},
        "raw_inputs": [
            {
                "source": "homepage",
                "payload": {
                    "url": "https://acme.example",
                    "text": "Acme helps finance teams close books faster with automated workflows.",
                },
            }
        ],
        "features": [
            {
                "dimension_name": "coherencia",
                "feature_name": "tone_consistency",
                "value": 0.8,
                "confidence": 0.9,
                "raw_value": "Tone is consistently operational and precise.",
            }
        ],
    }
    tldr = {
        "tldr_brand3": {
            "mission": {"detected": True, "content": "Help finance teams close faster."},
            "value_proposition": {"detected": True, "content": "Automated workflows for finance teams."},
        }
    }

    candidate = build_flow_candidate_from_current_outputs(snapshot=snapshot, tldr_payload=tldr)
    payload = candidate.to_dict()

    assert payload["schema_version"] == SV9_FLOW_CANDIDATE_VERSION
    assert payload["evidence_pack"]["schema_version"] == BRAND_EVIDENCE_PACK_VERSION
    assert payload["interpretation"]["schema_version"] == BRAND_INTERPRETATION_VERSION
    assert payload["evidence_pack"]["brand_name"] == "Acme"
    assert "brand3_score" not in payload
    assert "score" not in payload

    signals = payload["tile_signals"]
    assert signals
    assert all(signal["schema_version"] == SV9_TILE_SIGNALS_VERSION for signal in signals)
    assert {signal["effect"] for signal in signals} == {"supports"}
    assert {signal["source"] for signal in signals} == {"brand_interpretation"}


def test_flow_candidate_keeps_visual_signature_as_evidence_only_tile_signals() -> None:
    visual_signature = {
        "schema_version": "visual-signature-evidence-v1",
        "capture": {"status": "usable", "first_fold_evaluable": True},
        "tile_signals": [
            {
                "tile": "coherencia.C6",
                "effect": "weakens",
                "confidence": "medium",
                "source": "heuristic",
                "rationale": "Hero copy and visible visual system point in different directions.",
            }
        ],
    }

    candidate = build_flow_candidate_from_current_outputs(
        snapshot={"run": {"brand_name": "Acme", "url": "https://acme.example"}},
        tldr_payload={"tldr_brand3": {}},
        visual_signature_evidence=visual_signature,
    )
    signals = candidate.to_dict()["tile_signals"]

    assert {
        (signal["tile"], signal["effect"], signal["source"])
        for signal in signals
    } == {("coherencia.C6", "weakens", "visual_signature")}
    assert candidate.evidence_pack.evidence[0].ref == "visual_signature.capture"


def test_flow_candidate_blocks_positive_visual_signal_when_capture_is_unusable() -> None:
    visual_signature = {
        "schema_version": "visual-signature-evidence-v1",
        "capture": {"status": "blocked", "first_fold_evaluable": False},
        "tile_signals": [
            {
                "tile": "coherencia.C6",
                "effect": "supports",
                "confidence": "high",
                "rationale": "Would be unsafe to trust because capture is blocked.",
            }
        ],
    }

    candidate = build_flow_candidate_from_current_outputs(
        snapshot={"run": {"brand_name": "Acme", "url": "https://acme.example"}},
        tldr_payload={"tldr_brand3": {}},
        visual_signature_evidence=visual_signature,
    )
    signals = candidate.to_dict()["tile_signals"]

    assert signals == [
        {
            "schema_version": SV9_TILE_SIGNALS_VERSION,
            "component": "visual_signature",
            "tile": "visual_signature.capture",
            "effect": "capture_unreliable",
            "confidence": "medium",
            "source": "visual_signature",
            "evidence_refs": ["visual_signature.capture"],
            "rationale": "Visual Signature capture is not usable.",
        }
    ]


def test_flow_report_summarizes_candidate_quality_controls() -> None:
    candidate = build_flow_candidate_from_current_outputs(
        snapshot={"run": {"brand_name": "Acme", "url": "https://acme.example"}},
        tldr_payload={"tldr_brand3": {"mission": {"detected": True, "content": "Help teams ship."}}},
    )

    report = build_flow_report(candidate)

    assert report["schema_version"] == SV9_FLOW_REPORT_VERSION
    assert report["candidate_schema_version"] == SV9_FLOW_CANDIDATE_VERSION
    assert report["brand_name"] == "Acme"
    assert report["counts"]["interpretation_blocks"] == 1
    assert report["tile_signal_effects"] == {"supports": 1}


def test_sv9_flow_candidate_script_reads_json_and_prints_report(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    tldr_path = tmp_path / "tldr.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "run": {"brand_name": "Acme", "url": "https://acme.example"},
                "raw_inputs": [{"source": "homepage", "payload": {"text": "Acme helps teams ship."}}],
            }
        ),
        encoding="utf-8",
    )
    tldr_path.write_text(
        json.dumps({"tldr_brand3": {"mission": {"detected": True, "content": "Help teams ship."}}}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/sv9_flow_candidate.py",
            "--snapshot",
            str(snapshot_path),
            "--tldr",
            str(tldr_path),
            "--report",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["schema_version"] == SV9_FLOW_REPORT_VERSION
    assert payload["brand_name"] == "Acme"
    assert payload["counts"]["evidence_records"] == 1
    assert payload["tile_signal_effects"] == {"supports": 1}


def test_surface_inventory_keeps_scores_out_of_pre_sv9_canonical_path() -> None:
    assert pre_sv9_authority_violations() == []

    legacy_names = {artifact.name for artifact in legacy_score_artifacts()}
    assert "Magnetism score" in legacy_names
    assert "Visual Signature score" in legacy_names
    assert "SV9 scan" not in legacy_names


def test_surface_inventory_identifies_workers_to_extract_before_orchestrators() -> None:
    worker_names = {artifact.name for artifact in worker_artifacts()}

    assert {
        "Pass 1",
        "tldr_brand3",
        "Research Pack",
        "EvidenceGraph / Evidence vNext",
        "Visual Signature evidence",
        "SV9 tile signals",
    }.issubset(worker_names)
    assert len(CURRENT_SURFACE_INVENTORY) >= len(worker_names)
