from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.derivation import collect_evidences
from src.reports.vertical_signals import vertical_preferred_terms, vertical_terms_for_text

from .extractor_data import (
    DECLARATIVE_TLDR_BLOCKS,
    GENERIC_MAGNETISM_TERMS,
    LAYER_DEFINITIONS,
    LAYER_KEYS,
    PERFORMED_TLDR_BLOCKS,
    SPECIFICITY_TERMS,
    STRATEGIC_TLDR_BLOCKS,
    TLDR_BLOCK_CONTRACT,
    TLDR_KEYS,
    TLDR_TO_LAYER,
)


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


def evidence_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def default_tldr_mode(key: str, layer: dict[str, Any]) -> str:
    finding = str(layer.get("finding") or "")
    if not layer.get("detected"):
        return "not_detected"
    if finding and not finding.startswith("Detected "):
        return "interpreted_from_discourse"
    if key in {"magnetism", "value_proposition", "mission"}:
        return "compressed"
    return "interpreted_from_discourse"


def default_tldr_rationale(key: str, mode: str) -> str:
    if mode == "compressed":
        return f"The {key} block is compressed from direct evidence."
    if mode == "literal":
        return f"The {key} block is directly stated in the evidence."
    if mode == "interpreted_from_discourse":
        return f"The {key} block is articulated from observed discourse signals."
    return "Insufficient evidence to articulate this block responsibly."


def apply_block_specific_content_rules(
    key: str,
    content: Any,
    evidence: list[str],
    mode: str,
    rationale: str,
) -> tuple[Any, str, str]:
    if key in {"magnetism", "value_proposition"}:
        return evidence[0], "compressed", f"The {key} block is compressed from direct evidence."
    if key == "core_purpose":
        return (
            evidence[0],
            "interpreted_from_discourse",
            "The core_purpose block is a Brand3 hypothesis constrained to the available purpose signal.",
        )
    return content, mode, rationale


def derive_personality_block(layers: dict[str, Any]) -> dict[str, Any] | None:
    text = joined_layer_evidence(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"])
    if not text:
        return None
    low = text.lower()
    sage = any(term in low for term in ("funcional", "materias primas", "biorremediación", "bioremediation", "technical", "infrastructure", "api"))
    caregiver = any(term in low for term in ("regenerativo", "medio ambiente", "salud", "nutrition", "nutrición", "sostenible", "sostenibles"))
    creator = any(term in low for term in ("creamos", "create", "formulaciones", "ingredients", "ingredientes", "materias primas"))
    hero = any(term in low for term in ("just do it", "atletas", "athletes", "maratón", "marathon", "performance", "inspirar", "inspire"))
    if not any((sage, caregiver, creator, hero)):
        return None
    traits = []
    if hero:
        traits.append("Hero")
    if sage:
        traits.append("Applied Sage")
    if caregiver:
        traits.append("Caregiver")
    if creator:
        traits.append("scientific Creator")
    content = compose_personality_content(traits)
    evidence = first_layer_evidences(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"], limit=3)
    return {
        "content": content,
        "detected": True,
        "mode": "interpreted_from_discourse",
        "confidence": "medium" if len(evidence) >= 2 else "low",
        "evidence": evidence,
        "rationale": "The personality is inferred from repeated discourse patterns, not from a declared personality statement.",
        "source_layers": ["gamespace", "netspace", "ambientspace"],
        "human_review_recommended": False,
    }


def derive_brand_idea_block(layers: dict[str, Any]) -> dict[str, Any] | None:
    text = joined_layer_evidence(layers, ["mindspace", "aetherspace", "netspace", "ambientspace"])
    low = text.lower()
    if any(term in low for term in ("just do it", "atletas", "athletes")) and any(
        term in low for term in ("innovadores", "performance", "maratón", "marathon", "productos")
    ):
        evidence = first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=3)
        return {
            "content": "Action-led athletic performance for every athlete.",
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "medium" if len(evidence) >= 2 else "low",
            "evidence": evidence,
            "rationale": "The brand idea is articulated from the action mantra, athlete purpose, and performance-product context.",
            "source_layers": ["envispace", "mindspace", "aetherspace", "netspace"],
            "human_review_recommended": False,
        }
    if not ("macroalgas" in low and ("regenerativo" in low or "medio ambiente" in low)):
        return None
    evidence = first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=2)
    return {
        "content": "Mediterranean biotech translated into a regenerative industrial identity.",
        "detected": True,
        "mode": "interpreted_from_discourse",
        "confidence": "low",
        "evidence": evidence,
        "rationale": "The idea connects Mediterranean origin, biotech material, industry, and environmental regeneration; visual evidence is still needed.",
        "source_layers": ["envispace", "mindspace", "aetherspace"],
        "human_review_recommended": False,
    }


