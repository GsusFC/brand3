from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.annotations import annotate_visual_signature, build_annotation_audit
from src.visual_signature.annotations.annotate_visual_signature import validate_annotation_overlay
from src.visual_signature.annotations.providers.mock_provider import MockMultimodalAnnotationProvider
from src.visual_signature.annotations.types import ANNOTATION_TARGETS


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_annotate_corpus.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("visual_signature_annotate_corpus", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(brand_name: str = "Linear", category: str = "saas") -> dict:
    return {
        "brand_name": brand_name,
        "website_url": f"https://{brand_name.lower()}.example",
        "version": "visual-signature-mvp-1",
        "interpretation_status": "interpretable",
        "calibration": {"expected_category": category},
        "logo": {"logo_detected": True},
        "assets": {"image_count": 3},
        "vision": {
            "viewport_visual_density": "balanced",
            "screenshot": {
                "available": True,
                "quality": "usable",
                "path": "/tmp/mock.png",
                "capture_type": "viewport",
            },
        },
    }


def test_annotate_visual_signature_adds_top_level_annotation_overlay():
    annotated = annotate_visual_signature(visual_signature_payload=_payload())

    annotations = annotated["annotations"]
    assert annotations["version"] == "visual-signature-annotations-mvp-1"
    assert annotations["status"] == "annotated"
    assert annotations["provider"]["name"] == "mock"
    assert set(annotations["targets"]) == set(ANNOTATION_TARGETS)
    for target in annotations["targets"].values():
        assert target["label"]
        assert 0 <= target["confidence"] <= 1
        assert isinstance(target["evidence"], list)
        assert target["source"] in {"viewport_screenshot", "visual_signature_payload"}
        assert isinstance(target["limitations"], list)
    assert annotations["overall_confidence"]["score"] > 0
    assert validate_annotation_overlay(annotations)["valid"] is True


def test_annotate_visual_signature_handles_partial_mock_response():
    provider = MockMultimodalAnnotationProvider(
        {
            "status": "annotated",
            "targets": {
                "logo_prominence": {
                    "label": "clear",
                    "confidence": 0.9,
                    "evidence": ["Logo appears in the header."],
                    "source": "viewport_screenshot",
                    "limitations": [],
                }
            },
        }
    )

    annotated = annotate_visual_signature(visual_signature_payload=_payload(), provider=provider)

    assert annotated["annotations"]["status"] == "partial"
    assert list(annotated["annotations"]["targets"]) == ["logo_prominence"]
    validation = validate_annotation_overlay(annotated["annotations"])
    assert validation["valid"] is True
    assert validation["warnings"]


def test_annotate_visual_signature_marks_not_interpretable_without_provider_call():
    payload = _payload()
    payload["interpretation_status"] = "not_interpretable"

    annotated = annotate_visual_signature(visual_signature_payload=payload)

    assert annotated["annotations"]["status"] == "not_interpretable"
    assert annotated["annotations"]["targets"] == {}
    assert annotated["annotations"]["overall_confidence"]["score"] <= 0.2


def test_annotate_visual_signature_handles_provider_failure():
    annotated = annotate_visual_signature(
        visual_signature_payload=_payload(),
        provider=MockMultimodalAnnotationProvider(fail=True),
    )

    assert annotated["annotations"]["status"] == "failed"
    assert "mock_provider_failure" in annotated["annotations"]["errors"]
    assert annotated["annotations"]["overall_confidence"]["score"] == 0.0


def test_annotation_audit_summarizes_targets_and_statuses():
    payloads = [
        annotate_visual_signature(visual_signature_payload=_payload("A")),
        annotate_visual_signature(visual_signature_payload=_payload("B", "developer_first")),
    ]

    audit = build_annotation_audit(payloads)

    assert audit["total"] == 2
    assert audit["status_counts"]["annotated"] == 2
    assert audit["target_completion"]["logo_prominence"]["rate"] == 1.0
    assert "saas" in audit["per_category_status"]


def test_corpus_annotation_script_writes_overlays_and_audit(tmp_path):
    script = _load_script()
    input_dir = tmp_path / "payloads"
    output_dir = tmp_path / "annotations"
    input_dir.mkdir()
    for name in ("Linear", "Vercel"):
        (input_dir / f"{name.lower()}.json").write_text(json.dumps(_payload(name)), encoding="utf-8")

    manifest = script.annotate_corpus(input_dir=input_dir, output_dir=output_dir)

    assert manifest["annotated"] == 2
    assert manifest["errors"] == 0
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "annotation_audit.json").exists()
    assert "# Visual Signature Annotation Audit" in (output_dir / "annotation_audit.md").read_text(encoding="utf-8")
    overlay = json.loads((output_dir / "linear.json").read_text(encoding="utf-8"))
    assert overlay["annotations"]["provider"]["mock"] is True
