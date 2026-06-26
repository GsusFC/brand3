"""Build the offline Brand3 platform dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.platform.platform_builder_constants import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SCORING_OUTPUT_ROOT,
    DEFAULT_VISUAL_SIGNATURE_ROOT,
    GUARDRAILS,
    PROJECT_ROOT,
    SCORING_ARTIFACT_SPECS,
    VISUAL_SIGNATURE_ARTIFACT_SPECS,
    VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE,
)
from src.visual_signature.platform.platform_builder_artifacts import (
    absolute_artifact_path as _absolute_artifact_path,
    build_artifacts as _build_artifacts,
)
from src.visual_signature.platform.platform_builder_render import _platform_css
from src.visual_signature.platform.platform_builder_render import _platform_js
from src.visual_signature.platform.platform_builder_render import _render_index_html
from src.visual_signature.platform.platform_builder_sections import _build_scoring_summary
from src.visual_signature.platform.platform_builder_sections import build_sections
from src.visual_signature.platform.platform_builder_utils import _load_json_if_exists
from src.visual_signature.platform.platform_builder_utils import _write_text
from src.visual_signature.platform.platform_models import PlatformBundle
from src.visual_signature.versions import VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION


def build_platform_bundle(
    *,
    output_root: str | Path | None = None,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> dict[str, Any]:
    output_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    visual_signature_root = Path(visual_signature_root)
    scoring_output_root = Path(scoring_output_root)
    artifacts = _build_artifacts(
        output_root=output_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    artifact_map = {artifact.key: artifact for artifact in artifacts}
    json_map = {
        artifact.key: (
            _load_json_if_exists(_absolute_artifact_path(artifact, visual_signature_root, scoring_output_root))
            if artifact.artifact_type == "json"
            else None
        )
        for artifact in artifacts
    }
    scoring_summary = _build_scoring_summary(scoring_output_root=scoring_output_root, output_root=output_root)
    sections = build_sections(
        artifact_map=artifact_map,
        json_map=json_map,
        scoring_summary=scoring_summary,
        output_root=output_root,
        visual_signature_root=visual_signature_root,
    )

    missing_required = [artifact.key for artifact in artifacts if artifact.required and not artifact.exists]
    platform_status = "ready" if not missing_required else "degraded"
    navigation = [{"key": section.key, "label": section.title} for section in sections]
    next_steps = [
        "Inspect Initial Scoring and Visual Signature separately; do not use this platform as a scoring integration layer.",
        "Review pending queue items in the Reviewer Workflow section.",
        "Use calibration readiness block reasons to decide the next evidence collection target.",
        "Keep governance checks green before any broader corpus or provider pilot work.",
        "Treat this platform as navigation only; update source JSON/Markdown through existing generators.",
    ]
    bundle = PlatformBundle(
        schema_version=VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION,
        record_type=VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE,
        generated_at=datetime.now(timezone.utc).isoformat(),
        platform_status=platform_status,
        guardrails=GUARDRAILS,
        artifacts=artifacts,
        sections=sections,
        navigation=navigation,
        next_steps=next_steps,
        notes=[
            "Static/local dashboard generated from existing Brand3 scoring and Visual Signature artifacts.",
            "Initial Scoring and Visual Signature remain conceptually and technically separated.",
            "The platform does not create reviews, mutate captures, call providers, recompute scores, or affect production reports.",
        ],
    )
    return bundle.to_dict()


def validate_platform_bundle(
    *,
    platform_root: str | Path,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> list[str]:
    platform_root = Path(platform_root)
    errors: list[str] = []
    for filename in ("index.html", "platform.css", "platform.js"):
        if not (platform_root / filename).exists():
            errors.append(f"missing platform file: {filename}")

    payload = build_platform_bundle(
        output_root=platform_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    required_missing = [
        artifact["key"]
        for artifact in payload["artifacts"]
        if artifact["required"] and not artifact["exists"]
    ]
    if required_missing:
        errors.append(f"missing required source artifacts: {', '.join(required_missing)}")

    sections = {section["title"] for section in payload["sections"]}
    for title in ("Brand3 Overview", "Initial Scoring", "Visual Signature", "Captures", "Reviewer Workflow", "Calibration", "Governance", "Corpus Expansion"):
        if title not in sections:
            errors.append(f"missing section: {title}")
    return errors


def write_platform_bundle(
    *,
    output_root: str | Path | None = None,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> dict[str, str]:
    platform_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    platform_root.mkdir(parents=True, exist_ok=True)
    payload = build_platform_bundle(
        output_root=platform_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    _write_text(platform_root / "index.html", _render_index_html(payload))
    _write_text(platform_root / "platform.css", _platform_css())
    _write_text(platform_root / "platform.js", _platform_js())
    return {
        "platform_root": str(platform_root),
        "platform_index_html": str(platform_root / "index.html"),
        "platform_css": str(platform_root / "platform.css"),
        "platform_js": str(platform_root / "platform.js"),
    }