def derive_mission_block(layers: dict[str, Any]) -> dict[str, Any] | None:
    text = joined_layer_evidence(layers, ["tactispace", "netspace", "aetherspace", "ambientspace", "mindspace"])
    sentences = sentences_from_text(text)
    evidence = first_matching_sentence(sentences, ["creamos", "we create", "we build", "we provide"])
    if not evidence:
        return None
    return {
        "content": evidence,
        "detected": True,
        "mode": "compressed",
        "confidence": "medium",
        "evidence": [evidence],
        "rationale": "The evidence states a present-tense operating activity.",
        "source_layers": ["tactispace", "netspace"],
        "human_review_recommended": False,
    }


def derive_vision_block(layers: dict[str, Any]) -> dict[str, Any] | None:
    text = joined_layer_evidence(layers, ["mindspace", "aetherspace", "ambientspace"])
    sentences = sentences_from_text(text)
    evidence = first_matching_sentence(sentences, ["nuevo modelo", "future", "vision", "futuro"])
    if not evidence:
        return None
    return {
        "content": "A regenerative industrial model built around the potential of Mediterranean macroalgae."
        if "macroalgas" in evidence.lower()
        else evidence,
        "detected": True,
        "mode": "interpreted_from_discourse",
        "confidence": "medium",
        "evidence": [evidence],
        "rationale": "The evidence points to a future category model rather than only a current offer.",
        "source_layers": ["tactispace", "mindspace"],
        "human_review_recommended": False,
    }


def compose_personality_content(traits: list[str]) -> str:
    if not traits:
        return ""
    if len(traits) == 1:
        return traits[0]
    if len(traits) == 2:
        return f"{traits[0]} with {traits[1]} traits."
    return f"{traits[0]} with {traits[1]} and {traits[2]} traits."


def joined_layer_evidence(layers: dict[str, Any], layer_keys: list[str]) -> str:
    values: list[str] = []
    for key in layer_keys:
        layer = layers.get(key) or {}
        if layer.get("evidence"):
            values.append(str(layer["evidence"]))
        if layer.get("finding"):
            values.append(str(layer["finding"]))
    return "\n".join(values)


def first_layer_evidences(layers: dict[str, Any], layer_keys: list[str], limit: int) -> list[str]:
    evidence: list[str] = []
    for key in layer_keys:
        layer_evidence = layers.get(key, {}).get("evidence")
        if layer_evidence and layer_evidence not in evidence:
            evidence.append(str(layer_evidence))
        if len(evidence) >= limit:
            break
    return evidence


def enrich_layers_from_legacy_text(raw: dict[str, Any], layers: dict[str, Any]) -> None:
    if raw.get("metrics") or raw.get("tldr_brand3"):
        return

    text_parts: list[str] = []
    for layer in (raw.get("magenta_circle") or {}).values():
        evidence = layer.get("evidence") if isinstance(layer, dict) else None
        if isinstance(evidence, list):
            text_parts.extend(str(item) for item in evidence if item)
        elif evidence:
            text_parts.append(str(evidence))
    for value in (raw.get("tldr_grid") or {}).values():
        if value:
            text_parts.append(str(value))

    text = "\n".join(text_parts)
    if not text.strip():
        return

    sentences = sentences_from_text(text)
    keyword_signals = {
        "mindspace": ["únete", "unete", "nuevo modelo", "new model", "new paradigm", "mantra", "proprietary", "framework", "paradigm"],
        "aetherspace": ["regenerativo", "circular", "medio ambiente", "sostenible", "purpose", "mission", "manifesto"],
        "netspace": ["soluciones", "ingredientes activos", "materias primas", "servicios ambientales", "cosmética", "nutracéutica", "biorremediación", "api", "infrastructure", "financial services", "servicios financieros", "product development", "planning and building", "teams and agents"],
        "ambientspace": ["regenerativo", "circular", "sostenible", "sostenibles", "medio ambiente", "mediterráneo", "transparent", "secure"],
    }
    for layer, keywords in keyword_signals.items():
        if layers[layer]["detected"]:
            continue
        evidence = first_matching_sentence(sentences, keywords)
        if not evidence:
            continue
        finding = heuristic_finding(layer, evidence)
        layers[layer].update(
            {
                "finding": finding,
                "evidence": evidence,
                "detected": True,
                "confidence": "low",
                "status": "detected",
                "findings": finding,
                "evidence_list": [evidence],
            }
        )


