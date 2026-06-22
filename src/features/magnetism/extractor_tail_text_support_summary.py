"""Evidence packet and reading-level helpers for Magnetism tail-text support."""

from __future__ import annotations

from typing import Any

from src.reports.derivation import collect_evidences

from .extractor_data import LAYER_KEYS, TLDR_KEYS
from .extractor_tail_text_support_utils import clean_evidence_phrase


def derive_evidence_packet_summary(payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source") or "")
    url = str(payload.get("url") or "")
    if source == "brand_audit_snapshot":
        source_key = "brand_audit_snapshot"
        source_label = "Brand Audit evidence packet"
        evidence_basis = "Shared Brand Audit snapshot reused by Magnetism lenses."
    elif url == "manual" or not url:
        source_key = "manual_evidence"
        source_label = "Manual evidence packet"
        evidence_basis = "Manual evidence provided for this scan."
    else:
        source_key = "direct_web_scan"
        source_label = "Direct web evidence packet"
        evidence_basis = "Direct web scan evidence collected for this Magnetism run."

    layers = payload.get("magenta_circle") or {}
    detected_signal_count = sum(1 for layer in layers.values() if isinstance(layer, dict) and layer.get("detected"))
    layer_evidence_count = sum(
        1
        for layer in layers.values()
        if isinstance(layer, dict) and (layer.get("evidence") or layer.get("evidence_list"))
    )
    distillation = payload.get("content_distillation_summary")
    selected_count = 0
    quality_score = None
    if isinstance(distillation, dict):
        selected_count = int(distillation.get("selected_count") or 0)
        quality_score = distillation.get("quality_score")
    return {
        "source": source_key,
        "source_label": source_label,
        "evidence_basis": evidence_basis,
        "detected_signal_count": detected_signal_count,
        "total_signal_count": len(LAYER_KEYS),
        "layer_evidence_count": layer_evidence_count,
        "distilled_evidence_count": selected_count,
        "distillation_quality_score": quality_score,
        "value_policy": "Only TLDR-relevant evidence is surfaced in this view; raw extraction remains upstream.",
        "proof_support": {
            "status": "not_detected",
            "count": 0,
            "evidence": [],
            "reading": "No public proof signals were available in this evidence packet.",
        },
    }


def brand_audit_evidence_packet_summary(
    snapshot: dict[str, Any],
    strategic_packet: Any | None = None,
) -> dict[str, Any]:
    evidences = collect_evidences(snapshot)
    raw_inputs = snapshot.get("raw_inputs") or []
    sources = sorted({str(item.get("source")) for item in raw_inputs if item.get("source")})
    run = snapshot.get("run") or {}
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    summary = {
        "source": "brand_audit_snapshot",
        "source_label": "Brand Audit evidence packet",
        "evidence_basis": "Shared Brand Audit snapshot reused by Magnetism lenses.",
        "run_id": run.get("id"),
        "raw_input_count": len(raw_inputs),
        "evidence_item_count": len(snapshot.get("evidence_items") or []),
        "derived_evidence_count": len(evidences),
        "feature_count": len(snapshot.get("features") or []),
        "sources": sources,
        "data_quality": data_quality,
        "value_policy": "Brand Audit owns collection; Magnetism only interprets the shared evidence packet.",
    }
    if strategic_packet is not None:
        strategic_summary = strategic_packet.to_summary()
        proof_lines = strategic_packet.groups.get("proof_points", [])
        summary["strategic_group_counts"] = strategic_summary.get("group_counts")
        summary["strategic_source_counts"] = strategic_summary.get("source_counts")
        summary["strategic_rejected_count"] = strategic_summary.get("rejected_count")
        summary["strategic_warnings"] = strategic_summary.get("warnings")
        summary["value_policy"] = strategic_summary.get("value_policy") or summary["value_policy"]
        summary["proof_support"] = {
            "status": "observed" if proof_lines else "not_detected",
            "count": len(proof_lines),
            "evidence": [line.to_dict() for line in proof_lines[:3]],
            "reading": (
                "Observed public proof signals can support credibility, but they do not define mission, "
                "personality, values, or brand idea."
                if proof_lines
                else "No public proof signals were available in the strategic evidence packet."
            ),
        }
    return summary


def derive_system_reading(
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
    url: str = "",
    brand_name: str = "Unknown Brand",
) -> dict[str, Any]:
    """Build system reading summary from TLDR/layers/metrics."""

    _ = (url, brand_name)

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
        questions.append("What does the company explicitly do today, and what future change is it building toward?")

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

    if not tensions and len(weak_layers) >= 4:
        tensions.append(
            "The scan has limited observable signal coverage, so strategic conclusions should stay provisional."
        )
        questions.append("Which missing signals should be supplied by internal materials before using this as strategy?")

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


def add_legacy_fields(payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    diagnosis = payload["diagnosis"]
    tldr = payload["tldr_brand3"]

    payload["magnetism_score"] = metrics["magnetism_score"]
    payload["coherence_score"] = metrics["coherence_score"]
    payload["quadrant"] = metrics["quadrant"]
    payload["executive_headline"] = diagnosis["headline"]
    payload["observations"] = diagnosis["key_observations"][:3]
    payload["tldr_grid"] = {
        "niche": legacy_value(tldr["core_purpose"]),
        "value_proposition": legacy_value(tldr["value_proposition"]),
        "target_audience": "(no detectado)",
        "friction": "(no detectado)",
        "uniqueness": legacy_value(tldr["brand_idea"]),
        "primary_cta": legacy_value(tldr["mission"]),
        "core_promise": legacy_value(tldr["magnetism"]),
        "behavioral_hook": legacy_value(tldr["vision"]),
        "tone": legacy_value(tldr["personality"]),
    }
    payload["score_breakdown"] = {
        "magnetism": {
            "emotional_appeal": metrics["magnetism_breakdown"]["memorability"],
            "functional_differentiation": metrics["magnetism_breakdown"]["specificity"],
            "narrative_gravitas": metrics["magnetism_breakdown"]["originality"],
            "expressive_magnetism": metrics.get("magnetism_scoring_context", {}).get("expressive_magnetism_score"),
            "earned_magnetism": metrics.get("magnetism_scoring_context", {}).get("earned_magnetism_score"),
            "evidence_duty_status": metrics.get("magnetism_scoring_context", {}).get("evidence_duty_status"),
            "assessment": "Derived from detected internal layers and the literal magnetism phrase.",
        },
        "coherence": {
            "visual_identity": metrics["coherence_breakdown"]["semantic_alignment"],
            "tactical_alignment": metrics["coherence_breakdown"]["completeness"],
            "message_consistency": metrics["coherence_breakdown"]["absence_of_contradiction"],
            "assessment": "Derived from TLDR completeness, critical layer pairs, and contradiction checks.",
        },
    }


def legacy_value(block: dict[str, Any]) -> str:
    value = block.get("content")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "(no detectado)")


def brand_audit_evidence_text(snapshot: dict[str, Any]) -> str:
    evidences = collect_evidences(snapshot)
    preferred = [ev for ev in evidences if str(ev.source_type) in {"owned", "social"}]
    evidence_source = preferred or evidences

    lines: list[str] = []
    seen: set[str] = set()
    for ev in evidence_source:
        quote = clean_evidence_phrase(str(ev.quote or ""))
        if not quote or is_unusable_audit_quote(quote):
            continue
        key = quote.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {quote}")
        if len(lines) >= 80:
            break

    if lines:
        return "\n".join(lines)

    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") != "web":
            continue
        payload = raw_input.get("payload") or {}
        markdown = payload.get("markdown_content") or payload.get("content") or ""
        if markdown:
            return str(markdown)[:8000]
    return ""


def is_unusable_audit_quote(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith(("http://", "https://")):
        return True
    if len(value) < 6:
        return True
    if any(marker in low for marker in ("; evidence=", "source_type=", "dimension=", "feature=")):
        return True
    if any(marker in low for marker in ("/news/", "graphql api", "product roadmap", "__next_data__")):
        return True
    return False


def visual_semantics_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") != "visual_signature":
            continue
        payload = raw_input.get("payload") or {}
        semantics = payload.get("semantics")
        if semantics:
            return {"status": "detected", "data": semantics}
        if payload.get("signature", {}).get("semantics"):
            return {"status": "detected", "data": payload["signature"]["semantics"]}
    return {"status": "not_detected", "data": {}}


def snapshot_limitations(snapshot: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    run = snapshot.get("run") or {}
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    if data_quality:
        limitations.append(f"Brand Audit data quality: {data_quality}")
    if not snapshot.get("evidence_items") and not snapshot.get("features"):
        limitations.append("Brand Audit snapshot has no persisted feature evidence.")
    return limitations
