"""Private helper functions for evidence vNext filtering and comparison."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.evidence_packet import build_evidence_packet_v0
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph, build_evidence_graph_from_snapshot
from src.research.evidence_vnext_acquisition_contracts import _clean_text
from src.research.research_pack_builder import build_brand_research_pack_from_graph


ACCEPTED_ELIGIBILITIES = {"eligible_for_narrative_finding", "observation_only"}
REVIEW_ELIGIBILITIES = {"requires_human_review", "trust_security_review_only"}
REJECTED_ELIGIBILITIES = {"technical_only", "reject_noise", "blocked_empty_text"}
ACCEPTED_SOURCE_CLASSES = {
    "audited_surface",
    "owned_surface",
    "external_third_party",
    "repository",
    "competitor_comparison",
}
REVIEW_SOURCE_CLASSES = {"related_unresolved", "marketplace_listing", "trust_security"}
REJECTED_SOURCE_CLASSES = {"technical_internal", "visual_internal_metric", "noise"}
INTERNAL_ANALYSIS_FEATURES = {"content_authenticity", "brand_personality"}
INTERNAL_ANALYSIS_PROVIDERS = {"content_analysis"}


def _observations_from_packet(packet: dict[str, Any], *, snapshot: dict[str, Any]) -> list[Any]:
    from src.research.evidence_vnext import SourceObservation

    observations: list[SourceObservation] = []
    seen: set[tuple[str, str, str, str]] = set()
    dimension_inputs = packet.get("dimension_evidence_inputs") if isinstance(packet.get("dimension_evidence_inputs"), dict) else {}
    url_hints = _dimension_url_hints(dimension_inputs)
    text_url_hints = _snapshot_text_url_hints(snapshot)
    audit_root = _root_domain(_host(str(packet.get("audit_url") or "")))
    for dimension, items in dimension_inputs.items():
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = _clean_text(item.get("text"))
            url = str(item.get("url") or "").strip()
            source_class = str(item.get("source_class") or "")
            eligibility = str(item.get("eligibility") or "")
            classification_reason = str(item.get("classification_reason") or "")
            limits = str(item.get("limits") or "")
            if _is_internal_analysis_observation(item):
                source_class = "visual_internal_metric"
                eligibility = "technical_only"
                classification_reason = "internal_analysis_not_market_evidence"
            source_class, eligibility, classification_reason = _correct_exa_visual_false_positive(
                url=url,
                text=text,
                audit_root=audit_root,
                provider=str(item.get("feature_source") or ""),
                source_class=source_class,
                eligibility=eligibility,
                classification_reason=classification_reason,
            )
            if not url and text and classification_reason in {"missing_evidence_url", "owned_claim_without_url"}:
                inferred_url = url_hints.get(_dimension_group_key(str(dimension or ""), item))
                if inferred_url:
                    url = inferred_url
                    source_class, eligibility, classification_reason = _apply_inferred_url(
                        url=url,
                        audit_root=audit_root,
                        source_class=source_class,
                        eligibility=eligibility,
                        classification_reason=classification_reason,
                        reason="evidence_url_inferred_from_same_feature",
                    )
                    limits = _append_limit(limits, "URL inferred by evidence vNext from same feature evidence_url.")
            if not url and text and classification_reason in {"missing_evidence_url", "owned_claim_without_url"}:
                inferred_url = _infer_url_for_text(text, text_url_hints, audit_root=audit_root)
                if inferred_url:
                    url = inferred_url
                    source_class, eligibility, classification_reason = _apply_inferred_url(
                        url=url,
                        audit_root=audit_root,
                        source_class=source_class,
                        eligibility=eligibility,
                        classification_reason=classification_reason,
                        reason="evidence_url_inferred_from_raw_source_text",
                    )
                    limits = _append_limit(limits, "URL inferred by evidence vNext from raw source text match.")
            key = (str(dimension), text.lower(), url.lower(), eligibility)
            if key in seen:
                continue
            seen.add(key)
            observations.append(
                SourceObservation(
                    observation_id=f"obs_{len(observations) + 1:04d}",
                    text=text,
                    url=url,
                    dimension=str(dimension or ""),
                    provider=str(item.get("feature_source") or ""),
                    feature_name=str(item.get("feature_name") or ""),
                    source_class=source_class,
                    eligibility=eligibility,
                    gate_status=_gate_status(source_class=source_class, eligibility=eligibility, text=text),
                    classification_reason=classification_reason,
                    limits=limits,
                )
            )
    return _apply_covered_by_accepted_source(observations, audit_root=audit_root)


def _apply_covered_by_accepted_source(
    observations: list[Any],
    *,
    audit_root: str,
) -> list[Any]:
    from src.research.evidence_vnext import SourceObservation

    accepted = [item for item in observations if item.gate_status == "accepted" and item.url and item.text]
    if not accepted:
        return observations
    covered: list[SourceObservation] = []
    for item in observations:
        if item.gate_status != "review_required" or item.classification_reason != "missing_evidence_url" or item.url:
            covered.append(item)
            continue
        covered_url = _covered_by_accepted_source_url(item.text, accepted)
        if not covered_url:
            covered.append(item)
            continue
        source_class, eligibility, classification_reason = _apply_inferred_url(
            url=covered_url,
            audit_root=audit_root,
            source_class=item.source_class,
            eligibility=item.eligibility,
            classification_reason=item.classification_reason,
            reason="covered_by_accepted_source",
        )
        limits = _append_limit(item.limits, "URL covered by accepted same-root evidence in evidence vNext.")
        covered.append(
            SourceObservation(
                observation_id=item.observation_id,
                text=item.text,
                url=covered_url,
                dimension=item.dimension,
                provider=item.provider,
                feature_name=item.feature_name,
                source_class=source_class,
                eligibility=eligibility,
                gate_status=_gate_status(source_class=source_class, eligibility=eligibility, text=item.text),
                classification_reason=classification_reason,
                limits=limits,
            )
        )
    return covered


def _covered_by_accepted_source_url(text: str, accepted: list[Any]) -> str:
    fragments = _coverage_fragments(text)
    if not fragments:
        return ""
    urls_by_fragment: list[set[str]] = []
    for fragment in fragments:
        urls = {
            item.url
            for item in accepted
            if _coverage_fragment_matches_accepted(fragment, item.text)
        }
        if not urls:
            return ""
        urls_by_fragment.append(urls)
    intersection = set.intersection(*urls_by_fragment)
    if intersection:
        return _choose_inferred_url(intersection)
    return _choose_inferred_url(set().union(*urls_by_fragment))


def _coverage_fragment_matches_accepted(fragment: str, accepted_text: str) -> bool:
    accepted = _source_match_text(accepted_text)
    if not fragment or not accepted:
        return False
    return fragment in accepted or accepted in fragment


def _coverage_fragments(text: str) -> list[str]:
    normalized = _source_match_text(text)
    if len(normalized) < 20:
        return []
    sentence_fragments = [
        _source_match_text(part)
        for part in re.split(r"(?<=[.!?])\s+|\s+-\s+|\s+--\s+", normalized)
    ]
    fragments = [fragment for fragment in sentence_fragments if len(fragment) >= 24 and len(fragment.split()) >= 4]
    if len(fragments) >= 2:
        return _unique(fragments)
    return [normalized]


def _is_internal_analysis_observation(item: dict[str, Any]) -> bool:
    feature_name = str(item.get("feature_name") or "").lower()
    provider = str(item.get("feature_source") or "").lower()
    return feature_name in INTERNAL_ANALYSIS_FEATURES or provider in INTERNAL_ANALYSIS_PROVIDERS


def _correct_exa_visual_false_positive(
    *,
    url: str,
    text: str,
    audit_root: str,
    provider: str,
    source_class: str,
    eligibility: str,
    classification_reason: str,
) -> tuple[str, str, str]:
    if provider.lower() != "exa":
        return source_class, eligibility, classification_reason
    if source_class != "visual_internal_metric" or classification_reason != "visual_or_internal_analysis_not_market_evidence":
        return source_class, eligibility, classification_reason
    if not url or not text.strip():
        return source_class, eligibility, classification_reason
    corrected_source_class = _source_class_for_inferred_url(url, audit_root=audit_root, fallback="external_third_party")
    if corrected_source_class in {"audited_surface", "owned_surface"}:
        return corrected_source_class, "observation_only", "exa_external_product_evidence_not_internal_visual_analysis"
    return "external_third_party", "eligible_for_narrative_finding", "exa_external_product_evidence_not_internal_visual_analysis"


def _dimension_url_hints(dimension_inputs: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    urls_by_group: dict[tuple[str, str, str], set[str]] = {}
    for dimension, items in dimension_inputs.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            key = _dimension_group_key(str(dimension or ""), item)
            urls_by_group.setdefault(key, set()).add(url)
    return {key: next(iter(urls)) for key, urls in urls_by_group.items() if len(urls) == 1}


def _dimension_group_key(dimension: str, item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(dimension or ""),
        str(item.get("feature_name") or ""),
        str(item.get("feature_source") or ""),
    )


def _source_class_for_inferred_url(url: str, *, audit_root: str, fallback: str) -> str:
    host = _host(url)
    root = _root_domain(host)
    if not host:
        return fallback
    if audit_root and root == audit_root:
        return fallback if fallback in {"audited_surface", "owned_surface"} else "owned_surface"
    return "external_third_party"


def _apply_inferred_url(
    *,
    url: str,
    audit_root: str,
    source_class: str,
    eligibility: str,
    classification_reason: str,
    reason: str,
) -> tuple[str, str, str]:
    inferred_source_class = _source_class_for_inferred_url(url, audit_root=audit_root, fallback=source_class)
    if inferred_source_class == "external_third_party" and eligibility in {"requires_human_review", "observation_only"}:
        return inferred_source_class, "eligible_for_narrative_finding", reason
    if inferred_source_class in {"audited_surface", "owned_surface"} and eligibility == "requires_human_review":
        return inferred_source_class, "observation_only", reason
    if classification_reason == "owned_claim_without_url":
        return inferred_source_class, eligibility, reason
    return inferred_source_class, eligibility, classification_reason


def _snapshot_text_url_hints(snapshot: dict[str, Any]) -> list[tuple[str, str, str]]:
    hints: list[tuple[str, str, str]] = []
    for item in snapshot.get("raw_inputs") or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if source in {"web", "hyperbrowser"}:
            text = _clean_text(
                payload.get("markdown_content")
                or payload.get("content")
                or payload.get("text")
                or ""
            )
            url = str(payload.get("source_url") or payload.get("url") or payload.get("final_url") or "").strip()
            if text and url:
                hints.append((text.lower(), url, source))
        elif source == "exa":
            for collection in ("mentions", "news", "ai_visibility_results", "competitors"):
                entries = payload.get(collection)
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    url = str(entry.get("url") or "").strip()
                    text = _clean_text(
                        " ".join(
                            str(part or "")
                            for part in (
                                entry.get("title"),
                                entry.get("summary"),
                                entry.get("text"),
                                " ".join(str(value) for value in (entry.get("highlights") or [])),
                            )
                        )
                    )
                    if text and url:
                        hints.append((text.lower(), url, f"exa.{collection}"))
    return hints


def _infer_url_for_text(text: str, hints: list[tuple[str, str, str]], *, audit_root: str = "") -> str:
    needle = _source_match_text(text)
    if len(needle) < 20:
        return ""
    inferred = _infer_url_from_audited_source_windows(needle, hints, audit_root=audit_root)
    if inferred:
        return inferred
    matches = {url for haystack, url, _source in hints if needle in _source_match_text(haystack)}
    inferred = _choose_inferred_url(matches)
    if inferred:
        return inferred
    fragment_matches = [
        {url for haystack, url, _source in hints if fragment in _source_match_text(haystack)}
        for fragment in _source_match_fragments(needle)
    ]
    if len(fragment_matches) >= 2 and all(fragment_matches):
        inferred = _choose_inferred_url(set.intersection(*fragment_matches))
        if inferred:
            return inferred
        inferred = _choose_inferred_url(set().union(*fragment_matches))
        if inferred:
            return inferred
    return ""


def _infer_url_from_audited_source_windows(
    needle: str,
    hints: list[tuple[str, str, str]],
    *,
    audit_root: str,
) -> str:
    if not audit_root:
        return ""
    audited_hints = [
        (haystack, url)
        for haystack, url, source in hints
        if source in {"web", "hyperbrowser"} and _root_domain(_host(url)) == audit_root
    ]
    if not audited_hints:
        return ""
    exact_matches = {url for haystack, url in audited_hints if needle in _source_match_text(haystack)}
    inferred = _choose_inferred_url(exact_matches)
    if inferred:
        return inferred

    urls_by_window: list[set[str]] = []
    for window in _source_match_word_windows(needle):
        urls = {url for haystack, url in audited_hints if window in _source_match_text(haystack)}
        if urls:
            urls_by_window.append(urls)
    words = needle.split()
    if len(words) <= 6 and urls_by_window:
        return _choose_inferred_url(set().union(*urls_by_window))
    if len(urls_by_window) < 2:
        return ""
    intersection = set.intersection(*urls_by_window)
    if intersection:
        return _choose_inferred_url(intersection)
    return _choose_inferred_url(set().union(*urls_by_window))


def _source_match_word_windows(text: str) -> list[str]:
    words = _source_match_text(text).split()
    if len(words) < 5:
        return []
    if len(words) <= 6:
        window = " ".join(words)
        return [window] if len(window) >= 20 else []
    windows: list[str] = []
    for size in (9, 7, 5):
        if len(words) < size:
            continue
        for index in range(0, len(words) - size + 1):
            window = " ".join(words[index : index + size])
            if len(window) >= 24:
                windows.append(window)
    return _unique(windows)


def _choose_inferred_url(urls: set[str]) -> str:
    cleaned = {str(url or "").strip() for url in urls if str(url or "").strip()}
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return next(iter(cleaned))
    roots = {_root_domain(_host(url)) for url in cleaned}
    if len(roots) == 1 and next(iter(roots)):
        return sorted(cleaned, key=lambda url: (len(urlparse(url).path or ""), len(url), url))[0]
    return ""


def _source_match_text(value: Any) -> str:
    text = _clean_text(value).lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[*_`>#\[\]{}()]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _source_match_fragments(text: str) -> list[str]:
    fragments: list[str] = []
    for part in re.split(r"[,;|/]+", str(text or "")):
        fragment = _source_match_text(part)
        if len(fragment) < 16 or len(fragment.split()) < 2:
            continue
        fragments.append(fragment)
    return _unique(fragments)


def _gate_status(*, source_class: str, eligibility: str, text: str) -> str:
    if eligibility in REVIEW_ELIGIBILITIES or source_class in REVIEW_SOURCE_CLASSES:
        return "review_required"
    if eligibility in REJECTED_ELIGIBILITIES or source_class in REJECTED_SOURCE_CLASSES:
        return "rejected"
    if eligibility in ACCEPTED_ELIGIBILITIES and source_class in ACCEPTED_SOURCE_CLASSES and text.strip():
        return "accepted"
    if not text.strip():
        return "rejected"
    return "review_required"


def _observation_reason(item: Any) -> str:
    reason = str(getattr(item, "classification_reason", "") or "").strip()
    if reason:
        return reason
    if getattr(item, "eligibility", ""):
        return str(getattr(item, "eligibility"))
    if getattr(item, "source_class", ""):
        return str(getattr(item, "source_class"))
    return "unknown"


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _filter_claims(claims: list[EvidenceClaim], gate: Any) -> list[EvidenceClaim]:
    accepted_url_keys = {_url_key(item.url) for item in gate.accepted if item.url}
    unresolved_profile_url_keys = {
        _url_key(item.url)
        for item in gate.review_required
        if item.url and item.classification_reason == "same_name_external_profile_not_alias"
    }
    review_or_rejected_url_keys = {
        _url_key(item.url)
        for item in (*gate.review_required, *gate.rejected)
        if item.url
    }
    accepted_text_keys = {_text_key(item.text) for item in gate.accepted if item.text}
    accepted_url_by_text_key = {
        _text_key(item.text): item.url
        for item in gate.accepted
        if item.text and item.url
    }
    review_or_rejected_text_keys = {
        _text_key(item.text)
        for item in (*gate.review_required, *gate.rejected)
        if item.text
    }
    filtered: list[EvidenceClaim] = []
    for claim in claims:
        claim = _claim_with_inferred_url(claim, accepted_url_by_text_key)
        if _claim_rejected_by_gate(
            claim,
            accepted_url_keys=accepted_url_keys,
            unresolved_profile_url_keys=unresolved_profile_url_keys,
            review_or_rejected_url_keys=review_or_rejected_url_keys,
            accepted_text_keys=accepted_text_keys,
            review_or_rejected_text_keys=review_or_rejected_text_keys,
        ):
            filtered.append(
                EvidenceClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="noise",
                    quote=claim.quote,
                    source_id=claim.source_id,
                    source_url=claim.source_url,
                    source_type="noise",
                    surface_role=claim.surface_role,
                    entity_scope=claim.entity_scope,
                    confidence="low",
                    noise_reason=claim.noise_reason or _claim_noise_reason(claim, unresolved_profile_url_keys),
                    notes=_unique(
                        list(claim.notes)
                        + [_claim_noise_note(claim, unresolved_profile_url_keys)]
                    ),
                )
            )
            continue
        filtered.append(claim)
    return filtered


def _claim_with_inferred_url(claim: EvidenceClaim, accepted_url_by_text_key: dict[str, str]) -> EvidenceClaim:
    if claim.source_url:
        return claim
    inferred_url = accepted_url_by_text_key.get(_text_key(claim.text or claim.quote))
    if not inferred_url:
        return claim
    return EvidenceClaim(
        claim_id=claim.claim_id,
        text=claim.text,
        claim_type=claim.claim_type,
        quote=claim.quote,
        source_id=claim.source_id,
        source_url=inferred_url,
        source_type=claim.source_type,
        surface_role=claim.surface_role,
        entity_scope=claim.entity_scope,
        confidence=claim.confidence,
        freshness_days=claim.freshness_days,
        supports_blocks=list(claim.supports_blocks),
        contradicts=list(claim.contradicts),
        secondary_source_ids=list(claim.secondary_source_ids),
        secondary_source_urls=list(claim.secondary_source_urls),
        secondary_origins=list(claim.secondary_origins),
        noise_reason=claim.noise_reason,
        notes=_unique(list(claim.notes) + ["Source URL inferred by evidence vNext from same feature evidence_url."]),
    )


def _claim_rejected_by_gate(
    claim: EvidenceClaim,
    *,
    accepted_url_keys: set[str],
    unresolved_profile_url_keys: set[str],
    review_or_rejected_url_keys: set[str],
    accepted_text_keys: set[str],
    review_or_rejected_text_keys: set[str],
) -> bool:
    if claim.claim_type == "noise" or claim.source_type == "noise":
        return False
    claim_url_key = _url_key(claim.source_url)
    claim_text_key = _text_key(claim.text or claim.quote)

    if claim.source_type.startswith("owned_") and claim.claim_type != "feature_evidence":
        return False
    if claim.claim_type == "feature_evidence" and not claim.source_url:
        return True
    if claim_url_key and claim_url_key in unresolved_profile_url_keys:
        return True
    if claim_url_key and claim_url_key in accepted_url_keys:
        return False
    if claim_text_key and claim_text_key in accepted_text_keys:
        return False
    if claim_url_key and claim_url_key in review_or_rejected_url_keys:
        return True
    if claim_text_key and claim_text_key in review_or_rejected_text_keys:
        return True
    if claim.source_type in {"unknown", "third_party_context", "third_party_review", "press_founder"}:
        return claim.claim_type in {"unknown", "feature_evidence"} and not claim.source_url
    return False


def _claim_noise_reason(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "unresolved_external_profile_source"
    return "evidence_vnext_gate_rejected"


def _claim_noise_note(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "Quarantined by evidence vNext because source URL is an unresolved same-name external profile."
    return "Rejected by evidence vNext gate."


def _vnext_gaps(gate: Any, claims: list[EvidenceClaim]) -> list[str]:
    gaps: list[str] = []
    if gate.review_required:
        gaps.append("Evidence vNext found review-required evidence; excluded from vNext interpretation.")
    if gate.rejected and not any(claim.claim_type != "noise" for claim in claims):
        gaps.append("Evidence vNext rejected all interpretation candidates.")
    return gaps


def _vnext_warnings(gate: Any) -> list[str]:
    warnings: list[str] = []
    if gate.review_required:
        warnings.append("evidence_vnext_review_required")
    if gate.rejected:
        warnings.append("evidence_vnext_rejected_candidates")
    return warnings


def _append_limit(existing: str, addition: str) -> str:
    existing = str(existing or "").strip()
    addition = str(addition or "").strip()
    if not existing:
        return addition
    if not addition or addition in existing:
        return existing
    return f"{existing} {addition}"


def _url_key(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).strip("/").removeprefix("www.")
    path = parsed.path.strip("/")
    if not parsed.netloc and "/" in parsed.path:
        host, _, path = parsed.path.partition("/")
        host = host.strip("/").removeprefix("www.")
        path = path.strip("/")
    return f"{host}/{path}".rstrip("/")


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _root_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "")


def _text_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