def infer_brand_name(url_str: str) -> str:
    if not url_str:
        return "Manual Upload Brand"
    parsed = urlparse(url_str if "://" in url_str else f"https://{url_str}")
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0].capitalize()


def sentences_from_text(text: str) -> list[str]:
    raw_segments = [s.strip() for s in re.split(r"[.!?\n]+", text or "") if len(s.strip()) > 5]
    segments: list[str] = []
    for segment in raw_segments:
        if len(segment) <= 320:
            segments.append(segment)
            continue
        cuts = re.split(
            r"(?=\b(?:Macroalgas|Soluciones|Únete|Unete|Ingredientes|Creamos|Servicios|Nuestras)\b)",
            segment,
        )
        segments.extend(cut.strip() for cut in cuts if len(cut.strip()) > 10)
    return segments


def first_matching_sentence(sentences: list[str], keywords: list[str]) -> str | None:
    for keyword in keywords:
        for sentence in sentences:
            if is_navigation_noise(sentence):
                continue
            low = sentence.lower()
            if contains_keyword(low, keyword):
                return trim_evidence(sentence, keyword)
    return None


def heuristic_finding(layer: str, evidence: str) -> str:
    description = LAYER_DEFINITIONS[layer]["description"]
    return f"Detected {description}: {evidence[:180]}"


def tldr_content_from_layer(layer: dict[str, Any]) -> str | None:
    finding = clean_optional_string(layer.get("finding"))
    evidence = clean_optional_string(layer.get("evidence"))
    if finding and not finding.startswith("Detected "):
        return finding
    return evidence or finding


