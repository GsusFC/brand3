"""Experimental perceptual narrative hints for §4 findings.

This module reads static perceptual library artifacts and turns them into
prompt hints. It is intentionally opt-in and does not affect scoring,
report structure, Visual Signature, or runtime behavior unless callers
explicitly pass the hints into the narrative layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PERCEPTUAL_ROOT = ROOT / "examples" / "perceptual_library"
PATTERN_REGISTRY_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_pattern_registry.json"
READING_SEMANTICS_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_reading_semantics.json"
CASE_RECORD_GLOB = "cases/*/perceptual_case_record.json"

DEFAULT_DIMENSION_PATTERNS = {
    "coherencia": [
        "pattern_evidence_bound_behavior",
        "pattern_system_cohesion_difference",
        "pattern_claim_signal_gap",
    ],
    "presencia": [
        "pattern_guided_movement",
        "pattern_threshold_pacing",
        "pattern_claim_signal_gap",
    ],
    "percepcion": [
        "pattern_category_surface_translation",
        "pattern_evidence_bound_behavior",
        "pattern_claim_signal_gap",
    ],
    "diferenciacion": [
        "pattern_category_surface_translation",
        "pattern_system_cohesion_difference",
        "pattern_claim_signal_gap",
    ],
    "vitalidad": [
        "pattern_guided_movement",
        "pattern_concept_bearing_motion",
        "pattern_threshold_pacing",
    ],
}

FALLBACK_PATTERNS = [
    "pattern_category_surface_translation",
    "pattern_evidence_bound_behavior",
    "pattern_claim_signal_gap",
]


@dataclass(frozen=True)
class PerceptualNarrativeHints:
    """Structured hints passed to findings generation."""

    surface_signals: list[str] = field(default_factory=list)
    signal_clusters: list[str] = field(default_factory=list)
    matched_patterns: list[dict[str, str]] = field(default_factory=list)
    productive_tensions: list[str] = field(default_factory=list)
    confidence_notes: list[str] = field(default_factory=list)
    overreach_boundaries: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return not any(
            (
                self.surface_signals,
                self.signal_clusters,
                self.matched_patterns,
                self.productive_tensions,
                self.confidence_notes,
                self.overreach_boundaries,
            )
        )


def build_perceptual_narrative_hints(dimension: str) -> PerceptualNarrativeHints:
    """Build static narrative hints for one report dimension.

    The hints are reading lenses, not facts about the target brand. They must
    only guide how a finding handles evidence, confidence, and overreach.
    """
    artifacts = _load_artifacts()
    if not artifacts:
        return PerceptualNarrativeHints()

    pattern_ids = DEFAULT_DIMENSION_PATTERNS.get(dimension, FALLBACK_PATTERNS)
    registry = artifacts.get("registry") or {}
    patterns = {
        pattern.get("pattern_id"): pattern
        for pattern in registry.get("patterns", [])
        if isinstance(pattern, dict)
    }
    matched = [patterns[pid] for pid in pattern_ids if pid in patterns]

    return PerceptualNarrativeHints(
        surface_signals=_collect_surface_signals(artifacts.get("case_records", []), limit=5),
        signal_clusters=_collect_signal_clusters(artifacts.get("semantics") or {}, limit=3),
        matched_patterns=_format_matched_patterns(matched),
        productive_tensions=_collect_tensions(matched, limit=5),
        confidence_notes=_confidence_notes(artifacts.get("semantics") or {}),
        overreach_boundaries=_overreach_boundaries(artifacts.get("semantics") or {}),
    )


def format_perceptual_hints_for_prompt(hints: PerceptualNarrativeHints | None) -> str:
    """Render hints as a bounded prompt section."""
    if hints is None or hints.empty():
        return ""

    lines = [
        "EXPERIMENTAL PERCEPTUAL NARRATIVE HINTS",
        "Use these as reading lenses only. They are not facts about the target brand.",
        "Do not mention FLOC*, Charms, D4DATA, or Grandvalira unless those names appear in the evidence pool.",
        "",
    ]
    lines.extend(_section("Surface signals to look for", hints.surface_signals))
    lines.extend(_section("Signal clusters", hints.signal_clusters))
    if hints.matched_patterns:
        lines.append("Matched perceptual patterns:")
        for pattern in hints.matched_patterns:
            lines.append(
                "- "
                + pattern["pattern_name"]
                + ": "
                + pattern["perceptual_meaning"]
                + f" (confidence: {pattern['confidence_level']})"
            )
        lines.append("")
    lines.extend(_section("Productive tensions", hints.productive_tensions))
    lines.extend(_section("Confidence notes", hints.confidence_notes))
    lines.extend(_section("Overreach boundaries", hints.overreach_boundaries))
    lines.extend(
        [
            "Hard experimental rule: if material is copy-based, weak, unverified, or review-bound,",
            "write it as a limitation or conditional implication, never as fact.",
        ]
    )
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _load_artifacts() -> dict[str, Any]:
    if not PATTERN_REGISTRY_PATH.exists() or not READING_SEMANTICS_PATH.exists():
        return {}
    try:
        registry = _load_json(PATTERN_REGISTRY_PATH)
        semantics = _load_json(READING_SEMANTICS_PATH)
        case_records = [
            _load_json(path)
            for path in sorted(PERCEPTUAL_ROOT.glob(CASE_RECORD_GLOB))
            if path.is_file()
        ]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return {
        "registry": registry,
        "semantics": semantics,
        "case_records": case_records,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _collect_surface_signals(case_records: list[dict[str, Any]], limit: int) -> list[str]:
    signals: list[str] = []
    for record in case_records:
        for observation in record.get("visual_observations", []):
            if not isinstance(observation, dict):
                continue
            text = str(observation.get("observation") or "").strip()
            if text:
                signals.append(text)
            if len(signals) >= limit:
                return signals
    return signals


def _collect_signal_clusters(semantics: dict[str, Any], limit: int) -> list[str]:
    clusters: list[str] = []
    defs = semantics.get("definitions") or {}
    signal_clusters = defs.get("signal_clusters") or {}
    for example in signal_clusters.get("examples", []):
        if not isinstance(example, dict):
            continue
        cluster = example.get("cluster")
        if not isinstance(cluster, list):
            continue
        cluster_text = ", ".join(str(item) for item in cluster if item)
        if cluster_text:
            clusters.append(cluster_text)
        if len(clusters) >= limit:
            return clusters
    return clusters


def _format_matched_patterns(patterns: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for pattern in patterns:
        out.append(
            {
                "pattern_id": str(pattern.get("pattern_id") or ""),
                "pattern_name": str(pattern.get("pattern_name") or ""),
                "perceptual_meaning": str(pattern.get("perceptual_meaning") or ""),
                "confidence_level": str(pattern.get("confidence_level") or ""),
            }
        )
    return out


def _collect_tensions(patterns: list[dict[str, Any]], limit: int) -> list[str]:
    tensions: list[str] = []
    for pattern in patterns:
        for tension in pattern.get("typical_tensions", []):
            text = str(tension).strip()
            if text and text not in tensions:
                tensions.append(text)
            if len(tensions) >= limit:
                return tensions
    return tensions


def _confidence_notes(semantics: dict[str, Any]) -> list[str]:
    levels = (
        (semantics.get("definitions") or {})
        .get("perceptual_confidence", {})
        .get("levels", {})
    )
    notes = []
    for level in ("high", "medium", "low"):
        if levels.get(level):
            notes.append(f"{level}: {levels[level]}")
    return notes


def _overreach_boundaries(semantics: dict[str, Any]) -> list[str]:
    overreach = semantics.get("overreach_examples") or []
    generic = semantics.get("generic_llm_interpretation_to_avoid") or []
    return [str(item) for item in [*overreach[:3], *generic[:3]] if item]


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    lines = [f"{title}:"]
    lines.extend(f"- {item}" for item in items)
    lines.append("")
    return lines
