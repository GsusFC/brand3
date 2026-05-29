from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.reports.brand_research_pack import BrandResearchPack, EntityResolution, ResearchEvidence, ResearchSource


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack"
NOTES_DIR = OUT_DIR / "notes"

TLDR_KEYS = [
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
]

TLDR_QUESTIONS = {
    "core_purpose": "Why does this brand appear to exist beyond the product?",
    "magnetism": "What phrase, tension, or promise is most likely to be remembered?",
    "value_proposition": "What does the brand offer, to whom, and what changes for that audience?",
    "personality": "What personality does the brand perform through tone, vocabulary, behavior, and visual stance?",
    "brand_idea": "What conceptual idea connects category, offer, expression, and metaphor?",
    "attributes": "Which attributes are consistently demonstrated by product, behavior, proof, or language?",
    "values": "Which values does the brand appear to defend through what it says or does?",
    "mission": "What does the brand concretely do today?",
    "vision": "What future or category change is the brand trying to build?",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = f"https://{url}"
    return url.rstrip("/")


def _tldr_block(
    *,
    block: str,
    answer: str | None,
    claim_type: str,
    mode: str,
    confidence: str,
    reasoning: str,
    evidence_used: list[str],
    evidence_sources: list[dict[str, Any]],
    counter_evidence: list[str] | None = None,
    human_review_recommended: bool = False,
) -> dict[str, Any]:
    return {
        "block": block,
        "question": TLDR_QUESTIONS[block],
        "answer": answer,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence_used": evidence_used,
        "evidence_sources": evidence_sources,
        "counter_evidence": counter_evidence or [],
        "human_review_recommended": human_review_recommended,
    }


def _tldr_from_specs(specs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blocks: dict[str, Any] = {}
    for key in TLDR_KEYS:
        block_spec = specs.get(key)
        if block_spec is None:
            blocks[key] = _tldr_block(
                block=key,
                answer=None,
                claim_type="absent",
                mode="not_detected",
                confidence="low",
                reasoning="No stable evidence was available for this block in the current artifact set.",
                evidence_used=[],
                evidence_sources=[],
                counter_evidence=[],
                human_review_recommended=False,
            )
            continue
        blocks[key] = _tldr_block(block=key, **block_spec)
    return {"tldr_brand3": blocks}


def _evidence(text: str, *, source_key: str, source_type: str, label: str = "") -> dict[str, Any]:
    return {"text": text, "source_key": source_key, "source_type": source_type, "label": label}


def _research_pack(
    *,
    input_url: str,
    resolved_entity: dict[str, Any],
    entity_type: str,
    parent_brand: str = "",
    official_urls: list[str] | None = None,
    analyzed_urls: list[str] | None = None,
    source_map: dict[str, dict[str, Any]] | None = None,
    company_summary: str = "",
    product_summary: str = "",
    audience: str = "",
    offer: str = "",
    outcome: str = "",
    category: str = "",
    declared_purpose: str = "",
    declared_mission: str = "",
    future_direction: str = "",
    tone_of_voice: str = "",
    personality_signals: list[str] | None = None,
    visual_or_conceptual_signals: list[str] | None = None,
    values_signals: list[str] | None = None,
    attributes_signals: list[str] | None = None,
    proof_points: list[dict[str, Any]] | None = None,
    founder_or_press_context: list[dict[str, Any]] | None = None,
    noise_rejected: list[dict[str, Any]] | None = None,
    evidence_gaps: list[str] | None = None,
    confidence_notes: list[str] | None = None,
) -> dict[str, Any]:
    pack = BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=input_url,
        resolved_entity=EntityResolution.from_dict(resolved_entity),
        entity_type=entity_type,
        parent_brand=parent_brand,
        official_urls=official_urls or [],
        analyzed_urls=analyzed_urls or [],
        source_map={k: ResearchSource.from_dict(v) for k, v in (source_map or {}).items()},
        company_summary=company_summary,
        product_summary=product_summary,
        audience=audience,
        offer=offer,
        outcome=outcome,
        category=category,
        declared_purpose=declared_purpose,
        declared_mission=declared_mission,
        future_direction=future_direction,
        tone_of_voice=tone_of_voice,
        personality_signals=personality_signals or [],
        visual_or_conceptual_signals=visual_or_conceptual_signals or [],
        values_signals=values_signals or [],
        attributes_signals=attributes_signals or [],
        proof_points=[ResearchEvidence.from_dict(x) for x in (proof_points or [])],
        founder_or_press_context=[ResearchEvidence.from_dict(x) for x in (founder_or_press_context or [])],
        noise_rejected=[ResearchEvidence.from_dict(x) for x in (noise_rejected or [])],
        evidence_gaps=evidence_gaps or [],
        confidence_notes=confidence_notes or [],
    )
    return pack.to_dict()


def _scan_payload(scan_id: int) -> dict[str, Any]:
    conn = sqlite3.connect(BRAND3_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("select raw_payload from magnetism_scans where id = ?", (scan_id,)).fetchone()
        if row is None:
            raise RuntimeError(f"scan {scan_id} not found")
        return json.loads(row["raw_payload"])
    finally:
        conn.close()


def _normalize_scan_tldr(scan_payload: dict[str, Any], key: str = "tldr_brand3_current") -> dict[str, Any]:
    source = scan_payload.get(key)
    if not isinstance(source, dict) and key in {"tldr_brand3_current", "tldr_brand3_strategist"}:
        legacy = scan_payload.get("tldr_brand3")
        if isinstance(legacy, dict):
            source = legacy
    if not isinstance(source, dict):
        if key == "tldr_brand3_strategist" and isinstance(scan_payload.get("tldr_brand3_current"), dict):
            source = scan_payload["tldr_brand3_current"]
        else:
            return {"tldr_brand3": {}}

    if key == "tldr_brand3_strategist" and isinstance(source, dict) and isinstance(source.get("tldr_brand3"), dict):
        source = source["tldr_brand3"]

    blocks: dict[str, Any] = {}
    for block_key in TLDR_KEYS:
        raw = source.get(block_key) if isinstance(source.get(block_key), dict) else {}
        blocks[block_key] = {
            "block": raw.get("block") or block_key,
            "question": raw.get("question") or TLDR_QUESTIONS[block_key],
            "answer": raw.get("answer") or raw.get("content") or None,
            "claim_type": raw.get("claim_type") or ("absent" if not (raw.get("answer") or raw.get("content")) else "inferred"),
            "mode": raw.get("mode") or ("not_detected" if not (raw.get("answer") or raw.get("content")) else "interpreted_from_discourse"),
            "confidence": raw.get("confidence") or ("low" if not (raw.get("answer") or raw.get("content")) else "medium"),
            "reasoning": raw.get("reasoning") or raw.get("rationale") or "",
            "evidence_used": raw.get("evidence_used") or raw.get("evidence") or [],
            "evidence_sources": raw.get("evidence_sources") or [],
            "counter_evidence": raw.get("counter_evidence") or [],
            "human_review_recommended": bool(raw.get("human_review_recommended", False)),
        }
    return {"tldr_brand3": blocks}


def _manual_base44_pack() -> dict[str, Any]:
    pack_path = ROOT / "examples" / "reports" / "brand_research_pack" / "base44.brand_research_pack.v0.json"
    return _load_json(pack_path)


def _manual_bokeroon_pack() -> dict[str, Any]:
    return _research_pack(
        input_url="https://bokeroon.com",
        resolved_entity={
            "resolved_entity": "Bokeroon",
            "entity_type": "company",
            "canonical_url": "https://bokeroon.com",
            "parent_brand": "",
            "surface_role": "audited_surface",
            "entity_scope": "audited_surface",
            "confidence": "medium",
            "notes": ["Benchmarked from existing Brand3 corpus; feed page is noise."],
        },
        entity_type="company",
        official_urls=["https://bokeroon.com"],
        analyzed_urls=["https://bokeroon.com", "https://bokeroon.com/feed"],
        source_map={
            "https://bokeroon.com": {"url": "https://bokeroon.com", "source_type": "owned_official", "label": "Bokeroon"},
            "https://bokeroon.com/feed": {"url": "https://bokeroon.com/feed", "source_type": "noise", "label": "Bokeroon feed"},
        },
        company_summary="Bokeroon is a crypto platform for instant trading and simpler management.",
        product_summary="Bokeroon turns crypto management into an instant, transparent, simpler experience.",
        audience="Users overwhelmed by crypto complexity.",
        offer="A platform that makes crypto management faster, simpler, and more transparent.",
        outcome="Users can manage crypto without opacity or friction.",
        category="crypto platform",
        declared_purpose="Make crypto investing easier to understand and manage.",
        declared_mission="Build a platform that makes crypto management instant and transparent.",
        tone_of_voice="Urgent, encouraging, challenger-like, educational.",
        personality_signals=["urgent", "encouraging", "challenger-like", "educational"],
        visual_or_conceptual_signals=["crypto management without opacity"],
        values_signals=["clarity", "accessibility", "practical control"],
        attributes_signals=["clear", "fast", "transparent", "simple"],
        proof_points=[],
        founder_or_press_context=[],
        noise_rejected=[
            _evidence("feed/article prediction", source_key="https://bokeroon.com/feed", source_type="noise", label="Bokeroon feed"),
            _evidence("page chrome / navigation fragments", source_key="https://bokeroon.com", source_type="noise", label="Bokeroon home"),
        ],
        evidence_gaps=["Brand Idea remains weak and reviewable."],
        confidence_notes=["Entity is clear, but feed/blog noise should not be used as vision."],
    )


def _manual_base44_scanner_current() -> dict[str, Any]:
    return _tldr_from_specs(
        {
            "core_purpose": {
                "answer": "Partner with Base44 to help students create and innovate.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "medium",
                "reasoning": "The current scanner over-weighted the student partnership snippet as purpose.",
                "evidence_used": ["Partner with Base44 to help students create and innovate."],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": ["The partnership snippet is not the strongest owned explanation of why the company exists."],
                "human_review_recommended": True,
            },
            "magnetism": {
                "answer": "Our Mission, Your Vision.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "medium",
                "reasoning": "The page chrome phrase was incorrectly promoted.",
                "evidence_used": ["Our Mission, Your Vision"],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "noise"}],
                "counter_evidence": ["Page chrome should not be treated as the strongest brand phrase."],
                "human_review_recommended": True,
            },
            "value_proposition": {
                "answer": "Our Mission, Your Vision top of page # About Us...",
                "claim_type": "declared",
                "mode": "interpreted_from_discourse",
                "confidence": "low",
                "reasoning": "Navigation/chrome fragments were selected instead of the offer.",
                "evidence_used": ["Our Mission, Your Vision top of page # About Us..."],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "noise"}],
                "counter_evidence": ["The phrase is page chrome, not a value proposition."],
                "human_review_recommended": True,
            },
            "personality": {
                "answer": "Solo founder, $80M exit, 6 months...",
                "claim_type": "declared",
                "mode": "interpreted_from_discourse",
                "confidence": "low",
                "reasoning": "Founder exit proof was over-promoted into personality.",
                "evidence_used": ["Solo founder, $80M exit, 6 months..."],
                "evidence_sources": [{"source_key": "https://techcrunch.com/2026/01/01/base44-founder-exit", "source_type": "press_or_founder"}],
                "counter_evidence": ["Founder story is proof/context, not brand personality."],
                "human_review_recommended": True,
            },
            "mission": {
                "answer": "help anyone create their own apps with zero hassle",
                "claim_type": "declared",
                "mode": "literal",
                "confidence": "high",
                "reasoning": "The mission line is literal on the owned site.",
                "evidence_used": ["our mission to help anyone create their own apps with zero hassle"],
                "evidence_sources": [{"source_key": "https://base44.com/about", "source_type": "owned_about"}],
                "counter_evidence": [],
            },
        }
    )


