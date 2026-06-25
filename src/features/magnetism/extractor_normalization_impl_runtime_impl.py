from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_context_brief import build_brand_context_brief
from src.reports.vertical_signals import vertical_preferred_terms, vertical_terms_for_text


def normalize_analysis(
    raw: dict[str, Any],
    *,
    normalize_layers_fn,
    enrich_layers_from_legacy_text_fn,
    enrich_layers_from_strategic_packet_fn,
    derive_tldr_fn,
    derive_metrics_fn,
    derive_diagnosis_fn,
    derive_evidence_packet_summary_fn,
    derive_system_reading_fn,
    add_legacy_fields_fn,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "brand_name": str(raw.get("brand_name") or "Unknown Brand"),
        "url": str(raw.get("url") or ""),
        "analyzed_at": str(raw.get("analyzed_at") or datetime.now(timezone.utc).isoformat()),
        "fallback_used": bool(raw.get("fallback_used", False)),
        "limitations": [],
    }

    normalized["magenta_circle"] = normalize_layers_fn(raw.get("magenta_circle") or raw.get("layers") or {})
    enrich_layers_from_legacy_text_fn(raw, normalized["magenta_circle"])
    strategic_packet = raw.get("strategic_evidence_packet") if isinstance(raw.get("strategic_evidence_packet"), dict) else None
    if strategic_packet:
        enrich_layers_from_strategic_packet_fn(normalized["magenta_circle"], strategic_packet)
    brand_context_brief = raw.get("brand_context_brief") if isinstance(raw.get("brand_context_brief"), dict) else None
    if not brand_context_brief:
        brand_context_brief = build_brand_context_brief(
            brand_name=normalized["brand_name"],
            url=normalized["url"],
            layers=normalized["magenta_circle"],
            strategic_packet=strategic_packet,
        ).to_dict()
    normalized["brand_context_brief"] = brand_context_brief
    normalized["tldr_brand3"] = derive_tldr_fn(normalized["magenta_circle"], strategic_packet, brand_context_brief)
    if strategic_packet:
        normalized["strategic_evidence_packet"] = strategic_packet
    for key in (
        "research_pack",
        "analyst_tldr_raw",
        "analyst_tldr_validated",
        "analyst_tldr_analysis_error",
        "tldr_generation_mode",
        "legacy_tldr_brand3",
        "tldr_strategy",
    ):
        if key in raw:
            normalized[key] = raw[key]
    normalized["metrics"] = derive_metrics_fn(
        normalized["magenta_circle"],
        normalized["tldr_brand3"],
        scoring_context=(
            normalized.get("analyst_tldr_validated", {}).get("scoring_context")
            if isinstance(normalized.get("analyst_tldr_validated"), dict)
            else None
        ),
    )
    normalized["diagnosis"] = derive_diagnosis_fn(normalized["magenta_circle"], normalized["metrics"])
    if isinstance(raw.get("content_distillation_summary"), dict):
        normalized["content_distillation_summary"] = raw["content_distillation_summary"]
    normalized["evidence_packet_summary"] = derive_evidence_packet_summary_fn(normalized)
    if "system_reading" in raw and isinstance(raw["system_reading"], dict):
        normalized["system_reading"] = raw["system_reading"]
    elif normalized.get("fallback_used"):
        normalized["system_reading"] = derive_system_reading_fn(
            tldr=normalized["tldr_brand3"],
            layers=normalized["magenta_circle"],
            metrics=normalized["metrics"],
            evidence_packet_summary=normalized.get("evidence_packet_summary"),
        )
    else:
        normalized["system_reading"] = derive_system_reading_fn(
            tldr=normalized["tldr_brand3"],
            layers=normalized["magenta_circle"],
            metrics=normalized["metrics"],
            evidence_packet_summary=normalized.get("evidence_packet_summary"),
        )

    add_legacy_fields_fn(normalized)
    return normalized


def normalize_layers(raw_layers: dict[str, Any]) -> dict[str, Any]:
    layers: dict[str, Any] = {}
    for layer in [
        "mindspace",
        "aetherspace",
        "gamespace",
        "envispace",
        "netspace",
        "tactispace",
        "ambientspace",
    ]:
        raw_layer = raw_layers.get(layer) or {}

        old_evidence = raw_layer.get("evidence")
        evidence = normalize_evidence(old_evidence)
        finding = raw_layer.get("finding")
        if finding is None:
            finding = raw_layer.get("findings")
        finding = clean_optional_string(finding)

        detected_raw = raw_layer.get("detected")
        status_raw = str(raw_layer.get("status") or "").strip().lower()
        detected = bool(detected_raw) if isinstance(detected_raw, bool) else status_raw == "detected"
        if not detected and (finding or evidence):
            detected = status_raw != "not_detected"

        if not detected:
            finding = None
            evidence = None

        if layer == "tactispace" and finding and "cta" in finding.lower():
            finding = None
            evidence = None
            detected = False

        confidence = str(raw_layer.get("confidence") or "").strip().lower()
        if confidence not in {"high", "medium", "low", "insufficient"}:
            confidence = "medium" if detected else "insufficient"

        layers[layer] = {
            "finding": finding,
            "evidence": evidence,
            "detected": detected,
            "confidence": confidence,
            "status": "detected" if detected else "not_detected",
            "findings": finding or "No clear signal detected in the provided sources.",
            "evidence_list": [evidence] if evidence else [],
        }
    return layers


