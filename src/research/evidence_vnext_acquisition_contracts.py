"""Shadow acquisition contract normalization for evidence vNext."""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AcquisitionContractExclusion:
    """One item excluded by a shadow acquisition contract."""

    contract: str
    provider: str
    surface: str
    reason: str
    url: str
    text_preview: str = ""
    dimension: str = ""
    feature_name: str = ""
    collection: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "contract": self.contract,
            "provider": self.provider,
            "surface": self.surface,
            "reason": self.reason,
            "url": self.url,
            "text_preview": self.text_preview,
            "dimension": self.dimension,
            "feature_name": self.feature_name,
            "collection": self.collection,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionContractResult:
    """Shadow snapshot normalization result for evidence vNext contracts."""

    normalized_snapshot: dict[str, Any]
    exclusions: tuple[AcquisitionContractExclusion, ...]
    applied_contracts: tuple[str, ...] = ("exa.non_empty_text",)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_effect": False,
            "prompt_effect": False,
            "persistence_effect": False,
            "applied_contracts": list(self.applied_contracts),
            "exclusions": [item.to_dict() for item in self.exclusions],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        by_contract: dict[str, int] = {}
        by_surface: dict[str, int] = {}
        by_feature: dict[str, int] = {}
        for item in self.exclusions:
            by_contract[item.contract] = by_contract.get(item.contract, 0) + 1
            by_surface[item.surface] = by_surface.get(item.surface, 0) + 1
            if item.feature_name:
                by_feature[item.feature_name] = by_feature.get(item.feature_name, 0) + 1
        return {
            "excluded_count": len(self.exclusions),
            "exclusion_counts_by_contract": dict(sorted(by_contract.items())),
            "exclusion_counts_by_surface": dict(sorted(by_surface.items())),
            "exclusion_counts_by_feature": dict(sorted(by_feature.items())),
        }


def apply_evidence_vnext_acquisition_contracts(snapshot: dict[str, Any]) -> AcquisitionContractResult:
    """Apply shadow acquisition contracts to a snapshot without mutating it."""

    normalized = copy.deepcopy(snapshot)
    exclusions: list[AcquisitionContractExclusion] = []
    _normalize_exa_raw_inputs(normalized, exclusions)
    _normalize_exa_feature_raw_values(normalized, exclusions)
    return AcquisitionContractResult(
        normalized_snapshot=normalized,
        exclusions=tuple(exclusions),
    )


def _acquisition_diagnostics_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    exa_diagnostics: dict[str, Any] = {}
    for raw_input in snapshot.get("raw_inputs") or []:
        if not isinstance(raw_input, dict) or str(raw_input.get("source") or "") != "exa":
            continue
        payload = raw_input.get("payload")
        if not isinstance(payload, dict):
            continue
        diagnostics = payload.get("diagnostics")
        if isinstance(diagnostics, dict):
            exa_diagnostics = diagnostics
            break
    planned_intents = exa_diagnostics.get("planned_intents")
    if not isinstance(planned_intents, list):
        planned_intents = sorted((exa_diagnostics.get("intent_results") or {}).keys())
    return {
        "exa": {
            "strategy": str(exa_diagnostics.get("strategy") or "unknown"),
            "status": str(exa_diagnostics.get("status") or "unknown"),
            "competitor_intent_enabled": bool(exa_diagnostics.get("competitor_intent_enabled")),
            "planned_intents": [str(item) for item in planned_intents if item],
            "failed_intents": [str(item) for item in exa_diagnostics.get("failed_intents") or [] if item],
            "no_result_intents": [str(item) for item in exa_diagnostics.get("no_result_intents") or [] if item],
        }
    }


