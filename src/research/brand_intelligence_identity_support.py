"""Private helper support for Brand Intelligence identity resolution."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from src.research.brand_intelligence import (
    BrandIdentityBakeoffCase,
    BrandIdentityBakeoffResult,
    BrandIdentityCandidate,
    BrandIdentityResolution,
    BrandIdentitySignal,
    BrandSeed,
    ResolvedBrandEntity,
)


def _identity_resolution(
    seed: BrandSeed,
    status: str,
    candidates: list[BrandIdentityCandidate],
    *,
    selected: BrandIdentityCandidate | None,
    missing: list[str] | None = None,
    limitations: list[str] | None = None,
) -> BrandIdentityResolution:
    return BrandIdentityResolution(
        input_seed=seed,
        status=status,
        candidates=candidates,
        selected_candidate=selected,
        missing=_unique(missing or []),
        limitations=_unique(limitations or []),
    )


def _candidates_from_signals(signals: list[BrandIdentitySignal]) -> list[BrandIdentityCandidate]:
    grouped: dict[str, list[BrandIdentitySignal]] = {}
    for signal in signals:
        key = _normalize_name(signal.candidate_name)
        if not key:
            continue
        grouped.setdefault(key, []).append(signal)
    candidates = [_candidate_from_signal_group(items) for items in grouped.values()]
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)


def _candidate_from_signal_group(signals: list[BrandIdentitySignal]) -> BrandIdentityCandidate:
    best = max(signals, key=lambda item: item.confidence)
    avg_confidence = sum(item.confidence for item in signals) / max(1, len(signals))
    corroboration_bonus = min(0.08, max(0, len({item.source for item in signals}) - 1) * 0.04)
    confidence = round(min(0.99, max(best.confidence, avg_confidence + corroboration_bonus)), 4)
    limitations: list[str] = []
    signal_names = {item.signal for item in signals}
    if "subdomain_surface" in signal_names or "domain_family_match" in signal_names:
        limitations.append("subdomain_surface_needs_parent_validation")
    if "ambiguous_name" in signal_names:
        limitations.extend(["name_only_ambiguous_entity", "requires_external_entity_resolution"])
    if "url_seed" in signal_names:
        limitations.extend(["url_seed_not_verified_as_brand", "requires_multichannel_validation"])
    return BrandIdentityCandidate(
        name=best.candidate_name,
        entity_type=_strongest_entity_type(signals),
        confidence=confidence,
        canonical_url=next((item.canonical_url for item in signals if item.canonical_url), ""),
        parent_brand=next((item.parent_brand for item in signals if item.parent_brand), None),
        parent_url=next((item.parent_url for item in signals if item.parent_url), None),
        product_name=next((item.product_name for item in signals if item.product_name), None),
        product_url=next((item.product_url for item in signals if item.product_url), None),
        evidence=[
            _evidence(item.source, item.signal or "identity_signal", item.value or item.candidate_name, item.confidence)
            for item in signals
        ],
        limitations=_unique(limitations),
    )


def _strongest_entity_type(signals: list[BrandIdentitySignal]) -> str:
    typed = [item for item in signals if item.entity_type != "unknown"]
    if not typed:
        return "unknown"
    return max(typed, key=lambda item: item.confidence).entity_type


def _resolution_status_for_candidate(candidate: BrandIdentityCandidate) -> str:
    if candidate.confidence >= 0.82 and candidate.entity_type != "unknown" and not candidate.limitations:
        return "resolved"
    if candidate.confidence >= 0.2:
        return "provisional"
    return "unresolved"


def _entity_from_identity_resolution(identity: BrandIdentityResolution) -> ResolvedBrandEntity:
    seed = identity.input_seed
    candidate = identity.selected_candidate
    if candidate is None:
        return _unresolved(seed, identity.limitations[0] if identity.limitations else "insufficient_identity_signal", confidence=0.1)
    return ResolvedBrandEntity(
        requested_value=(seed.value or "").strip(),
        requested_kind=seed.kind,
        resolution_status=identity.status,
        resolved_name=candidate.name,
        entity_type=candidate.entity_type,
        analysis_mode=_analysis_mode_for_candidate(identity.status, candidate),
        confidence=candidate.confidence,
        canonical_url=candidate.canonical_url,
        parent_brand=candidate.parent_brand,
        parent_url=candidate.parent_url,
        product_name=candidate.product_name,
        product_url=candidate.product_url,
        evidence=list(candidate.evidence),
        limitations=_unique(list(candidate.limitations) + list(identity.limitations)),
    )


def _analysis_mode_for_candidate(status: str, candidate: BrandIdentityCandidate) -> str:
    if status == "unresolved":
        return "unresolved_seed"
    if candidate.entity_type == "product" and candidate.parent_brand:
        return "product_with_parent"
    if candidate.entity_type == "ecosystem":
        return "ecosystem"
    if candidate.entity_type == "company" and candidate.confidence >= 0.8:
        return "company_brand_with_products" if candidate.name == "LangChain" else "company_brand"
    if "subdomain_surface_needs_parent_validation" in candidate.limitations:
        return "subdomain_or_lab_surface"
    if "name_only_ambiguous_entity" in candidate.limitations:
        return "ambiguous_name"
    return "url_seed_unverified_brand"


def _unresolved(seed: BrandSeed, reason: str, *, confidence: float) -> ResolvedBrandEntity:
    value = (seed.value or "").strip()
    return ResolvedBrandEntity(
        requested_value=value,
        requested_kind=seed.kind,
        resolution_status="unresolved",
        resolved_name=(seed.provided_name or value or "Unknown").strip(),
        entity_type="unknown",
        analysis_mode="unresolved_seed",
        confidence=confidence,
        evidence=[_evidence("input", reason, value, confidence)],
        limitations=[reason, "requires_multichannel_validation"],
    )


def _evidence(source: str, signal: str, value: str, confidence: float) -> dict[str, object]:
    return {"source": source, "signal": signal, "value": value, "confidence": confidence}


def _normalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _label_from_host(host: str) -> str:
    label = (host or "").split(".")[0].replace("-", " ")
    known = {"chatgpt": "ChatGPT", "langchain": "LangChain", "naturaumana": "Natura Umana"}
    return known.get(label.lower(), label.title() if label else "")


def _clean_candidate_name(value: str) -> str:
    cleaned = str(value or "").strip()
    for separator in (" | ", " - ", " – ", " — "):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned


def _candidate_from_search_title(title: str) -> str:
    value = _clean_candidate_name(title)
    for prefix in ("official ", "about "):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip()
    return value


def _parent_from_text(text: str) -> str | None:
    low = (text or "").lower()
    if "openai" in low:
        return "OpenAI"
    if "anthropic" in low:
        return "Anthropic"
    return None


def _known_parent_url(parent: str | None) -> str | None:
    if parent == "OpenAI":
        return "https://openai.com"
    if parent == "Anthropic":
        return "https://anthropic.com"
    return None


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _external_result_text(result: dict[str, object]) -> str:
    return " ".join(
        str(result.get(key) or "")
        for key in ("url", "title", "text", "summary", "snippet")
    )


def _external_result_matches_entity(
    text: str,
    *,
    entity: ResolvedBrandEntity,
    seed_url: str = "",
    brand: str = "",
) -> bool:
    haystack = _match_text(text)
    tokens = set(_match_tokens(haystack))
    seed_host = _host(seed_url or entity.canonical_url)
    if seed_host and seed_host in haystack:
        return True

    anchors = _entity_match_anchors(entity, brand=brand)
    if entity.resolution_status != "resolved" and entity.requested_kind != "url":
        return any(" " in anchor and anchor in haystack for anchor in anchors)
    return any((anchor in haystack if " " in anchor else anchor in tokens) for anchor in anchors)


def _near_entity_token_collision(text: str, *, entity: ResolvedBrandEntity, brand: str = "") -> bool:
    tokens = set(_match_tokens(_match_text(text)))
    anchors = [anchor for anchor in _entity_match_anchors(entity, brand=brand) if " " not in anchor and len(anchor) >= 5]
    if not anchors or any(anchor in tokens for anchor in anchors):
        return False
    for anchor in anchors:
        for token in tokens:
            if len(token) < 5:
                continue
            if token.startswith(anchor) or anchor.startswith(token):
                return True
            if abs(len(token) - len(anchor)) <= 2 and _edit_distance_at_most(token, anchor, 2):
                return True
    return False


def _entity_match_anchors(entity: ResolvedBrandEntity, *, brand: str = "") -> list[str]:
    values = [
        brand,
        entity.resolved_name,
        entity.product_name or "",
        entity.parent_brand or "",
        _label_from_host(_host(entity.canonical_url)),
    ]
    anchors = [_match_text(value) for value in values if value]
    return _unique([anchor for anchor in anchors if len(anchor) >= 4])


def _match_text(value: str) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _match_tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in {"www", "com", "app", "ai", "io", "co", "inc", "the"}
    ]


def _edit_distance_at_most(left: str, right: str, limit: int) -> bool:
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        row_min = i
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _looks_like_placeholder(root: str) -> bool:
    return root in {"example.com", "invalid", "test", "localhost"} or root.endswith(".invalid")


def _is_ambiguous_name(value: str) -> bool:
    return _normalize_name(value) in {"mercury", "atlas", "nova", "base", "linear", "frontier"}


def _host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2:] == ["co", "uk"] and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _coerce_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _source_url_key(value: str) -> str:
    normalized = _normalize_url(value)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    return f"https://{host}{path}"


def _title_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _evaluate_identity_case(case: BrandIdentityBakeoffCase) -> BrandIdentityBakeoffResult:
    from src.research.brand_intelligence_identity import resolve_brand_identity_from_signals

    resolution = resolve_brand_identity_from_signals(case.seed, case.signals)
    selected = resolution.selected_candidate
    actual_name = selected.name if selected else ""
    status_pass = resolution.status == case.expected_status
    name_pass = not case.expected_name or _normalize_name(actual_name) == _normalize_name(case.expected_name)
    passed = status_pass and name_pass
    misresolved = case.expected_status != "resolved" and resolution.status == "resolved"
    return BrandIdentityBakeoffResult(
        case_id=case.case_id,
        expected_status=case.expected_status,
        actual_status=resolution.status,
        expected_name=case.expected_name,
        actual_name=actual_name,
        passed=passed,
        known_case=case.known_case,
        misresolved=misresolved,
        resolution=resolution,
    )
