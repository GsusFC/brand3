from __future__ import annotations

from typing import Any

from .extractor_data import (
    GENERIC_MAGNETISM_TERMS,
    SPECIFICITY_TERMS,
    TLDR_KEYS,
)
from .extractor_tail import clamp, coherence_tier, magnetism_tier, quadrant


def derive_metrics(
    layers: dict[str, Any],
    tldr: dict[str, Any],
    *,
    scoring_context: dict[str, Any] | None = None,
    int_between_fn,
    earned_magnetism_adjustment_fn,
    semantic_alignment_score_fn,
    absence_of_contradiction_score_fn,
    weighted_score_fn,
) -> dict[str, Any]:
    magnetism_text = tldr["magnetism"].get("content") or ""
    magnetism_breakdown = magnetism_phrase_breakdown(str(magnetism_text))
    phrase_score = weighted_score_fn(
        magnetism_breakdown,
        {
            "originality": 0.30,
            "specificity": 0.25,
            "memorability": 0.25,
            "verifiable_promise": 0.20,
        },
    )
    internal_layers = ["mindspace", "aetherspace", "envispace"]
    internal_detected = {
        "mindspace": layers["mindspace"]["detected"],
        "aetherspace": layers["aetherspace"]["detected"],
        "envispace": layers["envispace"]["detected"] or bool(tldr["brand_idea"].get("detected")),
    }
    internal_score = round(
        sum(100 if internal_detected[layer] else 0 for layer in internal_layers)
        / len(internal_layers)
    )
    expressive_magnetism_score = round((phrase_score * 0.55) + (internal_score * 0.45))
    earned_magnetism = earned_magnetism_adjustment_fn(
        expressive_magnetism_score,
        scoring_context,
        clamp_fn=clamp,
        int_between_fn=int_between_fn,
    )
    magnetism_score = earned_magnetism["score"]

    completeness = round(sum(1 for block in tldr.values() if block.get("detected")) / len(TLDR_KEYS) * 100)
    semantic_alignment = semantic_alignment_score_fn(layers, clamp_fn=clamp)
    absence_of_contradiction = absence_of_contradiction_score_fn(tldr, clamp_fn=clamp)
    coherence_score = round((completeness * 0.40) + (semantic_alignment * 0.40) + (absence_of_contradiction * 0.20))
    evidence_duty_penalty = int(earned_magnetism.get("coherence_penalty") or 0)
    coherence_score = clamp(coherence_score - evidence_duty_penalty)

    return {
        "magnetism_score": clamp(magnetism_score),
        "magnetism_tier": magnetism_tier(magnetism_score),
        "magnetism_breakdown": magnetism_breakdown,
        "magnetism_scoring_context": {
            "expressive_magnetism_score": clamp(expressive_magnetism_score),
            "earned_magnetism_score": clamp(magnetism_score),
            "promise_requires_evidence": earned_magnetism["promise_requires_evidence"],
            "evidence_duty_status": earned_magnetism["evidence_duty_status"],
            "reasoning": earned_magnetism["reasoning"],
            "evidence_gaps": earned_magnetism["evidence_gaps"],
            "source": earned_magnetism["source"],
        },
        "coherence_score": clamp(coherence_score),
        "coherence_tier": coherence_tier(coherence_score),
        "coherence_breakdown": {
            "completeness": clamp(completeness),
            "semantic_alignment": clamp(semantic_alignment),
            "absence_of_contradiction": clamp(absence_of_contradiction),
            "evidence_duty_penalty": evidence_duty_penalty,
        },
        "quadrant": quadrant(magnetism_score, coherence_score),
    }


