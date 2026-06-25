"""Canonical public evidence bundle for downstream Brand3 interpreters.

Brand Audit owns acquisition. This module adapts a persisted audit snapshot into
one reusable evidence bundle so Magnetism Scanner and future TLDR interpreters
read the same public evidence instead of scraping or selecting their own
independent inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from urllib.parse import urlparse

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import (
    StrategicEvidencePacket,
    build_strategic_evidence_packet,
)


MAX_PUBLIC_MENTIONS = 8
MAX_FALLBACK_LINES = 80
MAX_FALLBACK_MARKDOWN_CHARS = 8000
MIN_USABLE_QUOTE_LENGTH = 6
SOURCE_WEB = "web"
SOURCE_VISUAL_SIGNATURE = "visual_signature"
OWNED_EVIDENCE_SOURCE_TYPES = {"owned", "social"}
UNUSABLE_QUOTE_METADATA_MARKERS = (
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
)
UNUSABLE_QUOTE_CONTENT_MARKERS = (
    "/news/",
    "graphql api",
    "product roadmap",
    "__next_data__",
)


@dataclass
class RawInputContext:
    sources: list[str]
    fallback_markdown: str = ""
    visual_semantics: dict[str, Any] = field(
        default_factory=lambda: {"status": "not_detected", "data": {}}
    )
    web_page_roles: list[str] = field(default_factory=list)
    extraction_quality_report: dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalBrandEvidence:
    """Shared evidence view derived from a Brand Audit run snapshot."""

    brand_name: str
    url: str
    run_id: int | None
    strategic_packet: StrategicEvidencePacket
    interpreter_text: str
    visual_semantics: dict[str, Any]
    public_mentions: list[str] = field(default_factory=list)
    raw_input_sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    data_quality: Any = None
    derived_evidence_count: int = 0
    raw_input_count: int = 0
    evidence_item_count: int = 0
    feature_count: int = 0
    web_page_roles: list[str] = field(default_factory=list)
    extraction_quality_report: dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        strategic_summary = self.strategic_packet.to_summary()
        evidence_quality = _evidence_quality_summary(
            interpreter_text=self.interpreter_text,
            raw_input_count=self.raw_input_count,
            group_counts=strategic_summary.get("group_counts") or {},
            source_counts=strategic_summary.get("source_counts") or {},
            visual_semantics=self.visual_semantics,
        )
        proof_lines = self.strategic_packet.groups.get("proof_points", [])
        return {
            "source": "brand_audit_snapshot",
            "source_label": "Canonical Brand Audit evidence",
            "evidence_basis": "Shared Brand Audit snapshot reused by Brand3 downstream lenses.",
            "run_id": self.run_id,
            "raw_input_count": self.raw_input_count,
            "evidence_item_count": self.evidence_item_count,
            "derived_evidence_count": self.derived_evidence_count,
            "feature_count": self.feature_count,
            "sources": self.raw_input_sources,
            "data_quality": self.data_quality,
            "web_page_roles": self.web_page_roles,
            "extraction_quality_report": self.extraction_quality_report,
            "evidence_quality": evidence_quality,
            "strategic_group_counts": strategic_summary.get("group_counts"),
            "strategic_source_counts": strategic_summary.get("source_counts"),
            "strategic_rejected_count": strategic_summary.get("rejected_count"),
            "strategic_rejected_reason_counts": strategic_summary.get("rejected_reason_counts"),
            "strategic_warnings": strategic_summary.get("warnings"),
            "proof_support": _proof_support_summary(proof_lines),
            "value_policy": (
                "Brand Audit owns collection; downstream tools only interpret "
                "this shared evidence bundle."
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "brand_name": self.brand_name,
            "url": self.url,
            "interpreter_text": self.interpreter_text,
            "public_mentions": self.public_mentions,
            "visual_semantics": self.visual_semantics,
            "limitations": self.limitations,
            "strategic_packet": self.strategic_packet.to_dict(),
        }


KEY_STRATEGIC_GROUPS = ("product_offer", "audience", "outcome")
OWNED_STRATEGIC_SOURCE_TYPES = ("owned_raw", "owned", "social")


def _proof_support_summary(proof_lines: list[Any]) -> dict[str, Any]:
    if not proof_lines:
        return {
            "status": "not_detected",
            "count": 0,
            "evidence": [],
            "reading": "No public proof signals were available in the strategic evidence packet.",
        }

    return {
        "status": "observed",
        "count": len(proof_lines),
        "evidence": [line.to_dict() for line in proof_lines[:3]],
        "reading": (
            "Observed public proof signals can support credibility, but they do not define "
            "mission, personality, values, or brand idea."
        ),
    }


def _resolve_collect_evidences():
    """Return the monkeypatchable collect function used by this module.

    Tests patch ``src.reports.canonical_evidence.collect_evidences``, so this indirection
    preserves that surface while keeping the implementation in a separate module.
    """
    try:
        import importlib

        module = importlib.import_module("src.reports.canonical_evidence")
        overridden = getattr(module, "collect_evidences", None)
        if callable(overridden) and overridden is not collect_evidences:
            return overridden
    except Exception:
        return collect_evidences
    return collect_evidences


def _evidence_quality_summary(
    *,
    interpreter_text: str,
    raw_input_count: int,
    group_counts: dict[str, Any],
    source_counts: dict[str, Any],
    visual_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Summarize whether the canonical packet is useful for downstream lenses."""
    normalized_group_counts = {
        str(key): int(value or 0) for key, value in group_counts.items()
    }
    missing_key_groups = [
        group for group in KEY_STRATEGIC_GROUPS if not normalized_group_counts.get(group)
    ]
    usable_group_count = len(
        [count for count in normalized_group_counts.values() if count > 0]
    )
    owned_source_count = sum(
        int(source_counts.get(source_type) or 0)
        for source_type in OWNED_STRATEGIC_SOURCE_TYPES
    )
    visual_detected = visual_semantics.get("status") == "detected"

    reasons: list[str] = []
    if not interpreter_text.strip():
        reasons.append("no_interpreter_text")
    if raw_input_count <= 0:
        reasons.append("no_raw_inputs")
    if usable_group_count <= 0:
        reasons.append("no_strategic_groups")
    if not normalized_group_counts.get("product_offer"):
        reasons.append("no_product_offer")
    if not normalized_group_counts.get("audience"):
        reasons.append("no_audience")
    if not normalized_group_counts.get("outcome"):
        reasons.append("no_outcome")
    if owned_source_count <= 0:
        reasons.append("no_owned_evidence")

    if "no_interpreter_text" in reasons or "no_strategic_groups" in reasons:
        status = "insufficient"
    elif not normalized_group_counts.get("product_offer"):
        status = "weak"
    elif (
        all(group not in missing_key_groups for group in KEY_STRATEGIC_GROUPS)
        and owned_source_count > 0
    ):
        status = "strong"
    elif normalized_group_counts.get("product_offer") and (
        normalized_group_counts.get("audience") or normalized_group_counts.get("outcome")
    ):
        status = "usable"
    else:
        status = "weak"

    return {
        "status": status,
        "reasons": reasons,
        "key_groups": list(KEY_STRATEGIC_GROUPS),
        "missing_key_groups": missing_key_groups,
        "usable_group_count": usable_group_count,
        "owned_source_count": owned_source_count,
        "visual_semantics_detected": visual_detected,
    }