def enrich_layers_from_strategic_packet(
    layers: dict[str, Any],
    strategic_packet: dict[str, Any],
    replace_detected_ambientspace: bool = False,
) -> None:
    groups = strategic_packet.get("groups") if isinstance(strategic_packet, dict) else {}
    if not isinstance(groups, dict):
        return

    layer_group_map = {
        "mindspace": ["hero_claims"],
        "netspace": ["product_offer", "outcome", "audience"],
        "gamespace": ["personality_tone"],
        "ambientspace": ["values_language"],
    }
    for layer_key, group_names in layer_group_map.items():
        item = first_packet_item(groups, group_names)
        if not item:
            continue
        if layers.get(layer_key, {}).get("detected") and not (
            replace_detected_ambientspace and layer_key == "ambientspace"
        ):
            continue
        evidence = item["text"]
        confidence = packet_layer_confidence(layer_key, groups, item.get("group"))
        set_layer_from_packet(layers, layer_key, evidence, confidence)

    if not layers.get("tactispace", {}).get("detected"):
        tactispace_evidence = first_accepted_tactispace_packet_evidence(strategic_packet)
        if tactispace_evidence:
            set_layer_from_packet(layers, "tactispace", tactispace_evidence, "medium")


def first_packet_item(groups: dict[str, Any], group_names: list[str]) -> dict[str, str] | None:
    candidates: list[dict[str, str]] = []
    for group in group_names:
        for item in groups.get(group) or []:
            if not isinstance(item, dict):
                continue
            text = clean_evidence_phrase(str(item.get("text") or ""))
            if not text or is_navigation_noise(text):
                continue
            candidates.append({
                "text": text,
                "group": group,
                "source_type": str(item.get("source_type") or ""),
                "feature_name": str(item.get("feature_name") or ""),
            })
    if not candidates:
        return None
    from src.features.magnetism.block_interpreters import strategic_packet_candidate_priority
    return sorted(candidates, key=strategic_packet_candidate_priority)[0]


def first_accepted_tactispace_packet_evidence(strategic_packet: dict[str, Any]) -> str | None:
    from src.features.magnetism.block_interpreters import (
        TLDR_BLOCK_INTERPRETER_SPECS,
        accepted_block_evidence,
        strategic_packet_candidates,
    )
    tldr_to_layer = {"mission": "tactispace", "vision": "tactispace"}
    for key in ("mission", "vision"):
        spec = TLDR_BLOCK_INTERPRETER_SPECS[key]
        candidates = strategic_packet_candidates(key, spec, strategic_packet, str(tldr_to_layer.get(key, "netspace")))
        accepted = accepted_block_evidence(key, spec, candidates)
        if accepted:
            return accepted[0]["text"]
    return None


def packet_layer_confidence(layer_key: str, groups: dict[str, Any], primary_group: str | None) -> str:
    if layer_key == "netspace":
        has_offer = bool(groups.get("product_offer"))
        has_outcome = bool(groups.get("outcome"))
        if has_offer and has_outcome:
            return "high"
        if has_offer or primary_group in {"outcome", "audience"}:
            return "medium"
        return "low"
    return "medium"


def set_layer_from_packet(
    layers: dict[str, Any],
    layer_key: str,
    evidence: str,
    confidence: str,
) -> None:
    finding = heuristic_finding(layer_key, evidence)
    layers[layer_key] = {
        "finding": finding,
        "evidence": evidence,
        "detected": True,
        "confidence": confidence,
        "status": "detected",
        "findings": finding,
        "evidence_list": [evidence],
    }


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
    descriptions = {
        "mindspace": "central emotion, mantra, war cry, or magnetic phrase",
        "aetherspace": "purpose beyond the product",
        "gamespace": "brand personality and archetype",
        "envispace": "visual and conceptual brand idea",
        "netspace": "concrete value proposition and exchange of value",
        "tactispace": "mission and vision signals",
        "ambientspace": "values and attributes demonstrated in context",
    }
    return f"Detected {descriptions[layer]}: {evidence[:180]}"


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
