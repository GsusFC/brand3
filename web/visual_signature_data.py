"""Read-only Visual Signature data adapters for the local web UI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VISUAL_SIGNATURE_ROOT = PROJECT_ROOT / "examples" / "visual_signature"


ARTIFACTS: dict[str, dict[str, str]] = {
    "capture_manifest": {
        "label": "Capture manifest",
        "path": "screenshots/capture_manifest.json",
        "type": "json",
        "section": "overview",
    },
    "dismissal_audit": {
        "label": "Dismissal audit",
        "path": "screenshots/dismissal_audit.json",
        "type": "json",
        "section": "overview",
    },
    "governance_integrity_report": {
        "label": "Governance integrity report",
        "path": "governance/governance_integrity_report.json",
        "type": "json",
        "section": "governance",
    },
    "capability_registry": {
        "label": "Capability registry",
        "path": "governance/capability_registry.json",
        "type": "json",
        "section": "governance",
    },
    "runtime_policy_matrix": {
        "label": "Runtime policy matrix",
        "path": "governance/runtime_policy_matrix.json",
        "type": "json",
        "section": "governance",
    },
    "three_track_validation_plan": {
        "label": "Three-track validation plan",
        "path": "governance/three_track_validation_plan.json",
        "type": "json",
        "section": "governance",
    },
    "calibration_readiness": {
        "label": "Calibration readiness",
        "path": "calibration/calibration_readiness.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_manifest": {
        "label": "Calibration manifest",
        "path": "calibration/calibration_manifest.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_summary": {
        "label": "Calibration summary",
        "path": "calibration/calibration_summary.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_records": {
        "label": "Calibration records",
        "path": "calibration/calibration_records.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_reliability_report": {
        "label": "Calibration reliability report",
        "path": "calibration/calibration_reliability_report.md",
        "type": "markdown",
        "section": "calibration",
    },
    "corpus_expansion_manifest": {
        "label": "Corpus expansion manifest",
        "path": "corpus_expansion/corpus_expansion_manifest.json",
        "type": "json",
        "section": "corpus",
    },
    "pilot_metrics": {
        "label": "Pilot metrics",
        "path": "corpus_expansion/pilot_metrics.json",
        "type": "json",
        "section": "corpus",
    },
    "review_queue": {
        "label": "Review queue",
        "path": "corpus_expansion/review_queue.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_workflow_pilot": {
        "label": "Reviewer workflow pilot",
        "path": "corpus_expansion/reviewer_workflow_pilot.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_packet_index": {
        "label": "Reviewer packet index",
        "path": "corpus_expansion/reviewer_packets/reviewer_packet_index.md",
        "type": "markdown",
        "section": "reviewer",
    },
    "reviewer_viewer": {
        "label": "Reviewer viewer",
        "path": "corpus_expansion/reviewer_viewer/index.html",
        "type": "html",
        "section": "reviewer",
    },
}


SECTION_TITLES = {
    "overview": "Visual Signature Lab",
    "governance": "Visual Signature Lab Governance",
    "calibration": "Visual Signature Lab Calibration",
    "corpus": "Visual Signature Lab Corpus",
    "reviewer": "Visual Signature Lab Reviewer",
}


SECTION_INTROS = {
    "overview": "Read-only Visual Signature Lab navigation. Evidence is shown separately from Brand3 Scoring and has no scoring, rubric, report, provider, or runtime mutation impact.",
    "governance": "Capability registry, runtime policy matrix, governance integrity, and validation planning for the lab. Read-only.",
    "calibration": "Calibration manifests, records, reliability report, and readiness status for the lab. Read-only.",
    "corpus": "Corpus expansion manifest, pilot metrics, queue state, and limitations for the lab. Read-only.",
    "reviewer": "Reviewer workflow pilot, selected queue items, packet links, and local reviewer viewer entry point. Read-only.",
}

HUMAN_REVIEW_DESIGN_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "human_review_ui_design.json"
REVIEW_SEMANTICS_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "review_semantics.json"


def visual_signature_root() -> Path:
    return Path(os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT", str(DEFAULT_VISUAL_SIGNATURE_ROOT)))


def artifact_path(key: str, *, root: Path | None = None) -> Path | None:
    spec = ARTIFACTS.get(key)
    if not spec:
        return None
    root = root or visual_signature_root()
    return root / spec["path"]


def artifact_file_response_payload(key: str) -> tuple[Path, str] | None:
    spec = ARTIFACTS.get(key)
    path = artifact_path(key)
    if not spec or path is None or not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
    }.get(spec["type"], "text/plain; charset=utf-8")
    return path, media_type


def screenshot_file_response_payload(filename: str) -> tuple[Path, str] | None:
    path = visual_signature_root() / "screenshots" / filename
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    if not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }[path.suffix.lower()]
    return path, media_type


def build_screenshot_preview_model(filename: str) -> dict[str, Any] | None:
    payload = screenshot_file_response_payload(filename)
    if payload is None:
        return None

    selected_path, _media_type = payload
    selected_brand, selected_label = _variant_from_filename(selected_path)
    evidence = _visual_evidence_model()
    selected_item = None
    for item in evidence["items"]:
        if item.get("capture_id") == selected_brand:
            selected_item = item
            break
    if selected_item is None:
        selected_item = {
            "brand_name": selected_brand.replace("-", " ").title(),
            "capture_id": selected_brand,
            "website_url": "",
            "capture_status": "available",
            "obstruction_type": "unknown",
            "obstruction_severity": "unknown",
            "dismissal_attempted": False,
            "dismissal_successful": False,
            "perceptual_state": "evidence_record",
            "evidence_notes": [],
            "variants": [
                _screenshot_variant_payload("raw viewport", visual_signature_root() / "screenshots" / f"{selected_brand}.png"),
                _screenshot_variant_payload("clean attempt", visual_signature_root() / "screenshots" / f"{selected_brand}.clean-attempt.png"),
                _screenshot_variant_payload("full page", visual_signature_root() / "screenshots" / f"{selected_brand}.full-page.png"),
            ],
        }

    selected_variant = None
    for variant in selected_item["variants"]:
        if variant["filename"] == selected_path.name:
            selected_variant = dict(variant)
            break
    if selected_variant is None:
        selected_variant = _screenshot_variant_payload(selected_label, selected_path)

    root = visual_signature_root()
    capture_manifest = _load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = _load_json(root / "screenshots" / "dismissal_audit.json") or {}
    capture_entry = _find_manifest_row(capture_manifest, selected_item["brand_name"])
    dismissal_entry = _find_manifest_row(dismissal_audit, selected_item["brand_name"])
    related = [_related_variant_payload(variant, selected_variant["filename"]) for variant in selected_item["variants"]]
    available_related = [variant for variant in related if variant["exists"]]
    current_index = next(
        (index for index, variant in enumerate(available_related) if variant["filename"] == selected_variant["filename"]),
        -1,
    )
    previous_variant = available_related[current_index - 1] if current_index > 0 else None
    next_variant = available_related[current_index + 1] if 0 <= current_index < len(available_related) - 1 else None

    return {
        "title": f"{selected_item['brand_name']} screenshot preview",
        "brand_name": selected_item["brand_name"],
        "capture_id": selected_item["capture_id"],
        "website_url": selected_item.get("website_url") or "",
        "screenshot_type": selected_variant["label"],
        "selected": selected_variant,
        "related": related,
        "previous": previous_variant,
        "next": next_variant,
        "capture_status": selected_item.get("capture_status") or "available",
        "obstruction_type": selected_item.get("obstruction_type") or "unknown",
        "obstruction_severity": selected_item.get("obstruction_severity") or "unknown",
        "perceptual_state": selected_item.get("perceptual_state") or "evidence_record",
        "evidence_notes": selected_item.get("evidence_notes") or [],
        "source_artifacts": [
            {
                "label": "capture_manifest.json",
                "href": "/visual-signature/artifacts/capture_manifest",
                "path": str(root / "screenshots" / "capture_manifest.json"),
                "raw_json": _pretty_json(capture_entry) if capture_entry else "",
            },
            {
                "label": "dismissal_audit.json",
                "href": "/visual-signature/artifacts/dismissal_audit",
                "path": str(root / "screenshots" / "dismissal_audit.json"),
                "raw_json": _pretty_json(dismissal_entry) if dismissal_entry else "",
            },
        ],
        "nav": [
            {"label": "Overview", "href": "/visual-signature", "active": False},
            {"label": "Governance", "href": "/visual-signature/governance", "active": False},
            {"label": "Calibration", "href": "/visual-signature/calibration", "active": False},
            {"label": "Corpus", "href": "/visual-signature/corpus", "active": False},
            {"label": "Reviewer", "href": "/visual-signature/reviewer", "active": False},
        ],
    }


def _related_variant_payload(variant: dict[str, Any], selected_filename: str) -> dict[str, Any]:
    payload = dict(variant)
    payload["is_current"] = payload.get("filename") == selected_filename
    return payload


def build_visual_signature_model(section: str = "overview") -> dict[str, Any]:
    if section not in SECTION_TITLES:
        section = "overview"
    artifacts = {key: _artifact_payload(key) for key in ARTIFACTS}
    cards = _cards_for_section(section, artifacts)
    return {
        "section": section,
        "title": SECTION_TITLES[section],
        "intro": SECTION_INTROS[section],
        "nav": [
            {"label": "Lab Overview", "href": "/visual-signature", "active": section == "overview"},
            {"label": "Governance", "href": "/visual-signature/governance", "active": section == "governance"},
            {"label": "Calibration", "href": "/visual-signature/calibration", "active": section == "calibration"},
            {"label": "Corpus", "href": "/visual-signature/corpus", "active": section == "corpus"},
            {"label": "Reviewer", "href": "/visual-signature/reviewer", "active": section == "reviewer"},
        ],
        "guardrails": [
            "evidence-only",
            "no scoring impact",
            "no rubric impact",
            "no production report impact",
            "no provider calls",
            "no runtime mutation",
            "read-only source artifact navigation",
        ],
        "cards": cards,
        "artifacts": _artifacts_for_section(section, artifacts),
        "visual_evidence": _visual_evidence_model() if section == "overview" else {"items": [], "summary": {}},
        "records": _items_for_section(section, artifacts),
        "next_steps": _next_steps(section),
        "initial_scoring": {
            "href": "/",
            "reports_href": "/reports",
            "note": "Brand3 Scoring remains the existing executable flow. Dimension prose is render-time derived by the current report renderer, not a persisted Visual Signature artifact.",
        },
    }


def build_human_review_model(brand: str | None = None) -> dict[str, Any] | None:
    root = visual_signature_root()
    review_queue = _load_json(root / "corpus_expansion" / "review_queue.json") or {}
    pilot = _load_json(root / "corpus_expansion" / "reviewer_workflow_pilot.json") or {}
    design = _load_json(HUMAN_REVIEW_DESIGN_PATH) or {}
    semantics = _load_json(REVIEW_SEMANTICS_PATH) or {}
    evidence_model = _visual_evidence_model()
    evidence_items = {item["capture_id"]: item for item in evidence_model["items"]}

    selected_ids = set(_as_list(pilot.get("selected_review_queue_item_ids")))
    queue_items = []
    for item in _as_list(review_queue.get("queue_items")):
        if not isinstance(item, dict):
            continue
        capture_id = str(item.get("capture_id") or "")
        if capture_id not in {"headspace", "allbirds"}:
            continue
        if selected_ids and str(item.get("queue_id") or "") not in selected_ids:
            continue
        queue_items.append(_human_review_queue_item(item, active=False))

    queued_capture_ids = {item["capture_id"] for item in queue_items}
    for capture_id in ("headspace", "allbirds"):
        if capture_id in queued_capture_ids or capture_id not in evidence_items:
            continue
        evidence = evidence_items[capture_id]
        queue_items.append(
            {
                "queue_id": f"queue_{capture_id}",
                "capture_id": capture_id,
                "brand_name": evidence["brand_name"],
                "category": "unknown",
                "queue_state": "queued",
                "confidence_bucket": "unknown",
                "website_url": evidence.get("website_url") or "",
                "active": False,
                "href": f"/visual-signature/reviewer/human-review/{capture_id}",
            }
        )

    queue_items.sort(key=lambda item: 0 if item["capture_id"] == "headspace" else 1)
    if not queue_items:
        for capture_id in ("headspace", "allbirds"):
            evidence = evidence_items.get(capture_id)
            if evidence:
                queue_items.append(
                    {
                        "queue_id": f"queue_{capture_id}",
                        "capture_id": capture_id,
                        "brand_name": evidence["brand_name"],
                        "category": "unknown",
                        "queue_state": "queued",
                        "confidence_bucket": "unknown",
                        "website_url": evidence.get("website_url") or "",
                        "active": False,
                        "href": f"/visual-signature/reviewer/human-review/{capture_id}",
                    }
                )

    active_slug = _slugify(brand or "")
    if not active_slug and queue_items:
        active_slug = queue_items[0]["capture_id"]
    active_queue = next((item for item in queue_items if item["capture_id"] == active_slug), None)
    if active_queue is None and queue_items:
        active_queue = queue_items[0]
    if active_queue is None:
        return None

    for item in queue_items:
        item["active"] = item["capture_id"] == active_queue["capture_id"]

    active_evidence = evidence_items.get(active_queue["capture_id"]) or _fallback_evidence_for_capture(active_queue)
    active_capture = _human_review_active_capture(active_queue, active_evidence)
    first_cases = design.get("first_cases") if isinstance(design.get("first_cases"), dict) else {}
    case_design = first_cases.get(active_capture["capture_id"], {}) if isinstance(first_cases, dict) else {}

    return {
        "title": "Visual Signature Lab Human Review",
        "intro": "Evidence-first human review for the Visual Signature Lab. Draft answers are local-only in this phase and do not create completed review records.",
        "nav": [
            {"label": "Lab Overview", "href": "/visual-signature", "active": False},
            {"label": "Governance", "href": "/visual-signature/governance", "active": False},
            {"label": "Calibration", "href": "/visual-signature/calibration", "active": False},
            {"label": "Corpus", "href": "/visual-signature/corpus", "active": False},
            {"label": "Lab Reviewer", "href": "/visual-signature/reviewer", "active": True},
        ],
        "guardrails": [
            "evidence-only",
            "no scoring impact",
            "no persistence",
            "no provider calls",
            "no runtime mutation",
            "no completed review records",
        ],
        "queue": {
            "items": queue_items,
            "summary": {
                "selected": len(queue_items),
                "pending": sum(1 for item in queue_items if item["queue_state"] in {"queued", "needs_additional_evidence"}),
                "needs_additional_evidence": sum(1 for item in queue_items if item["queue_state"] == "needs_additional_evidence"),
                "unresolved": sum(1 for item in queue_items if item["queue_state"] == "unresolved"),
            },
        },
        "active": active_capture,
        "question_groups": _human_review_question_groups(design, case_design, semantics),
        "semantic_guidance": _human_review_semantic_guidance(semantics),
        "outcomes": ["confirmed", "contradicted", "unresolved", "insufficient_review"],
        "confidence_buckets": ["unknown", "low", "medium", "high"],
        "status_mapping": ["approved", "rejected", "needs_more_evidence"],
        "case_guidance": {
            "primary_tasks": _as_list(case_design.get("primary_reviewer_task")),
            "ui_emphasis": _as_list(case_design.get("ui_emphasis")),
        },
        "record_preview_fields": [
            "reviewer_id",
            "queue_id",
            "capture_id",
            "review_outcome",
            "confidence_bucket",
            "question_answers",
            "notes",
            "evidence_refs",
        ],
        "source_artifacts": _human_review_source_artifacts(root, active_capture),
    }


def _visual_evidence_model() -> dict[str, Any]:
    root = visual_signature_root()
    screenshots_dir = root / "screenshots"
    capture_manifest = _load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = _load_json(root / "screenshots" / "dismissal_audit.json") or {}
    rows = _as_list(capture_manifest.get("results"))
    audit_rows = {
        str(row.get("brand_name") or "").lower(): row
        for row in _as_list(dismissal_audit.get("results"))
        if isinstance(row, dict)
    }

    items = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        brand_name = str(row.get("brand_name") or "Unknown brand")
        audit = audit_rows.get(brand_name.lower()) or {}
        variants = _screenshot_variants(row, screenshots_dir=screenshots_dir)
        items.append(
            {
                "brand_name": brand_name,
                "capture_id": _slugify(brand_name),
                "website_url": row.get("website_url") or row.get("page_url") or "",
                "capture_status": row.get("status") or "available",
                "obstruction_type": _nested(row, "before_obstruction", "type") or "unknown",
                "obstruction_severity": _nested(row, "before_obstruction", "severity") or "unknown",
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "perceptual_state": row.get("perceptual_state") or audit.get("perceptual_state") or "evidence_record",
                "evidence_notes": _as_list(row.get("evidence_integrity_notes"))[:4],
                "variants": variants,
            }
        )

    if not items and screenshots_dir.exists():
        grouped: dict[str, dict[str, Any]] = {}
        for path in sorted(screenshots_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            brand, label = _variant_from_filename(path)
            grouped.setdefault(
                brand,
                {
                    "brand_name": brand.replace("-", " ").title(),
                    "capture_id": brand,
                    "website_url": "",
                    "capture_status": "available",
                    "obstruction_type": "unknown",
                    "obstruction_severity": "unknown",
                    "dismissal_attempted": False,
                    "dismissal_successful": False,
                    "perceptual_state": "evidence_record",
                    "evidence_notes": [],
                    "variants": [],
                },
            )["variants"].append(_screenshot_variant_payload(label, path))
        items = list(grouped.values())

    variant_counts = {
        "raw viewport": sum(1 for item in items for variant in item["variants"] if variant["label"] == "raw viewport" and variant["exists"]),
        "clean attempt": sum(1 for item in items for variant in item["variants"] if variant["label"] == "clean attempt" and variant["exists"]),
        "full page": sum(1 for item in items for variant in item["variants"] if variant["label"] == "full page" and variant["exists"]),
    }
    return {
        "summary": {
            "capture_count": len(items),
            "raw_viewport_count": variant_counts["raw viewport"],
            "clean_attempt_count": variant_counts["clean attempt"],
            "full_page_count": variant_counts["full page"],
        },
        "items": items,
    }


def _human_review_queue_item(item: dict[str, Any], *, active: bool) -> dict[str, Any]:
    capture_id = _slugify(str(item.get("capture_id") or item.get("brand_name") or ""))
    return {
        "queue_id": item.get("queue_id") or f"queue_{capture_id}",
        "capture_id": capture_id,
        "brand_name": item.get("brand_name") or capture_id.replace("-", " ").title(),
        "category": item.get("category") or "unknown",
        "queue_state": item.get("queue_state") or "queued",
        "confidence_bucket": item.get("confidence_bucket") or "unknown",
        "website_url": item.get("website_url") or "",
        "active": active,
        "href": f"/visual-signature/reviewer/human-review/{capture_id}",
    }


def _fallback_evidence_for_capture(queue_item: dict[str, Any]) -> dict[str, Any]:
    root = visual_signature_root()
    capture_id = queue_item["capture_id"]
    return {
        "brand_name": queue_item["brand_name"],
        "capture_id": capture_id,
        "website_url": queue_item.get("website_url") or "",
        "capture_status": "available",
        "obstruction_type": "unknown",
        "obstruction_severity": "unknown",
        "dismissal_attempted": False,
        "dismissal_successful": False,
        "perceptual_state": "evidence_record",
        "evidence_notes": [],
        "variants": [
            _screenshot_variant_payload("raw viewport", root / "screenshots" / f"{capture_id}.png"),
            _screenshot_variant_payload("clean attempt", root / "screenshots" / f"{capture_id}.clean-attempt.png"),
            _screenshot_variant_payload("full page", root / "screenshots" / f"{capture_id}.full-page.png"),
        ],
    }


def _human_review_active_capture(queue_item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    variants = evidence.get("variants") or []
    raw_variant = next((variant for variant in variants if variant.get("label") == "raw viewport"), None)
    return {
        "queue_id": queue_item["queue_id"],
        "capture_id": queue_item["capture_id"],
        "brand_name": evidence.get("brand_name") or queue_item["brand_name"],
        "category": queue_item.get("category") or "unknown",
        "website_url": evidence.get("website_url") or queue_item.get("website_url") or "",
        "queue_state": queue_item.get("queue_state") or "queued",
        "confidence_bucket": queue_item.get("confidence_bucket") or "unknown",
        "capture_status": evidence.get("capture_status") or "available",
        "perceptual_state": evidence.get("perceptual_state") or "evidence_record",
        "obstruction_type": evidence.get("obstruction_type") or "unknown",
        "obstruction_severity": evidence.get("obstruction_severity") or "unknown",
        "dismissal_attempted": bool(evidence.get("dismissal_attempted")),
        "dismissal_successful": bool(evidence.get("dismissal_successful")),
        "evidence_notes": evidence.get("evidence_notes") or [],
        "variants": variants,
        "primary_variant": raw_variant or (variants[0] if variants else None),
        "evidence_refs": [variant["href"] for variant in variants if variant.get("exists")],
    }


def _human_review_question_groups(
    design: dict[str, Any],
    case_design: dict[str, Any],
    semantics: dict[str, Any],
) -> list[dict[str, Any]]:
    regions = _as_list(_nested(design, "canonical_reviewer_screen", "regions"))
    groups = []
    for region in regions:
        if not isinstance(region, dict) or region.get("id") != "structured_visual_questions":
            continue
        for group in _as_list(region.get("question_groups")):
            if isinstance(group, dict):
                group_name = group.get("name") or "Review questions"
                groups.append(
                    {
                        "name": group_name,
                        "questions": [
                            _question_semantics(str(question), group_name, semantics)
                            for question in _as_list(group.get("questions"))
                        ],
                    }
                )
    default_questions = [str(question) for question in _as_list(case_design.get("default_questions"))]
    if default_questions:
        groups.insert(
            0,
            {
                "name": "Case-specific questions",
                "questions": [
                    _question_semantics(question, "Case-specific questions", semantics)
                    for question in default_questions
                ],
            },
        )
    return groups


def _human_review_semantic_guidance(semantics: dict[str, Any]) -> dict[str, Any]:
    confidence = semantics.get("confidence_semantics") if isinstance(semantics.get("confidence_semantics"), dict) else {}
    observation_vs_interpretation = (
        semantics.get("observation_vs_interpretation")
        if isinstance(semantics.get("observation_vs_interpretation"), dict)
        else {}
    )
    return {
        "source": "review_semantics.json",
        "summary": semantics.get("core_intent")
        or "Reviewer answers are structured human visual perception, not classification alone.",
        "confidence_meaning": confidence.get("meaning")
        or "Confidence means reviewer certainty from available evidence.",
        "confidence_buckets": confidence.get("buckets") if isinstance(confidence.get("buckets"), dict) else {},
        "observation_definition": _nested(observation_vs_interpretation, "observation", "definition")
        or "Observation is tied directly to visible evidence.",
        "interpretation_definition": _nested(observation_vs_interpretation, "interpretation", "definition")
        or "Interpretation derives meaning from observations.",
    }


def _question_semantics(question: str, group_name: str, semantics: dict[str, Any]) -> dict[str, Any]:
    category_id = _question_category_id(question, group_name)
    taxonomy = _taxonomy_by_id(semantics).get(category_id, {})
    answer_type = _answer_type_for_question(question, category_id)
    observation_type = _observation_type_for_question(question, category_id)
    question_id = f"{_slugify(group_name)}__{_slugify(question)}"
    return {
        "id": question_id,
        "text": question,
        "category": taxonomy.get("id") or category_id,
        "category_label": _humanize_semantic_label(taxonomy.get("id") or category_id),
        "category_purpose": taxonomy.get("purpose") or "Evidence-bound visual perception question.",
        "observation_type": observation_type,
        "observation_type_label": _humanize_semantic_label(observation_type),
        "answer_type": answer_type,
        "answer_type_label": _humanize_semantic_label(answer_type),
        "answer_guidance": _answer_guidance(answer_type),
        "confidence_guidance": _confidence_guidance(semantics),
        "observation_interpretation_guidance": _observation_interpretation_guidance(observation_type, semantics),
    }


def _taxonomy_by_id(semantics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in _as_list(semantics.get("question_taxonomy"))
        if isinstance(item, dict) and item.get("id")
    }


def _question_category_id(question: str, group_name: str) -> str:
    text = f"{group_name} {question}".lower()
    if "case-specific" in text:
        return _case_specific_category_id(question)
    if "supplemental" in text or "clean attempt" in text or "full-page" in text or "full page" in text:
        return "supplemental_evidence"
    if "obstruction" in text or "modal" in text or "login" in text or "protected" in text or "affordance" in text:
        return "obstruction"
    if "contradict" in text or "unresolved" in text or "missing" in text or "ambiguous" in text or "more evidence" in text:
        return "contradiction_and_unresolved"
    if "logo" in text or "imagery" in text or "product" in text or "people" in text or "template" in text or "category" in text:
        return "visual_perception"
    if "exist" in text or "available" in text or "usable" in text or "broken" in text or "cropped" in text:
        return "evidence_availability"
    return "evidence_support"


def _case_specific_category_id(question: str) -> str:
    text = question.lower()
    if "clean attempt" in text:
        return "supplemental_evidence"
    if "login" in text or "protected" in text or "modal" in text or "obstruction" in text or "affordance" in text:
        return "obstruction"
    if "more evidence" in text or "queue state" in text or "needed" in text:
        return "contradiction_and_unresolved"
    if "raw viewport" in text or "sufficient" in text:
        return "evidence_availability"
    return "evidence_support"


def _answer_type_for_question(question: str, category_id: str) -> str:
    text = question.lower()
    if category_id in {"evidence_support", "visual_perception", "contradiction_and_unresolved"}:
        return "graded_judgment"
    if "severity" in text or "materially" in text or "reduce" in text or "supported" in text or "appropriate" in text:
        return "graded_judgment"
    return "binary_judgment"


def _observation_type_for_question(question: str, category_id: str) -> str:
    text = question.lower()
    if "broken" in text:
        return "evidence_broken"
    if "missing" in text or "more evidence" in text or "needed" in text:
        return "evidence_missing"
    if "raw viewport" in text or "usable" in text or "sufficient" in text:
        return "viewport_usable"
    if "clean attempt" in text and ("reduce" in text or "change" in text):
        return "clean_attempt_effect_visible"
    if "clean attempt" in text:
        return "clean_attempt_available"
    if "full-page" in text or "full page" in text:
        return "full_page_context_available"
    if "obstruction type" in text or "modal" in text or "login" in text or "protected" in text or "affordance" in text:
        return "obstruction_type_visible"
    if "obstruct" in text or "severity" in text:
        return "obstruction_severity_visible"
    if "infer" in text or "inference" in text:
        return "unsupported_inference_present"
    if "contradict" in text:
        return "claim_contradicted"
    if "supported" in text or "appropriate" in text or "claim" in text:
        return "claim_supported"
    if category_id == "visual_perception":
        if "category" in text:
            return "category_cue_visible"
        if "layout" in text or "template" in text:
            return "layout_trait_visible"
        return "visual_element_present"
    return "claim_supported"


def _answer_guidance(answer_type: str) -> dict[str, str]:
    if answer_type == "binary_judgment":
        return {
            "yes": "visible evidence shows this is present or true",
            "partial": "part of the evidence is visible, but it is incomplete or ambiguous",
            "no": "visible evidence does not show this",
            "uncertain": "the reviewer cannot determine this from the available evidence",
        }
    return {
        "yes": "visible evidence clearly supports the judgment",
        "partial": "visible evidence partly supports it, but the support is incomplete or mixed",
        "no": "visible evidence does not support the judgment",
        "uncertain": "the evidence is too ambiguous, missing, or conflicting to judge",
    }


def _confidence_guidance(semantics: dict[str, Any]) -> str:
    confidence = semantics.get("confidence_semantics") if isinstance(semantics.get("confidence_semantics"), dict) else {}
    buckets = confidence.get("buckets") if isinstance(confidence.get("buckets"), dict) else {}
    low = buckets.get("low", "Evidence is weak, partial, ambiguous, obstructed, or internally inconsistent.")
    high = buckets.get("high", "Evidence clearly supports the answer with minimal ambiguity.")
    return f"Confidence means certainty from evidence. Low: {low} High: {high}"


def _observation_interpretation_guidance(observation_type: str, semantics: dict[str, Any]) -> str:
    observation_vs_interpretation = (
        semantics.get("observation_vs_interpretation")
        if isinstance(semantics.get("observation_vs_interpretation"), dict)
        else {}
    )
    observation_definition = _nested(observation_vs_interpretation, "observation", "definition") or "Observation is tied directly to visible evidence."
    interpretation_definition = _nested(observation_vs_interpretation, "interpretation", "definition") or "Interpretation derives meaning from observations."
    if observation_type in {
        "evidence_available",
        "evidence_missing",
        "evidence_broken",
        "viewport_obstructed",
        "obstruction_type_visible",
        "visual_element_present",
        "visual_element_absent",
        "category_cue_visible",
    }:
        return f"Observation: {observation_definition}"
    return f"Interpretation: {interpretation_definition}"


def _humanize_semantic_label(value: str) -> str:
    return value.replace("_", " ")


def _human_review_source_artifacts(root: Path, active: dict[str, Any]) -> list[dict[str, str]]:
    capture_id = active["capture_id"]
    artifact_paths = [
        ("review_queue.json", root / "corpus_expansion" / "review_queue.json"),
        ("reviewer_workflow_pilot.json", root / "corpus_expansion" / "reviewer_workflow_pilot.json"),
        ("capture_manifest.json", root / "screenshots" / "capture_manifest.json"),
        ("dismissal_audit.json", root / "screenshots" / "dismissal_audit.json"),
        ("phase_one state", root / "phase_one" / "records" / capture_id / "state.json"),
        ("phase_one obstruction", root / "phase_one" / "records" / capture_id / "obstruction.json"),
        ("phase_two review", root / "phase_two" / "records" / capture_id / "reviewed_dataset_eligibility.json"),
    ]
    return [
        {
            "label": label,
            "path": str(path),
            "status": "available" if path.exists() else "missing_or_unknown",
        }
        for label, path in artifact_paths
    ]


def _screenshot_variants(row: dict[str, Any], *, screenshots_dir: Path) -> list[dict[str, Any]]:
    brand_slug = _slugify(str(row.get("brand_name") or ""))
    candidates = [
        ("raw viewport", row.get("raw_screenshot_path") or row.get("screenshot_path") or screenshots_dir / f"{brand_slug}.png"),
        ("clean attempt", row.get("clean_attempt_screenshot_path") or screenshots_dir / f"{brand_slug}.clean-attempt.png"),
        ("full page", row.get("secondary_screenshot_path") or screenshots_dir / f"{brand_slug}.full-page.png"),
    ]
    return [_screenshot_variant_payload(label, Path(path)) for label, path in candidates if path]


def _screenshot_variant_payload(label: str, path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else (PROJECT_ROOT / path)
    exists = resolved.exists() and _is_under_root(resolved)
    filename = resolved.name
    return {
        "label": label,
        "exists": exists,
        "filename": filename,
        "path": str(resolved),
        "href": f"/visual-signature/screenshots/{filename}",
        "preview_href": f"/visual-signature/screenshots/{filename}/preview",
        "alt": f"{label} screenshot: {filename}",
    }


def _variant_from_filename(path: Path) -> tuple[str, str]:
    name = path.name
    stem = path.stem
    if stem.endswith(".clean-attempt"):
        return stem.removesuffix(".clean-attempt"), "clean attempt"
    if stem.endswith(".full-page"):
        return stem.removesuffix(".full-page"), "full page"
    return stem, "raw viewport"


def _artifact_payload(key: str) -> dict[str, Any]:
    spec = ARTIFACTS[key]
    path = artifact_path(key)
    exists = bool(path and path.exists())
    payload = _load_json(path) if exists and spec["type"] == "json" else None
    return {
        "key": key,
        "label": spec["label"],
        "type": spec["type"],
        "section": spec["section"],
        "exists": exists,
        "path": str(path) if path else "",
        "source_href": f"/visual-signature/artifacts/{key}",
        "status": _status_for(payload, exists=exists),
        "summary": _summary_for(payload, spec["type"], exists=exists),
        "raw_json": _pretty_json(payload) if payload is not None else "",
    }


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else {"items": value}


def _status_for(payload: dict[str, Any] | None, *, exists: bool) -> str:
    if not exists:
        return "missing"
    if not isinstance(payload, dict):
        return "available"
    for key in ("status", "readiness_status", "validation_status", "pilot_status", "record_type"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return "available"


def _summary_for(payload: dict[str, Any] | None, artifact_type: str, *, exists: bool) -> dict[str, Any]:
    if not exists:
        return {"state": "missing_or_unknown"}
    if artifact_type != "json" or not isinstance(payload, dict):
        return {"state": "available"}
    keys = (
        "schema_version",
        "record_type",
        "generated_at",
        "checked_at",
        "completed_at",
        "status",
        "readiness_status",
        "validation_status",
        "pilot_status",
        "record_count",
        "capability_count",
        "policy_count",
        "error_count",
        "warning_count",
        "selected_review_queue_item_count",
        "current_capture_count",
        "reviewed_capture_count",
        "target_capture_count",
        "reviewer_coverage",
        "contradiction_rate",
        "unresolved_rate",
    )
    return {key: payload[key] for key in keys if key in payload}


def _cards_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    card_keys = {
        "overview": [
            "governance_integrity_report",
            "capability_registry",
            "runtime_policy_matrix",
            "calibration_readiness",
            "calibration_reliability_report",
            "pilot_metrics",
            "reviewer_workflow_pilot",
        ],
        "governance": [
            "governance_integrity_report",
            "capability_registry",
            "runtime_policy_matrix",
            "three_track_validation_plan",
        ],
        "calibration": [
            "calibration_readiness",
            "calibration_manifest",
            "calibration_summary",
            "calibration_records",
            "calibration_reliability_report",
        ],
        "corpus": [
            "corpus_expansion_manifest",
            "pilot_metrics",
            "review_queue",
            "reviewer_workflow_pilot",
        ],
        "reviewer": [
            "reviewer_workflow_pilot",
            "review_queue",
            "reviewer_packet_index",
            "reviewer_viewer",
        ],
    }[section]
    return [artifacts[key] for key in card_keys]


def _artifacts_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if section == "overview":
        return [
            artifacts[key]
            for key in (
                "governance_integrity_report",
                "capability_registry",
                "runtime_policy_matrix",
                "calibration_readiness",
                "calibration_reliability_report",
                "pilot_metrics",
                "reviewer_workflow_pilot",
            )
        ]
    return [artifact for artifact in artifacts.values() if artifact["section"] == section]


def _items_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if section == "governance":
        registry = _load_json(artifact_path("capability_registry")) or {}
        return [
            {
                "title": item.get("capability_id", "capability"),
                "status": item.get("maturity_state") or item.get("evidence_status") or "record",
                "meta": {
                    "layer": item.get("layer"),
                    "evidence_status": item.get("evidence_status"),
                    "production_enabled": item.get("production_enabled", False),
                },
            }
            for item in _as_list(registry.get("capabilities"))[:12]
        ]
    if section in {"corpus", "reviewer"}:
        queue = _load_json(artifact_path("review_queue")) or {}
        pilot = _load_json(artifact_path("reviewer_workflow_pilot")) or {}
        selected = set(_as_list(pilot.get("selected_review_queue_item_ids")))
        rows = []
        for item in _as_list(queue.get("queue_items")):
            if section == "corpus" or item.get("queue_id") in selected or item.get("queue_state") in {"queued", "needs_additional_evidence"}:
                rows.append(
                    {
                        "title": item.get("brand_name") or item.get("queue_id", "queue item"),
                        "status": item.get("queue_state") or "record",
                        "meta": {
                            "queue_id": item.get("queue_id"),
                            "category": item.get("category"),
                            "capture_id": item.get("capture_id"),
                            "selected_for_pilot": item.get("queue_id") in selected,
                        },
                    }
                )
        return rows[:20]
    if section == "calibration":
        readiness = _load_json(artifact_path("calibration_readiness")) or {}
        rows = []
        for reason in _as_list(readiness.get("block_reasons")) + _as_list(readiness.get("warning_reasons")):
            rows.append({"title": str(reason), "status": "readiness_note", "meta": {}})
        return rows
    return []


def _next_steps(section: str) -> list[str]:
    if section == "overview":
        return [
            "Use Brand3 Scoring through the existing scan form and report routes.",
            "Use Visual Signature pages only to inspect source artifacts and readiness.",
            "Keep scoring and Visual Signature decisions separate.",
        ]
    if section == "governance":
        return ["Resolve governance integrity errors in source artifacts before expanding runtime scope."]
    if section == "calibration":
        return ["Use calibration readiness block reasons to decide the next evidence target."]
    if section == "corpus":
        return ["Review pilot metrics and queue state before broadening corpus expansion."]
    if section == "reviewer":
        return ["Open reviewer packets/viewer for human review, but do not persist decisions through this platform."]
    return []


def _pretty_json(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _nested(payload: dict[str, Any], key: str, nested_key: str) -> Any:
    value = payload.get(key)
    return value.get(nested_key) if isinstance(value, dict) else None


def _find_manifest_row(payload: dict[str, Any], brand_name: str) -> dict[str, Any] | None:
    target = brand_name.lower()
    for row in _as_list(payload.get("results")):
        if isinstance(row, dict) and str(row.get("brand_name") or "").lower() == target:
            return row
    return None


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in normalized.split("-") if part)


def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(visual_signature_root().resolve())
    except ValueError:
        return False
    return True
