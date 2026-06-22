"""Support helpers for EvidenceGraph source normalization."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
import hashlib
import re

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
