"""Brand Research Pack orchestration logic."""

from __future__ import annotations

from typing import Any

from src.reports.brand_research_pack_types import BrandResearchPack
from src.reports.brand_research_pack_sources import (
    _build_source_map as _build_source_map_impl,
    _collect_analyzed_urls as _collect_analyzed_urls_impl,
    _collect_official_urls as _collect_official_urls_impl,
    _confidence_notes as _confidence_notes_impl,
    _evidence_gaps as _evidence_gaps_impl,
    _payload_for_source as _payload_for_source_impl,
    _payload_url as _payload_url_impl,
    _primary_web_text as _primary_web_text_impl,
    _resolve_entity_resolution as _resolve_entity_resolution_impl,
)
from src.reports.strategic_evidence_packet import build_strategic_evidence_packet
from src.reports.brand_research_pack_building_helpers import (
    _attribute_signals,
    _build_evidence_from_source_map,
    _build_evidence_list,
    _build_noise_list,
    _build_supplemental_context_evidence,
    _concept_signals,
    _filter_values_signals,
    _first_meaningful_text,
    _infer_audience,
    _infer_category,
    _infer_outcome,
    _line_texts,
    _lines_text,
    _looks_like_press_or_founder_text,
    _normalize_url,
    _shadow_sources_from_snapshot,
    _tone_summary,
    _unique_texts,
)


