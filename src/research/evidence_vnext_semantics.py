"""Heuristic semantic assessment for evidence vNext."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse


SEMANTIC_MATERIAL_CLASSES = {
    "owned_brand_evidence",
    "customer_case",
    "market_news",
    "direct_brand_evidence",
}
SEMANTIC_WEAK_CLASSES = {
    "competitor_comparison",
    "tangential",
    "wrong_entity",
}

SEMANTIC_BRAND_TOKEN_STOPWORDS = {
    "www",
    "com",
    "net",
    "org",
    "io",
    "ai",
    "app",
    "co",
    "inc",
    "llc",
    "ltd",
}
class _SourceObservationProtocol(Protocol):
    observation_id: str
    text: str
    url: str
    provider: str
    feature_name: str
    source_class: str
    eligibility: str
    gate_status: str
    classification_reason: str


class _EvidenceVNextPacketProtocol(Protocol):
    brand_name: str
    url: str
    observations: tuple[Any, ...]

    @property
    def accepted(self) -> tuple[Any, ...]: ...


def build_evidence_vnext_semantic_assessment(packet: _EvidenceVNextPacketProtocol) -> dict[str, Any]:
    """Classify accepted evidence by semantic usefulness without changing the gate."""

    assessments = tuple(_semantic_assessment_for_observation(packet, item) for item in packet.observations)
    class_counts: dict[str, int] = {}
    materiality_counts: dict[str, int] = {}
    entity_fit_counts: dict[str, int] = {}
    accepted_weak = 0
    accepted_material = 0
    for item in assessments:
        class_counts[item.semantic_class] = class_counts.get(item.semantic_class, 0) + 1
        materiality_counts[item.materiality] = materiality_counts.get(item.materiality, 0) + 1
        entity_fit_counts[item.entity_fit] = entity_fit_counts.get(item.entity_fit, 0) + 1
        if item.gate_status == "accepted" and item.semantic_class in SEMANTIC_WEAK_CLASSES:
            accepted_weak += 1
        if item.gate_status == "accepted" and item.semantic_class in SEMANTIC_MATERIAL_CLASSES:
            accepted_material += 1
    accepted_count = len(packet.accepted)
    return {
        "version": "evidence_vnext_semantic_assessment_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "model_effect": False,
        "classifier": "heuristic_shadow_v0",
        "assessments": [item.to_dict() for item in assessments],
        "summary": {
            "assessment_count": len(assessments),
            "accepted_count": accepted_count,
            "accepted_material_count": accepted_material,
            "accepted_weak_count": accepted_weak,
            "accepted_material_rate": _safe_ratio(accepted_material, accepted_count),
            "accepted_weak_rate": _safe_ratio(accepted_weak, accepted_count),
            "semantic_class_counts": dict(sorted(class_counts.items())),
            "materiality_counts": dict(sorted(materiality_counts.items())),
            "entity_fit_counts": dict(sorted(entity_fit_counts.items())),
        },
    }


def _semantic_assessment_for_observation(
    packet: _EvidenceVNextPacketProtocol,
    item: _SourceObservationProtocol,
) -> Any:
    if item.gate_status != "accepted":
        return _semantic_result(
            item,
            semantic_class="contract_blocked",
            entity_fit="blocked",
            materiality="not_applicable",
            confidence=1.0,
            reason_codes=(_observation_reason(item),),
        )

    brand_tokens = _semantic_brand_tokens(packet.brand_name, packet.url)
    haystack = _semantic_haystack(item)
    url_lower = item.url.lower()
    entity_fit = _semantic_entity_fit(haystack, brand_tokens=brand_tokens, audit_url=packet.url, source_url=item.url)

    if _is_placeholder_social_profile(item):
        return _semantic_result(
            item,
            semantic_class="wrong_entity",
            entity_fit="wrong_entity",
            materiality="not_applicable",
            confidence=0.9,
            reason_codes=("social_profile_placeholder_only",),
        )

    comparison_text = f"{item.text} {item.feature_name} {item.classification_reason}".lower()
    if item.source_class == "competitor_comparison" or _contains_any(
        comparison_text,
        ("alternative", "alternatives", "competitor", "competitors", "best tools", "compared"),
    ):
        return _semantic_result(
            item,
            semantic_class="competitor_comparison",
            entity_fit=entity_fit,
            materiality="low",
            confidence=0.75,
            reason_codes=("comparison_or_alternatives_surface",),
        )

    if item.source_class in {"audited_surface", "owned_surface"}:
        return _semantic_result(
            item,
            semantic_class="owned_brand_evidence",
            entity_fit="strong",
            materiality="high",
            confidence=0.95,
            reason_codes=("owned_or_audited_source",),
        )

    if entity_fit == "missing":
        return _semantic_result(
            item,
            semantic_class="tangential",
            entity_fit=entity_fit,
            materiality="low",
            confidence=0.75,
            reason_codes=("brand_entity_not_visible_in_text_or_url",),
        )

    if "github.com" in url_lower and entity_fit == "strong":
        return _semantic_result(
            item,
            semantic_class="owned_brand_evidence",
            entity_fit=entity_fit,
            materiality="high",
            confidence=0.85,
            reason_codes=("official_repository_signal",),
        )

    if _contains_any(haystack, ("case study", "case-stud", "customer story", "/customers/", "customers/")):
        return _semantic_result(
            item,
            semantic_class="customer_case",
            entity_fit=entity_fit,
            materiality="high",
            confidence=0.85,
            reason_codes=("customer_or_case_study_surface",),
        )

    if _contains_any(
        haystack,
        (
            "announces",
            "announced",
            "announcement",
            "releases",
            "released",
            "launches",
            "launched",
            "ships",
            "shipped",
            "funding",
            "raises",
            "raised",
            "partnership",
            "collaboration",
            "acquires",
            "acquired",
        ),
    ):
        return _semantic_result(
            item,
            semantic_class="market_news",
            entity_fit=entity_fit,
            materiality="medium",
            confidence=0.8,
            reason_codes=("market_news_or_press_signal",),
        )

    if "github.com" in url_lower and entity_fit != "strong":
        return _semantic_result(
            item,
            semantic_class="tangential",
            entity_fit=entity_fit,
            materiality="low",
            confidence=0.7,
            reason_codes=("repository_without_strong_brand_fit",),
        )

    return _semantic_result(
        item,
        semantic_class="direct_brand_evidence",
        entity_fit=entity_fit,
        materiality="medium" if entity_fit == "strong" else "low",
        confidence=0.7,
        reason_codes=("direct_external_brand_surface",),
    )


def _semantic_result(
    item: _SourceObservationProtocol,
    *,
    semantic_class: str,
    entity_fit: str,
    materiality: str,
    confidence: float,
    reason_codes: tuple[str, ...],
) -> Any:
    return SemanticEvidenceAssessment(
        observation_id=item.observation_id,
        url=item.url,
        provider=item.provider,
        gate_status=item.gate_status,
        semantic_class=semantic_class,
        entity_fit=entity_fit,
        materiality=materiality,
        confidence=confidence,
        reason_codes=reason_codes,
        text_preview=_clean_text(item.text)[:180],
    )


def _semantic_haystack(item: _SourceObservationProtocol) -> str:
    return f"{item.url} {item.text} {item.feature_name} {item.classification_reason}".lower()


def _semantic_brand_tokens(brand_name: str, brand_url: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in re.split(r"[^a-z0-9]+", str(brand_name or "").lower()):
        if len(token) >= 3 and token not in SEMANTIC_BRAND_TOKEN_STOPWORDS:
            tokens.append(token)
    root = _root_domain(_host(brand_url))
    if root:
        domain_token = root.split(".")[0]
        if len(domain_token) >= 3 and domain_token not in SEMANTIC_BRAND_TOKEN_STOPWORDS:
            tokens.append(domain_token)
    return tuple(_unique(tokens))


def _semantic_entity_fit(
    haystack: str,
    *,
    brand_tokens: tuple[str, ...],
    audit_url: str,
    source_url: str,
) -> str:
    audit_root = _root_domain(_host(audit_url))
    source_root = _root_domain(_host(source_url))
    if audit_root and source_root == audit_root:
        return "strong"
    haystack_tokens = set(re.findall(r"[a-z0-9]+", haystack.lower()))
    visible_tokens = [token for token in brand_tokens if token and token in haystack_tokens]
    if len(visible_tokens) >= 1:
        return "strong"
    return "missing"


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _is_placeholder_social_profile(item: _SourceObservationProtocol) -> bool:
    if item.provider != "social_scrape" and item.feature_name != "social_footprint":
        return False
    text = _clean_text(item.text).lower()
    return bool(re.fullmatch(r"[a-z0-9_. -]+ profile candidate", text))


def _observation_reason(item: _SourceObservationProtocol) -> str:
    return item.classification_reason or item.eligibility or item.source_class or "unknown"


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _host(url: str) -> str:
    text = str(url or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return (parsed.netloc or parsed.path).strip("/").removeprefix("www.")


def _root_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "")
@dataclass(frozen=True, slots=True)
class SemanticEvidenceAssessment:
    observation_id: str
    url: str
    provider: str
    gate_status: str
    semantic_class: str
    entity_fit: str
    materiality: str
    confidence: float
    reason_codes: tuple[str, ...] = ()
    text_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "url": self.url,
            "provider": self.provider,
            "gate_status": self.gate_status,
            "semantic_class": self.semantic_class,
            "entity_fit": self.entity_fit,
            "materiality": self.materiality,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "text_preview": self.text_preview,
        }
