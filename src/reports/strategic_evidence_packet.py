"""Strategic evidence packet derived from Brand Audit snapshots.

Brand Audit owns data collection. This module turns a persisted run snapshot into
small, named evidence groups that downstream interpreters can reuse without
reading raw scraper text or internal feature metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from src.reports.derivation import Evidence, collect_evidences
from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url
from src.reports.vertical_signals import vertical_group_keywords


GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hero_claims": (
        "introducing",
        "meet ",
        "built for",
        "designed for",
        "purpose-built",
        "just do it",
        "earn every",
        "system for",
        "platform for",
    ),
    "product_offer": (
        "platform",
        "plataforma",
        "infrastructure",
        "infraestructura",
        "api",
        "payments",
        "pagos",
        "billing",
        "facturacion",
        "facturación",
        "services",
        "servicios",
        "products",
        "productos",
        "software",
        "model",
        "ai assistant",
        "chatbot",
        "banking",
        "wealth management",
        "private banking",
        "business analyst",
        "human intelligence",
        "research people",
        "research people and companies",
        "brand identities",
        "ai-powered search",
        "product discovery",
        "merchandising",
        "conversions",
        "shopper intent",
        "ecommerce",
        "e-commerce",
        "branding solution",
        "brand execution",
        "brand and website",
        "deliverables",
        "calendar app",
        "productivity tools",
        "extendable launcher",
        "application launcher",
        "observability service",
        "monitoring",
        "portfolio platform",
        "jobs and recruiting site",
    )
    + vertical_group_keywords("product_offer"),
    "audience": (
        "teams",
        "agents",
        "developers",
        "businesses",
        "founders",
        "startups",
        "finance teams",
        "sales teams",
        "wealth managers",
        "creators",
        "customers",
        "clients",
        "shopper",
        "shoppers",
        "manufacturer",
        "manufacturers",
        "people and companies",
        "enterprise",
        "fortune 100",
        "asesores",
        "empresas",
        "clientes",
        "fabricante",
        "fabricantes",
        "distribuidor",
        "distribuidores",
        "atletas",
        "athletes",
    ),
    "outcome": (
        "helps",
        "help ",
        "eliminate risks",
        "secure your competitive advantage",
        "grow",
        "increase",
        "reduce",
        "automate",
        "productive",
        "productivity",
        "efficient",
        "efficiency",
        "drive success",
        "build relationships",
        "get things done",
        "make people talk",
        "solve problems",
        "learn faster",
        "faster",
        "deploy instantly",
        "build and ship",
        "develop and ship",
        "ship digital products",
        "scale",
        "improve product discovery",
        "increasing conversions",
        "boosts conversions",
        "reduce no-result searches",
        "streamline",
        "centralise",
        "centralize",
        "gestionar",
        "hacer crecer",
        "automatizar",
        "reducir costes",
        "reduce costes",
        "facilitar",
        "optimiza",
        "asegura",
        "empowering",
        "impulsando",
    )
    + vertical_group_keywords("outcome"),
    "mission_language": (
        "we build",
        "we create",
        "we provide",
        "we help",
        "we make",
        "we enable",
        "we develop",
        "we empower",
        "our mission",
        "on a mission to",
        "make developers",
        "make teams",
        "help companies",
        "ayuda a",
        "ofrece",
        "creamos",
        "proporcionamos",
    ),
    "vision_language": (
        "future of",
        "built for the future",
        "new model",
        "new paradigm",
        "transform the future",
        "transforming the future",
        "shape the future",
        "creative entity",
        "creative work",
        "wield power",
        "world stage",
        "futuro de",
        "nuevo modelo",
        "nueva generación",
        "transformar la categoría",
        "transformar el futuro",
    ),
    "values_language": (
        "trusted",
        "trust",
        "secure",
        "security",
        "privacy",
        "transparent",
        "sustainable",
        "regenerative",
        "confianza",
        "seguro",
        "seguridad",
        "sostenible",
    )
    + vertical_group_keywords("values_language"),
    "personality_tone": (
        "bold",
        "fast",
        "simple",
        "powerful",
        "precise",
        "creative",
        "ambition",
        "culture",
        "inspire",
        "inspirar",
        "innovative",
        "innovadores",
    ),
    "proof_points": (
        "customers",
        "customer",
        "clients",
        "client",
        "clientes",
        "cliente",
        "trusted by",
        "con la confianza",
        "case study",
        "case studies",
        "customer story",
        "success story",
        "caso de éxito",
        "casos de éxito",
        "testimonial",
        "testimonials",
        "testimonio",
        "testimonios",
        "reviews",
        "review",
        "reseñas",
        "resenas",
        "opiniones",
        "millions",
        "global",
        "leader",
        "used by",
        "raises",
        "funding",
    ),
    "third_party_context": (
        "raises",
        "funding",
        "report",
        "market",
        "competitor",
        "news",
    ),
}

OWNED_SOURCE_TYPES = {"owned", "social", "owned_raw"}
CONTEXT_SOURCE_TYPES = {"encyclopedic", "news", "review", "other", "changelog"}
_EMBEDDED_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)


NOISE_MARKERS = (
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
    "__next_data__",
    "graphql api",
    "product roadmap",
    "rg --files",
    "/bin/bash",
)


@dataclass
class StrategicEvidenceLine:
    text: str
    source_type: str
    source_domain: str | None = None
    url: str | None = None
    feature_name: str | None = None
    dimension: str | None = None
    surface_role: str | None = None
    entity_scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_type": self.source_type,
            "source_domain": self.source_domain,
            "url": self.url,
            "feature_name": self.feature_name,
            "dimension": self.dimension,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
        }


@dataclass
class StrategicEvidencePacket:
    brand_name: str
    url: str
    run_id: int | None
    groups: dict[str, list[StrategicEvidenceLine]] = field(default_factory=dict)
    rejected: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_counts: dict[str, int] = field(default_factory=dict)

    def group_text(self, group: str, limit: int = 6) -> list[str]:
        return [line.text for line in self.groups.get(group, [])[:limit]]

    def to_interpreter_text(self) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for group in GROUP_KEYWORDS:
            for line in self.group_text(group):
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                lines.append(line)
        return '\n'.join(lines).strip()

    def to_summary(self) -> dict[str, Any]:
        return {
            "source": "strategic_evidence_packet",
            "source_label": "Strategic Evidence Packet",
            "evidence_basis": "Grouped Brand Audit evidence reused by TLDR interpreters.",
            "run_id": self.run_id,
            "group_counts": {key: len(value) for key, value in self.groups.items()},
            "source_counts": self.source_counts,
            "rejected_count": len(self.rejected),
            "rejected_reason_counts": _rejected_reason_counts(self.rejected),
            "warnings": self.warnings,
            "value_policy": "Brand Audit owns collection; this packet only groups strategically relevant public evidence.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "brand_name": self.brand_name,
            "url": self.url,
            "groups": {
                key: [line.to_dict() for line in value]
                for key, value in self.groups.items()
            },
            "rejected": self.rejected[:40],
        }


def _entity_research_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") == "entity_research_packet" and isinstance(item.get("payload"), dict):
            return item["payload"]
    audit = ((snapshot.get("run") or {}).get("audit") or {})
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _rejected_reason_counts(rejected: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rejected:
        reason = str(item.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def build_strategic_evidence_packet(snapshot: dict[str, Any]) -> StrategicEvidencePacket:
    run = snapshot.get("run") or {}
    packet = StrategicEvidencePacket(
        brand_name=str(run.get("brand_name") or "Unknown Brand"),
        url=str(run.get("url") or ""),
        run_id=run.get("id"),
    )
    evidences = collect_evidences(snapshot)
    preferred = [ev for ev in evidences if str(ev.source_type) in OWNED_SOURCE_TYPES]
    context = [ev for ev in evidences if str(ev.source_type) in CONTEXT_SOURCE_TYPES]
    seen: set[str] = set()
    for ev in preferred:
        source_type = str(ev.source_type)
        packet.source_counts[source_type] = packet.source_counts.get(source_type, 0) + 1
        _add_candidate_line(
            packet,
            seen,
            text=str(ev.quote or ""),
            source_type=source_type,
            source_domain=ev.source_domain,
            url=ev.url,
            feature_name=ev.feature_name,
            dimension=ev.dimension,
            entity_research_packet=_entity_research_packet(snapshot),
        )

    # Raw owned web copy is the brand's own voice. Process it before
    # contextual evidence so a duplicated search/context snippet cannot
    # downgrade the same claim to third-party context.
    _add_owned_raw_web_candidates(packet, snapshot, seen)

    for ev in context:
        source_type = str(ev.source_type)
        packet.source_counts[source_type] = packet.source_counts.get(source_type, 0) + 1
        _add_candidate_line(
            packet,
            seen,
            text=str(ev.quote or ""),
            source_type=source_type,
            source_domain=ev.source_domain,
            url=ev.url,
            feature_name=ev.feature_name,
            dimension=ev.dimension,
            entity_research_packet=_entity_research_packet(snapshot),
        )

    if not preferred:
        packet.warnings.append("No owned/social evidence found; packet relies on contextual evidence.")
    if not packet.groups:
        packet.warnings.append("No strategically usable evidence groups found.")
    _rank_packet_groups(packet)
    if not packet.groups.get("product_offer"):
        packet.warnings.append("No product offer evidence group found.")
    if not packet.groups.get("audience"):
        packet.warnings.append("No audience evidence group found.")
    return packet



def _rank_packet_groups(packet: StrategicEvidencePacket) -> None:
    for group, lines in list(packet.groups.items()):
        packet.groups[group] = sorted(lines, key=lambda line: _line_priority(line, group))


def _line_priority(line: StrategicEvidenceLine, group: str) -> tuple[int, int, int, int, int, int]:
    low = line.text.lower()
    source_rank = {"owned_raw": 0, "owned": 1, "social": 2}.get(line.source_type, 3)
    feature_rank = 2 if line.feature_name == "search_visibility" else 0
    context_rank = 1 if group == "third_party_context" else 0
    noise_rank = 0
    if _looks_like_promotion_or_event(low):
        noise_rank += 3
    if _looks_like_short_label(low):
        noise_rank += 3
    if _looks_like_title_or_directory(low):
        noise_rank += 2
    proof_page_rank = 0
    if group == "proof_points":
        proof_page_rank = 0 if _is_proof_page_url(line.url) else 1
    useful_length = min(len(line.text), 260)
    return (source_rank, proof_page_rank, noise_rank, feature_rank, context_rank, -useful_length)


def _looks_like_promotion_or_event(low: str) -> bool:
    return any(
        marker in low
        for marker in (
            "off your first payment",
            "use code",
            "welcome20",
            "conference",
            "webinar",
            "register now",
            "save your spot",
            "named a leader",
            "magic quadrant",
        )
    )


def _looks_like_short_label(low: str) -> bool:
    if len(low) > 64:
        return False
    if any(mark in low for mark in (".", "?", "!")):
        return False
    if low.startswith(("we ", "our ", "built ", "build ", "make ", "meet ", "earn ")):
        return False
    if re.search(r"\b(?:is|are|helps|help|enables|enable|offers|provides|builds|creates|automates|streamlines|improves|reduces)\b", low):
        return False
    if low in {
        "case studies",
        "customer stories",
        "testimonials",
        "reviews",
        "estudios de caso",
        "casos de éxito",
        "testimonios",
        "reseñas",
        "opiniones",
    }:
        return True
    return any(marker in low for marker in (" + ", "products", "services", "platform", "infrastructure", "software delivery", "financial services"))



def _looks_like_bare_page_label(low: str) -> bool:
    if len(low) > 40:
        return False
    if any(mark in low for mark in (".", "?", "!", ":", "|")):
        return False
    if any(char.isdigit() for char in low):
        return False
    return not re.search(
        r"\b(?:is|are|helps|help|enables|enable|offers|provides|builds|creates|automates|streamlines|improves|reduces|usó|logró|alcanzo|alcanzó|genera|mejora|reduce|optimiza|escala|scaled)\b",
        low,
    )


def _looks_like_title_or_directory(low: str) -> bool:
    return (
        " | " in low
        or " - " in low[:120]
        or "company details" in low
        or "industry:" in low
        or "employees:" in low
    )


def _add_owned_raw_web_candidates(
    packet: StrategicEvidencePacket,
    snapshot: dict[str, Any],
    seen: set[str],
) -> None:
    run_url = ((snapshot.get("run") or {}).get("url") or packet.url or "")
    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") != "web":
            continue
        payload = raw_input.get("payload") or {}
        markdown = str(payload.get("markdown_content") or payload.get("content") or "")
        if not markdown:
            continue
        source_url = str(
            payload.get("canonical_url")
            or payload.get("url")
            or payload.get("page_url")
            or run_url
        )
        pages = [(source_url, _primary_web_page_text(markdown))]
        pages.extend(_embedded_web_subpage_texts(markdown))
        for page_url, page_text in pages:
            if page_text:
                _add_owned_raw_page_candidates(packet, seen, page_text, page_url, entity_research_packet=_entity_research_packet(snapshot))


def _add_owned_raw_page_candidates(
    packet: StrategicEvidencePacket,
    seen: set[str],
    text: str,
    source_url: str,
    entity_research_packet: dict[str, Any] | None = None,
) -> None:
    added = 0
    max_lines = 32 if _is_proof_page_url(source_url) else 24
    for line in _raw_candidate_lines(text):
        before = sum(len(values) for values in packet.groups.values())
        _add_candidate_line(
            packet,
            seen,
            text=line,
            source_type="owned_raw",
            source_domain=None,
            url=source_url,
            feature_name="raw_web",
            dimension=None,
            entity_research_packet=entity_research_packet,
        )
        after = sum(len(values) for values in packet.groups.values())
        if after > before:
            added += 1
            packet.source_counts["owned_raw"] = packet.source_counts.get("owned_raw", 0) + 1
        if added >= max_lines:
            break



def _primary_web_page_text(markdown: str) -> str:
    match = _EMBEDDED_SUBPAGE_RE.search(markdown or "")
    if not match:
        return markdown
    return markdown[: match.start()].strip(" -\n")


def _embedded_web_subpage_texts(markdown: str) -> list[tuple[str, str]]:
    matches = list(_EMBEDDED_SUBPAGE_RE.finditer(markdown or ""))
    pages: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        page_url = match.group("url").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        text = (markdown[start:end] or "").strip(" -\n")
        if page_url or text:
            pages.append((page_url, text))
    return pages

def _add_candidate_line(
    packet: StrategicEvidencePacket,
    seen: set[str],
    *,
    text: str,
    source_type: str,
    source_domain: str | None = None,
    url: str | None = None,
    feature_name: str | None = None,
    dimension: str | None = None,
    entity_research_packet: dict[str, Any] | None = None,
) -> None:
    cleaned = _clean_quote(text)
    reject_reason = _reject_reason(cleaned)
    if reject_reason:
        packet.rejected.append({"text": cleaned[:220], "reason": reject_reason})
        return
    key = cleaned.lower()
    if key in seen:
        packet.rejected.append({"text": cleaned[:220], "reason": "duplicate"})
        return
    seen.add(key)

    groups = _groups_for(cleaned, source_type, url=url)
    if not groups:
        packet.rejected.append({"text": cleaned[:220], "reason": "low_strategic_signal"})
        return
    line = StrategicEvidenceLine(
        text=cleaned,
        source_type=source_type,
        source_domain=source_domain,
        url=url,
        feature_name=feature_name,
        dimension=dimension,
        surface_role=surface_role_for_url(url or "", entity_research_packet),
        entity_scope=entity_scope_for_url(url or "", entity_research_packet),
    )
    for group in groups:
        if len(packet.groups.setdefault(group, [])) < 8:
            packet.groups[group].append(line)


def _raw_candidate_lines(text: str) -> list[str]:
    candidates: list[str] = []
    cta_pattern = re.compile(
        r"\b(?:start free trial|book demo|contact sales|contacta con ventas|try for free|get started|inicia sesión|log in)\b",
        re.I,
    )
    for raw in (text or "").splitlines():
        line = _clean_quote(raw)
        if not line:
            continue
        cta_chunks = [_clean_quote(chunk) for chunk in cta_pattern.split(line)]
        cta_chunks = [chunk for chunk in cta_chunks if len(chunk) >= 8]
        if len(cta_chunks) > 1:
            candidates.extend(cta_chunks)
            continue
        if len(line) <= 320:
            candidates.append(line)
            continue
        chunks = re.split(r"(?<=[.!?])\s+|\s{2,}", line)
        candidates.extend(_clean_quote(chunk) for chunk in chunks if len(_clean_quote(chunk)) >= 8)
    return candidates[:160]


def _groups_for(text: str, source_type: str, url: str | None = None) -> list[str]:
    low = text.lower()
    if _looks_like_testimonial_quote(low):
        return ["proof_points"]

    if source_type in OWNED_SOURCE_TYPES and _is_proof_page_url(url):
        return [] if _looks_like_bare_page_label(low) else ["proof_points"]

    groups = [
        group
        for group, keywords in GROUP_KEYWORDS.items()
        if any(keyword in low for keyword in keywords)
    ]
    if "product_offer" in groups and _looks_like_about_mission_or_values_line(low):
        groups = [group for group in groups if group != "product_offer"]
    if source_type not in OWNED_SOURCE_TYPES and groups:
        groups = [group for group in groups if group in {"proof_points", "third_party_context"}]
        if "third_party_context" not in groups:
            groups.append("third_party_context")
    return list(dict.fromkeys(groups))


def _looks_like_about_mission_or_values_line(low: str) -> bool:
    return low.startswith(
        (
            "historia de la marca",
            "nuestra misión",
            "nuestra mision",
            "nuestro propósito",
            "nuestro proposito",
            "valores y filosofía",
            "valores y filosofia",
            "inclusión ",
            "inclusion ",
            "valoramos ",
        )
    ) or "inclusión valoramos" in low or "inclusion valoramos" in low


def _is_proof_page_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        path = urlparse(url).path.lower()
    except ValueError:
        return False
    return any(
        marker in path
        for marker in (
            "/customers",
            "/customer",
            "/clients",
            "/client",
            "/clientes",
            "/cliente",
            "/case-study",
            "/case-studies",
            "/success-stories",
            "/stories",
            "/casos",
            "/caso-de-exito",
            "/casos-de-exito",
            "/reviews",
            "/review",
            "/ratings",
            "/resenas",
            "/reseñas",
            "/opiniones",
            "/testimonials",
            "/testimonial",
            "/testimonios",
            "/testimonio",
        )
    )


def _clean_quote(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip(" -|•*\t")
    text = re.sub(r"^#+\s*", "", text).strip()
    text = re.sub(r"^sign in to [^,]{2,80},\s*", "", text, flags=re.I).strip()
    text = re.sub(
        r"^(?P<brand>[A-Z][^.!?]{1,80})(?:\s+\([^)]{2,120}\))?\s+(?P=brand)\s+is\s+(?:a|an)\s+[^.!?]{2,120}\s+company\.\s*",
        "",
        text,
        flags=re.I,
    )
    for marker in (" [![", "🚀 See the teams behind", " See the teams behind this year"):
        idx = text.find(marker)
        if idx > 40:
            text = text[:idx].strip()
    if " # " in text:
        before, after = text.split(" # ", 1)
        repeated = before.lower().split(" - ")[-1].strip()
        if repeated and repeated in after.lower():
            text = after.strip()
    text = re.sub(
        r"^[^.!?]{8,110}\s+[|–]\s+[^.!?]{2,80}\s+(?=(?:the|el|la|los|las|kit is|[A-Z][a-z0-9]+ is)\b)",
        "",
        text,
        count=1,
        flags=re.I,
    ).strip()
    text = re.sub(r"\s+(for|para|with|by|to)$", "", text, flags=re.I).strip()
    return text.strip()

def _reject_reason(text: str) -> str | None:
    low = text.lower().strip()
    if not low or len(low) < 6:
        return "empty_or_too_short"
    if low.startswith(("http://", "https://")):
        return "url_only"
    if low.startswith("source:"):
        return "source_metadata"
    if text.strip().startswith("![") or _looks_like_image_or_logo_noise(text, low):
        return "image_alt_text_noise"
    if _looks_like_legal_or_footer_noise(low):
        return "legal_or_footer_noise"
    if _looks_like_directory_profile_noise(low):
        return "company_profile_metadata"
    if _looks_like_customer_story_fragment(low):
        return "customer_story_fragment_noise"
    if _looks_truncated(low):
        return "truncated_fragment_noise"
    if low in {"we make good shit"}:
        return "generic_slogan_noise"
    if _looks_like_short_label(low):
        return "navigation_or_section_heading_noise"
    if "company details" in low or ("industry:" in low and "type:" in low):
        return "company_profile_metadata"
    if "employees:" in low and "monthly growth" in low:
        return "company_profile_metadata"
    if any(marker in low for marker in NOISE_MARKERS):
        return "internal_or_technical_noise"
    if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", low) or "finding email" in low or "credits left" in low:
        return "demo_contact_or_app_state_noise"
    if re.match(r"^([a-z][a-z0-9& .-]{2,50}) \1 is (?:a|an) ", low):
        return "embedded_directory_or_competitor_noise"
    if re.fullmatch(r"\[[^\]]{2,90}\]\(https?://[^)]+\)", text.strip()):
        return "markdown_link_only_noise"
    if low in {"platform capabilities", "explore services", "help and security", "startups program", "shots shots designers services explore popular"}:
        return "navigation_or_section_heading_noise"
    if "differentiates from" in low and any(marker in low for marker in ("logo", "mark", "blue", "green", "visual", "sterility", "wellness")):
        return "visual_comparison_noise"
    # Testimonial quotes are valid proof evidence, while group selection keeps
    # them out of mission/value-proposition groups.
    if (
        "api dashboard try" in low
        or "try api for free" in low
        or "one platform, two great hosting paths" in low
        or low in {"api dashboard", "dashboard"}
        or ("products pricing" in low and len(low) < 90)
    ):
        return "navigation_or_cta_noise"
    profile_hits = sum(1 for marker in ("employs", "founded in", "headquartered", "total funding", "yoy") if marker in low)
    if profile_hits >= 2:
        return "company_profile_metadata"
    if "manufacturing company" in low and "wide range of products" in low:
        return "company_profile_metadata"
    if re.match(r"^[a-z0-9 .,&()-]{2,90} is a [a-z &-]+ company\. .{0,90}\bis a ", low):
        return "company_profile_metadata"
    nav_hits = sum(
        1
        for marker in (
            "pricing", "customers", "partners", "log in", "book demo", "open positions",
            "solutions", "resources", "backed by", "join us", "about us", "contact", "sign up",
        )
        if marker in low
    )
    if nav_hits >= 3:
        return "navigation_or_hiring_noise"
    if any(marker in low for marker in ("/news/", "/blog/", "read more", "press release")):
        return "article_or_navigation_noise"
    if "hashtag" in low and any(marker in low for marker in ("instagram", "comparte tus propias fotos", "inspírate", "inspirate")):
        return "article_or_navigation_noise"
    if "operando en más de" in low or "operando en mas de" in low:
        return "company_profile_metadata"
    if "cookies" in low or "cookie" in low:
        return "legal_or_footer_noise"
    if "carrito de compra" in low:
        return "navigation_or_cta_noise"
    if "special price" in low and len(low) < 80:
        return "navigation_or_section_heading_noise"
    if "to showcase" in low and (" at " in low or "conference" in low):
        return "promotion_or_event_noise"
    if _looks_like_promotion_or_event(low) and not any(marker in low for marker in ("platform", "software", "api")):
        return "promotion_or_event_noise"
    if _looks_like_ecommerce_grid_noise(low):
        return "navigation_or_cta_noise"
    if "magic quadrant" in low or "named a leader" in low:
        return "analyst_report_or_award_noise"
    return None


def _looks_like_image_or_logo_noise(text: str, low: str) -> bool:
    return (
        "![" in text
        or "_next/image" in low
        or "copy svg" in low
        or "download svg" in low
        or "get the sentry logo" in low
        or "customer logos" in low
        or re.search(r"\b(?:logo|logos)\b", low) and "http" in low
    )


def _looks_like_ecommerce_grid_noise(low: str) -> bool:
    ecommerce_nav_hits = sum(
        1
        for marker in (
            "view more",
            "view collection",
            "shop now",
            "special price",
            "buscar producto",
            "back in stock",
            "new trending",
            "código:",
            "codigo:",
            "finalizan en",
            "obtén un",
            "obten un",
        )
        if marker in low
    )
    category_hits = sum(
        1
        for marker in (
            "sillas",
            "sofás",
            "sofas",
            "mesas",
            "taburetes",
            "almacenaje",
            "decoración",
            "decoracion",
            "iluminación",
            "iluminacion",
            "textil",
            "electrodomésticos",
            "electrodomesticos",
            "jardín",
            "jardin",
        )
        if marker in low
    )
    return ecommerce_nav_hits >= 2 or (ecommerce_nav_hits >= 1 and category_hits >= 4)


def _looks_like_legal_or_footer_noise(low: str) -> bool:
    legal_hits = sum(
        1
        for marker in (
            "privacy policy",
            "política de privacidad",
            "politica de privacidad",
            "política de cookies",
            "politica de cookies",
            "terms of service",
            "copyright",
            "all rights reserved",
            "legal entity",
            "aviso legal",
            "protección de datos",
            "proteccion de datos",
            "información personal",
            "informacion personal",
            "datos personales",
            "legislación vigente",
            "legislacion vigente",
            "medidas técnicas y organizativas",
            "medidas tecnicas y organizativas",
            "rgpd",
            "lssi",
            "effective date",
            "last updated",
            "opt-out",
        )
        if marker in low
    )
    if legal_hits >= 1 and any(
        marker in low
        for marker in (
            "policy",
            "política",
            "politica",
            "terms",
            "copyright",
            "legal",
            "all rights",
            "protección de datos",
            "proteccion de datos",
            "información personal",
            "informacion personal",
            "datos personales",
            "legislación vigente",
            "legislacion vigente",
            "medidas técnicas y organizativas",
            "medidas tecnicas y organizativas",
            "rgpd",
            "lssi",
        )
    ):
        return True
    nav_hits = sum(
        1
        for marker in ("company", "blog", "careers", "pricing", "docs", "support", "resources", "status")
        if marker in low
    )
    return nav_hits >= 5 and ("copyright" in low or "privacy" in low or "terms" in low)


def _looks_like_directory_profile_noise(low: str) -> bool:
    return any(
        marker in low
        for marker in (
            "company profile & funding",
            "company profile, team, funding",
            "pitchbook",
            "crunchbase",
            "tracxn",
            "your browser was unable to load",
            "leadership hire last 30 days",
            "boeing is among the largest global aerospace manufacturers",
        )
    )


def _looks_like_customer_story_fragment(low: str) -> bool:
    return (
        low.startswith("read story]")
        or "read story](" in low
        or "customers/" in low and ("![" in low or "**" in low or "_next/image" in low)
    )


def _looks_truncated(low: str) -> bool:
    return bool(re.search(r"\b(?:throu|softwar|platfor|developmen|infrastructur|users?|c|w|cr)\s*$", low.strip(), re.I))


def _looks_like_testimonial_quote(low: str) -> bool:
    stripped = low.strip()
    if not stripped.startswith(("“", '"', "> “", ">")):
        return False
    return any(
        marker in stripped
        for marker in (
            " for us",
            " customer",
            " using ",
            " nos ofrece",
            " nos ayuda",
            " servicio al cliente",
            " procesos de trabajo",
        )
    )