def contains_keyword(text: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    if " " in keyword:
        return re.search(escaped, text, flags=re.IGNORECASE) is not None
    return re.search(rf"(?<![A-Za-zÀ-ÿ0-9]){escaped}(?![A-Za-zÀ-ÿ0-9])", text, flags=re.IGNORECASE) is not None


def trim_evidence(sentence: str, keyword: str, max_chars: int = 260) -> str:
    sentence = " ".join(sentence.split())
    if len(sentence) <= max_chars:
        return clean_evidence_phrase(sentence)
    match = re.search(re.escape(keyword), sentence, flags=re.IGNORECASE)
    if not match:
        return clean_evidence_phrase(sentence[:max_chars].rstrip())
    start = max(0, match.start() - 80)
    end = min(len(sentence), start + max_chars)
    trimmed = sentence[start:end].strip()
    if start > 0:
        trimmed = f"...{trimmed}"
    if end < len(sentence):
        trimmed = f"{trimmed}..."
    return clean_evidence_phrase(trimmed)


def clean_evidence_phrase(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" -•*\t")
    for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
        idx = cleaned.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip()
    return cleaned


def is_navigation_noise(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith("main menu"):
        return True
    nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
    return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2


def normalize_evidence(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            cleaned = clean_optional_string(item)
            if cleaned:
                return cleaned
        return None
    return clean_optional_string(value)


def clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"none", "null", "no clear signal detected in the provided sources."}:
        return None
    return cleaned


def extract_three_terms(text: str, key: str) -> list[str] | None:
    preferred = {
        "attributes": [
            "regenerativo",
            "circular",
            "sostenible",
            "medio ambiente",
            "mediterráneo",
            "funcional",
            "transparente",
            "trust",
            "security",
            "seguro",
            "real-time control",
            "centralised",
            "centralized",
            "performance",
            "innovative",
            "athletic",
            "action-oriented",
            "developer-first",
            "secure",
            "pragmatic",
            "ai-native",
            "practical",
            "editorial",
            "experimental",
            *vertical_preferred_terms("attributes"),
        ],
        "values": [
            "regenerativo",
            "circular",
            "sostenibilidad",
            "medio ambiente",
            "transparencia",
            "claridad",
            "confianza",
            "trust",
            "security",
            "inspiration",
            "inspiración",
            "inclusivity",
            "innovation",
            "innovación",
            "fairness",
            "transparency",
            "customer empathy",
            "developer empathy",
            *vertical_preferred_terms("values"),
        ],
    }
    found: list[str] = []
    low = text.lower()
    if key == "attributes":
        if any(term in low for term in ("maratón", "maraton", "athlete", "athletes", "atletas")):
            found.extend(["performance", "athletic"])
        if any(term in low for term in ("devs", "developers", "builders", "ship", "deploy", "run any code")):
            found.append("developer-first")
        if any(term in low for term in ("security", "secure", "sandboxes", "isolated", "isolation", "private networking", "encryption", "untrusted code")):
            found.append("secure")
        if any(term in low for term in ("pay only", "actual usage", "based on usage", "down to the second", "waive", "refund", "unintended charges")):
            found.append("pragmatic")
        if any(term in low for term in ("custom agents", "ai agents", "artificial intelligence", "edge of ai")):
            found.extend(["ai-native", "practical"])
        if any(term in low for term in ("newsletter", "write for you", "media company", "question")):
            found.append("editorial")
        if any(term in low for term in ("incubate", "foundry", "experiment", "what comes next")):
            found.append("experimental")
        if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
            found.append("innovative")
        found.extend(vertical_terms_for_text(text, "attributes"))
    if key == "values":
        if any(term in low for term in ("inspirar", "inspire", "inspiration")):
            found.append("inspiration")
        if any(term in low for term in ("todo tipo de atletas", "all types of athletes")):
            found.append("inclusivity")
        if any(term in low for term in ("waive", "refund", "unintended charges", "unexpected", "weird on your bill")):
            found.append("fairness")
        if any(term in low for term in ("based on usage", "pay only", "actual cpu", "actual usage", "billing", "down to the second")):
            found.append("transparency")
        if any(term in low for term in ("tell us", "we would love to work with you", "we have engineers", "support customers", "devs", "developers")):
            found.append("developer empathy")
        if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
            found.append("innovation")
        found.extend(vertical_terms_for_text(text, "values"))
    found = list(dict.fromkeys(found))
    if len(found) >= 3:
        return found[:3]
    for term in preferred.get(key, []):
        if term in low and term not in found:
            found.append(term)
        if len(found) == 3:
            return found

    if key in {"attributes", "values"}:
        return found[:3] if found else None

    candidates = re.split(r"[,;/]| and | y ", text)
    terms: list[str] = []
    for candidate in candidates:
        cleaned = re.sub(r"[^A-Za-zÀ-ÿ0-9 -]", "", candidate).strip().lower()
        words = [w for w in cleaned.split() if len(w) > 2]
        if not words:
            continue
        term = words[-1]
        if term not in terms:
            terms.append(term)
        if len(terms) == 3:
            break
    if len(terms) < 3 and key == "attributes":
        terms.extend([term for term in ["specific", "observable", "grounded"] if term not in terms])
    if len(terms) < 3 and key == "values":
        terms.extend([term for term in ["clarity", "proof", "consistency"] if term not in terms])
    return terms[:3] if terms else None


def magnetism_phrase_breakdown(text: str) -> dict[str, int]:
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


def semantic_alignment_score(layers: dict[str, Any]) -> int:
    pairs = [
        ("mindspace", "gamespace"),
        ("aetherspace", "tactispace"),
        ("netspace", "ambientspace"),
    ]
    scores = []
    for left, right in pairs:
        left_detected = layers[left]["detected"]
        right_detected = layers[right]["detected"]
        if left_detected and right_detected:
            scores.append(85)
        elif left_detected or right_detected:
            scores.append(45)
        else:
            scores.append(55)

    envispace_bonus = 10 if layers["envispace"]["detected"] else -10
    return clamp(round(sum(scores) / len(scores)) + envispace_bonus)


def absence_of_contradiction_score(tldr: dict[str, Any]) -> int:
    values_text = " ".join(str(block.get("content") or "") for block in tldr.values() if block.get("content")).lower()
    contradiction_pairs = [
        ("playful", "institutional"),
        ("rebel", "compliance"),
        ("simple", "configurable"),
        ("premium", "cheap"),
    ]
    penalties = sum(1 for a, b in contradiction_pairs if a in values_text and b in values_text)
    return clamp(92 - penalties * 18)


def weighted_score(scores: dict[str, int], weights: dict[str, float]) -> int:
    return round(sum(scores[key] * weight for key, weight in weights.items()))


def int_between(value: Any, minimum: int, maximum: int) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(minimum, min(maximum, number))


def quadrant(magnetism_score: int, coherence_score: int) -> str:
    high_magnetism = magnetism_score >= 70
    high_coherence = coherence_score >= 70
    if high_magnetism and high_coherence:
        return "Señal fuerte · validar antes de escalar"
    if high_magnetism and not high_coherence:
        return "Eslogan sin estructura · peligrosa"
    if not high_magnetism and high_coherence:
        return "Bien pensada sin alma comercial"
    return "Marca sin escribir · target FLOC*"


def magnetism_tier(score: int) -> str:
    if score >= 85:
        return "Magnetic"
    if score >= 70:
        return "Memorable"
    return "Forgettable"


def coherence_tier(score: int) -> str:
    if score >= 80:
        return "Aligned"
    if score >= 50:
        return "Functional"
    return "Fragmented"


def legacy_value(block: dict[str, Any]) -> str:
    value = block.get("content")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "(no detectado)")


def clamp(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def normalized_tldr_confidence(value: Any, detected: bool) -> str:
    confidence = str(value or "").strip().lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    return "low" if not detected else "medium"


def infer_claim_type(key: str, mode: str, detected: bool) -> str:
    if not detected:
        return "absent"
    if mode in {"literal", "compressed"} and key in DECLARATIVE_TLDR_BLOCKS:
        return "declared"
    if key in PERFORMED_TLDR_BLOCKS:
        return "performed"
    return "inferred"


def observations_for_block(key: str, evidence_used: list[str], content: Any) -> list[str]:
    observations: list[str] = []
    if evidence_used:
        observations.append(f"Uses {len(evidence_used)} traceable evidence item(s) selected for {key}.")
    if content:
        observations.append("Produces a bounded Brand3 articulation from the selected evidence.")
    if not observations:
        observations.append("No sufficient public evidence was selected for this block.")
    return observations


def default_counter_evidence(key: str, claim_type: str, detected: bool, layers: dict[str, Any]) -> list[str]:
    if not detected:
        return ["No sufficient public evidence was found for this TLDR block."]
    if claim_type == "inferred":
        return ["The brand does not explicitly declare this exact Brand3 articulation in the available evidence."]
    if key in STRATEGIC_TLDR_BLOCKS and not layers.get(TLDR_TO_LAYER[key], {}).get("detected"):
        return ["The primary Magenta Circle layer for this block is weak or absent."]
    return []


def should_recommend_human_review(
    key: str,
    claim_type: str,
    mode: str,
    confidence: str,
    detected: bool,
    evidence_used: list[str],
) -> bool:
    if not detected:
        return False
    if mode == "needs_human_review":
        return True
    if key in STRATEGIC_TLDR_BLOCKS and claim_type == "inferred":
        return confidence == "low" or len(evidence_used) < 2
    return False


def has_tldr_v03_contract(block: dict[str, Any]) -> bool:
    required = {
        "block",
        "question",
        "evidence_scope",
        "source_signal",
        "source_signal_path",
        "source_layer",
        "observations",
        "answer",
        "claim_type",
        "reasoning",
        "evidence_used",
        "counter_evidence",
        "human_review_recommended",
    }
    return required.issubset(block.keys())
