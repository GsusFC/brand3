"""Tile signals and limitations for Visual Signature evidence packets."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import dict_or_empty as _dict
from src.visual_signature._internal.utils import unique as _unique
from src.visual_signature.evidence_utils import distinctiveness_proxy, score01, string_list

VISUAL_TILE_IDS = (
    "coherencia.C6",
    "brand_idea.I1",
    "brand_idea.I2",
    "brand_idea.I3",
    "brand_idea.I6",
    "brand_idea.I7",
    "brand_idea.I8",
    "brand_idea.I9",
    "core_purpose.PR8",
    "magnetism.MG1",
    "magnetism.MG5",
    "magnetism.MG7",
)


def tile_signals(
    payload: dict[str, Any],
    *,
    capture: dict[str, Any],
    identity: dict[str, Any],
    visual_system: dict[str, Any],
    first_impression: dict[str, Any],
    copy_visual_alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    if capture.get("status") != "usable":
        return [
            tile_signal(
                tile=tile,
                effect="insufficient_evidence",
                confidence="high",
                source="heuristic",
                evidence_refs=["visual_signature:capture"],
                rationale=f"capture_unreliable:{capture.get('status')}",
            )
            for tile in VISUAL_TILE_IDS
        ]

    consistency = score01(_dict(visual_system.get("consistency")).get("overall_consistency"))
    logo_confidence = score01(identity.get("confidence"))
    has_logo = bool(identity.get("logo_detected"))
    density = str(_dict(visual_system.get("layout")).get("visual_density") or "unknown")
    layout_patterns = string_list(_dict(visual_system.get("layout")).get("layout_patterns"))
    polish_score = score01(first_impression.get("visual_polish"))
    copy_summary = str(copy_visual_alignment.get("summary") or "")
    return [
        threshold_signal("coherencia.C6", consistency, source="heuristic", evidence_refs=["visual_signature:consistency"]),
        threshold_signal("brand_idea.I1", logo_confidence if has_logo else 0.0, source="heuristic", evidence_refs=["visual_signature:identity"]),
        threshold_signal("brand_idea.I2", consistency, source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        threshold_signal("brand_idea.I3", polish_score, source="llm_multimodal", evidence_refs=["visual_signature:first_impression"]),
        threshold_signal("brand_idea.I6", 0.72 if layout_patterns else 0.35, source="heuristic", evidence_refs=["visual_signature:layout"]),
        threshold_signal("brand_idea.I7", 0.7 if density in {"balanced", "sparse"} else 0.4, source="heuristic", evidence_refs=["visual_signature:layout"]),
        threshold_signal("brand_idea.I8", consistency, source="heuristic", evidence_refs=["visual_signature:palette", "visual_signature:typography"]),
        threshold_signal("brand_idea.I9", distinctiveness_proxy(payload), source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        threshold_signal(
            "core_purpose.PR8",
            0.72 if copy_summary else 0.35,
            source="llm_multimodal" if copy_summary else "heuristic",
            evidence_refs=copy_visual_alignment.get("evidence_refs") or ["visual_signature:layout"],
        ),
        threshold_signal("magnetism.MG1", polish_score, source="llm_multimodal", evidence_refs=first_impression.get("evidence_refs") or ["visual_signature:first_impression"]),
        threshold_signal("magnetism.MG5", distinctiveness_proxy(payload), source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        threshold_signal(
            "magnetism.MG7",
            polish_score if copy_summary else consistency,
            source="llm_multimodal" if copy_summary else "heuristic",
            evidence_refs=["visual_signature:semantics"] if copy_summary else ["visual_signature:consistency"],
        ),
    ]


def threshold_signal(tile: str, score: float, *, source: str, evidence_refs: list[str]) -> dict[str, Any]:
    bounded = max(0.0, min(1.0, float(score or 0.0)))
    if bounded >= 0.62:
        effect = "supports"
    elif bounded <= 0.42:
        effect = "weakens"
    else:
        effect = "insufficient_evidence"
    confidence = "high" if bounded >= 0.75 or bounded <= 0.25 else "medium" if bounded >= 0.55 or bounded <= 0.45 else "low"
    return tile_signal(
        tile=tile,
        effect=effect,
        confidence=confidence,
        source=source,
        evidence_refs=evidence_refs,
        rationale=f"visual_signal_score:{round(bounded, 3)}",
    )


def tile_signal(
    *,
    tile: str,
    effect: str,
    confidence: str,
    source: str,
    evidence_refs: list[str],
    rationale: str,
) -> dict[str, Any]:
    return {
        "tile": tile,
        "effect": effect,
        "confidence": confidence,
        "source": source,
        "evidence_refs": _unique([str(item) for item in evidence_refs if item]),
        "rationale": rationale,
    }


def limitations(payload: dict[str, Any], capture: dict[str, Any]) -> list[str]:
    values: list[str] = []
    extraction = _dict(payload.get("extraction_confidence"))
    values.extend(str(item) for item in extraction.get("limitations") or [])
    acquisition = _dict(payload.get("acquisition"))
    values.extend(f"acquisition_error:{item}" for item in acquisition.get("errors") or [])
    values.extend(f"acquisition_warning:{item}" for item in acquisition.get("warnings") or [])
    if capture.get("status") != "usable":
        values.append(f"capture_unreliable:{capture.get('status')}")
    if not capture.get("available"):
        values.append("screenshot_not_available")
    obstruction = _dict(capture.get("obstruction"))
    if obstruction.get("present"):
        values.append(f"visual_obstruction:{obstruction.get('type')}")
    if capture.get("first_fold_evaluable") is False:
        values.append("first_fold_not_evaluable")
    return _unique(values)
