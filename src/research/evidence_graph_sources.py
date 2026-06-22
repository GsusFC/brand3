"""Source normalization and classification helpers for EvidenceGraph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
import hashlib
import re

from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url


_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)

ALLOWED_SOURCE_TYPES = {
    "owned_home",
    "owned_about",
    "owned_product",
    "owned_pricing",
    "owned_security",
    "owned_docs",
    "owned_proof",
    "press_founder",
    "third_party_review",
    "third_party_context",
    "social",
    "competitor_context",
    "noise",
    "unknown",
}


@dataclass(slots=True)
class ResearchSource:
    """One discovered or analyzed surface."""

    source_id: str
    url: str
    source_type: str
    label: str = ""
    surface_role: str = ""
    entity_scope: str = ""
    title: str = ""
    origin: str = ""
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        _validate(self.source_type, ALLOWED_SOURCE_TYPES, "source_type")
        if self.notes is None:
            self.notes = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "source_type": self.source_type,
            "label": self.label,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "title": self.title,
            "origin": self.origin,
            "notes": list(self.notes or []),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchSource":
        return cls(
            source_id=str(data.get("source_id") or ""),
            url=str(data.get("url") or ""),
            source_type=str(data.get("source_type") or "unknown"),
            label=str(data.get("label") or ""),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            title=str(data.get("title") or ""),
            origin=str(data.get("origin") or ""),
            notes=_str_list(data.get("notes")),
        )


def build_sources(snapshot: dict[str, Any], *, entity_packet: dict[str, Any] | None) -> dict[str, ResearchSource]:
    run = _dict(snapshot.get("run"))
    input_url = _normalize_url(str(run.get("url") or ""))
    brand_name = str((entity_packet or {}).get("entity_name") or run.get("brand_name") or "")
    brand_domain = _root_domain(_host(input_url))
    sources: dict[str, ResearchSource] = {}

    def add(
        url: str,
        *,
        source_type: str,
        label: str = "",
        title: str = "",
        origin: str = "",
        surface_role: str = "",
        entity_scope: str = "",
        notes: list[str] | None = None,
    ) -> None:
        normalized = _normalize_url(url)
        if not normalized:
            return
        source_type = source_type if source_type in ALLOWED_SOURCE_TYPES else "unknown"
        source_id = _source_id(normalized)
        if source_id in sources:
            existing = sources[source_id]
            merged_notes = list(existing.notes or [])
            if origin and origin != existing.origin:
                merged_notes.append(f"Also observed via {origin}.")
            sources[source_id] = ResearchSource(
                source_id=source_id,
                url=existing.url,
                source_type=_prefer_source_type(existing.source_type, source_type),
                label=existing.label or label,
                surface_role=_prefer_annotation(existing.surface_role, surface_role),
                entity_scope=_prefer_annotation(existing.entity_scope, entity_scope),
                title=existing.title or title,
                origin=existing.origin or origin,
                notes=_unique(merged_notes + (notes or [])),
            )
            return
        sources[source_id] = ResearchSource(
            source_id=source_id,
            url=normalized,
            source_type=source_type,
            label=label,
            surface_role=surface_role,
            entity_scope=entity_scope,
            title=title,
            origin=origin,
            notes=_unique(notes or []),
        )

    if input_url:
        add(
            input_url,
            source_type="owned_home",
            label="input_url",
            title=str(run.get("brand_name") or ""),
            origin="run",
            surface_role="audited_surface",
            entity_scope="audited_surface",
            notes=["Initial URL supplied to Brand Audit."],
        )

    for raw_input in snapshot.get("raw_inputs") or []:
        source = str(raw_input.get("source") or "")
        payload = _dict(raw_input.get("payload"))
        if source in {"web", "hyperbrowser"}:
            text = str(payload.get("markdown_content") or payload.get("content") or "")
            for url in _web_urls(payload, fallback=input_url) or [str(payload.get("source_url") or payload.get("url") or input_url)]:
                add(
                    url,
                    source_type=_classify_source_url(url, brand_domain=brand_domain, text=text),
                    label=str(payload.get("title") or source),
                    title=str(payload.get("title") or ""),
                    origin=f"raw_inputs.{source}",
                    surface_role=surface_role_for_url(url, entity_packet),
                    entity_scope=entity_scope_for_url(url, entity_packet),
                    notes=[
                        "Owned web content collected by Brand Audit."
                        if source == "web"
                        else "Owned web shadow content collected by Hyperbrowser."
                    ],
                )
        elif source == "exa":
            for collection in ("mentions", "news", "ai_visibility_results", "competitors"):
                for item in payload.get(collection) or []:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("url") or "")
                    text = " ".join(
                        part
                        for part in [
                            str(item.get("title") or ""),
                            str(item.get("summary") or ""),
                            str(item.get("text") or ""),
                            " ".join(str(h) for h in item.get("highlights") or []),
                        ]
                        if part.strip()
                    )
                    source_type = "competitor_context" if collection == "competitors" else _classify_source_url(
                        url,
                        brand_domain=brand_domain,
                        text=text,
                        external=True,
                    )
                    notes = ["External discovery evidence collected by Brand Audit."]
                    if collection != "competitors" and _external_entity_boundary_collision(
                        url,
                        text,
                        brand_name=brand_name,
                        brand_domain=brand_domain,
                    ):
                        source_type = "noise"
                        notes.append(
                            "entity_boundary_collision: external evidence appears to reference a near-name entity, not the audited entity."
                        )
                    add(
                        url,
                        source_type=source_type,
                        label=str(item.get("title") or collection),
                        title=str(item.get("title") or ""),
                        origin=f"raw_inputs.exa.{collection}",
                        surface_role="external_context",
                        entity_scope="external_context",
                        notes=notes,
                    )
        elif source == "social":
            for url in _social_urls(payload):
                add(
                    url,
                    source_type="social",
                    label=str(payload.get("brand_name") or "social"),
                    origin="raw_inputs.social",
                    surface_role="social",
                    entity_scope="external_context",
                )
        elif source == "competitors":
            for url in _competitor_urls(payload):
                add(
                    url,
                    source_type="competitor_context",
                    label="competitor",
                    origin="raw_inputs.competitors",
                    surface_role="external_context",
                    entity_scope="external_context",
                )

    if entity_packet:
        for surface in list(entity_packet.get("owned_surfaces") or []) + list(entity_packet.get("product_surfaces") or []):
            if not isinstance(surface, dict):
                continue
            url = str(surface.get("url") or "")
            role = str(surface.get("role") or "")
            add(
                url,
                source_type=_source_type_from_entity_role(role, url),
                label=role or "owned_surface",
                origin="entity_research_packet",
                surface_role=role,
                entity_scope=str(surface.get("entity_scope") or ""),
                notes=[str(surface.get("reason") or "Owned surface from entity research packet.")],
            )

    return dict(sorted(sources.items()))


def _web_urls(payload: dict[str, Any], *, fallback: str = "") -> list[str]:
    urls: list[str] = []
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            urls.append(value)
    urls.extend(str(url) for url in payload.get("owned_fallback_urls") or [] if str(url).strip())
    markdown = str(payload.get("markdown_content") or payload.get("content") or "")
    urls.extend(match.group("url") for match in _SUBPAGE_RE.finditer(markdown))
    if fallback:
        urls.append(fallback)
    return _unique(_normalize_url(url) for url in urls)


def _social_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("profiles", "platforms", "profile_urls"):
        value = payload.get(key)
        if isinstance(value, dict):
            for item in value.values():
                if isinstance(item, dict):
                    urls.append(str(item.get("url") or item.get("profile_url") or ""))
                else:
                    urls.append(str(item))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    urls.append(str(item.get("url") or item.get("profile_url") or ""))
    return _unique(_normalize_url(url) for url in urls)


def _competitor_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in payload.get("competitors") or []:
        if isinstance(item, dict):
            urls.append(str(item.get("url") or item.get("website") or ""))
    return _unique(_normalize_url(url) for url in urls)


def _classify_source_url(url: str, *, brand_domain: str, text: str = "", external: bool = False) -> str:
    normalized = _normalize_url(url)
    host = _host(normalized)
    path = (urlparse(normalized).path or "/").lower()
    text_low = text.lower()
    if not normalized:
        return "unknown"
    if _is_social(host):
        return "social"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        if path in {"", "/"}:
            return "owned_home"
        if any(marker in path for marker in ("/about", "/company", "/mission", "/manifesto", "/team", "/story", "/principles")):
            return "owned_about"
        if any(marker in path for marker in ("/security", "/privacy", "/trust", "/legal", "/terms", "/compliance")):
            return "owned_security"
        if any(marker in path for marker in ("/docs", "/documentation", "/developers", "/api", "/help", "/support")):
            return "owned_docs"
        if any(marker in path for marker in ("/pricing", "/plans")):
            return "owned_pricing"
        if any(marker in path for marker in ("/customers", "/case", "/stories", "/testimonials", "/reviews")):
            return "owned_proof"
        if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/app", "/demo", "/lab", "/natureos")):
            return "owned_product"
        if any(marker in path for marker in ("/blog", "/news", "/feed", "/article", "/post", "/resources")):
            return "noise"
        return "owned_home"
    if external and any(marker in text_low for marker in ("founder", "interview", "launch", "raises", "raised", "funding", "acquired", "press")):
        return "press_founder"
    if external and any(marker in text_low for marker in ("review", "customer", "testimonial", "case study", "trusted by", "used by")):
        return "third_party_review"
    if external:
        return "third_party_context"
    return "unknown"


def _external_entity_boundary_collision(url: str, text: str, *, brand_name: str, brand_domain: str) -> bool:
    token = _identity_token(brand_name=brand_name, brand_domain=brand_domain)
    if len(token) < 5:
        return False
    observed_tokens = _identity_tokens(" ".join([url, text]))
    if not observed_tokens or token in observed_tokens:
        return False
    for observed in observed_tokens:
        if len(observed) < 5:
            continue
        if observed.startswith(token) or token.startswith(observed):
            return True
        if abs(len(observed) - len(token)) <= 2 and _edit_distance_at_most(observed, token, 2):
            return True
    return False


def _identity_token(*, brand_name: str, brand_domain: str) -> str:
    for value in (brand_name, brand_domain.split(".", 1)[0]):
        tokens = sorted(_identity_tokens(value), key=lambda item: (-len(item), item))
        if tokens:
            return tokens[0]
    return ""


def _identity_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in {"www", "com", "app", "ai", "io", "co", "inc", "the"}
    }


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


def _source_type_from_entity_role(role: str, url: str) -> str:
    if role.startswith("product:"):
        return "owned_product"
    if role in {"audited_surface", "parent_home"}:
        return "owned_home"
    if role == "mission_about":
        return "owned_about"
    if role == "product_system":
        return "owned_product"
    if role == "policy_security":
        return "owned_security"
    if role == "pricing":
        return "owned_pricing"
    if role == "proof_customer":
        return "owned_proof"
    return _classify_source_url(url, brand_domain=_root_domain(_host(url)))


def _prefer_source_type(existing: str, candidate: str) -> str:
    priority = {
        "unknown": 0,
        "noise": 1,
        "owned_home": 2,
        "third_party_context": 2,
        "social": 2,
        "competitor_context": 2,
        "press_founder": 3,
        "third_party_review": 3,
        "owned_about": 4,
        "owned_pricing": 4,
        "owned_security": 4,
        "owned_docs": 4,
        "owned_proof": 4,
        "owned_product": 5,
    }
    if priority.get(candidate, 0) > priority.get(existing, 0):
        return candidate
    if existing in {"unknown", "noise"} and candidate not in {"unknown", "noise"}:
        return candidate
    return existing


def _prefer_annotation(existing: str, candidate: str) -> str:
    if not candidate:
        return existing
    if not existing:
        return candidate
    if candidate.startswith("product:") or existing in {"unknown", "external_context", "evidence", "owned_surface"}:
        return candidate
    return existing


def _source_id(url: str) -> str:
    normalized = _normalize_url(url)
    if not normalized:
        return ""
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"src_{digest}"


def _normalize_url(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    path = parsed.path if parsed.netloc else ""
    if path == "/":
        path = ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _host(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _is_social(host: str) -> bool:
    return host.endswith((
        "linkedin.com",
        "x.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "facebook.com",
        "github.com",
    ))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _unique(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _validate(value: str, allowed: set[str], field_name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
