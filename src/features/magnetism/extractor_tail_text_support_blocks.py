"""Block-level heuristics and TLDR shape helpers."""

from __future__ import annotations

from typing import Any

from .extractor_tail_text_support_utils import first_matching_sentence, heuristic_finding, sentences_from_text


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
        "mindspace": ["únete", "unete", "nuevo modelo", "new model", "new paradigm", "mantra", "framework", "paradigm"],
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