def _normalize_exa_raw_inputs(snapshot: dict[str, Any], exclusions: list[AcquisitionContractExclusion]) -> None:
    for raw_input in snapshot.get("raw_inputs") or []:
        if not isinstance(raw_input, dict) or str(raw_input.get("source") or "") != "exa":
            continue
        payload = raw_input.get("payload")
        if not isinstance(payload, dict):
            continue
        for collection in ("mentions", "news", "ai_visibility_results", "competitors"):
            entries = payload.get(collection)
            if not isinstance(entries, list):
                continue
            kept: list[Any] = []
            for entry in entries:
                if _is_empty_exa_result(entry):
                    exclusions.append(
                        AcquisitionContractExclusion(
                            contract="exa.non_empty_text",
                            provider="exa",
                            surface=f"raw_inputs.exa.{collection}",
                            reason="empty_text_evidence_blocked",
                            url=str(entry.get("url") or "").strip() if isinstance(entry, dict) else "",
                            text_preview=_clean_text(_exa_entry_text(entry))[:180] if isinstance(entry, dict) else "",
                            collection=collection,
                        )
                    )
                    continue
                kept.append(entry)
            payload[collection] = kept


def _normalize_exa_feature_raw_values(snapshot: dict[str, Any], exclusions: list[AcquisitionContractExclusion]) -> None:
    for feature in snapshot.get("features") or []:
        if not isinstance(feature, dict) or str(feature.get("source") or "") != "exa":
            continue
        raw = _parse_shadow_raw_value(feature.get("raw_value"))
        if not isinstance(raw, dict):
            continue
        normalized_raw, removed = _normalize_exa_feature_raw_dict(raw, feature=feature)
        if removed:
            exclusions.extend(removed)
            feature["raw_value"] = normalized_raw


def _normalize_exa_feature_raw_dict(
    raw: dict[str, Any],
    *,
    feature: dict[str, Any],
) -> tuple[dict[str, Any], list[AcquisitionContractExclusion]]:
    normalized = copy.deepcopy(raw)
    exclusions: list[AcquisitionContractExclusion] = []
    for key in ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples", "gaps"):
        entries = normalized.get(key)
        if not isinstance(entries, list):
            continue
        kept: list[Any] = []
        for entry in entries:
            if isinstance(entry, dict) and _is_empty_exa_feature_entry(entry):
                exclusions.append(_feature_exclusion(feature=feature, key=key, entry=entry))
                continue
            kept.append(entry)
        normalized[key] = kept
    evidence_url = str(normalized.get("evidence_url") or "").strip()
    if evidence_url and not _raw_payload_has_text(normalized):
        exclusions.append(
            AcquisitionContractExclusion(
                contract="exa.non_empty_text",
                provider="exa",
                surface="features.exa.raw_value.evidence_url",
                reason="empty_text_evidence_blocked",
                url=evidence_url,
                dimension=str(feature.get("dimension_name") or ""),
                feature_name=str(feature.get("feature_name") or ""),
                collection="evidence_url",
            )
        )
        normalized.pop("evidence_url", None)
    return normalized, exclusions


def _feature_exclusion(
    *,
    feature: dict[str, Any],
    key: str,
    entry: dict[str, Any],
) -> AcquisitionContractExclusion:
    return AcquisitionContractExclusion(
        contract="exa.non_empty_text",
        provider="exa",
        surface=f"features.exa.raw_value.{key}",
        reason="empty_text_evidence_blocked",
        url=_feature_entry_url(entry),
        text_preview=_clean_text(_feature_entry_text(entry))[:180],
        dimension=str(feature.get("dimension_name") or ""),
        feature_name=str(feature.get("feature_name") or ""),
        collection=key,
    )


def _is_empty_exa_result(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    return bool(str(entry.get("url") or "").strip()) and not _clean_text(_exa_entry_text(entry))


def _is_empty_exa_feature_entry(entry: dict[str, Any]) -> bool:
    return bool(_feature_entry_url(entry)) and not _clean_text(_feature_entry_text(entry))


def _feature_entry_url(entry: dict[str, Any]) -> str:
    source = entry.get("source")
    source_url = source if isinstance(source, str) and source.strip().startswith(("http://", "https://")) else ""
    return str(entry.get("source_url") or entry.get("url") or source_url or "").strip()


def _feature_entry_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "quote",
        "snippet",
        "text",
        "example",
        "title",
        "summary",
        "markdown",
        "markdown_content",
        "content",
        "self_says",
        "third_party_says",
    ):
        value = entry.get(key)
        if isinstance(value, str):
            parts.append(value)
    highlights = entry.get("highlights")
    if isinstance(highlights, list):
        parts.extend(str(item or "") for item in highlights)
    return " ".join(parts)


