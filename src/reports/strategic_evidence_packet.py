"""Strategic evidence packet derived from Brand Audit snapshots.

Brand Audit owns data collection. This module turns a persisted run snapshot into
small, named evidence groups that downstream interpreters can reuse without
reading raw scraper text or internal feature metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.reports.derivation import Evidence, collect_evidences


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
    ),
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
        "asesores",
        "empresas",
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
        "build relationships",
        "get things done",
        "improve product discovery",
        "increasing conversions",
        "reduce no-result searches",
        "streamline",
        "centralise",
        "centralize",
        "gestionar",
        "hacer crecer",
        "automatizar",
        "empowering",
        "impulsando",
    ),
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
        "transform",
        "shape the future",
        "creative entity",
        "creative work",
        "wield power",
        "world stage",
        "futuro de",
        "nuevo modelo",
        "nueva generación",
        "transformar",
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
    ),
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
        "trusted by",
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_type": self.source_type,
            "source_domain": self.source_domain,
            "url": self.url,
            "feature_name": self.feature_name,
            "dimension": self.dimension,
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


def _line_priority(line: StrategicEvidenceLine, group: str) -> tuple[int, int, int, int, int]:
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
    useful_length = min(len(line.text), 260)
    return (source_rank, noise_rank, feature_rank, context_rank, -useful_length)


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
    return any(marker in low for marker in (" + ", "products", "services", "platform", "infrastructure", "software delivery", "financial services"))


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
        text = str(payload.get("markdown_content") or payload.get("content") or "")
        if not text:
            continue
        source_url = str(payload.get("canonical_url") or run_url)
        added = 0
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
            )
            after = sum(len(values) for values in packet.groups.values())
            if after > before:
                added += 1
            if added >= 24:
                break


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

    groups = _groups_for(cleaned, source_type)
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


def _groups_for(text: str, source_type: str) -> list[str]:
    low = text.lower()
    groups = [
        group
        for group, keywords in GROUP_KEYWORDS.items()
        if any(keyword in low for keyword in keywords)
    ]
    if source_type not in OWNED_SOURCE_TYPES and groups:
        groups = [group for group in groups if group in {"proof_points", "third_party_context"}]
        if "third_party_context" not in groups:
            groups.append("third_party_context")
    return groups


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
    if text.strip().startswith("!["):
        return "image_alt_text_noise"
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
    if (low.startswith("“") or low.startswith('"')) and (" for us" in low or " customer" in low or " using " in low):
        return "testimonial_quote_noise"
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
    if "to showcase" in low and (" at " in low or "conference" in low):
        return "promotion_or_event_noise"
    if _looks_like_promotion_or_event(low) and not any(marker in low for marker in ("platform", "software", "api")):
        return "promotion_or_event_noise"
    if "magic quadrant" in low or "named a leader" in low:
        return "analyst_report_or_award_noise"
    return None
