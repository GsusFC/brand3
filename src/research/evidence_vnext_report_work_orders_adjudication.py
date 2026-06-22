"""Adjudication context helpers for evidence vNext work orders."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _report():
    return import_module("src.research.evidence_vnext_report")


def _work_order_context(run: dict[str, Any]) -> dict[str, Any]:
    report = _report()
    review_examples = list(run.get("remaining_review_examples") or [])
    material_overlaps = list(run.get("projected_material_overlaps") or [])
    changed_material_fields = list(run.get("changed_material_fields") or [])
    profile_urls = [
        report._context_url_identity(item.get("url"))
        for item in (*review_examples, *material_overlaps)
        if str(item.get("classification_reason") or "")
        in {"same_name_external_profile_not_alias", "same_name_external_profile_material_source"}
    ]
    review_urls = [report._context_url_identity(item.get("url")) for item in review_examples if str(item.get("url") or "")]
    affected_material_fields = [
        str(item.get("field") or "")
        for item in material_overlaps
        if str(item.get("field") or "") in report.MANUAL_AUDIT_MATERIAL_FIELDS
    ]
    changed_material_field_names = [
        str(item.get("field") or "")
        for item in changed_material_fields
        if str(item.get("field") or "") in report.MANUAL_AUDIT_MATERIAL_FIELDS
    ]
    return {
        "remaining_review_examples": review_examples,
        "projected_material_overlaps": material_overlaps,
        "changed_material_fields": changed_material_fields,
        "profile_urls": report._unique([url for url in profile_urls if url]),
        "review_urls": report._unique([url for url in review_urls if url]),
        "affected_material_fields": report._unique(affected_material_fields or changed_material_field_names),
        "changed_material_field_names": report._unique(changed_material_field_names),
    }


def _decision_record_template(
    *,
    run_id: Any,
    work_order_id: str,
    packet: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    report = _report()
    template: dict[str, Any] = {
        "work_order_id": work_order_id,
        "run_id": run_id,
        "decision": "",
        "reviewer": "",
        "rationale": "",
    }
    for field in packet.get("decision_required_fields") or []:
        template.setdefault(str(field), "")
    if "profile_url" in template:
        template["profile_url"] = report._join_unique(context.get("profile_urls") or [])
    if "affected_material_fields" in template:
        template["affected_material_fields"] = report._join_unique(context.get("affected_material_fields") or [])
    if "approved_material_fields" in template:
        template["approved_material_fields"] = report._join_unique(context.get("changed_material_field_names") or [])
    if "quarantined_source_urls" in template:
        template["quarantined_source_urls"] = report._join_unique(context.get("review_urls") or [])
    return template


def _adjudication_intake(work_orders: list[dict[str, Any]]) -> dict[str, Any]:
    records = [_adjudication_record(order) for order in work_orders]
    expected_output_counts: dict[str, int] = {}
    packet_counts: dict[str, int] = {}
    for record in records:
        expected = str(record.get("expected_output") or "unknown")
        expected_output_counts[expected] = expected_output_counts.get(expected, 0) + 1
        packet = str(record.get("packet_id") or "unknown")
        packet_counts[packet] = packet_counts.get(packet, 0) + 1
    return {
        "status": "pending_decisions" if records else "empty",
        "pending_count": len(records),
        "expected_output_counts": dict(sorted(expected_output_counts.items())),
        "packet_counts": dict(sorted(packet_counts.items())),
        "records": records,
    }


def _adjudication_record(work_order: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_order_id": work_order.get("work_order_id") or "",
        "packet_id": work_order.get("packet_id") or "",
        "run_id": work_order.get("run_id"),
        "brand_name": work_order.get("brand_name") or "",
        "status": "pending_decision",
        "expected_output": work_order.get("expected_output") or "",
        "requires_recompute": bool(work_order.get("requires_recompute")),
        "allowed_decisions": list(work_order.get("allowed_decisions") or []),
        "required_fields": list(work_order.get("decision_required_fields") or []),
        "record": dict(work_order.get("decision_record_template") or {}),
    }
