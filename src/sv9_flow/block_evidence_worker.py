"""Deterministic block evidence shortlist worker for SV9 Flow."""

from __future__ import annotations

from dataclasses import dataclass

from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord

BLOCK_EVIDENCE_SHORTLIST_VERSION = "sv9-flow-block-evidence-shortlists-v1"

_DEFAULT_LIMIT = 5

_BLOCK_TERMS: dict[str, tuple[str, ...]] = {
    "vision": (
        "vision",
        "future",
        "aspiration",
        "ambition",
        "become",
        "toward",
        "long-term",
        "next generation",
        "category leader",
    ),
    "brand_idea": (
        "idea",
        "concept",
        "tagline",
        "slogan",
        "methodology",
        "platform",
        "visual",
        "signature",
        "distinctive",
        "ownable",
        "unique",
        "unique_phrases",
        "phrase",
        "vocabulary",
        "brand_vocabulary",
        "differentiator",
        "differentiator_claimed",
        "claimed",
    ),
    "attributes": (
        "attribute",
        "attributes",
        "specialized",
        "boutique",
        "fast",
        "simple",
        "modern",
        "expert",
        "developer",
        "professional",
    ),
    "personality": (
        "personality",
        "tone",
        "voice",
        "pragmatic",
        "direct",
        "human",
        "professional",
        "technical",
        "casual",
        "accessible",
    ),
    "mission": ("mission", "helps", "provide", "enable", "specializes", "serves", "build"),
    "value_proposition": (
        "value proposition",
        "offer",
        "offers",
        "helps",
        "provides",
        "for teams",
        "customers",
        "financial",
        "measurable",
        "defendable",
        "investment",
        "capital",
        "euros",
        "translate",
        "traduce",
        "argumento",
        "monetización",
    ),
    "core_purpose": ("purpose", "why", "enable", "help", "free", "maximize", "discover"),
    "values": ("values", "principles", "beliefs", "clarity", "efficiency", "empathy", "collaboration"),
    "magnetism": ("magnetism", "momentum", "affinity", "engagement", "community", "recognizable", "demand"),
}

_TYPE_BONUS: dict[str, int] = {
    "raw_input": 1,
    "visual_tile_signal": 1,
    "visual_capture": 0,
}

_FEATURE_BONUS_TERMS = (
    "positioning",
    "tone",
    "visual",
    "brand",
    "personality",
    "consistency",
    "diferenciacion",
    "coherencia",
)

_TEXT_STRATEGY_BLOCKS = {
    "brand_idea",
    "mission",
    "vision",
    "value_proposition",
    "core_purpose",
    "values",
}


@dataclass(frozen=True, slots=True)
class BlockEvidenceShortlist:
    block: str
    evidence_refs: list[str]
    version: str = BLOCK_EVIDENCE_SHORTLIST_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "block": self.block,
            "evidence_refs": list(self.evidence_refs),
        }


def build_block_evidence_shortlists(
    evidence_pack: BrandEvidencePack,
    *,
    blocks: tuple[str, ...] | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, list[str]]:
    """Select stable evidence refs per block before LLM drafting."""

    block_names = blocks or tuple(_BLOCK_TERMS)
    return {
        block: _shortlist_for_block(block, evidence_pack.evidence, limit=limit)
        for block in block_names
    }


def _shortlist_for_block(block: str, evidence: list[EvidenceRecord], *, limit: int) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, record in enumerate(evidence):
        score = _score_record(block, record)
        if score <= 0:
            continue
        scored.append((-score, index, record.ref))
    scored.sort()
    refs: list[str] = []
    for _, _, ref in scored:
        if ref not in refs:
            refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def _score_record(block: str, record: EvidenceRecord) -> int:
    terms = _BLOCK_TERMS.get(block, ())
    haystack = " ".join(
        (
            record.evidence_type,
            record.source,
            record.content,
            " ".join(str(value) for value in record.metadata.values()),
        )
    ).lower()
    score = sum(3 for term in terms if term in haystack)
    score += _TYPE_BONUS.get(record.evidence_type, 0)
    if block in _TEXT_STRATEGY_BLOCKS:
        if record.ref.startswith("visual_signature.") or record.source == "visual_signature":
            score -= 5
        if record.ref.startswith("raw_inputs."):
            score += 2
    if record.ref.startswith("features."):
        score += sum(1 for term in _FEATURE_BONUS_TERMS if term in haystack)
    if record.confidence == "high":
        score += 1
    return score
