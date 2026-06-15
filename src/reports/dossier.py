"""
Build the report dossier/view-model from a run snapshot.

This module owns the orchestration that combines:
  - deterministic context derivation from the SQLite snapshot
  - narrative overlays (synthesis, findings, tensions)

The renderer should stay presentation-only and consume the dossier returned
here without needing to know about snapshot internals.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .derivation import (
    Evidence,
    build_report_base,
    build_report_context_from_base,
    collect_evidences,
    derive_data_quality,
    group_by_dimension,
)
from .evidence_packet import build_evidence_packet_v0
from .narrative import (
    Finding,
    SynthesisContext,
    generate_all_findings,
    generate_synthesis,
    generate_tensions,
)

log = logging.getLogger("brand3.reports.dossier")

REPORT_NARRATIVE_SOURCE = "report_narrative"
REPORT_NARRATIVE_VERSION = 1


def build_brand_dossier(
    snapshot: dict,
    theme: str = "dark",
    analyzer=None,
    *,
    enable_perceptual_narrative: bool = False,
    prefer_persisted_narrative: bool = True,
    narrative_payload: dict[str, Any] | None = None,
) -> dict:
    """Build the full report dossier from a run snapshot.

    The returned dict keeps the legacy flat report keys for template
    compatibility, but it is now built from a richer base dossier shape
    (`brand`, `evaluation`, `narrative`, `sources`, `audit`, `ui`) that other
    surfaces can reuse directly later.
    """
    base = build_report_base(snapshot, theme=theme)
    persisted_narrative = narrative_payload or (
        _latest_persisted_report_narrative(snapshot)
        if prefer_persisted_narrative
        else None
    )
    if persisted_narrative:
        _apply_persisted_report_narrative(base, persisted_narrative)
    else:
        _apply_narrative(
            base,
            snapshot,
            analyzer,
            enable_perceptual_narrative=enable_perceptual_narrative,
        )
    return build_report_context_from_base(base)


def build_report_narrative_payload(
    snapshot: dict,
    analyzer=None,
    *,
    enable_perceptual_narrative: bool = False,
    analyst_pass: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate the persisted narrative overlay for a run snapshot.

    This is intended for audit finalization/backfill, not public report reads.
    Public reads consume the returned payload from storage and never call LLM.
    """
    payload = build_report_narrative_payload_from_analyst(snapshot, analyst_pass)
    if payload is not None:
        return payload

    dossier = build_brand_dossier(
        snapshot,
        analyzer=analyzer,
        enable_perceptual_narrative=enable_perceptual_narrative,
        prefer_persisted_narrative=False,
    )
    return {
        "version": REPORT_NARRATIVE_VERSION,
        "source": REPORT_NARRATIVE_SOURCE,
        "generated_at": datetime.now().isoformat(),
        "run_id": (snapshot.get("run") or {}).get("id"),
        "synthesis_prose": dossier.get("synthesis_prose") or "",
        "summary": dossier.get("summary") or "",
        "tensions_prose": dossier.get("tensions_prose"),
        "findings_by_dimension": {
            dim.get("name"): [
                _finding_to_payload(finding)
                for finding in (dim.get("findings") or [])
            ]
            for dim in (dossier.get("dimensions") or [])
            if dim.get("name")
        },
    }


