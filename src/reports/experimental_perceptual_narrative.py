"""Experimental perceptual narrative hints for §4 findings.

This module reads static perceptual library artifacts and turns them into
prompt hints. It is intentionally opt-in and does not affect scoring,
report structure, Visual Signature, or runtime behavior unless callers
explicitly pass the hints into the narrative layer.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .perceptual_corpus import load_perceptual_artifacts


ROOT = Path(__file__).resolve().parents[2]
PERCEPTUAL_ROOT = ROOT / "examples" / "perceptual_library"
PATTERN_REGISTRY_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_pattern_registry.json"
READING_SEMANTICS_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_reading_semantics.json"
CASE_RECORD_GLOB = "cases/*/perceptual_case_record.json"
SURFACE_SIGNAL_LIMIT = 5
MAX_SURFACE_SIGNALS_PER_DOMAIN = 2
MAX_SURFACE_SIGNALS_PER_PATTERN = 2
DOMAIN_PRIORITY = {
    "SaaS": 0,
    "culture": 1,
    "fintech": 2,
    "other": 3,
    "web3": 4,
    "crypto": 5,
}

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
    surface_signal_details: list[dict[str, Any]] = field(default_factory=list)
    signal_clusters: list[str] = field(default_factory=list)
    matched_patterns: list[dict[str, str]] = field(default_factory=list)
    productive_tensions: list[str] = field(default_factory=list)
    confidence_notes: list[str] = field(default_factory=list)
    overreach_boundaries: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return not any(
            (
                self.surface_signals,
                self.surface_signal_details,
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
    stable_case_records = _stable_case_records(artifacts.get("case_records", []))

    surface_signal_details = _collect_surface_signal_entries(stable_case_records, limit=SURFACE_SIGNAL_LIMIT)

    return PerceptualNarrativeHints(
        surface_signals=[entry["observation"] for entry in surface_signal_details],
        surface_signal_details=surface_signal_details,
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
    if hints.surface_signal_details:
        lines.append("Surface signal evidence:")
        for entry in hints.surface_signal_details:
            evidence_refs = ", ".join(entry.get("evidence_refs", []))
            pattern_name = str(entry.get("selected_pattern_name") or entry.get("selected_pattern_id") or "")
            lines.append(
                "- "
                + entry["observation"]
                + f" [{entry['original_domain']} · {pattern_name} · {evidence_refs}]"
            )
        lines.append("")
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
    try:
        artifacts = load_perceptual_artifacts()
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not artifacts:
        return _fallback_artifacts()
    return artifacts


def _fallback_artifacts() -> dict[str, Any]:
    return {
        "registry": {
            "patterns": [
                {
                    "pattern_id": "pattern_category_surface_translation",
                    "pattern_name": "Category-To-Surface Translation",
                    "perceptual_meaning": "Category language becomes credible only when surface mechanisms make it observable.",
                    "confidence_level": "medium",
                    "typical_tensions": [
                        "category claim vs observed product surface",
                        "copy-supported clarity vs product-surface proof",
                    ],
                },
                {
                    "pattern_id": "pattern_evidence_bound_behavior",
                    "pattern_name": "Evidence-Bound Behavior",
                    "perceptual_meaning": "The reading stays useful by naming what the evidence can and cannot support.",
                    "confidence_level": "medium",
                    "typical_tensions": [
                        "available owned evidence vs missing external corroboration",
                    ],
                },
                {
                    "pattern_id": "pattern_claim_signal_gap",
                    "pattern_name": "Claim / Signal Gap",
                    "perceptual_meaning": "A strong claim should be treated as conditional when the visible proof is thin.",
                    "confidence_level": "low",
                    "typical_tensions": [
                        "declared ambition vs observable proof",
                    ],
                },
                {
                    "pattern_id": "pattern_guided_movement",
                    "pattern_name": "Guided Movement",
                    "perceptual_meaning": "Navigation, sequence, or interaction evidence can show how attention is directed.",
                    "confidence_level": "medium",
                    "typical_tensions": [
                        "guided action vs exposed complexity",
                    ],
                },
                {
                    "pattern_id": "pattern_system_cohesion_difference",
                    "pattern_name": "System Cohesion Difference",
                    "perceptual_meaning": "Repeated language and surface behavior can support a bounded cohesion reading.",
                    "confidence_level": "medium",
                    "typical_tensions": [
                        "owned-channel consistency vs broader market corroboration",
                    ],
                },
                {
                    "pattern_id": "pattern_concept_bearing_motion",
                    "pattern_name": "Concept-Bearing Motion",
                    "perceptual_meaning": "Motion should only be interpreted when sequence or interaction evidence is present.",
                    "confidence_level": "low",
                    "typical_tensions": [
                        "motion language vs captured motion evidence",
                    ],
                },
                {
                    "pattern_id": "pattern_threshold_pacing",
                    "pattern_name": "Threshold Pacing",
                    "perceptual_meaning": "Page rhythm can clarify how the brand moves users from attention to action.",
                    "confidence_level": "medium",
                    "typical_tensions": [
                        "attention capture vs action clarity",
                    ],
                },
            ]
        },
        "semantics": {
            "definitions": {
                "signal_clusters": {
                    "examples": [
                        {"cluster": ["copy", "navigation", "proof modules"]},
                        {"cluster": ["visual hierarchy", "density", "product objects"]},
                        {"cluster": ["interaction", "sequence", "CTA behavior"]},
                    ]
                },
                "perceptual_confidence": {
                    "levels": {
                        "high": "repeated visible mechanisms converge across surfaces",
                        "medium": "surface signals and copy align but remain partially corroborated",
                        "low": "the reading depends on sparse, owned, or copy-only evidence",
                    }
                },
            },
            "overreach_examples": [
                "Do not infer internal intent from aesthetics alone.",
                "Do not claim user emotion without naming surface mechanisms.",
                "Do not treat category ambition as proven market position.",
            ],
            "generic_llm_interpretation_to_avoid": [
                "premium and sophisticated visual identity",
                "seamless and intuitive experience",
                "market-leading platform",
            ],
        },
        "case_records": [
            {
                "domain_context": {
                    "original_domain": "other",
                    "technology_context": [],
                    "traditional_equivalent_category": "brand strategy reading",
                    "business_model_analogy": "method note",
                    "transferable_brand_patterns": [
                        "Category-To-Surface Translation",
                        "Evidence-Bound Behavior",
                        "Claim / Signal Gap",
                    ],
                    "domain_specific_noise": [],
                    "normalization_status": "normalized",
                },
                "visual_observations": [
                    {"observation": "Repeated product language can support a surface reading only when tied to visible mechanisms."},
                    {"observation": "Sparse owned evidence should lower confidence rather than produce a broad brand conclusion."},
                ]
            }
        ],
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _collect_surface_signal_entries(case_records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates_by_domain: dict[str, list[dict[str, Any]]] = {}
    domain_order: list[str] = []

    for record_index, record in enumerate(case_records):
        if not isinstance(record, dict):
            continue
        domain_context = record.get("domain_context")
        if not isinstance(domain_context, dict):
            continue
        domain = str(domain_context.get("original_domain") or "other")
        if domain not in candidates_by_domain:
            candidates_by_domain[domain] = []
            domain_order.append(domain)
        pattern_lookup = {
            str(pattern.get("pattern_id") or ""): str(pattern.get("pattern_name") or "")
            for pattern in record.get("pattern_refs", [])
            if isinstance(pattern, dict)
        }
        pattern_ids = [pid for pid in pattern_lookup if pid]
        for observation_index, observation in enumerate(record.get("visual_observations", [])):
            if not isinstance(observation, dict):
                continue
            text = str(observation.get("observation") or "").strip()
            if not text:
                continue
            evidence_refs = [
                str(ref).strip()
                for ref in observation.get("evidence_refs", [])
                if isinstance(ref, str) and ref.strip()
            ]
            candidates_by_domain[domain].append(
                {
                    "key": (record.get("case_id") or f"record-{record_index}", observation_index, text),
                    "case_id": str(record.get("case_id") or ""),
                    "original_domain": domain,
                    "observation": text,
                    "evidence_refs": evidence_refs,
                    "pattern_ids": pattern_ids,
                    "pattern_lookup": pattern_lookup,
                    "record_index": record_index,
                    "observation_index": observation_index,
                }
            )

    if not candidates_by_domain:
        return []

    ordered_domains = sorted(
        candidates_by_domain,
        key=lambda domain: (
            DOMAIN_PRIORITY.get(domain, len(DOMAIN_PRIORITY)),
            domain_order.index(domain),
            domain,
        ),
    )
    for domain in ordered_domains:
        candidates_by_domain[domain].sort(
            key=lambda entry: (
                -entry["record_index"],
                entry["observation_index"],
                entry["case_id"],
                entry["observation"],
            )
        )

    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, int, str]] = set()
    domain_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()

    while len(selected) < limit:
        made_progress = False
        for domain in ordered_domains:
            if len(selected) >= limit:
                break
            if domain_counts[domain] >= MAX_SURFACE_SIGNALS_PER_DOMAIN:
                continue
            for candidate in candidates_by_domain[domain]:
                if candidate["key"] in selected_keys:
                    continue
                selected_pattern_id = _select_surface_signal_pattern(candidate["pattern_ids"], pattern_counts)
                if selected_pattern_id is None:
                    continue
                selected_pattern_name = candidate["pattern_lookup"].get(selected_pattern_id, selected_pattern_id)
                selected_candidate = dict(candidate)
                selected_candidate["selected_pattern_id"] = selected_pattern_id
                selected_candidate["selected_pattern_name"] = selected_pattern_name
                selected.append(selected_candidate)
                selected_keys.add(candidate["key"])
                domain_counts[domain] += 1
                pattern_counts[selected_pattern_id] += 1
                made_progress = True
                break
        if not made_progress:
            break

    return selected


def _select_surface_signal_pattern(pattern_ids: list[str], pattern_counts: Counter[str]) -> str | None:
    for pattern_id in pattern_ids:
        if not pattern_id:
            continue
        if pattern_counts[pattern_id] < MAX_SURFACE_SIGNALS_PER_PATTERN:
            return pattern_id
    return None


def _stable_case_records(case_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stable: list[dict[str, Any]] = []
    for record in case_records:
        if not isinstance(record, dict):
            continue
        domain_context = record.get("domain_context")
        if not isinstance(domain_context, dict):
            continue
        if domain_context.get("normalization_status") != "normalized":
            continue
        stable.append(record)
    return stable


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
