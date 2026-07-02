"""Native SV9 ingress for SV9 Flow candidates.

Resolves an Sv9FlowCandidate into the two inputs the evaluator consumes —
per-block detection input and per-component tile signals — so the flow does
not have to disguise itself as a scanner/Magnetism payload to be scored.

Imports from sv9_flow are restricted to contracts; that direction is enforced
by tests/test_sv9_flow_architecture.py.
"""

from __future__ import annotations

from typing import Any

from src.sv9_flow.contracts import EvidenceRecord, Sv9FlowCandidate

SV9_FLOW_INGRESS_VERSION = "sv9-flow-ingress-v1"
SV9_FLOW_DETECTION_MODE = "sv9_flow"
_MAX_EVIDENCE_ITEMS = 5
_MAX_EVIDENCE_CHARS = 700


def detection_blocks_from_flow_candidate(candidate: Sv9FlowCandidate) -> dict[str, dict[str, Any]]:
    """Build the evaluator's per-block detection input from a flow candidate.

    Same keys the evaluator reads from a tldr_brand3 block: detected, content,
    confidence, mode, rationale, limitations, evidence. It does not produce a
    score and it does not reinterpret evidence; it only resolves block refs
    back to snippets the tile evaluator can cite.
    """

    evidence_by_ref = {record.ref: record for record in candidate.evidence_pack.evidence}
    blocks: dict[str, dict[str, Any]] = {}
    for block_name, block in sorted(candidate.interpretation.blocks.items()):
        if not isinstance(block, dict):
            continue
        refs = _unique_strings(candidate.interpretation.evidence_refs.get(block_name, []))
        content = str(block.get("content") or "").strip()
        # SV9 must never score a detected block without evidence refs,
        # regardless of which producer built the candidate.
        detected = bool(block.get("detected")) and bool(content) and bool(refs)
        limitations = _block_limitations(block_name, candidate.limitations)
        if bool(block.get("detected")) and bool(content) and not refs:
            limitations = limitations + ["contract_violation:detected_without_evidence_refs"]
        blocks[block_name] = {
            "detected": detected,
            "content": content,
            "confidence": _confidence(block.get("confidence")),
            "mode": SV9_FLOW_DETECTION_MODE,
            "rationale": str(block.get("rationale") or "").strip(),
            "limitations": limitations,
            "evidence": _evidence_snippets(refs, evidence_by_ref),
            "evidence_refs": refs[:_MAX_EVIDENCE_ITEMS],
            "source": "sv9_flow",
            "ingress_version": SV9_FLOW_INGRESS_VERSION,
        }
    return blocks


def flow_candidate_extra_signals(candidate: Sv9FlowCandidate) -> dict[str, list[dict[str, Any]]]:
    """Group the candidate's tile signals per component for the evaluator."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for signal in candidate.tile_signals:
        component = str(signal.component or "").strip()
        if not component:
            continue
        grouped.setdefault(component, []).append(
            {
                "feature": "sv9_flow_tile_signal",
                "legacy_dimension": signal.schema_version,
                "value": signal.effect,
                "confidence": signal.confidence,
                "source": signal.source,
                "tile": signal.tile,
                "effect": signal.effect,
                "evidence_refs": list(signal.evidence_refs),
                "rationale": signal.rationale,
                "detail": (
                    f"tile={signal.tile}; effect={signal.effect}; "
                    f"rationale={signal.rationale}; evidence_refs={', '.join(signal.evidence_refs)}"
                ),
            }
        )
    return grouped


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
    return _unique_strings(snippets)[:_MAX_EVIDENCE_ITEMS]


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
    return _unique_strings(matches)[:_MAX_EVIDENCE_ITEMS]


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


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
