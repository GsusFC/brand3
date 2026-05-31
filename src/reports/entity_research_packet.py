"""Entity Research Packet v0.1 for Brand3 evidence expansion.

This module is deterministic and network-free. It decides what owned surfaces
should be considered when an input URL is likely a product, lab, or secondary
surface instead of the full parent brand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class EntityResearchSurface:
    url: str
    role: str
    entity_scope: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "url": self.url,
            "role": self.role,
            "entity_scope": self.entity_scope,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EntityResearchPacket:
    version: str
    input_url: str
    audited_surface_type: str
    entity_name: str
    parent_brand: str | None
    product_name: str | None
    brand_architecture: str
    owned_surfaces: list[EntityResearchSurface] = field(default_factory=list)
    product_surfaces: list[EntityResearchSurface] = field(default_factory=list)
    block_source_guidance: dict[str, list[str]] = field(default_factory=dict)
    confidence: str = "low"
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "input_url": self.input_url,
            "audited_surface_type": self.audited_surface_type,
            "entity_name": self.entity_name,
            "parent_brand": self.parent_brand,
            "product_name": self.product_name,
            "brand_architecture": self.brand_architecture,
            "owned_surfaces": [surface.to_dict() for surface in self.owned_surfaces],
            "product_surfaces": [surface.to_dict() for surface in self.product_surfaces],
            "block_source_guidance": self.block_source_guidance,
            "confidence": self.confidence,
            "limitations": self.limitations,
        }


def build_entity_research_packet(
    *,
    input_url: str,
    brand_name: str = "",
    entity_discovery: dict[str, Any] | None = None,
    discovery_search_plan: dict[str, Any] | None = None,
    web_data: Any | None = None,
    exa_data: Any | None = None,
) -> EntityResearchPacket:
    normalized_input = _normalize_url(input_url)
    host = _host(normalized_input)
    root = _root_domain(host)
    subdomain = _subdomain(host, root)
    discovery = entity_discovery or {}
    plan = discovery_search_plan or {}

    product_name = _clean_name(str(discovery.get("product_name") or "")) or _product_name_from_subdomain(subdomain)
    parent_brand = _clean_name(str(discovery.get("parent_brand_name") or "")) or _parent_name_from_root(root)
    entity_name = _clean_name(str(discovery.get("entity_name") or brand_name or "")) or product_name or parent_brand or root
    if _looks_like_domain_name(entity_name):
        entity_name = _brand_name_from_root(root) or entity_name
    if _looks_like_domain_name(parent_brand):
        parent_brand = _brand_name_from_root(root) or parent_brand

    if str(discovery.get("analysis_scope") or "") == "product_with_parent":
        audited_type = "product_surface"
        architecture = "parent_brand_with_product_surface"
        confidence = "high"
    elif subdomain in {"lab", "labs", "app", "beta", "demo", "studio", "platform"}:
        audited_type = "product_lab" if subdomain in {"lab", "labs", "beta", "demo"} else "product_surface"
        architecture = "parent_brand_with_product_surface"
        confidence = "medium"
    elif subdomain and subdomain not in {"www", "m"}:
        audited_type = "secondary_surface"
        architecture = "parent_brand_with_secondary_surface"
        confidence = "medium"
    else:
        audited_type = "parent_home"
        architecture = "single_brand_surface"
        confidence = "medium" if root else "low"
        parent_brand = None

    surfaces = _owned_surfaces(
        input_url=normalized_input,
        root=root,
        audited_type=audited_type,
        parent_brand=parent_brand,
        parent_url=_normalize_url(str(discovery.get("parent_url") or "")),
        include_candidate_paths=(
            _has_discovery_signal(discovery, "subdomain_product_parent")
            or subdomain in {"lab", "labs", "app", "beta", "demo", "studio", "platform"}
            or audited_type in {"product_lab", "secondary_surface"}
        ),
        owned_urls=_unique_urls(
            list(plan.get("owned_urls") or [])
            + _web_owned_urls(web_data)
            + _exa_owned_urls(exa_data, root=root)
        ),
    )
    product_surfaces = _product_surfaces_from_owned_surfaces(surfaces, root=root)
    limitations: list[str] = []
    if architecture != "single_brand_surface" and not root:
        limitations.append("Could not derive parent root domain from input URL.")
    if architecture != "single_brand_surface" and len(surfaces) <= 1:
        limitations.append("No parent owned surfaces were available beyond the audited URL.")

    return EntityResearchPacket(
        version="entity_research_packet_v0_1",
        input_url=normalized_input,
        audited_surface_type=audited_type,
        entity_name=entity_name,
        parent_brand=parent_brand,
        product_name=product_name,
        brand_architecture=architecture,
        owned_surfaces=surfaces,
        product_surfaces=product_surfaces,
        block_source_guidance=_block_source_guidance(),
        confidence=confidence if not limitations else "low",
        limitations=limitations,
    )


def surface_role_for_url(url: str, packet: dict[str, Any] | EntityResearchPacket | None = None) -> str:
    normalized = _normalize_url(url)
    packet_dict = packet.to_dict() if isinstance(packet, EntityResearchPacket) else packet or {}
    for surface in packet_dict.get("owned_surfaces") or []:
        surface_url = _normalize_url(str(surface.get("url") or ""))
        if surface_url and surface_url.rstrip("/") == normalized.rstrip("/"):
            return str(surface.get("role") or "unknown")
    return _role_from_path(normalized)


def entity_scope_for_url(url: str, packet: dict[str, Any] | EntityResearchPacket | None = None) -> str:
    normalized = _normalize_url(url)
    packet_dict = packet.to_dict() if isinstance(packet, EntityResearchPacket) else packet or {}
    for surface in packet_dict.get("owned_surfaces") or []:
        surface_url = _normalize_url(str(surface.get("url") or ""))
        if surface_url and surface_url.rstrip("/") == normalized.rstrip("/"):
            return str(surface.get("entity_scope") or "unknown")
    return "unknown"


def _owned_surfaces(
    *,
    input_url: str,
    root: str,
    audited_type: str,
    parent_brand: str | None,
    parent_url: str = "",
    include_candidate_paths: bool = False,
    owned_urls: list[str],
) -> list[EntityResearchSurface]:
    surfaces: list[EntityResearchSurface] = []
    seen: set[str] = set()

    def add(url: str, role: str, entity_scope: str, reason: str) -> None:
        normalized = _normalize_url(url)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        surfaces.append(EntityResearchSurface(normalized, role, entity_scope, reason))

    add(input_url, "audited_surface", "audited_surface", "Input URL supplied by user.")
    if root and audited_type != "parent_home":
        parent_home = parent_url or f"https://www.{root}"
        add(parent_home, "parent_home", "parent_brand", "Root domain inferred as parent brand home.")
        parent_origin = _origin(parent_home)
        if include_candidate_paths:
            for path, role, reason in (
                ("/mission", "mission_about", "Mission page candidate for parent brand context."),
                ("/about", "mission_about", "About page candidate for parent brand context."),
                ("/manifesto", "mission_about", "Manifesto page candidate for parent brand context."),
                ("/natureos", "product_system", "Known product-system path candidate."),
                ("/privacy-policy", "policy_security", "Privacy/security page candidate for values evidence."),
                ("/security", "policy_security", "Security page candidate for values evidence."),
            ):
                add(f"{parent_origin}{path}", role, "parent_brand", reason)

    for owned_url in owned_urls:
        role = _role_from_path(owned_url)
        scope = _entity_scope_from_role(role, owned_url, input_url)
        add(owned_url, role, scope, "Owned URL discovered by entity discovery/search plan.")
    return surfaces[:20]


def _role_from_path(url: str) -> str:
    parsed = urlparse(_normalize_url(url))
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if path == "/":
        return "parent_home"
    if any(marker in path for marker in ("/mission", "/about", "/manifesto", "/principles")):
        return "mission_about"
    if any(marker in path for marker in ("/privacy", "/security", "/trust", "/legal")):
        return "policy_security"
    if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/natureos", "/langsmith", "/langgraph", "/langchain")):
        return "product_system"
    if any(marker in path for marker in ("/pricing", "/plans")):
        return "pricing"
    if any(marker in path for marker in ("/blog", "/news", "/feed", "/post", "/article", "/resources")):
        return "blog_feed"
    if any(marker in path for marker in ("/customers", "/clients", "/case", "/stories", "/reviews", "/testimonials", "/casos", "/opiniones")):
        return "proof_customer"
    return "owned_surface"


def _block_source_guidance() -> dict[str, list[str]]:
    return {
        "core_purpose": ["mission_about", "parent_home"],
        "magnetism": ["audited_surface"],
        "value_proposition": ["audited_surface", "product_system", "product_surface"],
        "personality": ["audited_surface", "parent_home"],
        "brand_idea": ["parent_home", "product_system", "audited_surface"],
        "attributes": ["audited_surface", "product_system"],
        "values": ["policy_security", "mission_about"],
        "mission": ["mission_about", "parent_home", "product_system"],
        "vision": ["mission_about", "product_system"],
    }


def _origin(value: str) -> str:
    parsed = urlparse(_normalize_url(value))
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme or 'https'}://{parsed.netloc}".rstrip("/")


def _has_discovery_signal(discovery: dict[str, Any], signal: str) -> bool:
    for item in discovery.get("evidence") or []:
        if str(item.get("signal") or "") == signal:
            return True
    return False


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


def _host(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _subdomain(host: str, root: str) -> str:
    if not host or not root or host == root:
        return ""
    suffix = f".{root}"
    if not host.endswith(suffix):
        return ""
    return host[: -len(suffix)].split(".")[-1]


def _parent_name_from_root(root: str) -> str:
    if not root:
        return ""
    label = root.split(".")[0]
    return label.replace("-", " ").title()


def _product_name_from_subdomain(subdomain: str) -> str:
    return "" if subdomain in {"", "www", "lab", "labs", "app", "beta", "demo"} else subdomain.replace("-", " ").title()


def _clean_name(value: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    return "" if cleaned.lower() in {"none", "unknown"} else cleaned


def _brand_name_from_root(root: str) -> str:
    label = (root or "").split(".")[0]
    known = {
        "langchain": "LangChain",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "naturaumana": "Natura Umana",
        "sigmaos": "SigmaOS",
    }
    return known.get(label.lower(), label.replace("-", " ").title() if label else "")


def _looks_like_domain_name(value: str) -> bool:
    text = (value or "").strip().lower()
    return bool(text and "." in text and " " not in text)


def _web_owned_urls(web_data: Any | None) -> list[str]:
    if web_data is None:
        return []
    urls: list[str] = []
    urls.extend(str(item) for item in getattr(web_data, "owned_fallback_urls", []) or [])
    urls.extend(str(item) for item in getattr(web_data, "links", []) or [])
    return _unique_urls(urls)


def _exa_owned_urls(exa_data: Any | None, *, root: str) -> list[str]:
    if exa_data is None or not root:
        return []
    urls: list[str] = []
    for attr in ("mentions", "news", "ai_visibility_results"):
        for item in getattr(exa_data, attr, []) or []:
            url = str(getattr(item, "url", "") or "")
            host = _host(url)
            if host == root or host.endswith("." + root):
                urls.append(url)
    return _unique_urls(urls)


def _entity_scope_from_role(role: str, url: str, input_url: str) -> str:
    if _normalize_url(url).rstrip("/") == input_url.rstrip("/"):
        return "audited_surface"
    if role == "product_system":
        product = _product_name_from_path(url)
        return f"product:{product}" if product else "product_surface"
    if role in {"pricing", "proof_customer"}:
        return "commercial_surface"
    if role in {"mission_about", "parent_home", "policy_security"}:
        return "parent_brand"
    return "owned_surface"


def _product_surfaces_from_owned_surfaces(
    surfaces: list[EntityResearchSurface],
    *,
    root: str,
) -> list[EntityResearchSurface]:
    product_surfaces: list[EntityResearchSurface] = []
    seen: set[str] = set()
    for surface in surfaces:
        if surface.role != "product_system":
            continue
        product = _product_name_from_path(surface.url)
        if not product:
            continue
        key = f"{product}:{surface.url}"
        if key in seen:
            continue
        seen.add(key)
        product_surfaces.append(
            EntityResearchSurface(
                url=surface.url,
                role=f"product:{product}",
                entity_scope=f"product:{product}",
                reason=f"Detected product surface for {product} under {_brand_name_from_root(root) or root}.",
            )
        )
    return product_surfaces[:12]


def _product_name_from_path(url: str) -> str:
    path = (urlparse(_normalize_url(url)).path or "").lower()
    known = (
        ("langsmith", "LangSmith"),
        ("langgraph", "LangGraph"),
        ("langchain", "LangChain OSS"),
        ("natureos", "NatureOS"),
        ("humanpods", "HumanPods"),
        ("tinynature", "tinyNature"),
    )
    for marker, name in known:
        if marker in path:
            return name
    return ""


def _unique_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        normalized = _normalize_url(str(url or ""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