def build_canonical_brand_evidence(snapshot: dict[str, Any]) -> CanonicalBrandEvidence:
    """Build the shared evidence bundle from a persisted Brand Audit snapshot."""
    run = snapshot.get("run") or {}
    strategic_packet = build_strategic_evidence_packet(snapshot)
    evidences = _resolve_collect_evidences()(snapshot)
    raw_inputs = snapshot.get("raw_inputs") or []
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    raw_input_context = _raw_input_context(raw_inputs)

    interpreter_text = strategic_packet.to_interpreter_text() or _fallback_evidence_text(
        evidences, raw_input_context.fallback_markdown
    )
    mentions = _public_mentions(strategic_packet)

    return CanonicalBrandEvidence(
        brand_name=str(run.get("brand_name") or "Unknown Brand"),
        url=str(run.get("url") or "manual"),
        run_id=run.get("id"),
        strategic_packet=strategic_packet,
        interpreter_text=interpreter_text,
        visual_semantics=raw_input_context.visual_semantics,
        public_mentions=mentions,
        raw_input_sources=raw_input_context.sources,
        limitations=_snapshot_limitations(snapshot),
        data_quality=data_quality,
        derived_evidence_count=len(evidences),
        raw_input_count=len(raw_inputs),
        evidence_item_count=len(snapshot.get("evidence_items") or []),
        feature_count=len(snapshot.get("features") or []),
        web_page_roles=raw_input_context.web_page_roles,
        extraction_quality_report=raw_input_context.extraction_quality_report,
    )


