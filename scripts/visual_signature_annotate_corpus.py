#!/usr/bin/env python3
"""Annotate Visual Signature corpus payloads with the mock multimodal provider."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.annotations import annotate_visual_signature, build_annotation_audit  # noqa: E402
from src.visual_signature.annotations.calibration import annotation_audit_markdown  # noqa: E402
from src.visual_signature.annotations.providers.mock_provider import MockMultimodalAnnotationProvider  # noqa: E402


DEFAULT_INPUT_DIR = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "baselines"
    / "first_pass"
    / "eligible_payloads"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "mock_first_pass"
)


def annotate_corpus(
    *,
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    source = Path(input_dir)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    provider = MockMultimodalAnnotationProvider()
    started_at = datetime.now().isoformat()
    outputs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for path in sorted(source.glob("*.json")):
        if path.name == "manifest.json" or path.name.endswith(".error.json"):
            continue
        try:
            payload = _load_json(path)
            annotated = annotate_visual_signature(
                visual_signature_payload=payload,
                provider=provider,
                expected_category=_expected_category(payload),
                viewport_screenshot_path=_viewport_path(payload),
            )
            output_path = destination / path.name
            _write_json(output_path, annotated)
            outputs.append(
                {
                    "brand_name": annotated.get("brand_name"),
                    "website_url": annotated.get("website_url"),
                    "expected_category": _expected_category(annotated),
                    "status": (annotated.get("annotations") or {}).get("status"),
                    "output_json": str(output_path),
                }
            )
        except Exception as exc:
            errors.append({"source_json": str(path), "error": str(exc)})
    annotated_payloads = [_load_json(Path(row["output_json"])) for row in outputs]
    audit = build_annotation_audit(annotated_payloads)
    _write_json(destination / "annotation_audit.json", audit)
    (destination / "annotation_audit.md").write_text(annotation_audit_markdown(audit) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "visual-signature-corpus-annotation-run-1",
        "started_at": started_at,
        "completed_at": datetime.now().isoformat(),
        "provider": {"name": provider.name, "model": provider.model, "mock": True},
        "input_dir": str(source),
        "output_dir": str(destination),
        "total": len(outputs) + len(errors),
        "annotated": len(outputs),
        "errors": len(errors),
        "annotation_audit_json": str(destination / "annotation_audit.json"),
        "annotation_audit_md": str(destination / "annotation_audit.md"),
        "results": outputs,
        "error_results": errors,
    }
    _write_json(destination / "manifest.json", manifest)
    return manifest


def _expected_category(payload: dict[str, Any]) -> str | None:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    value = calibration.get("expected_category") or payload.get("category")
    return str(value) if value else None


def _viewport_path(payload: dict[str, Any]) -> str | None:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    path = screenshot.get("path")
    return str(path) if path else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Annotate Visual Signature corpus payloads with a mock provider.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Folder of Visual Signature payload JSON files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Folder for annotation overlay JSON files.")
    args = parser.parse_args(argv)
    result = annotate_corpus(input_dir=args.input_dir, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
