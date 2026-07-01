"""Adapters from SV9 Flow contracts to the current SV9 evaluator inputs."""

from __future__ import annotations

from typing import Any

from src.sv9_flow._utils import unique_strings
from src.sv9_flow.contracts import EvidenceRecord, Sv9FlowCandidate

SV9_FLOW_TLDR_ADAPTER_VERSION = "sv9-flow-tldr-adapter-v1"
SV9_FLOW_TLDR_MODE = "sv9_flow"
_MAX_EVIDENCE_ITEMS = 5
_MAX_EVIDENCE_CHARS = 700


def build_tldr_from_flow_candidate(candidate: Sv9FlowCandidate) -> dict[str, dict[str, Any]]:
    """Convert a flow candidate into the TLDR block shape read by SV9.

    This is a compatibility adapter for shadow evaluation. It does not produce
    a score and it does not reinterpret evidence; it only maps flow block refs
    back to evidence snippets that the current tile evaluator can cite.
    """

    evidence_by_ref = {record.ref: record for record in candidate.evidence_pack.evidence}
    tldr: dict[str, dict[str, Any]] = {}
    for block_name, block in sorted(candidate.interpretation.blocks.items()):
        if not isinstance(block, dict):
            continue
        refs = unique_strings(candidate.interpretation.evidence_refs.get(block_name, []))
        content = str(block.get("content") or "").strip()
        detected = bool(block.get("detected")) and bool(content)
        tldr[block_name] = {
            "detected": detected,
            "content": content,
            "confidence": _confidence(block.get("confidence")),
            "mode": SV9_FLOW_TLDR_MODE,
            "rationale": str(block.get("rationale") or "").strip(),
            "limitations": _block_limitations(block_name, candidate.limitations),
            "evidence": _evidence_snippets(refs, evidence_by_ref),
            "evidence_refs": refs[:_MAX_EVIDENCE_ITEMS],
            "source": "sv9_flow",
            "adapter_version": SV9_FLOW_TLDR_ADAPTER_VERSION,
        }
    return tldr


def build_magnetism_result_from_flow_candidate(
    candidate: Sv9FlowCandidate,
    *,
    source_run_id: int | str | None = None,
) -> dict[str, Any]:
    """Build the minimal scanner-like payload accepted by `src.sv9.service`."""

    payload: dict[str, Any] = {
        "brand_name": candidate.evidence_pack.brand_name,
        "source_url": candidate.evidence_pack.url,
        "tldr_brand3": build_tldr_from_flow_candidate(candidate),
        "sv9_flow_adapter_version": SV9_FLOW_TLDR_ADAPTER_VERSION,
        "sv9_flow_candidate_schema_version": candidate.schema_version,
        "limitations": unique_strings(candidate.limitations),
    }
    if source_run_id is not None:
        payload["source_run_id"] = source_run_id
    return payload


def _evidence_snippets(
    refs: list[str],
    evidence_by_ref: dict[str, EvidenceRecord],
) -> list[str]:
    snippets: list[str] = []
    for ref in refs:
        record = evidence_by_ref.get(ref)
        if record is None:
            continue
        content = " ".join(record.content.split())
        if not content:
            continue
        snippets.append(content[:_MAX_EVIDENCE_CHARS])
    return unique_strings(snippets)[:_MAX_EVIDENCE_ITEMS]


def _confidence(value: Any) -> str:
    confidence = str(value or "").strip().lower()
    return confidence if confidence in {"low", "medium", "high"} else "medium"


def _block_limitations(block_name: str, limitations: list[str]) -> list[str]:
    terms = _limitation_terms(block_name)
    if not terms:
        return []
    matches: list[str] = []
    for limitation in limitations:
        text = str(limitation or "").strip()
        haystack = text.lower()
        if text and any(term in haystack for term in terms):
            matches.append(text)
    return unique_strings(matches)[:_MAX_EVIDENCE_ITEMS]


def _limitation_terms(block_name: str) -> tuple[str, ...]:
    if block_name == "magnetism":
        return (
            "magnetism",
            "community",
            "developer advocacy",
            "organic growth",
            "growth statistics",
            "market pull",
            "traction",
            "demand",
        )
    if block_name == "vision":
        return ("vision", "future", "long-term", "long term", "aspiration")
    if block_name == "values":
        return ("values", "principles", "beliefs", "culture")
    return (block_name,)