def _public_mentions(strategic_packet: StrategicEvidencePacket) -> list[str]:
    mentions: list[str] = []
    seen: set[str] = set()
    for group in ("proof_points", "third_party_context"):
        for line in strategic_packet.groups.get(group, []):
            text = line.text.strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                mentions.append(text)
            if len(mentions) >= MAX_PUBLIC_MENTIONS:
                return mentions
    return mentions


def _raw_input_context(raw_inputs: list[dict[str, Any]]) -> RawInputContext:
    sources = sorted(
        {str(item.get("source")) for item in raw_inputs if item.get("source")}
    )
    fallback_markdown = ""
    visual_semantics: dict[str, Any] = {"status": "not_detected", "data": {}}
    web_pages: list[dict[str, Any]] = []

    for raw_input in reversed(raw_inputs):
        source = raw_input.get("source")
        payload = raw_input.get("payload") or {}

        if source == SOURCE_WEB:
            markdown = str(payload.get("markdown_content") or payload.get("content") or "")
            page_url = str(
                payload.get("canonical_url")
                or payload.get("url")
                or payload.get("page_url")
                or ""
            )
            title = str(payload.get("title") or "")
            seen_urls: set[str] = set()
            primary_text = _primary_web_page_text(markdown)
            if markdown or page_url or title:
                web_pages.append(
                    {
                        "url": page_url,
                        "title": title,
                        "text": primary_text,
                        "role": _infer_page_role(page_url, title, primary_text),
                    }
                )
                if page_url:
                    seen_urls.add(page_url.rstrip("/"))
            for page in _embedded_web_subpages(markdown):
                normalized_url = str(page.get("url") or "").rstrip("/")
                if normalized_url and normalized_url in seen_urls:
                    continue
                if normalized_url:
                    seen_urls.add(normalized_url)
                web_pages.append(page)
            for fallback_url in payload.get("owned_fallback_urls") or []:
                fallback_url = str(fallback_url or "")
                normalized_url = fallback_url.rstrip("/")
                if not fallback_url or normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                web_pages.append(
                    {
                        "url": fallback_url,
                        "title": "",
                        "text": "",
                        "role": _infer_page_role(fallback_url),
                    }
                )
            if not fallback_markdown:
                fallback_markdown = markdown

        if (
            source == SOURCE_VISUAL_SIGNATURE
            and visual_semantics["status"] == "not_detected"
        ):
            semantics = payload.get("semantics")
            if semantics:
                visual_semantics = {"status": "detected", "data": semantics}
                continue
            signature = payload.get("signature") or {}
            if isinstance(signature, dict) and signature.get("semantics"):
                visual_semantics = {
                    "status": "detected",
                    "data": signature["semantics"],
                }

    page_role_set = {page["role"] for page in web_pages if page.get("role")}
    page_roles = [role for role in PAGE_ROLE_ORDER if role in page_role_set]
    return RawInputContext(
        sources=sources,
        fallback_markdown=fallback_markdown[:MAX_FALLBACK_MARKDOWN_CHARS],
        visual_semantics=visual_semantics,
        web_page_roles=page_roles,
        extraction_quality_report=_build_extraction_quality_report(web_pages),
    )