def build_report_narrative_payload_from_analyst(
    snapshot: dict,
    analyst_pass: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(analyst_pass, dict) or analyst_pass.get("analysis_error"):
        return None

    summary = str(analyst_pass.get("executive_summary") or "").strip()
    dimensions = analyst_pass.get("dimensions")
    if not summary or not isinstance(dimensions, dict):
        return None

    findings_by_dimension: dict[str, list[dict[str, Any]]] = {}
    for name, block in dimensions.items():
        if not isinstance(name, str) or not isinstance(block, dict):
            continue
        finding = _finding_payload_from_analyst_dimension(block)
        if finding is not None:
            findings_by_dimension[name] = [finding]

    if not findings_by_dimension:
        return None

    primary_risk = str(analyst_pass.get("primary_risk") or "").strip()
    primary_opportunity = str(analyst_pass.get("primary_opportunity") or "").strip()
    tension_parts = []
    if primary_risk:
        tension_parts.append(f"Primary risk: {primary_risk}")
    if primary_opportunity:
        tension_parts.append(f"Primary opportunity: {primary_opportunity}")

    return {
        "version": REPORT_NARRATIVE_VERSION,
        "source": REPORT_NARRATIVE_SOURCE,
        "generated_at": datetime.now().isoformat(),
        "run_id": (snapshot.get("run") or {}).get("id"),
        "synthesis_prose": summary,
        "summary": summary,
        "tensions_prose": " ".join(tension_parts) or None,
        "findings_by_dimension": findings_by_dimension,
    }


def _finding_payload_from_analyst_dimension(block: dict[str, Any]) -> dict[str, Any] | None:
    diagnosis = str(block.get("diagnosis") or "").strip()
    findings = [
        str(item).strip()
        for item in (block.get("findings") or [])
        if str(item).strip()
    ]
    evidence = [
        str(item).strip()
        for item in (block.get("evidence") or [])
        if str(item).strip()
    ]
    recommendation = str(block.get("recommendation") or "").strip()
    limitations = [
        str(item).strip()
        for item in (block.get("limitations") or [])
        if str(item).strip()
    ]

    title = diagnosis or (findings[0] if findings else "")
    observation_parts = findings[:2] or evidence[:2]
    implication_parts = []
    if recommendation:
        implication_parts.append(recommendation)
    if limitations:
        implication_parts.append("Limitations: " + "; ".join(limitations[:2]))

    observation = " ".join(observation_parts).strip()
    implication = " ".join(implication_parts).strip()
    if not title or not observation:
        return None
    return {
        "title": title,
        "observation": observation,
        "implication": implication,
        "typical_decision": "",
        "evidence_urls": [],
    }


def _latest_persisted_report_narrative(snapshot: dict) -> dict[str, Any] | None:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != REPORT_NARRATIVE_SOURCE:
            continue
        payload = item.get("payload")
        if isinstance(payload, dict) and payload.get("version") == REPORT_NARRATIVE_VERSION:
            return payload
    return None


def _apply_persisted_report_narrative(base: dict, payload: dict[str, Any]) -> None:
    synthesis = str(
        payload.get("synthesis_prose") or payload.get("summary") or ""
    ).strip()
    if synthesis:
        base["narrative"]["summary"] = synthesis
        base["narrative"]["synthesis_prose"] = synthesis
    if payload.get("tensions_prose"):
        base["narrative"]["tensions_prose"] = str(payload["tensions_prose"]).strip()

    findings_by_dimension = payload.get("findings_by_dimension") or {}
    if not isinstance(findings_by_dimension, dict):
        return
    for dim in base["dimensions"]:
        raw_findings = findings_by_dimension.get(dim["name"]) or []
        if not isinstance(raw_findings, list):
            continue
        dim["findings"] = [
            finding
            for finding in (_finding_from_payload(item) for item in raw_findings)
            if finding is not None
        ]


def _finding_to_payload(finding: Finding | dict[str, Any]) -> dict[str, Any]:
    if isinstance(finding, Finding) or (
        hasattr(finding, "title")
        and hasattr(finding, "observation")
        and hasattr(finding, "implication")
    ):
        return {
            "title": finding.title,
            "observation": finding.observation,
            "implication": finding.implication,
            "typical_decision": getattr(finding, "typical_decision", ""),
            "evidence_urls": list(getattr(finding, "evidence_urls", [])),
        }
    return {
        "title": str(finding.get("title") or ""),
        "observation": str(finding.get("observation") or finding.get("prose") or ""),
        "implication": str(finding.get("implication") or ""),
        "typical_decision": str(finding.get("typical_decision") or ""),
        "evidence_urls": [
            str(url)
            for url in (finding.get("evidence_urls") or [])
            if isinstance(url, str)
        ],
    }


def _finding_from_payload(item: Any) -> Finding | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    observation = str(item.get("observation") or item.get("prose") or "").strip()
    if not title or not observation:
        return None
    evidence_urls = item.get("evidence_urls") or []
    if not isinstance(evidence_urls, list):
        evidence_urls = []
    return Finding(
        title=title,
        observation=observation,
        implication=str(item.get("implication") or "").strip(),
        typical_decision=str(item.get("typical_decision") or "").strip(),
        evidence_urls=[str(url) for url in evidence_urls if isinstance(url, str)],
    )


def _pick_top_evidences(evidences: list[Evidence], limit: int = 4) -> list[Evidence]:
    """Pick up to `limit` evidences with a non-empty quote, maximizing diversity
    of source_type. Fills the remainder with whatever is left once every bucket
    has been represented once.
    """
    with_quote = [ev for ev in evidences if ev.quote]
    if not with_quote:
        return []
    seen_types: set[str] = set()
    picked: list[Evidence] = []
    for ev in with_quote:
        if ev.source_type in seen_types:
            continue
        seen_types.add(ev.source_type)
        picked.append(ev)
        if len(picked) >= limit:
            return picked
    for ev in with_quote:
        if ev in picked:
            continue
        picked.append(ev)
        if len(picked) >= limit:
            break
    return picked


def _apply_narrative(
    base: dict,
    snapshot: dict,
    analyzer,
    *,
    enable_perceptual_narrative: bool = False,
) -> None:
    """Mutate the structured base dossier with LLM-generated narrative overlays.

    On any failure the relevant slot keeps the deterministic placeholder
    already populated by `build_report_base`.
    """
    run = snapshot.get("run") or {}
    brand = base["brand"]["name"]
    run_id = run.get("id")
    analysis_date = run.get("completed_at") or run.get("started_at")
    composite = run.get("composite_score")
    if composite is not None and not isinstance(composite, (int, float)):
        composite = None

    evidences = collect_evidences(snapshot)
    dim_evs = group_by_dimension(evidences, snapshot)
    data_quality = derive_data_quality(snapshot)
    context_readiness = (base.get("evaluation") or {}).get("context_readiness", {})
    context_status = context_readiness.get("status")
    if context_readiness.get("available") and context_status == "insufficient_data":
        base["narrative"]["summary"] = (
            base["narrative"]["summary"]
            + " Context pre-scan found insufficient machine-readable coverage."
        )
        base["narrative"]["synthesis_prose"] = base["narrative"]["summary"]
        return

    try:
        packet = build_evidence_packet_v0(snapshot)
    except Exception as exc:
        log.warning("dossier: failed to build evidence packet: %s", exc)
        packet = None

    try:
        findings_by_dim = generate_all_findings(
            dim_evs,
            brand,
            analyzer=analyzer,
            run_id=run_id,
            analysis_date=analysis_date,
            enable_perceptual_narrative=enable_perceptual_narrative,
            packet=packet,
        )
    except Exception as exc:
        log.warning("narrative.generate_all_findings failed: %s", exc)
        findings_by_dim = {}
    for dim in base["dimensions"]:
        dim["findings"] = findings_by_dim.get(dim["name"], [])

    try:
        tensions = generate_tensions(
            dim_evs,
            brand,
            analyzer=analyzer,
            run_id=run_id,
            analysis_date=analysis_date,
        )
    except Exception as exc:
        log.warning("narrative.generate_tensions failed: %s", exc)
        tensions = None
    base["narrative"]["tensions_prose"] = tensions

    synth_ctx = SynthesisContext(
        brand=brand,
        url=base["brand"].get("url") or "",
        composite_score=composite,
        dimensions=dim_evs,
        data_quality=data_quality,
        top_evidences=_pick_top_evidences(evidences, limit=4),
        analysis_date=analysis_date,
        tension_text=tensions,
    )
    try:
        synthesis = generate_synthesis(synth_ctx, analyzer=analyzer, run_id=run_id)
    except Exception as exc:
        log.warning("narrative.generate_synthesis failed: %s", exc)
        synthesis = None
    if synthesis:
        base["narrative"]["synthesis_prose"] = synthesis
        base["narrative"]["summary"] = synthesis
