from __future__ import annotations

from src.visual_signature import capture, perception
from src.visual_signature.versions import (
    VISUAL_DIAGNOSIS_CLEAN_CAPTURE_DECISION_SCHEMA_VERSION,
    VISUAL_EVIDENCE_PACK_SCHEMA_VERSION,
)


def test_capture_api_exports_are_resolvable() -> None:
    assert capture.__all__ == [
        "VisualDiagnosis",
        "VisualEvidenceBundle",
        "VisualEvidenceSource",
        "VisualSignalProvenance",
        "VisualEvidence",
        "fuse_visual_signature_payloads",
        "build_visual_diagnosis",
        "build_clean_capture_decision",
        "build_visual_evidence_from_local_inputs",
        "clean_attempt_quality",
        "capture_computed_style_snapshot",
        "computed_style_snapshot_to_visual_signature",
        "enrich_visual_signature_with_local_screenshot",
        "screenshot_capture_to_visual_signature",
        "extract_computed_style_snapshot_from_page",
        "build_signal_provenance",
    ]
    assert all(hasattr(capture, item) for item in capture.__all__)

    assert capture.VisualEvidenceBundle().schema_version == VISUAL_EVIDENCE_PACK_SCHEMA_VERSION
    assert (
        capture.build_clean_capture_decision(
            {
                "raw_screenshot_path": "/tmp/example.png",
                "raw_viewport_metrics": {"viewport_whitespace_ratio": 0.4, "viewport_composition": "clean"},
                "clean_attempt_metrics": {"viewport_whitespace_ratio": 0.35, "viewport_composition": "clean"},
                "before_obstruction": {"present": True, "type": "cookie_banner", "coverage_ratio": 0.5},
                "after_obstruction": {"present": False, "type": "none", "coverage_ratio": 0.2},
                "dismissal_attempted": True,
            }
        )["schema_version"]
        == VISUAL_DIAGNOSIS_CLEAN_CAPTURE_DECISION_SCHEMA_VERSION
    )


def test_perception_api_exports_are_resolvable() -> None:
    assert perception.__all__ == [
        "PerceptualStateMachine",
        "classify_mutation_result",
        "classify_obstruction_state",
        "evaluate_intervention_eligibility",
    ]
    assert all(hasattr(perception, item) for item in perception.__all__)