def _manual_base44_analyst() -> dict[str, Any]:
    return _tldr_from_specs(
        {
            "core_purpose": {
                "answer": "Democratize software creation by letting people turn ideas into working apps without code, team, or technical setup.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The owned homepage and about copy support a stronger purpose reading than the founder story.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Our mission to help anyone create their own apps with zero hassle.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": ["The company does not state this exact sentence literally."],
                "human_review_recommended": True,
            },
            "magnetism": {
                "answer": "Built for builders, powered by possibility.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "No single literal line is stronger; this is the cleanest synthetic reading from the owned offer.",
                "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "value_proposition": {
                "answer": "Base44 lets builders, founders, and teams turn natural language prompts into working apps, including tools, back-office apps, customer portals, and enterprise products.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "This is the clearest owned offer statement on the surface.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Using just natural language, you can create tools, back-office apps, customer portals, or complete enterprise products that are ready to use.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "personality": {
                "answer": "Builder-first, empowering, fast, anti-friction, practical.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The tone is inferred from the product promise and mission, not from founder exit proof.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Our mission to help anyone create their own apps with zero hassle.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": ["Founder exit proof belongs in context, not personality."],
                "human_review_recommended": True,
            },
            "brand_idea": {
                "answer": "Software creation becomes a conversation; intent becomes working software.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The offer and mission strongly imply a conversational software-creation model.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Using just natural language, you can create tools, back-office apps, customer portals, or complete enterprise products that are ready to use.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "attributes": {
                "answer": "Fast, accessible, full-stack, conversational, practical.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "These attributes are repeated across the offer and mission.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Using just natural language, you can create tools, back-office apps, customer portals, or complete enterprise products that are ready to use.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "values": {
                "answer": "Accessibility, autonomy, creative agency, speed, removing gatekeepers.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The mission and product frame imply these values even when not stated literally.",
                "evidence_used": [
                    "Our mission to help anyone create their own apps with zero hassle.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com/about", "source_type": "owned_about"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "mission": {
                "answer": "Help anyone create their own apps with zero hassle.",
                "claim_type": "declared",
                "mode": "literal",
                "confidence": "high",
                "reasoning": "The mission is stated directly on the owned about page.",
                "evidence_used": ["Our mission to help anyone create their own apps with zero hassle."],
                "evidence_sources": [{"source_key": "https://base44.com/about", "source_type": "owned_about"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "vision": {
                "answer": "Move from buying or manually coding software to creating software from intent.",
                "claim_type": "inferred",
                "mode": "needs_human_review",
                "confidence": "low",
                "reasoning": "The vision is not literal; it is inferred from the category shift implied by the product.",
                "evidence_used": [
                    "Base44 is an AI app builder for non-technical founders.",
                    "Using just natural language, you can create tools, back-office apps, customer portals, or complete enterprise products that are ready to use.",
                ],
                "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                "counter_evidence": ["The future change is not declared in owned source text."],
                "human_review_recommended": True,
            },
        }
    )


def _manual_bokeroon_current() -> dict[str, Any]:
    return _tldr_from_specs(
        {
            "core_purpose": {
                "answer": "¿Listo para simplificar tus inversiones en criptomonedas?",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "medium",
                "reasoning": "The scanner treated the rhetorical CTA as purpose.",
                "evidence_used": ["¿Listo para simplificar tus inversiones en criptomonedas?"],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": ["A question is supporting evidence, not the full purpose block."],
                "human_review_recommended": True,
            },
            "magnetism": {
                "answer": "Menos complicaciones, más claridad.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "This is the strongest remembered phrase in the current corpus.",
                "evidence_used": ["Menos complicaciones, más claridad."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "value_proposition": {
                "answer": "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "The owned product line is strong and should be preserved.",
                "evidence_used": ["En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "personality": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "The current scanner had no stable personality reading.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": [],
            },
            "brand_idea": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "The conceptual idea is weak and should be reviewed rather than asserted.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": [],
            },
            "attributes": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "The current scanner under-extracted attributes despite repeated cues.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": [],
            },
            "values": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "Values were not stably supported in the current read.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": [],
            },
            "mission": {
                "answer": "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "The mission-like product line is explicit and strong.",
                "evidence_used": ["En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "vision": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "Feed/article prediction should not be elevated into vision.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": ["Feed/article content remains rejected."],
            },
        }
    )


def _manual_bokeroon_analyst() -> dict[str, Any]:
    return _tldr_from_specs(
        {
            "core_purpose": {
                "answer": "Make crypto investing easier to understand and manage for users who feel overwhelmed by complexity.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The owned promise and transparency language support an inferred purpose.",
                "evidence_used": [
                    "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente.",
                    "Menos complicaciones, más claridad.",
                ],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "magnetism": {
                "answer": "Menos complicaciones, más claridad.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "This phrase is the strongest memorable line in the evidence.",
                "evidence_used": ["Menos complicaciones, más claridad."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "value_proposition": {
                "answer": "Bokeroon is building a platform that turns crypto management into an instant, transparent, and simpler experience.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "The platform promise is literal and owned.",
                "evidence_used": ["En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "personality": {
                "answer": "Urgent, encouraging, challenger-like, educational.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The question + clarity language suggest a guiding tone rather than a purely factual one.",
                "evidence_used": ["¿Listo para simplificar tus inversiones en criptomonedas?", "Menos complicaciones, más claridad."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "brand_idea": {
                "answer": "Crypto management without opacity.",
                "claim_type": "inferred",
                "mode": "needs_human_review",
                "confidence": "low",
                "reasoning": "This is a weak but useful synthesis and should remain reviewable.",
                "evidence_used": ["Menos complicaciones, más claridad.", "experiencia instantánea y transparente"],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "attributes": {
                "answer": "Clear, fast, transparent, simple.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The repeated adjectives are explicit in the offer and slogan.",
                "evidence_used": ["Menos complicaciones, más claridad.", "instantánea y transparente"],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "values": {
                "answer": "Clarity, accessibility, practical control.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The product framing points to practical control and clarity.",
                "evidence_used": ["Menos complicaciones, más claridad.", "instantánea y transparente"],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "mission": {
                "answer": "Build a platform that makes crypto management instant and transparent.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "This is the clearest owned operating statement.",
                "evidence_used": ["En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."],
                "evidence_sources": [{"source_key": "https://bokeroon.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "vision": {
                "answer": None,
                "claim_type": "absent",
                "mode": "not_detected",
                "confidence": "low",
                "reasoning": "Feed/article prediction remains rejected as future direction evidence.",
                "evidence_used": [],
                "evidence_sources": [],
                "counter_evidence": ["Feed/article prediction is not owned vision."],
            },
        }
    )


def _pack_from_scan_and_audit(scan_payload: dict[str, Any], audit_output: dict[str, Any]) -> dict[str, Any]:
    entity = audit_output.get("entity_discovery") or {}
    bc = scan_payload.get("brand_context_brief") or {}
    sep = scan_payload.get("strategic_evidence_packet") or {}
    groups = sep.get("groups") if isinstance(sep.get("groups"), dict) else {}

    def first(group: str) -> str:
        items = groups.get(group) or []
        if not items:
            return ""
        item = items[0]
        return str(item.get("text") or "").strip()

    input_url = _normalize_url(str(audit_output.get("url") or scan_payload.get("url") or ""))
    entity_type = str(entity.get("entity_type") or "unknown")
    parent_brand = str(entity.get("parent_brand_name") or entity.get("parent_brand") or "")
    resolved_entity = {
        "resolved_entity": str(entity.get("entity_name") or entity.get("canonical_brand_name") or audit_output.get("brand") or audit_output.get("brand_profile", {}).get("name") or input_url),
        "entity_type": entity_type,
        "canonical_url": str(entity.get("canonical_url") or input_url),
        "parent_brand": parent_brand,
        "surface_role": "audited_surface" if entity_type in {"company", "unknown"} else "product_surface",
        "entity_scope": str(entity.get("analysis_scope") or ("product_surface" if entity_type in {"product", "sub_brand"} else "audited_surface")),
        "confidence": str(entity.get("confidence") or "medium"),
        "notes": [str(x) for x in entity.get("warnings") or []],
    }

    source_map = {
        input_url: {
            "url": input_url,
            "source_type": "owned_official",
            "label": str(audit_output.get("brand") or audit_output.get("brand_profile", {}).get("name") or input_url),
            "surface_role": "owned_official",
            "entity_scope": "audited_surface",
            "title": str(audit_output.get("brand") or input_url),
            "notes": [],
        }
    }
    if bc.get("operating_mission_signal"):
        source_map[f"{input_url}/about"] = {
            "url": f"{input_url}/about",
            "source_type": "owned_about",
            "label": "about",
            "surface_role": "owned_about",
            "entity_scope": "audited_surface",
            "title": "",
            "notes": [],
        }

    proof_points = []
    for item in groups.get("proof_points") or []:
        text = str(item.get("text") or "").strip()
        if text:
            proof_points.append(_evidence(text, source_key=str(item.get("url") or input_url), source_type=str(item.get("source_type") or "proof_point"), label=str(item.get("feature_name") or "proof")))
    if not proof_points and audit_output.get("evidence_summary", {}).get("by_source", {}).get("exa", 0):
        proof_points.append(_evidence("Evidence available from exa and Brand Audit corpus.", source_key="exa", source_type="context", label="summary"))

    founder_or_press_context = []
    for item in groups.get("third_party_context") or []:
        text = str(item.get("text") or "").strip()
        if text:
            founder_or_press_context.append(_evidence(text, source_key=str(item.get("url") or input_url), source_type=str(item.get("source_type") or "press_or_founder"), label=str(item.get("feature_name") or "context")))

    noise_rejected = []
    for item in sep.get("rejected") or []:
        text = str(item.get("text") or "").strip()
        if text:
            noise_rejected.append(_evidence(text, source_key=input_url, source_type="noise", label=str(item.get("reason") or "noise")))

    return _research_pack(
        input_url=input_url,
        resolved_entity=resolved_entity,
        entity_type=entity_type,
        parent_brand=parent_brand,
        official_urls=[input_url],
        analyzed_urls=[input_url] + [u for u in [
            str(item.get("url") or "").strip()
            for item in (groups.get("product_offer") or [])[:3]
        ] if u],
        source_map=source_map,
        company_summary=str(bc.get("what_it_is") or bc.get("value_proposition_signal") or first("product_offer") or audit_output.get("brand") or input_url),
        product_summary=str(bc.get("value_proposition_signal") or first("product_offer") or ""),
        audience=str(first("audience") or ""),
        offer=str(bc.get("value_proposition_signal") or first("product_offer") or ""),
        outcome=str(first("outcome") or ""),
        category=str(entity.get("entity_type") or audit_output.get("niche_classification", {}).get("niche") or "unknown"),
        declared_purpose=str(bc.get("operating_mission_signal") or first("mission_language") or ""),
        declared_mission=str(bc.get("operating_mission_signal") or first("mission_language") or ""),
        future_direction=str(bc.get("future_direction_signal") or first("vision_language") or ""),
        tone_of_voice=str(first("personality_tone") or ""),
        personality_signals=[str(item.get("text") or "").strip() for item in (groups.get("personality_tone") or []) if str(item.get("text") or "").strip()],
        visual_or_conceptual_signals=[str(x) for x in ([bc.get("future_direction_signal")] if bc.get("future_direction_signal") else [])],
        values_signals=[str(item.get("text") or "").strip() for item in (groups.get("values_language") or []) if str(item.get("text") or "").strip()],
        attributes_signals=[str(item.get("text") or "").strip() for item in (groups.get("product_offer") or [])[:3] if str(item.get("text") or "").strip()],
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        noise_rejected=noise_rejected,
        evidence_gaps=[str(x) for x in (audit_output.get("entity_discovery", {}).get("warnings") or [])],
        confidence_notes=[str(audit_output.get("evidence_summary", {}).get("by_quality", {}))],
    )


def _manual_heygen_pack(audit_output: dict[str, Any]) -> dict[str, Any]:
    ed = audit_output.get("entity_discovery") or {}
    input_url = _normalize_url(str(ed.get("input_url") or audit_output.get("url") or "https://www.heygen.com"))
    resolved_entity = {
        "resolved_entity": str(ed.get("canonical_brand_name") or ed.get("entity_name") or "HeyGen"),
        "entity_type": "company",
        "canonical_url": str(ed.get("canonical_url") or input_url),
        "parent_brand": "",
        "surface_role": "audited_surface",
        "entity_scope": "audited_surface",
        "confidence": "medium",
        "notes": [str(x) for x in (ed.get("warnings") or [])],
    }
    return _research_pack(
        input_url=input_url,
        resolved_entity=resolved_entity,
        entity_type="company",
        official_urls=[input_url, "https://heygen.com"],
        analyzed_urls=[input_url],
        source_map={
            input_url: {"url": input_url, "source_type": "owned_official", "label": "HeyGen", "surface_role": "owned_official", "entity_scope": "audited_surface", "title": "HeyGen", "notes": []},
            "https://developers.heygen.com": {"url": "https://developers.heygen.com", "source_type": "owned_product", "label": "HeyGen docs", "surface_role": "owned_product", "entity_scope": "audited_surface", "title": "Developers", "notes": []},
        },
        company_summary="HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production.",
        product_summary="HeyGen lets teams create talking-avatar videos and localize content at scale.",
        audience="Marketers, creators, and teams that need scalable video production.",
        offer="An AI video platform for creating, localizing, and scaling avatar-led video content.",
        outcome="Users can produce videos faster and localize them for more markets and audiences.",
        category="AI video platform",
        declared_purpose="Make video creation easier and more scalable.",
        declared_mission="Help teams create and localize video at scale.",
        future_direction="Video creation becomes faster, more scalable, and more accessible.",
        tone_of_voice="Polished, product-led, scalable.",
        personality_signals=["polished", "product-led", "scalable"],
        visual_or_conceptual_signals=["video localization at scale"],
        values_signals=["accessibility", "speed", "scale"],
        attributes_signals=["scalable", "localized", "video-first"],
        proof_points=[],
        founder_or_press_context=[],
        noise_rejected=[
            _evidence("navigation / page chrome fragments", source_key=input_url, source_type="noise", label="HeyGen home"),
        ],
        evidence_gaps=["No magnetism scan exists in the current corpus for this URL."],
        confidence_notes=["Research pack synthesized from Brand Audit artifacts without a current scanner payload."],
    )


def _write_case_note(case: dict[str, Any]) -> None:
    note = [
        f"# {case['source_url']}",
        "",
        f"- Brand audit run: `{case['brand_audit_run_id']}`",
        f"- Magnetism scan: `{case['magnetism_scan_id']}`" if case.get("magnetism_scan_id") is not None else "- Magnetism scan: not available in current corpus",
        f"- Source kind: `{case['source_kind']}`",
        "",
        case["manual_notes"],
        "",
        "## Differences",
        json.dumps(case["differences"], ensure_ascii=False, indent=2),
    ]
    (NOTES_DIR / f"{case['slug']}.md").write_text("\n".join(note) + "\n")


def _normalize_manual_case(case: dict[str, Any]) -> dict[str, Any]:
    research_pack = case["research_pack"]
    analyst = case["analyst_tldr"]
    scanner = case.get("scanner_current_tldr")
    if not isinstance(analyst, dict) or "tldr_brand3" not in analyst:
        raise ValueError(f"{case['slug']} analyst_tldr is malformed")
    if scanner is not None and (not isinstance(scanner, dict) or "tldr_brand3" not in scanner):
        raise ValueError(f"{case['slug']} scanner_current_tldr is malformed")
    return {
        "slug": case["slug"],
        "source_url": case["source_url"],
        "brand_audit_run_id": case["brand_audit_run_id"],
        "magnetism_scan_id": case.get("magnetism_scan_id"),
        "research_pack": research_pack,
        "analyst_tldr": analyst,
        "manual_notes": case["manual_notes"],
        "scanner_current_tldr": scanner,
        "differences": case["differences"],
        "source_kind": case["source_kind"],
    }


def build_dataset() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    # Base44 fixture.
    base44_pack = _manual_base44_pack()
    base44_analyst = _load_json(ROOT / "examples" / "reports" / "magnetism_guardrails" / "base44.validated_tldr.v0.json")
    base44_case = {
        "slug": "base44",
        "source_url": "https://base44.com",
        "brand_audit_run_id": 81,
        "magnetism_scan_id": 8,
        "source_kind": "benchmark_fixture",
        "research_pack": base44_pack,
        "analyst_tldr": base44_analyst,
        "scanner_current_tldr": _manual_base44_scanner_current(),
        "manual_notes": "Benchmark regression case. Base44 is the clearest example of structural noise and founder-proof over-promotion in the old scanner.",
        "differences": {
            "error_taxonomy": [
                "structural_noise_selected",
                "proof_point_as_personality",
                "concept_not_inferred",
                "entity_context_not_promoted",
            ],
            "summary": "Manual reading favors the owned offer and mission; the current scanner over-weights chrome and founder proof.",
        },
    }
    cases.append(_normalize_manual_case(base44_case))

    # Bokeroon fixture.
    bokeroon_case = {
        "slug": "bokeroon",
        "source_url": "https://bokeroon.com",
        "brand_audit_run_id": 80,
        "magnetism_scan_id": 7,
        "source_kind": "benchmark_fixture",
        "research_pack": _manual_bokeroon_pack(),
        "analyst_tldr": _manual_bokeroon_analyst(),
        "scanner_current_tldr": _manual_bokeroon_current(),
        "manual_notes": "Benchmark regression case. Feed/article predictions should remain noise; attributes and clarity language matter.",
        "differences": {
            "error_taxonomy": [
                "rhetorical_question_as_purpose",
                "attributes_under_extracted",
                "brand_idea_weak_but_not_absent",
                "feed_or_article_noise",
            ],
            "summary": "Manual reading preserves the offer and extracts clarity/instant/transparency signals. The old scanner treated a rhetorical question as purpose.",
        },
    }
    cases.append(_normalize_manual_case(bokeroon_case))

    # Scan-backed cases.
    scan_backed = [
        {
            "slug": "fly-io",
            "source_url": "https://fly.io",
            "brand_audit_run_id": 142,
            "magnetism_scan_id": 40,
            "audit_output": ROOT / "output" / "fly-io-20260526-224522.json",
            "scan_id": 40,
            "manual_notes": "Benchmark target: the strategist pass is close, but the dataset records the current scan and the strategist reading separately.",
            "differences": {
                "error_taxonomy": [],
                "summary": "Fly is largely solved; the main residual risk is overclaiming the conceptual idea if evidence gets too metaphorical.",
            },
        },
        {
            "slug": "every-to-about",
            "source_url": "https://every.to/about",
            "brand_audit_run_id": 135,
            "magnetism_scan_id": 41,
            "audit_output": ROOT / "output" / "every-to-20260526-103220.json",
            "scan_id": 41,
            "manual_notes": "Multi-surface brand: publication + software + services. The dataset preserves that entity architecture instead of flattening it into a newsletter only.",
            "differences": {
                "error_taxonomy": [],
                "summary": "The manual reading and strategist pass are close; the key evaluation axis is whether the multi-surface entity architecture remains intact.",
            },
        },
        {
            "slug": "lab-naturaumana-ai",
            "source_url": "https://lab.naturaumana.ai",
            "brand_audit_run_id": 148,
            "magnetism_scan_id": 39,
            "audit_output": ROOT / "output" / "lab-naturaumana-ai-20260528-114433.json",
            "scan_id": 39,
            "manual_notes": "Subdomain / product-surface case. Parent entity expansion matters; the product surface alone underreads purpose and vision.",
            "differences": {
                "error_taxonomy": [
                    "audited_surface_too_narrow",
                    "parent_entity_not_expanded",
                    "product_surface_used_as_full_brand",
                ],
                "summary": "The current scanner is directionally good, but the dataset keeps the parent-brand context explicit so subdomain inference remains reviewable.",
            },
        },
        {
            "slug": "creatify-ai-es",
            "source_url": "https://creatify.ai/es/",
            "brand_audit_run_id": 129,
            "magnetism_scan_id": 23,
            "audit_output": ROOT / "output" / "creatify-20260525-213337.json",
            "scan_id": 23,
            "manual_notes": "High-signal performance marketing case. The brand is mostly stable; the main risk is collapsing proof points into the core offer.",
            "differences": {
                "error_taxonomy": [],
                "summary": "Current TLDR is usable. Manual reading keeps proof points, audience and outcome separated from the core offer.",
            },
        },
    ]

    conn = sqlite3.connect(BRAND3_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        for item in scan_backed:
            audit_output = _load_json(item["audit_output"])
            scan_payload = _scan_payload(item["scan_id"])
            research_pack = _pack_from_scan_and_audit(scan_payload, audit_output)
            analyst = _normalize_scan_tldr(scan_payload, "tldr_brand3_strategist" if "tldr_brand3_strategist" in scan_payload else "tldr_brand3_current")
            scanner = _normalize_scan_tldr(scan_payload, "tldr_brand3_current")
            if not analyst.get("tldr_brand3"):
                analyst = scanner
            cases.append(
                _normalize_manual_case(
                    {
                        "slug": item["slug"],
                        "source_url": item["source_url"],
                        "brand_audit_run_id": item["brand_audit_run_id"],
                        "magnetism_scan_id": item["magnetism_scan_id"],
                        "source_kind": "magnetism_scan" if item["magnetism_scan_id"] is not None else "brand_audit_output",
                        "research_pack": research_pack,
                        "analyst_tldr": analyst,
                        "scanner_current_tldr": scanner,
                        "manual_notes": item["manual_notes"],
                        "differences": item["differences"],
                    }
                )
            )
    finally:
        conn.close()

    # HeyGen has Brand Audit output but no magnetism scan in the current corpus.
    heygen_output = _load_json(ROOT / "output" / "www-heygen-com-20260518-222330.json")
    heygen_pack = _manual_heygen_pack(heygen_output)
    heygen_analyst = _tldr_from_specs(
        {
            "core_purpose": {
                "answer": "Make video creation and localization easy enough for teams to scale without a studio bottleneck.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The audit summary and public presence inventory indicate a scalable AI video platform.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "magnetism": {
                "answer": "Video creation, without the studio bottleneck.",
                "claim_type": "inferred",
                "mode": "compressed",
                "confidence": "medium",
                "reasoning": "The strongest remembered tension is scale versus production friction.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "value_proposition": {
                "answer": "HeyGen lets teams create talking-avatar videos and localize content at scale.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "The product offer is a straightforward summary of the platform.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "personality": {
                "answer": "Polished, product-led, scalable.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The public evidence points to a polished product organization more than a quirky one.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "brand_idea": {
                "answer": "Video localization at scale.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The platform, product and discovery evidence point to this conceptual core.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "attributes": {
                "answer": "Scalable, localized, video-first.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "These are the most stable repeated qualities in the audit output.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
            },
            "values": {
                "answer": "Accessibility, speed, scale.",
                "claim_type": "inferred",
                "mode": "interpreted_from_discourse",
                "confidence": "medium",
                "reasoning": "The platform promise implies these values without overclaiming them as explicit declarations.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": True,
            },
            "mission": {
                "answer": "Help teams create and localize video at scale.",
                "claim_type": "declared",
                "mode": "compressed",
                "confidence": "high",
                "reasoning": "The operating mission is a direct synthesis of the owned platform description.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": [],
                "human_review_recommended": False,
            },
            "vision": {
                "answer": "Video creation becomes faster, more scalable, and more accessible.",
                "claim_type": "inferred",
                "mode": "needs_human_review",
                "confidence": "low",
                "reasoning": "The future frame is plausible but not explicitly declared in the current audit snapshot.",
                "evidence_used": ["HeyGen is an AI video creation platform centered on avatars, localization, and scalable video production."],
                "evidence_sources": [{"source_key": "https://www.heygen.com", "source_type": "owned_official"}],
                "counter_evidence": ["No current magnetism scan exists in the corpus, so future direction remains reviewable."],
                "human_review_recommended": True,
            },
        }
    )
    cases.append(
        _normalize_manual_case(
            {
                "slug": "heygen",
                "source_url": "https://www.heygen.com",
                "brand_audit_run_id": 104,
                "magnetism_scan_id": None,
                "source_kind": "brand_audit_output",
                "research_pack": heygen_pack,
                "analyst_tldr": heygen_analyst,
                "scanner_current_tldr": None,
                "manual_notes": "HeyGen exists in Brand Audit output but not in the current magnetism scan table. The dataset keeps it as a research-pack-only case.",
                "differences": {
                    "error_taxonomy": ["missing_scanner_scan"],
                    "summary": "The case is still useful for evaluation, but there is no current magnetism scan to compare against.",
                },
            }
        )
    )

    dataset = {
        "version": "tldr_brand3_research_pack_dataset_v0_1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": cases,
        "missing_cases": [
            {
                "source_url": "https://pinata.cloud",
                "status": "not_found_in_current_corpus",
                "reason": "No matching Brand Audit run, Magnetism scan, or local output artifact was present for pinata.cloud in the current workspace.",
            }
        ],
    }
    return dataset


def write_outputs(dataset: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "dataset.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n")

    index_md = [
        "# TLDR Brand3 Research Pack dataset",
        "",
        "Initial evaluation set built from existing Brand Audit and Magnetism Scanner artifacts.",
        "",
        "| Case | Source URL | Brand Audit Run | Magnetism Scan | Source Kind |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for case in dataset["cases"]:
        index_md.append(
            f"| {case['source_url'].replace('https://', '')} | {case['source_url']} | {case['brand_audit_run_id']} | {case.get('magnetism_scan_id') if case.get('magnetism_scan_id') is not None else 'n/a'} | {case['source_kind']} |"
        )
    index_md.extend([
        "",
        "## Missing corpus entries",
    ])
    for missing in dataset.get("missing_cases", []):
        index_md.append(f"- {missing['source_url']}: {missing['reason']}")
    (OUT_DIR / "README.md").write_text("\n".join(index_md) + "\n")

    for case in dataset["cases"]:
        _write_case_note(case)


def main() -> None:
    dataset = build_dataset()
    write_outputs(dataset)


if __name__ == "__main__":
    main()
