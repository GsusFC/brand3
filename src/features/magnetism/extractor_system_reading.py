"""System reading derivation for Magnetism payloads."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.extractor_constants import TLDR_KEYS


def derive_system_reading(
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
    url: str = "",
    brand_name: str = "Unknown Brand",
) -> dict[str, Any]:
    """Derive concise reverse-engineering outputs inside TLDR instead of a parallel report."""
    del url, brand_name

    def detected(block_name: str) -> bool:
        block = tldr.get(block_name) or {}
        return bool(block.get("detected") or block.get("answer") or block.get("content"))

    tensions: list[str] = []
    questions: list[str] = []

    value_detected = detected("value_proposition")
    magnetism_score = int(metrics.get("magnetism_score") or 0)
    weak_layers = [key for key, layer in layers.items() if isinstance(layer, dict) and not layer.get("detected")]
    detected_block_count = sum(1 for key in TLDR_KEYS if detected(key))
    limited_evidence_coverage = len(weak_layers) >= 2 or detected_block_count <= 7

    if value_detected and not detected("personality"):
        tensions.append(
            "The offer is functionally visible, but the brand voice/personality is not yet observable from the evidence."
        )
        questions.append(
            "Should the buyer remember operational utility, trust, ambition, or a sharper point of view?"
        )

    if value_detected and not detected("brand_idea"):
        tensions.append(
            "The product logic is clearer than the larger brand idea connecting category, expression, and point of view."
        )
        questions.append(
            "What category belief or metaphor should make the offer easier to recognize and repeat?"
        )

    if value_detected and not detected("mission") and not detected("vision"):
        tensions.append("The current offer is clearer than the brand's operating mission or future direction.")
        questions.append(
            "What does the company explicitly do today, and what future change is it building toward?"
        )

    if value_detected and magnetism_score and magnetism_score < 70:
        tensions.append(
            "The offer has usable evidence, but the magnetic hook may not yet create strong first-screen memory."
        )
        questions.append("Which phrase or tension should a buyer retain after the first visit?")

    if limited_evidence_coverage:
        tensions.insert(
            0,
            "Some score pressure comes from limited public evidence coverage, not necessarily from strategic weakness in the brand itself.",
        )
        questions.insert(
            0,
            "Which missing internal or public evidence should be supplied before treating the score as a strategic verdict?",
        )

    if not tensions:
        if len(weak_layers) >= 4:
            tensions.append(
                "The scan has limited observable signal coverage, so strategic conclusions should stay provisional."
            )
            questions.append(
                "Which missing signals should be supplied by internal materials before using this as strategy?"
            )

    proof_support = (
        evidence_packet_summary.get("proof_support")
        if isinstance(evidence_packet_summary, dict)
        and isinstance(evidence_packet_summary.get("proof_support"), dict)
        else None
    )
    if proof_support and proof_support.get("status") == "observed":
        credibility_support = {
            "status": "observed",
            "count": int(proof_support.get("count") or 0),
            "evidence": proof_support.get("evidence") or [],
            "reading": proof_support.get("reading")
            or "Observed public proof signals support credibility without defining the brand strategy.",
        }
    else:
        credibility_support = {
            "status": "not_detected",
            "count": 0,
            "evidence": [],
            "reading": "No public proof signals were available for a separate credibility reading.",
        }

    return {
        "strategic_tensions": tensions[:3],
        "validation_questions": questions[:3],
        "credibility_support": credibility_support,
        "derived_from": "TLDR Brand3 blocks and Magenta signal coverage",
    }
