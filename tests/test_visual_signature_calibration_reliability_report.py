from __future__ import annotations

from pathlib import Path

from src.visual_signature.calibration import (
    CALIBRATION_ROOT,
    build_calibration_reliability_report,
    validate_calibration_output_root,
    write_calibration_reliability_report,
)


def test_calibration_reliability_report_generation(tmp_path: Path):
    assert validate_calibration_output_root(CALIBRATION_ROOT) == []

    output_path = tmp_path / "calibration_reliability_report.md"
    written_path = write_calibration_reliability_report(CALIBRATION_ROOT, output_path)

    assert written_path == output_path
    assert output_path.exists()

    report = output_path.read_text(encoding="utf-8")
    assert "# Visual Signature Calibration Reliability Report" in report
    assert "Evidence-only: yes" in report
    assert "Manifest validation status: `valid`" in report
    assert "Bundle validation status: `valid`" in report
    assert "- Total claims: 5" in report
    assert "- Reviewed claims: 5" in report
    assert "- Confirmed: 2 (40%)" in report
    assert "- Contradicted: 2 (40%)" in report
    assert "- Unresolved: 1 (20%)" in report
    assert "- High-confidence contradictions: 2" in report
    assert "### Confidence Bucket Analysis" in report
    assert "- high: 5" in report
    assert "### Overconfidence Findings" in report
    assert "Allbirds" in report and "The Verge" in report
    assert "### Underconfidence Findings" in report
    assert "none surfaced in this bundle" in report
    assert "## Category Breakdown" in report
    assert "## Perception Source Breakdown" in report
    assert "## Claim Kind Breakdown" in report
    assert "## Notable Confirmed Claims" in report
    assert "## Notable Contradicted Claims" in report
    assert "## Unresolved Claims Needing Review" in report
    assert "OpenAI" in report
    assert "## Limitations" in report
    assert "not ready for broader corpus use" in report
    assert "Summary markdown present: yes" in report


def test_calibration_reliability_report_string_builder_reads_bundle():
    report = build_calibration_reliability_report(CALIBRATION_ROOT)
    assert "Visual Signature Calibration Reliability Report" in report
    assert "Summary markdown present: yes" in report
    assert "Source artifact refs: 5" in report
