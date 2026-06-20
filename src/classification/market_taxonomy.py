"""Controlled Brand3 market taxonomy.

The taxonomy is inspired by company intelligence products but is owned by
Brand3: each tag has a definition, aliases, and a clear group. These tags are
context only, not scoring inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

TAXONOMY_VERSION = "brand3_market_classification_v0_1"

GROUPS = (
    "business_model",
    "sector_industry",
    "technology_capability",
    "market_signals",
    "corporate_status",
)

CONFIDENCE_LEVELS = ("high", "medium", "low")
TAG_STATUSES = ("proposed", "accepted", "rejected", "stale")
CLASSIFIERS = ("heuristic", "llm", "manual")


@dataclass(frozen=True)
class TagDefinition:
    tag: str
    group: str
    definition: str
    aliases: tuple[str, ...] = ()


def _tag(
    group: str,
    tag: str,
    definition: str,
    aliases: tuple[str, ...] = (),
) -> TagDefinition:
    return TagDefinition(tag=tag, group=group, definition=definition, aliases=aliases)


TAXONOMY: dict[str, tuple[TagDefinition, ...]] = {
    "business_model": (
        _tag("business_model", "B2B", "Sells primarily to businesses or professional teams."),
        _tag("business_model", "B2C", "Sells primarily to consumers or individual users."),
        _tag(
            "business_model",
            "SaaS",
            "Software delivered as a hosted service.",
            ("software as a service",),
        ),
        _tag("business_model", "subscription", "Recurring paid access model."),
        _tag("business_model", "marketplace", "Connects two or more sides of a transaction."),
        _tag(
            "business_model",
            "platform",
            "Provides a base product other users or businesses build on.",
        ),
        _tag("business_model", "services", "Sells human-delivered or agency-like services."),
        _tag("business_model", "enterprise", "Targets large organizations or enterprise buyers."),
        _tag("business_model", "consumer", "Targets individual consumer usage."),
        _tag(
            "business_model",
            "open_source",
            "Product or core distribution is open source.",
            ("oss", "open source"),
        ),
    ),
    "sector_industry": (
        _tag(
            "sector_industry",
            "artificial intelligence",
            "AI as primary market category.",
            ("ai",),
        ),
        _tag("sector_industry", "media", "Media, publishing, entertainment, or audience business."),
        _tag("sector_industry", "content production", "Tools or services for creating content."),
        _tag(
            "sector_industry",
            "fintech",
            "Financial technology, payments, banking, or spend management.",
        ),
        _tag("sector_industry", "cybersecurity", "Security, trust, identity, or risk products."),
        _tag(
            "sector_industry",
            "healthcare",
            "Healthcare, wellness, clinical, or medical products.",
        ),
        _tag(
            "sector_industry",
            "education",
            "Learning, training, education, or knowledge products.",
        ),
        _tag(
            "sector_industry",
            "infrastructure",
            "Technical infrastructure, cloud, data, or developer foundations.",
        ),
        _tag("sector_industry", "design", "Design, creative tooling, or visual production."),
        _tag("sector_industry", "ecommerce", "Commerce, retail, stores, or DTC selling."),
        _tag(
            "sector_industry",
            "marketing technology",
            "Marketing, growth, CRM, or campaign tooling.",
            ("martech",),
        ),
        _tag(
            "sector_industry",
            "developer tools",
            "Tools built for software developers.",
            ("devtools",),
        ),
        _tag(
            "sector_industry",
            "project management",
            "Planning, issue tracking, work management, or collaboration.",
        ),
    ),
    "technology_capability": (
        _tag(
            "technology_capability",
            "generative AI",
            "Generates text, image, audio, video, code, or synthetic content.",
            ("genai", "gen ai", "generative ai"),
        ),
        _tag(
            "technology_capability",
            "image recognition",
            "Detects, classifies, or understands image contents.",
        ),
        _tag("technology_capability", "image generation", "Generates or transforms images."),
        _tag(
            "technology_capability",
            "natural language processing",
            "Processes or understands human language.",
            ("nlp",),
        ),
        _tag("technology_capability", "automation", "Automates workflows, tasks, or operations."),
        _tag(
            "technology_capability",
            "data infrastructure",
            "Stores, moves, transforms, or serves data.",
        ),
        _tag("technology_capability", "analytics", "Measures, reports, or analyzes data."),
        _tag("technology_capability", "blockchain", "Uses blockchain or crypto rails."),
        _tag("technology_capability", "computer vision", "Understands or processes visual inputs."),
        _tag(
            "technology_capability",
            "API",
            "Exposes a programmable interface for product use.",
            ("api",),
        ),
        _tag(
            "technology_capability",
            "workflow orchestration",
            "Coordinates multi-step operational workflows.",
        ),
    ),
    "market_signals": (
        _tag(
            "market_signals",
            "funding announced",
            "Public funding round or investment announcement.",
        ),
        _tag("market_signals", "accelerator backed", "Backed by a recognized accelerator."),
        _tag(
            "market_signals",
            "fast growth list",
            "Included in a public growth ranking or list.",
            ("ft 1000", "techscale200"),
        ),
        _tag(
            "market_signals",
            "enterprise adoption",
            "Public enterprise customer adoption signal.",
        ),
        _tag("market_signals", "press coverage", "Covered by a relevant third-party publication."),
        _tag("market_signals", "award", "Received a public award."),
        _tag(
            "market_signals",
            "public customer logos",
            "Shows public customer logos or named customers.",
        ),
    ),
    "corporate_status": (
        _tag("corporate_status", "acquired", "Company has been acquired."),
        _tag(
            "corporate_status",
            "subsidiary",
            "Company operates as a subsidiary.",
            ("became subsidiary",),
        ),
        _tag("corporate_status", "merged", "Company has merged with another entity."),
        _tag("corporate_status", "rebranded", "Company has changed its market identity or name."),
        _tag(
            "corporate_status",
            "stealth",
            "Company is intentionally operating with limited public information.",
        ),
        _tag("corporate_status", "active", "Company appears active in market."),
        _tag("corporate_status", "inactive", "Company appears inactive or discontinued."),
    ),
}


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


_ALIAS_INDEX: dict[tuple[str, str], str] = {}
for group, definitions in TAXONOMY.items():
    for definition in definitions:
        _ALIAS_INDEX[(group, _norm(definition.tag))] = definition.tag
        for alias in definition.aliases:
            _ALIAS_INDEX[(group, _norm(alias))] = definition.tag


def canonical_tag(group: str, value: str) -> str | None:
    """Return the controlled tag for a group/value pair, if allowed."""
    if group not in TAXONOMY:
        return None
    return _ALIAS_INDEX.get((group, _norm(value)))


def tag_definition(group: str, value: str) -> TagDefinition | None:
    canonical = canonical_tag(group, value)
    if canonical is None:
        return None
    for definition in TAXONOMY[group]:
        if definition.tag == canonical:
            return definition
    return None


def tags_for_group(group: str) -> tuple[str, ...]:
    return tuple(definition.tag for definition in TAXONOMY.get(group, ()))