def _exa_entry_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "text", "markdown", "markdown_content", "content"):
        value = entry.get(key)
        if isinstance(value, str):
            parts.append(value)
    highlights = entry.get("highlights")
    if isinstance(highlights, list):
        parts.extend(str(item or "") for item in highlights)
    return " ".join(parts)


def _raw_payload_has_text(raw: dict[str, Any]) -> bool:
    for key in ("evidence_snippet", "summary", "text", "markdown", "content"):
        if _clean_text(raw.get(key)):
            return True
    snippets = raw.get("evidence_snippets")
    if isinstance(snippets, list) and any(_clean_text(item) for item in snippets):
        return True
    for key in ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples", "gaps"):
        entries = raw.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, str) and _clean_text(entry):
                return True
            if isinstance(entry, dict) and _clean_text(_feature_entry_text(entry)):
                return True
    return False


def _parse_shadow_raw_value(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        pass
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        return raw


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def build_acquisition_matrix(
    *,
    provider_rows: dict[str, dict[str, Any]],
    source_class_rows: dict[str, dict[str, Any]],
    gate_payload: dict[str, Any],
) -> None:
    for status_key in ("accepted", "review_required", "rejected"):
        observations = gate_payload.get(status_key) or []
        if not isinstance(observations, list):
            continue
        for item in observations:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "unknown_provider")
            source_class = str(item.get("source_class") or "unknown_source")
            reason = _observation_reason(item) if status_key != "accepted" else "accepted"
            _increment_acquisition_row(
                rows=provider_rows,
                key=provider,
                key_field="provider",
                status_key=status_key,
                reason=reason,
                peer_field="source_classes",
                peer_value=source_class,
            )
            _increment_acquisition_row(
                rows=source_class_rows,
                key=source_class,
                key_field="source_class",
                status_key=status_key,
                reason=reason,
                peer_field="providers",
                peer_value=provider,
            )


def accumulate_acquisition_contract_exclusions(*, target: dict[str, Any], payload: dict[str, Any]) -> None:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    target["total"] = int(target.get("total") or 0) + int(summary.get("excluded_count") or 0)
    for source_key, target_key in (
        ("exclusion_counts_by_contract", "by_contract"),
        ("exclusion_counts_by_surface", "by_surface"),
        ("exclusion_counts_by_feature", "by_feature"),
    ):
        counts = summary.get(source_key) if isinstance(summary.get(source_key), dict) else {}
        bucket = target.setdefault(target_key, {})
        for key, value in counts.items():
            bucket[str(key)] = int(bucket.get(str(key)) or 0) + int(value or 0)
        target[target_key] = dict(sorted(bucket.items()))


def accumulate_acquisition_diagnostics(
    *,
    target: list[dict[str, Any]],
    payload: dict[str, Any],
    run_id: int | None,
    brand_name: str,
) -> None:
    exa = payload.get("exa") if isinstance(payload.get("exa"), dict) else {}
    target.append(
        {
            "run_id": run_id,
            "brand_name": brand_name,
            "provider": "exa",
            "strategy": str(exa.get("strategy") or "unknown"),
            "status": str(exa.get("status") or "unknown"),
            "competitor_intent_enabled": bool(exa.get("competitor_intent_enabled")),
            "planned_intents": [str(item) for item in exa.get("planned_intents") or [] if item],
            "failed_intents": [str(item) for item in exa.get("failed_intents") or [] if item],
            "no_result_intents": [str(item) for item in exa.get("no_result_intents") or [] if item],
        }
    )


