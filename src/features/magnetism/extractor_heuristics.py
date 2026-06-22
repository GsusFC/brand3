"""Heuristic extraction helpers for Magnetism fallback path."""

from __future__ import annotations

from typing import Any, Callable

from src.reports.vertical_signals import vertical_layer_keywords


def extract_via_heuristic(
    web_markdown: str,
    visual_semantics: dict[str, Any],
    brand_name: str,
    url: str,
    *,
    collector_error: str,
    content_distillation_summary: dict[str, Any] | None,
    strategic_evidence_packet: dict[str, Any] | None,
    sentences_fn: Callable[[str], list[str]],
    first_matching_sentence_fn: Callable[[list[str], list[str]], str | None],
    heuristic_finding_fn: Callable[[str, str], str],
    is_testimonial_evidence_fn: Callable[[str], bool],
    normalize_analysis_fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Fallback extraction that marks only directly matched signals as detected."""
    sentences = sentences_fn(web_markdown)

    keyword_signals = {
        "mindspace": [
            "just do it",
            "mantra",
            "belief",
            "earn",
            "fight",
            "inspire",
            "proprietary",
            "framework",
            "paradigm",
            "new model",
            "new paradigm",
            "únete",
            "unete",
            "nuevo modelo",
        ],
        "aetherspace": [
            "mission",
            "purpose",
            "why",
            "founded",
            "exists",
            "values",
            "manifesto",
            "inspirar",
            "inspire",
            "regenerativo",
            "circular",
            "medio ambiente",
            "sostenible",
        ],
        "gamespace": ["voice", "tone", "playful", "bold", "rebel", "sage", "creator", "trusted"],
        "envispace": ["design", "visual", "aesthetic", "palette", "typography", "minimal", "brutalist"],
        "netspace": [
            "value",
            "api",
            "developer",
            "automation",
            "platform",
            "infrastructure",
            "financial services",
            "servicios financieros",
            "accept payments",
            "aceptar pagos",
            "billing",
            "facturación",
            "product development",
            "planning and building",
            "teams and agents",
            "integration",
            "sdk",
            "innovadores",
            "productos innovadores",
            "soluciones",
            "ingredientes activos",
            "materias primas",
            "servicios ambientales",
            *vertical_layer_keywords("netspace"),
        ],
        "tactispace": [
            "creamos",
            "we create",
            "we build",
            "we provide",
            "mission",
            "vision",
            "roadmap",
            "future",
            "new model",
            "new paradigm",
            "misión",
            "vision",
            "visión",
            "futuro",
            "nuevo modelo",
        ],
        "ambientspace": [
            "values",
            "trusted",
            "secure",
            "simple",
            "transparent",
            "offline",
            "event",
            "support",
            "performance",
            "custom agents",
            "ai agents",
            "prioritization",
            "okr planning",
            "growth tracking",
            "maratón",
            "maraton",
            "atletas",
            "athletes",
            "regenerativo",
            "circular",
            "sostenible",
            "sostenibles",
            "medio ambiente",
            *vertical_layer_keywords("ambientspace"),
        ],
    }

    layers: dict[str, Any] = {}
    for layer, keywords in keyword_signals.items():
        evidence = first_matching_sentence_fn(sentences, keywords)
        finding = None
        detected = evidence is not None
        confidence = "medium" if detected else "insufficient"

        if layer == "tactispace" and evidence and is_testimonial_evidence_fn(evidence):
            evidence = None
            detected = False
            confidence = "insufficient"

        if detected:
            finding = heuristic_finding_fn(layer, evidence or "")

        if layer == "envispace" and isinstance(visual_semantics, dict):
            sem = visual_semantics.get("data") or {}
            style = sem.get("aesthetic_style")
            mood = sem.get("visual_mood")
            if style and not detected:
                evidence = f"Visual style: {style}"
                finding = f"Visual signature detected as {style}."
                detected = True
                confidence = "low"
            elif style and mood and detected:
                finding = f"{finding} Visual analysis also reports {style} with a {mood} mood."

        layers[layer] = {
            "finding": finding,
            "evidence": evidence,
            "detected": detected,
            "confidence": confidence,
        }

    payload = {
        "brand_name": brand_name,
        "url": url,
        "magenta_circle": layers,
        "fallback_used": True,
    }
    if content_distillation_summary:
        payload["content_distillation_summary"] = content_distillation_summary
    if strategic_evidence_packet:
        payload["strategic_evidence_packet"] = strategic_evidence_packet

    normalized = normalize_analysis_fn(payload)
    if collector_error:
        normalized["limitations"].append(f"Web collection fallback: {collector_error}")
    return normalized