_EMBEDDED_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)


def _primary_web_page_text(markdown: str) -> str:
    match = _EMBEDDED_SUBPAGE_RE.search(markdown or "")
    if not match:
        return markdown
    return markdown[: match.start()].strip(" -\n")


def _embedded_web_subpages(markdown: str) -> list[dict[str, Any]]:
    matches = list(_EMBEDDED_SUBPAGE_RE.finditer(markdown or ""))
    pages: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        page_url = match.group("url").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        text = (markdown[start:end] or "").strip(" -\n")
        if not page_url and not text:
            continue
        pages.append(
            {
                "url": page_url,
                "title": "",
                "text": text,
                "role": _infer_page_role(page_url, text=text),
            }
        )
    return pages


PAGE_ROLE_ORDER = (
    "homepage",
    "product",
    "solutions",
    "pricing",
    "customers",
    "case_studies",
    "reviews",
    "testimonials",
    "trust",
    "docs",
    "about",
    "careers",
    "blog",
    "unknown",
)
CORE_PAGE_ROLES = ("homepage", "product", "solutions", "about")
PROOF_PAGE_ROLES = ("customers", "case_studies", "reviews", "testimonials")
TRUST_PAGE_ROLES = ("trust",)


def _is_localized_homepage_path(path: str) -> bool:
    cleaned = (path or "").strip("/").lower()
    if not cleaned:
        return False
    parts = cleaned.split("/")
    if len(parts) != 1:
        return False
    locale = parts[0]
    return bool(re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", locale))


def _infer_page_role(url: str, title: str = "", text: str = "") -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}" if url else "")
    path = (parsed.path or "/").strip().lower()
    combined = f"{url} {title} {text[:500]}".lower()

    if path in {"", "/"} or _is_localized_homepage_path(path):
        return "homepage"
    if any(marker in path for marker in ("/pricing", "/plans", "/price")):
        return "pricing"
    if any(marker in path for marker in ("/customers", "/customer", "/clients", "/client", "/clientes", "/cliente")):
        return "customers"
    if any(marker in path for marker in ("/case-studies", "/case_studies", "/case-study", "/stories", "/success-stories", "/casos", "/caso-de-exito", "/casos-de-exito")):
        return "case_studies"
    if any(marker in path for marker in ("/reviews", "/review", "/ratings", "/resenas", "/reseñas", "/opiniones")):
        return "reviews"
    if any(marker in path for marker in ("/testimonials", "/testimonial", "/testimonios", "/testimonio")):
        return "testimonials"
    if any(marker in path for marker in ("/security", "/trust", "/privacy", "/compliance")):
        return "trust"
    if any(marker in path for marker in ("/docs", "/documentation", "/developers", "/api")):
        return "docs"
    if any(marker in path for marker in ("/about", "/company", "/manifesto")):
        return "about"
    if any(marker in path for marker in ("/careers", "/jobs", "/hiring")):
        return "careers"
    if any(marker in path for marker in ("/blog", "/news", "/resources", "/articles")):
        return "blog"
    if any(marker in path for marker in ("/product", "/products", "/platform", "/features")):
        return "product"
    if any(marker in path for marker in ("/solutions", "/use-cases", "/use_cases", "/industries")):
        return "solutions"
    if any(marker in combined for marker in ("platform", "product", "features", "software", "api")):
        return "product"
    if any(marker in combined for marker in ("solutions", "use cases", "for teams", "for enterprise")):
        return "solutions"
    return "unknown"