def finalize_acquisition_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    strategy_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    competitor_intent_enabled_count = 0
    for row in rows:
        strategy = str(row.get("strategy") or "unknown")
        status = str(row.get("status") or "unknown")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        if row.get("competitor_intent_enabled"):
            competitor_intent_enabled_count += 1
    return {
        "exa": {
            "strategy_counts": dict(sorted(strategy_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "competitor_intent_enabled_count": competitor_intent_enabled_count,
            "rows": rows,
        }
    }


def finalize_acquisition_matrix(
    *,
    provider_rows: dict[str, dict[str, Any]],
    source_class_rows: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "provider_rows": _finalize_acquisition_rows(provider_rows, key_field="provider"),
        "source_class_rows": _finalize_acquisition_rows(source_class_rows, key_field="source_class"),
    }


def _increment_acquisition_row(
    *,
    rows: dict[str, dict[str, Any]],
    key: str,
    key_field: str,
    status_key: str,
    reason: str,
    peer_field: str,
    peer_value: str,
) -> None:
    row = rows.setdefault(
        key,
        {
            key_field: key,
            "accepted": 0,
            "review_required": 0,
            "rejected": 0,
            "total": 0,
            "reason_counts": {},
            peer_field: {},
        },
    )
    row[status_key] = int(row.get(status_key) or 0) + 1
    row["total"] = int(row.get("total") or 0) + 1
    _increment_count(row["reason_counts"], reason)
    _increment_count(row[peer_field], peer_value)


def _finalize_acquisition_rows(rows: dict[str, dict[str, Any]], *, key_field: str) -> list[dict[str, Any]]:
    result = []
    for row in rows.values():
        normalized = dict(row)
        normalized["reason_counts"] = _count_dict(_top_counts(normalized.get("reason_counts") or {}, limit=5))
        if key_field == "provider":
            normalized["source_classes"] = _count_dict(_top_counts(normalized.get("source_classes") or {}, limit=5))
        else:
            normalized["providers"] = _count_dict(_top_counts(normalized.get("providers") or {}, limit=5))
        result.append(normalized)
    return sorted(result, key=lambda item: (-int(item.get("total") or 0), str(item.get(key_field) or "")))


def _increment_count(counts: dict[str, int], key: str) -> None:
    counts[str(key or "unknown")] = counts.get(str(key or "unknown"), 0) + 1


def _top_counts(counts: dict[str, Any], limit: int = 3) -> list[tuple[str, int]]:
    pairs = [(str(key), int(value or 0)) for key, value in counts.items()]
    return sorted(pairs, key=lambda item: (-item[1], item[0]))[:limit]


def _count_dict(pairs: list[tuple[str, int]]) -> dict[str, int]:
    return {key: value for key, value in pairs}


def _observation_reason(item: dict[str, Any]) -> str:
    return (
        str(item.get("classification_reason") or "").strip()
        or str(item.get("eligibility") or "").strip()
        or str(item.get("source_class") or "").strip()
        or "unknown"
    )


def build_provider_acquisition_contracts(acquisition_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = {
        str(row.get("provider") or ""): row
        for row in acquisition_matrix.get("provider_rows") or []
        if isinstance(row, dict)
    }
    contracts: list[dict[str, Any]] = []
    exa = rows.get("exa") or {}
    exa_reasons = exa.get("reason_counts") or {}
    if int(exa_reasons.get("empty_text_evidence_blocked") or 0):
        contracts.append(
            build_provider_contract(
                contract="exa.non_empty_text",
                provider="exa",
                severity="high",
                recommended_action="reject_empty_text_results_before_feature_evidence",
                reason_codes=["empty_text_evidence_blocked"],
                affected_observation_count=int(exa_reasons.get("empty_text_evidence_blocked") or 0),
                current_counts=exa,
            )
        )
    exa_boundary_count = int(exa_reasons.get("same_name_external_profile_not_alias") or 0) + int(
        exa_reasons.get("same_name_different_root_domain") or 0
    )
    if exa_boundary_count:
        contracts.append(
            build_provider_contract(
                contract="exa.entity_boundary_review",
                provider="exa",
                severity="high",
                recommended_action="preserve_same_name_or_different_root_results_as_review_only",
                reason_codes=["same_name_external_profile_not_alias", "same_name_different_root_domain"],
                affected_observation_count=exa_boundary_count,
                current_counts=exa,
            )
        )

    llm = rows.get("llm") or {}
    llm_reasons = llm.get("reason_counts") or {}
    if int(llm_reasons.get("missing_evidence_url") or 0):
        contracts.append(
            build_provider_contract(
                contract="llm.material_quote_source_url",
                provider="llm",
                severity="high",
                recommended_action="require_source_url_for_material_quotes_or_keep_review_gated",
                reason_codes=["missing_evidence_url"],
                affected_observation_count=int(llm_reasons.get("missing_evidence_url") or 0),
                current_counts=llm,
            )
        )

    for provider, reason_code, contract_name, action in (
        (
            "content_analysis",
            "internal_analysis_not_market_evidence",
            "content_analysis.diagnostic_only",
            "keep_internal_analysis_out_of_market_narrative_evidence",
        ),
        (
            "visual_analysis",
            "visual_or_internal_analysis_not_market_evidence",
            "visual_analysis.diagnostic_only",
            "keep_visual_analysis_out_of_market_narrative_evidence",
        ),
        (
            "context",
            "technical_context_not_brand_narrative_evidence",
            "context.technical_only",
            "keep_technical_context_out_of_brand_narrative_evidence",
        ),
    ):
        row = rows.get(provider) or {}
        count = int((row.get("reason_counts") or {}).get(reason_code) or 0)
        if count:
            contracts.append(
                build_provider_contract(
                    contract=contract_name,
                    provider=provider,
                    severity="medium",
                    recommended_action=action,
                    reason_codes=[reason_code],
                    affected_observation_count=count,
                    current_counts=row,
                )
            )

    social = rows.get("social_scrape") or {}
    social_reasons = social.get("reason_counts") or {}
    if int(social_reasons.get("same_name_external_profile_not_alias") or 0):
        contracts.append(
            build_provider_contract(
                contract="social_scrape.alias_confirmation",
                provider="social_scrape",
                severity="high",
                recommended_action="require_alias_confirmation_before_material_or_promotion_use",
                reason_codes=["same_name_external_profile_not_alias"],
                affected_observation_count=int(social_reasons.get("same_name_external_profile_not_alias") or 0),
                current_counts=social,
            )
        )

    return contracts


def build_provider_contract_backlog(provider_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    counts: dict[str, int] = {}
    observation_counts: dict[str, int] = {}
    for item in provider_contracts:
        status = str(item.get("implementation_status") or "unknown")
        affected = int(item.get("affected_observation_count") or 0)
        counts[status] = counts.get(status, 0) + 1
        observation_counts[status] = observation_counts.get(status, 0) + affected
        rows.append(
            {
                "contract": item.get("contract") or "",
                "provider": item.get("provider") or "",
                "implementation_status": status,
                "implementation_lane": item.get("implementation_lane") or "",
                "affected_observation_count": affected,
                "next_step": item.get("next_step") or "",
                "proposed_tests": list(item.get("proposed_tests") or []),
            }
        )
    return {
        "counts": dict(sorted(counts.items())),
        "observation_counts": dict(sorted(observation_counts.items())),
        "rows": sorted(
            rows,
            key=lambda item: (
                str(item.get("implementation_status") or ""),
                -int(item.get("affected_observation_count") or 0),
                str(item.get("contract") or ""),
            ),
        ),
    }


def build_provider_contract(
    *,
    contract: str,
    provider: str,
    severity: str,
    recommended_action: str,
    reason_codes: list[str],
    affected_observation_count: int,
    current_counts: dict[str, Any],
) -> dict[str, Any]:
    implementation = build_provider_contract_implementation(contract)
    return {
        "contract": contract,
        "provider": provider,
        "severity": severity,
        "recommended_action": recommended_action,
        "reason_codes": reason_codes,
        "affected_observation_count": affected_observation_count,
        "current_counts": {
            "accepted": int(current_counts.get("accepted") or 0),
            "review_required": int(current_counts.get("review_required") or 0),
            "rejected": int(current_counts.get("rejected") or 0),
            "total": int(current_counts.get("total") or 0),
        },
        "runtime_effect": False,
        "prompt_effect": False,
        "enforcement_point": implementation["enforcement_point"],
        "implementation_status": implementation["implementation_status"],
        "implementation_lane": implementation["implementation_lane"],
        "next_step": implementation["next_step"],
        "acceptance_criteria": implementation["acceptance_criteria"],
        "proposed_tests": implementation["proposed_tests"],
    }


def build_provider_contract_implementation(contract: str) -> dict[str, Any]:
    specs = {
        "exa.non_empty_text": {
            "enforcement_point": "exa_raw_result_normalization",
            "implementation_status": "upstream_enforced",
            "implementation_lane": "collector_normalization",
            "next_step": "Keep collector and feature-level non-empty text guards for new runs; old snapshots may still report historical exclusions.",
            "acceptance_criteria": [
                "Exa results with URL but empty title, summary, text, and markdown are excluded before feature evidence construction.",
                "Excluded empty Exa results remain visible as diagnostic rejects, not material claims.",
            ],
            "proposed_tests": [
                "test_exa_empty_text_result_is_rejected_before_material_evidence",
                "test_exa_non_empty_result_can_still_be_accepted",
            ],
        },
        "exa.entity_boundary_review": {
            "enforcement_point": "exa_entity_classification",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep the vNext entity-boundary gate and later decide whether to move it upstream.",
            "acceptance_criteria": [
                "Same-name or different-root Exa records are preserved as review_required with entity-boundary reason codes.",
                "Entity-boundary Exa records cannot enter material fields before alias confirmation.",
            ],
            "proposed_tests": [
                "test_exa_same_name_different_root_is_review_required",
                "test_exa_entity_boundary_record_is_excluded_from_material_fields",
            ],
        },
        "llm.material_quote_source_url": {
            "enforcement_point": "llm_material_quote_contract",
            "implementation_status": "prompt_contract_needed",
            "implementation_lane": "llm_output_contract",
            "next_step": "Require source_url for material quote/tone outputs or keep them review-gated.",
            "acceptance_criteria": [
                "LLM tone or quote outputs need source_url before entering proof/context fields.",
                "Unsourced LLM material quotes remain review-gated or are excluded from material evidence.",
            ],
            "proposed_tests": [
                "test_llm_material_quote_requires_source_url",
                "test_unsourced_llm_quote_stays_out_of_material_fields",
            ],
        },
        "content_analysis.diagnostic_only": {
            "enforcement_point": "internal_analysis_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep content-analysis outputs diagnostic-only in vNext and avoid promotion into material evidence.",
            "acceptance_criteria": [
                "Content-analysis observations remain available for diagnostics.",
                "Content-analysis observations cannot become market narrative evidence.",
            ],
            "proposed_tests": [
                "test_content_analysis_is_diagnostic_only",
                "test_content_analysis_does_not_populate_material_fields",
            ],
        },
        "visual_analysis.diagnostic_only": {
            "enforcement_point": "visual_analysis_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep visual-analysis outputs diagnostic-only in vNext and avoid promotion into narrative proof.",
            "acceptance_criteria": [
                "Visual-analysis observations remain diagnostic.",
                "Visual-analysis observations cannot become narrative proof points.",
            ],
            "proposed_tests": [
                "test_visual_analysis_is_diagnostic_only",
                "test_visual_analysis_does_not_populate_material_fields",
            ],
        },
        "context.technical_only": {
            "enforcement_point": "technical_context_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep technical context diagnostic-only and outside Brand3 narrative evidence.",
            "acceptance_criteria": [
                "Technical context remains available for debugging and methodology.",
                "Technical context does not become brand narrative evidence.",
            ],
            "proposed_tests": [
                "test_context_technical_signal_is_rejected_as_narrative_evidence",
                "test_context_technical_signal_remains_diagnostic",
            ],
        },
        "social_scrape.alias_confirmation": {
            "enforcement_point": "social_profile_entity_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep social profiles review-gated unless placeholder auto-clear or explicit material alias work order applies.",
            "acceptance_criteria": [
                "Same-name social profiles require alias confirmation before material or promotion use.",
                "Unconfirmed social profiles remain review-gated with entity-boundary reason codes.",
            ],
            "proposed_tests": [
                "test_social_profile_requires_alias_confirmation",
                "test_unconfirmed_social_profile_does_not_enter_material_fields",
            ],
        },
    }
    return specs.get(
        contract,
        {
            "enforcement_point": "unknown",
            "implementation_status": "unknown",
            "implementation_lane": "unknown",
            "next_step": "",
            "acceptance_criteria": [],
            "proposed_tests": [],
        },
    )