def derive_diagnosis(layers: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    detected = [layer for layer, value in layers.items() if value["detected"]]
    missing = [layer for layer, value in layers.items() if not value["detected"]]
    detected_count = len(detected)

    headline = (
        f"Marca con {detected_count}/7 capas detectadas: magnetismo {metrics['magnetism_tier'].lower()} "
        f"y coherencia {metrics['coherence_tier'].lower()}."
    )
    observations = [
        f"Capas detectadas: {', '.join(detected) if detected else 'ninguna'}.",
        f"Capas sin evidencia suficiente: {', '.join(missing) if missing else 'ninguna'}.",
        "El diagnostico se limita a senales observables; no incluye recomendaciones estrategicas no validadas.",
    ]
    if detected_count <= 5:
        observations.append(
            "Si el score baja, puede deberse a cobertura insuficiente de evidencia publica, no necesariamente a debilidad estrategica de la marca."
        )
    return {"headline": headline, "key_observations": observations}


def earned_magnetism_adjustment(
    expressive_score: int,
    scoring_context: dict[str, Any] | None,
    *,
    clamp_fn=clamp,
    int_between_fn,
) -> dict[str, Any]:
    if not isinstance(scoring_context, dict) or not scoring_context:
        return {
            "score": clamp_fn(expressive_score),
            "coherence_penalty": 0,
            "promise_requires_evidence": False,
            "evidence_duty_status": "not_evaluated",
            "reasoning": "",
            "evidence_gaps": [],
            "source": "code_expressive_score",
        }

    status = str(scoring_context.get("evidence_duty_status") or "not_required").strip().lower()
    if status not in {"not_required", "satisfied", "partial", "weak"}:
        status = "not_required"
    requires_evidence = bool(scoring_context.get("promise_requires_evidence")) or status in {"partial", "weak"}
    earned = int_between_fn(scoring_context.get("earned_magnetism_score"), 0, 100)
    if earned is None:
        earned = expressive_score
    penalty = int_between_fn(scoring_context.get("coherence_evidence_duty_penalty"), 0, 25) or 0

    if not requires_evidence or status in {"not_required", "satisfied"}:
        score = expressive_score
        penalty = 0
    else:
        score = min(expressive_score, earned)

    gaps = scoring_context.get("evidence_gaps")
    if not isinstance(gaps, list):
        gaps = []
    return {
        "score": clamp_fn(score),
        "coherence_penalty": penalty,
        "promise_requires_evidence": bool(requires_evidence),
        "evidence_duty_status": status,
        "reasoning": str(scoring_context.get("reasoning") or ""),
        "evidence_gaps": [str(item) for item in gaps if str(item).strip()][:5],
        "source": "analyst_scoring_context",
    }


def magnetism_phrase_breakdown(text: str) -> dict[str, int]:
    import re

    if not text:
        return {
            "originality": 0,
            "specificity": 0,
            "memorability": 0,
            "verifiable_promise": 0,
        }

    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    word_count = len(words)
    generic_hits = sum(1 for word in words if word in GENERIC_MAGNETISM_TERMS)
    specific_hits = sum(1 for word in words if word in SPECIFICITY_TERMS)
    has_number = bool(re.search(r"\d", text))
    has_action = bool(re.search(r"\b(build|do|earn|save|ship|reduce|automate|protect|find|create|launch|inspire)\b", text.lower()))
    is_short_imperative = 2 <= word_count <= 4 and has_action

    originality = 92 if is_short_imperative else 85 - (generic_hits * 14)
    specificity = 35 + min(specific_hits * 18, 55) + (10 if has_number else 0)
    if is_short_imperative:
        specificity = max(specificity, 62)
    memorability = 95 if is_short_imperative else 80 if 2 <= word_count <= 8 else 58 if word_count <= 14 else 35
    verifiable = 45 + (25 if has_action else 0) + (20 if has_number or specific_hits >= 2 else 0)
    if is_short_imperative:
        verifiable = max(verifiable, 75)
    return {
        "originality": clamp(originality),
        "specificity": clamp(specificity),
        "memorability": clamp(memorability),
        "verifiable_promise": clamp(verifiable),
    }