def build_brand_research_pack_from_snapshot(snapshot: dict[str, Any]) -> BrandResearchPack:
    """Adapt a persisted Brand Audit snapshot into a canonical research pack."""

    run = snapshot.get("run") or {}
    raw_inputs = snapshot.get("raw_inputs") or []
    strategic_packet = build_strategic_evidence_packet(snapshot)
    entity_packet = _entity_packet(snapshot)
    web_payload = _payload_for_source_impl(raw_inputs, "web")
    exa_payload = _payload_for_source_impl(raw_inputs, "exa")
    context_payload = _payload_for_source_impl(raw_inputs, "context")
    social_payload = _payload_for_source_impl(raw_inputs, "social")

    input_url = _normalize_url(
        str(
            run.get("url")
            or (entity_packet or {}).get("input_url")
            or _payload_url_impl(web_payload)
            or ""
        )
    )
    brand_name = str(run.get("brand_name") or "").strip()
    resolved = _resolve_entity_resolution_impl(
        input_url=input_url,
        brand_name=brand_name,
        run=run,
        entity_packet=entity_packet,
        web_payload=web_payload,
        exa_payload=exa_payload,
        context_payload=context_payload,
        social_payload=social_payload,
        strategic_packet=strategic_packet,
    )

    source_map = _build_source_map_impl(
        snapshot=snapshot,
        strategic_packet=strategic_packet,
        entity_packet=entity_packet,
    )
    official_urls = _collect_official_urls_impl(source_map, input_url=input_url, entity_packet=entity_packet)
    analyzed_urls = _collect_analyzed_urls_impl(snapshot, source_map=source_map)

    offer_lines = strategic_packet.groups.get("product_offer", [])
    audience_lines = strategic_packet.groups.get("audience", [])
    outcome_lines = strategic_packet.groups.get("outcome", [])
    mission_lines = strategic_packet.groups.get("mission_language", [])
    vision_lines = strategic_packet.groups.get("vision_language", [])
    values_lines = strategic_packet.groups.get("values_language", [])
    personality_lines = strategic_packet.groups.get("personality_tone", [])
    hero_lines = strategic_packet.groups.get("hero_claims", [])
    proof_lines = strategic_packet.groups.get("proof_points", [])
    third_party_lines = strategic_packet.groups.get("third_party_context", [])
    press_like_personality_lines = [
        line
        for line in personality_lines
        if _looks_like_press_or_founder_text(str(line.text or ""))
    ]
    clean_personality_lines = [line for line in personality_lines if line not in press_like_personality_lines]

    company_summary = _first_meaningful_text(
        _primary_web_text_impl(web_payload),
        _lines_text(hero_lines),
        _lines_text(offer_lines),
        _lines_text(mission_lines),
    )
    product_summary = _first_meaningful_text(
        _primary_web_text_impl(web_payload),
        _lines_text(offer_lines),
        _lines_text(hero_lines),
        _lines_text(outcome_lines),
    )
    offer = _first_meaningful_text(
        _primary_web_text_impl(web_payload),
        _lines_text(offer_lines),
        company_summary,
        _lines_text(hero_lines),
    )
    audience = _infer_audience(audience_lines, offer, company_summary)
    outcome = _infer_outcome(outcome_lines, offer, product_summary)
    category = _infer_category(
        offer,
        product_summary,
        company_summary,
        exa_payload,
        context_payload,
        resolved,
    )
    declared_purpose = _first_meaningful_text(_lines_text(mission_lines), _lines_text(hero_lines))
    declared_mission = _first_meaningful_text(_lines_text(mission_lines))
    future_direction = _first_meaningful_text(_lines_text(vision_lines))
    tone_of_voice = _tone_summary(clean_personality_lines, product_summary)
    personality_signals = _unique_texts(
        _attribute_signals(_line_texts(clean_personality_lines) or [product_summary, offer], snapshot)
    )
    visual_or_conceptual_signals = _unique_texts(
        _concept_signals(
            company_summary,
            product_summary,
            offer,
            declared_mission,
            future_direction,
        )
    )
    values_signals = _unique_texts(_filter_values_signals(values_lines))
    attributes_signals = _unique_texts(
        _attribute_signals(
            [company_summary, product_summary, offer, tone_of_voice, declared_mission],
            snapshot,
        )
    )
    proof_points = _build_evidence_list(
        proof_lines,
        kind="proof",
        default_topic="proof_point",
    )
    founder_or_press_context = _build_evidence_list(
        third_party_lines,
        kind="context",
        default_topic="founder_or_press",
    )
    founder_or_press_context.extend(
        _build_evidence_list(
            press_like_personality_lines,
            kind="context",
            default_topic="founder_or_press",
        )
    )
    founder_or_press_context.extend(
        _build_evidence_from_source_map(source_map, allowed_types={"press_or_founder"}, kind="context")
    )
    founder_or_press_context.extend(
        _build_supplemental_context_evidence(snapshot, proof_points + founder_or_press_context)
    )
    proof_points.extend(
        _build_evidence_from_source_map(source_map, allowed_types={"proof_point"}, kind="proof")
    )
    noise_rejected = _build_noise_list(strategic_packet.rejected, web_payload)
    noise_rejected.extend(
        _build_evidence_from_source_map(source_map, allowed_types={"noise"}, kind="noise")
    )

    evidence_gaps = _evidence_gaps_impl(
        company_summary=company_summary,
        product_summary=product_summary,
        offer=offer,
        audience=audience,
        outcome=outcome,
        proof_points=proof_points,
        mission=declared_mission,
        official_urls=official_urls,
    )
    confidence_notes = _confidence_notes_impl(
        resolved=resolved,
        source_map=source_map,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        web_payload=web_payload,
        entity_packet=entity_packet,
    )

    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=input_url,
        resolved_entity=resolved,
        entity_type=resolved.entity_type,
        parent_brand=resolved.parent_brand,
        official_urls=official_urls,
        analyzed_urls=analyzed_urls,
        source_map=source_map,
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
        personality_signals=personality_signals,
        visual_or_conceptual_signals=visual_or_conceptual_signals,
        values_signals=values_signals,
        attributes_signals=attributes_signals,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        noise_rejected=noise_rejected,
        shadow_sources=_shadow_sources_from_snapshot(snapshot),
        evidence_gaps=evidence_gaps,
        confidence_notes=confidence_notes,
    )


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(
            raw_input.get("payload"), dict
        ):
            return raw_input["payload"]
    run = snapshot.get("run") or {}
    audit = run.get("audit") if isinstance(run.get("audit"), dict) else {}
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None