def _build_extraction_quality_report(web_pages: list[dict[str, Any]]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    total_text_chars = 0
    for page in web_pages:
        role = str(page.get("role") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
        total_text_chars += len(str(page.get("text") or "").strip())

    roles = [role for role in PAGE_ROLE_ORDER if role_counts.get(role)]
    missing_core_roles = [role for role in CORE_PAGE_ROLES if not role_counts.get(role)]
    missing_proof_roles = [role for role in PROOF_PAGE_ROLES if not role_counts.get(role)]

    reasons: list[str] = []
    if not web_pages:
        reasons.append("no_owned_web_pages")
    if not role_counts.get("homepage"):
        reasons.append("missing_homepage")
    if not (role_counts.get("product") or role_counts.get("solutions")):
        reasons.append("missing_product_or_solution_page")
    if not role_counts.get("about"):
        reasons.append("missing_about_page")
    if not any(role_counts.get(role) for role in PROOF_PAGE_ROLES):
        reasons.append("missing_customer_proof_page")
    if total_text_chars < 1200:
        reasons.append("low_owned_text_volume")

    if "no_owned_web_pages" in reasons:
        status = "capture_gap"
        likely_failure_cause = "no_owned_web_pages"
    elif "missing_product_or_solution_page" in reasons and total_text_chars < 2500:
        status = "weak"
        likely_failure_cause = "missing_product_pages"
    elif "missing_homepage" in reasons:
        status = "weak"
        likely_failure_cause = "missing_homepage"
    elif len(missing_core_roles) <= 1 and total_text_chars >= 2500:
        status = "strong"
        likely_failure_cause = None
    else:
        status = "usable"
        likely_failure_cause = "partial_owned_page_coverage" if reasons else None

    return {
        "status": status,
        "reasons": reasons,
        "owned_page_count": len(web_pages),
        "owned_text_chars": total_text_chars,
        "owned_page_roles": roles,
        "owned_page_role_counts": {role: role_counts[role] for role in roles},
        "missing_core_roles": missing_core_roles,
        "missing_proof_roles": missing_proof_roles,
        "homepage_detected": bool(role_counts.get("homepage")),
        "product_page_detected": bool(role_counts.get("product")),
        "solutions_page_detected": bool(role_counts.get("solutions")),
        "about_page_detected": bool(role_counts.get("about")),
        "customers_page_detected": bool(role_counts.get("customers")),
        "case_studies_page_detected": bool(role_counts.get("case_studies")),
        "reviews_page_detected": bool(role_counts.get("reviews")),
        "testimonials_page_detected": bool(role_counts.get("testimonials")),
        "trust_or_security_page_detected": any(role_counts.get(role) for role in TRUST_PAGE_ROLES),
        "pricing_page_detected": bool(role_counts.get("pricing")),
        "likely_failure_cause": likely_failure_cause,
    }


def _fallback_evidence_text(evidences: list[Any], fallback_markdown: str) -> str:
    preferred = [
        ev for ev in evidences if str(ev.source_type) in OWNED_EVIDENCE_SOURCE_TYPES
    ]
    evidence_source = preferred or evidences

    lines: list[str] = []
    seen: set[str] = set()
    for ev in evidence_source:
        quote = _clean_evidence_phrase(str(ev.quote or ""))
        if not quote or _is_unusable_audit_quote(quote):
            continue
        key = quote.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {quote}")
        if len(lines) >= MAX_FALLBACK_LINES:
            break

    if lines:
        return "\n".join(lines)
    return fallback_markdown


def _snapshot_limitations(snapshot: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    run = snapshot.get("run") or {}
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    if data_quality:
        limitations.append(f"Brand Audit data quality: {data_quality}")
    if not snapshot.get("evidence_items") and not snapshot.get("features"):
        limitations.append("Brand Audit snapshot has no persisted feature evidence.")
    return limitations


def _clean_evidence_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip(" -|•*\t")
    return text.strip()


def _is_unusable_audit_quote(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith(("http://", "https://")):
        return True
    if len(value) < MIN_USABLE_QUOTE_LENGTH:
        return True
    if any(marker in low for marker in UNUSABLE_QUOTE_METADATA_MARKERS):
        return True
    if any(marker in low for marker in UNUSABLE_QUOTE_CONTENT_MARKERS):
        return True
    return False
