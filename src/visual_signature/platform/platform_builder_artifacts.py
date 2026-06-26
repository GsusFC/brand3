"""Artifact resolution helpers for the offline platform dashboard."""

from __future__ import annotations

from pathlib import Path

from src.visual_signature.platform.platform_builder_constants import (
    DEFAULT_SCORING_OUTPUT_ROOT,
    PROJECT_ROOT,
    SCORING_ARTIFACT_SPECS,
    VISUAL_SIGNATURE_ARTIFACT_SPECS,
)
from src.visual_signature.platform.platform_builder_utils import (
    _artifact_summary,
    _filesystem_summary,
    _load_json_if_exists,
    _safe_get,
    _to_output_relative_path,
)
from src.visual_signature.platform.platform_models import PlatformArtifact


def build_artifacts(*, output_root: Path, visual_signature_root: Path, scoring_output_root: Path) -> list[PlatformArtifact]:
    artifacts: list[PlatformArtifact] = []
    for key, label, relative_path, artifact_type, required in SCORING_ARTIFACT_SPECS:
        absolute_path = PROJECT_ROOT / relative_path
        artifacts.append(
            PlatformArtifact(
                key=key,
                label=label,
                path=_to_output_relative_path(absolute_path, output_root=output_root),
                artifact_type=artifact_type,
                required=required,
                exists=absolute_path.exists(),
                summary=_filesystem_summary(absolute_path, artifact_type=artifact_type),
            )
        )
    if scoring_output_root != DEFAULT_SCORING_OUTPUT_ROOT:
        custom_scoring_paths = {
            "scoring_output_root": scoring_output_root,
            "scoring_reports_root": scoring_output_root / "reports",
        }
        artifacts = [
            PlatformArtifact(
                key=artifact.key,
                label=artifact.label,
                path=_to_output_relative_path(custom_scoring_paths[artifact.key], output_root=output_root),
                artifact_type=artifact.artifact_type,
                required=False,
                exists=custom_scoring_paths[artifact.key].exists(),
                summary=_filesystem_summary(custom_scoring_paths[artifact.key], artifact_type=artifact.artifact_type),
            )
            if artifact.key in custom_scoring_paths
            else artifact
            for artifact in artifacts
        ]
    for key, label, relative_path, artifact_type, required in VISUAL_SIGNATURE_ARTIFACT_SPECS:
        absolute_path = visual_signature_root / relative_path
        payload = _load_json_if_exists(absolute_path) if artifact_type == "json" else None
        artifacts.append(
            PlatformArtifact(
                key=key,
                label=label,
                path=_to_output_relative_path(absolute_path, output_root=output_root),
                artifact_type=artifact_type,
                required=required,
                exists=absolute_path.exists(),
                record_type=_safe_get(payload, "record_type"),
                generated_at=_safe_get(payload, "generated_at") or _safe_get(payload, "checked_at") or _safe_get(payload, "completed_at"),
                summary=_artifact_summary(payload),
            )
        )
    return artifacts


def absolute_artifact_path(artifact: PlatformArtifact, visual_signature_root: Path, scoring_output_root: Path) -> Path:
    if artifact.key == "scoring_output_root":
        return scoring_output_root
    if artifact.key == "scoring_reports_root":
        return scoring_output_root / "reports"
    for key, _label, relative_path, _type, _required in SCORING_ARTIFACT_SPECS:
        if key == artifact.key:
            return PROJECT_ROOT / relative_path
    for key, _label, relative_path, _type, _required in VISUAL_SIGNATURE_ARTIFACT_SPECS:
        if key == artifact.key:
            return visual_signature_root / relative_path
    return visual_signature_root / artifact.path
