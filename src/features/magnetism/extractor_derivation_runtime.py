"""Derivation utilities for `MagnetismExtractor`.

These methods are pure orchestration over extracted layers: normalization,
TLDR derivation, scoring, and legacy compatibility fields.
"""

from __future__ import annotations

from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import StrategicEvidencePacket
from src.features.magnetism.analyst_tldr import maybe_build_system_reading as _maybe_build_system_reading
from src.features.magnetism.extractor_constants import LAYER_KEYS, TLDR_KEYS, TLDR_TO_LAYER
from src.features.magnetism.extractor_normalization import (
    enrich_layers_from_legacy_text as _norm_enrich_layers_from_legacy_text,
    enrich_layers_from_strategic_packet as _norm_enrich_layers_from_strategic_packet,
    first_accepted_tactispace_packet_evidence as _norm_first_accepted_tactispace_packet_evidence,
    first_packet_item as _norm_first_packet_item,
    first_matching_sentence as _norm_first_matching_sentence,
    heuristic_finding as _norm_heuristic_finding,
    infer_brand_name as _norm_infer_brand_name,
    is_navigation_noise as _norm_is_navigation_noise,
    normalize_analysis as _norm_normalize_analysis,
    normalize_evidence as _norm_normalize_evidence,
    normalize_layers as _norm_normalize_layers,
    packet_layer_confidence as _norm_packet_layer_confidence,
    sentences_from_text as _norm_sentences_from_text,
    set_layer_from_packet as _norm_set_layer_from_packet,
    trim_evidence as _norm_trim_evidence,
    clean_evidence_phrase as _norm_clean_evidence_phrase,
    clean_optional_string as _norm_clean_optional_string,
    contains_keyword as _norm_contains_keyword,
    extract_three_terms as _norm_extract_three_terms,
)
from src.features.magnetism.extractor_tail import (
    brand_audit_evidence_text as _tail_brand_audit_evidence_text,
    default_counter_evidence as _tail_default_counter_evidence,
    has_tldr_v03_contract as _tail_has_tldr_v03_contract,
    is_unusable_audit_quote as _tail_is_unusable_audit_quote,
    infer_claim_type as _tail_infer_claim_type,
    legacy_value as _tail_legacy_value,
    observations_for_block as _tail_observations_for_block,
    should_recommend_human_review as _tail_should_recommend_human_review,
    snapshot_limitations as _tail_snapshot_limitations,
    visual_semantics_from_snapshot as _tail_visual_semantics_from_snapshot,
)
from src.features.magnetism.extractor_tldr import (
    derive_tldr as _tldr_derive_tldr,
    empty_tldr_block as _tldr_empty_tldr_block,
    interpret_tldr_block_from_spec as _tldr_interpret_tldr_block_from_spec,
    tldr_content_from_layer as _tldr_content_from_layer,
    with_tldr_contract as _tldr_with_tldr_contract,
)
from src.features.magnetism.extractor_derivation_blocks_runtime import (
    MagnetismExtractorDerivationBlocksMixin,
)
from src.features.magnetism.extractor_derivation_scoring_runtime import (
    MagnetismExtractorDerivationScoringMixin,
)


