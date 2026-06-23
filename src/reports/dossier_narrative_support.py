"""Payload conversion helpers for persisted report narrative overlays."""

from __future__ import annotations

from typing import Any

from .narrative_types import Finding

REPORT_NARRATIVE_SOURCE = "report_narrative"
REPORT_NARRATIVE_VERSION = 1


def _finding_payload_from_analyst_dimension(block: dict[str, Any]) -> dict[str, Any] | None:
    diagnosis = str(block.get("diagnosis") or "").strip()
    findings = [str(item).strip() for item in (block.get("findings") or []) if str(item).strip()]
    evidence = [str(item).strip() for item in (block.get("evidence") or []) if str(item).strip()]
    recommendation = str(block.get("recommendation") or "").strip()
    limitations = [str(item).strip() for item in (block.get("limitations") or []) if str(item).strip()]

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
    synthesis = str(payload.get("synthesis_prose") or payload.get("summary") or "").strip()
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
    if isinstance(finding, Finding) or (hasattr(finding, "title") and hasattr(finding, "observation") and hasattr(finding, "implication")):
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
        "evidence_urls": [str(url) for url in (finding.get("evidence_urls") or []) if isinstance(url, str)],
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