def _resolve_maybe_build_system_reading(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve system-reading through the public extractor facade for stable monkeypatching."""
    try:
        from src.features.magnetism import extractor as extractor_module

        patched = getattr(extractor_module, "maybe_build_system_reading")
        if callable(patched):
            return patched(
                llm=llm,
                brand_name=brand_name,
                url=url,
                tldr=tldr,
                layers=layers,
                metrics=metrics,
                evidence_packet_summary=evidence_packet_summary,
            )
    except Exception:
        pass
    return _maybe_build_system_reading(
        llm=llm,
        brand_name=brand_name,
        url=url,
        tldr=tldr,
        layers=layers,
        metrics=metrics,
        evidence_packet_summary=evidence_packet_summary,
    )


class MagnetismExtractorDerivationMixin(
    MagnetismExtractorDerivationBlocksMixin,
    MagnetismExtractorDerivationScoringMixin,
):
    """Post-parse derivation and scoring helpers for Magnetism extraction."""

    def _normalize_analysis(self, raw: dict[str, Any]) -> dict[str, Any]:
        return _norm_normalize_analysis(
            raw,
            normalize_layers_fn=self._normalize_layers,
            enrich_layers_from_legacy_text_fn=self._enrich_layers_from_legacy_text,
            enrich_layers_from_strategic_packet_fn=self._enrich_layers_from_strategic_packet,
            derive_tldr_fn=self._derive_tldr,
            derive_metrics_fn=self._derive_metrics,
            derive_diagnosis_fn=self._derive_diagnosis,
            derive_evidence_packet_summary_fn=self._derive_evidence_packet_summary,
            derive_system_reading_fn=self._derive_system_reading,
            add_legacy_fields_fn=self._add_legacy_fields,
        )

    def ensure_tldr_v03_contract(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Upgrade persisted scans that already have metrics/TLDR but predate the v0.3 block contract."""
        tldr = payload.get("tldr_brand3")
        layers = payload.get("magenta_circle")
        if not isinstance(tldr, dict) or not isinstance(layers, dict):
            return payload

        upgraded: dict[str, Any] = {}
        changed = False
        for key in TLDR_KEYS:
            layer_key = TLDR_TO_LAYER[key]
            block = tldr.get(key)
            if not isinstance(block, dict):
                block = self._empty_tldr_block(key, layer_key)
                changed = True
            if not self._has_tldr_v03_contract(block):
                changed = True
            upgraded[key] = self._with_tldr_contract(key, block, layers)

        if changed:
            payload = dict(payload)
            payload["tldr_brand3"] = upgraded
            self._add_legacy_fields(payload)
        if "evidence_packet_summary" not in payload:
            payload = dict(payload)
            payload["evidence_packet_summary"] = self._derive_evidence_packet_summary(payload)
        if "content_distillation_summary" not in payload:
            payload = dict(payload)
            payload["content_distillation_summary"] = None
        if "system_reading" not in payload:
            payload = dict(payload)
            payload["system_reading"] = self._build_system_reading(
                tldr=payload["tldr_brand3"],
                layers=payload.get("magenta_circle") or {},
                metrics=payload.get("metrics") or {},
                url=payload.get("url", ""),
                brand_name=payload.get("brand_name", "Unknown Brand"),
                evidence_packet_summary=(
                    payload.get("evidence_packet_summary")
                    if isinstance(payload.get("evidence_packet_summary"), dict)
                    else None
                ),
            )
        return payload

    def _build_system_reading(
        self,
        *,
        tldr: dict[str, Any],
        layers: dict[str, Any],
        metrics: dict[str, Any],
        url: str,
        brand_name: str,
        evidence_packet_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        llm_reading = _resolve_maybe_build_system_reading(
            llm=self.system_reading_llm,
            brand_name=brand_name,
            url=url,
            tldr=tldr,
            layers=layers,
            metrics=metrics,
            evidence_packet_summary=evidence_packet_summary if isinstance(evidence_packet_summary, dict) else None,
        )
        if isinstance(llm_reading, dict):
            return llm_reading
        return self._derive_system_reading(
            tldr=tldr,
            layers=layers,
            metrics=metrics,
            evidence_packet_summary=evidence_packet_summary,
        )

    @staticmethod
    def _has_tldr_v03_contract(block: dict[str, Any]) -> bool:
        return _tail_has_tldr_v03_contract(block)

    def _normalize_layers(self, raw_layers: dict[str, Any]) -> dict[str, Any]:
        return _norm_normalize_layers(raw_layers)

    def _enrich_layers_from_strategic_packet(
        self,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any],
        replace_detected_ambientspace: bool = False,
    ) -> None:
        _norm_enrich_layers_from_strategic_packet(layers, strategic_packet, replace_detected_ambientspace)

    @staticmethod
    def _first_packet_item(
        groups: dict[str, Any],
        group_names: list[str],
    ) -> dict[str, str] | None:
        return _norm_first_packet_item(groups, group_names)

    def _first_accepted_tactispace_packet_evidence(self, strategic_packet: dict[str, Any]) -> str | None:
        return _norm_first_accepted_tactispace_packet_evidence(strategic_packet)

    @staticmethod
    def _packet_layer_confidence(
        layer_key: str,
        groups: dict[str, Any],
        primary_group: str | None,
    ) -> str:
        return _norm_packet_layer_confidence(layer_key, groups, primary_group)

    def _set_layer_from_packet(
        self,
        layers: dict[str, Any],
        layer_key: str,
        evidence: str,
        confidence: str,
    ) -> None:
        _norm_set_layer_from_packet(layers, layer_key, evidence, confidence)

    def _derive_tldr(
        self,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any] | None = None,
        brand_context_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _tldr_derive_tldr(
            layers,
            strategic_packet=strategic_packet,
            brand_context_brief=brand_context_brief,
            personality_block_fn=self._derive_personality_block,
            brand_idea_block_fn=self._derive_brand_idea_block,
        )

    def _interpret_tldr_block_from_spec(
        self,
        key: str,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any] | None = None,
        brand_context_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return _tldr_interpret_tldr_block_from_spec(
            key,
            layers,
            strategic_packet=strategic_packet,
            brand_context_brief=brand_context_brief,
        )

    @staticmethod
    def _is_testimonial_evidence(text: str) -> bool:
        low = text.strip().lower()
        return low.startswith((">", "“", "\"")) or " nos ofrece " in low or " customer " in low

    @staticmethod
    def _empty_tldr_block(key: str, layer_key: str) -> dict[str, Any]:
        return _tldr_empty_tldr_block(key, layer_key)

    def _with_tldr_contract(
        self,
        key: str,
        block: dict[str, Any],
        layers: dict[str, Any],
    ) -> dict[str, Any]:
        return _tldr_with_tldr_contract(key, block, layers)

    @staticmethod
    def _infer_claim_type(key: str, mode: str, detected: bool) -> str:
        return _tail_infer_claim_type(key, mode, detected)

    @staticmethod
    def _observations_for_block(key: str, evidence_used: list[str], content: Any) -> list[str]:
        return _tail_observations_for_block(key, evidence_used, content)

    @staticmethod
    def _default_counter_evidence(
        key: str,
        claim_type: str,
        detected: bool,
        layers: dict[str, Any],
    ) -> list[str]:
        return _tail_default_counter_evidence(key, claim_type, detected, layers)

    @staticmethod
    def _should_recommend_human_review(
        key: str,
        claim_type: str,
        mode: str,
        confidence: str,
        detected: bool,
        evidence_used: list[str],
    ) -> bool:
        return _tail_should_recommend_human_review(key, claim_type, mode, confidence, detected, evidence_used)

    def _derive_evidence_packet_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Summarize the shared evidence basis without embedding a second report."""
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

    @staticmethod
    def _brand_audit_evidence_packet_summary(
        snapshot: dict[str, Any],
        strategic_packet: StrategicEvidencePacket | None = None,
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

    def _add_legacy_fields(self, payload: dict[str, Any]) -> None:
        """Keep current storage/routes/templates working while the UI migrates."""
        metrics = payload["metrics"]
        diagnosis = payload["diagnosis"]
        tldr = payload["tldr_brand3"]

        payload["magnetism_score"] = metrics["magnetism_score"]
        payload["coherence_score"] = metrics["coherence_score"]
        payload["quadrant"] = metrics["quadrant"]
        payload["executive_headline"] = diagnosis["headline"]
        payload["observations"] = diagnosis["key_observations"][:3]
        payload["tldr_grid"] = {
            "niche": _tail_legacy_value(tldr["core_purpose"]),
            "value_proposition": _tail_legacy_value(tldr["value_proposition"]),
            "target_audience": "(no detectado)",
            "friction": "(no detectado)",
            "uniqueness": _tail_legacy_value(tldr["brand_idea"]),
            "primary_cta": _tail_legacy_value(tldr["mission"]),
            "core_promise": _tail_legacy_value(tldr["magnetism"]),
            "behavioral_hook": _tail_legacy_value(tldr["vision"]),
            "tone": _tail_legacy_value(tldr["personality"]),
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

    @staticmethod
    def _brand_audit_evidence_text(snapshot: dict[str, Any]) -> str:
        return _tail_brand_audit_evidence_text(snapshot)

    @staticmethod
    def _is_unusable_audit_quote(value: str) -> bool:
        return _tail_is_unusable_audit_quote(value)

    @staticmethod
    def _visual_semantics_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return _tail_visual_semantics_from_snapshot(snapshot)

    @staticmethod
    def _snapshot_limitations(snapshot: dict[str, Any]) -> list[str]:
        return _tail_snapshot_limitations(snapshot)

    @staticmethod
    def _evidence_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value:
            return [str(value).strip()]
        return []

    @staticmethod
    def _default_tldr_mode(key: str, layer: dict[str, Any]) -> str:
        finding = str(layer.get("finding") or "")
        if not layer.get("detected"):
            return "not_detected"
        if finding and not finding.startswith("Detected "):
            return "interpreted_from_discourse"
        if key in {"magnetism", "value_proposition", "mission"}:
            return "compressed"
        return "interpreted_from_discourse"

    @staticmethod
    def _default_tldr_rationale(key: str, mode: str) -> str:
        if mode == "compressed":
            return f"The {key} block is compressed from direct evidence."
        if mode == "literal":
            return f"The {key} block is directly stated in the evidence."
        if mode == "interpreted_from_discourse":
            return f"The {key} block is articulated from observed discourse signals."
        return "Insufficient evidence to articulate this block responsibly."

    @staticmethod
    def _apply_block_specific_content_rules(
        key: str,
        content: Any,
        evidence: list[str],
        mode: str,
        rationale: str,
    ) -> tuple[Any, str, str]:
        """Keep declarative blocks grounded in quoted evidence instead of LLM paraphrase."""
        if key in {"magnetism", "value_proposition"}:
            return evidence[0], "compressed", f"The {key} block is compressed from direct evidence."
        if key == "core_purpose":
            return (
                evidence[0],
                "interpreted_from_discourse",
                "The core_purpose block is a Brand3 hypothesis constrained to the available purpose signal.",
            )
        return content, mode, rationale

    def _enrich_layers_from_legacy_text(self, raw: dict[str, Any], layers: dict[str, Any]) -> None:
        _norm_enrich_layers_from_legacy_text(raw, layers)

    @staticmethod
    def _infer_brand_name(url_str: str) -> str:
        return _norm_infer_brand_name(url_str)

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return _norm_sentences_from_text(text)

    @staticmethod
    def _first_matching_sentence(sentences: list[str], keywords: list[str]) -> str | None:
        return _norm_first_matching_sentence(sentences, keywords)

    @staticmethod
    def _heuristic_finding(layer: str, evidence: str) -> str:
        return _norm_heuristic_finding(layer, evidence)

    @staticmethod
    def _tldr_content_from_layer(layer: dict[str, Any]) -> str | None:
        return _tldr_content_from_layer(layer)

    @staticmethod
    def _contains_keyword(text: str, keyword: str) -> bool:
        return _norm_contains_keyword(text, keyword)

    @staticmethod
    def _trim_evidence(sentence: str, keyword: str, max_chars: int = 260) -> str:
        return _norm_trim_evidence(sentence, keyword, max_chars)

    @staticmethod
    def _clean_evidence_phrase(value: str) -> str:
        return _norm_clean_evidence_phrase(value)

    @staticmethod
    def _is_navigation_noise(value: str) -> bool:
        return _norm_is_navigation_noise(value)

    @staticmethod
    def _normalize_evidence(value: Any) -> str | None:
        return _norm_normalize_evidence(value)

    @staticmethod
    def _clean_optional_string(value: Any) -> str | None:
        return _norm_clean_optional_string(value)

    @staticmethod
    def _extract_three_terms(text: str, key: str) -> list[str] | None:
        return _norm_extract_three_terms(text, key)
