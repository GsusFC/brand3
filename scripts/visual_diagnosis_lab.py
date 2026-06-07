#!/usr/bin/env python3
"""Run lab-only Brand3 visual diagnosis over local evidence files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.visual_diagnosis import build_visual_diagnosis
from src.visual_diagnosis.bundle import (
    VisualEvidenceBundle,
    VisualEvidenceSource,
    fuse_visual_signature_payloads,
)
from src.visual_diagnosis.computed_style import computed_style_snapshot_to_visual_signature
from src.visual_diagnosis.clean_capture import build_clean_capture_decision
from src.visual_diagnosis.evidence import (
    build_visual_evidence_from_local_inputs,
    enrich_visual_signature_with_local_screenshot,
    screenshot_capture_to_visual_signature,
)
from src.visual_diagnosis.provenance import build_signal_provenance


DEFAULT_OUTPUT_ROOT = Path("out") / "visual_diagnosis_lab"


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(Path(path))
    if isinstance(payload, dict) and isinstance(payload.get("brands"), list):
        rows = payload["brands"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("manifest must be a JSON array or an object with a brands array")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each manifest row must be a JSON object")
        if not str(row.get("brand_name") or "").strip():
            raise ValueError("each manifest row requires brand_name")
        if not str(row.get("website_url") or "").strip():
            raise ValueError("each manifest row requires website_url")
        result.append(row)
    return result


def run_lab(manifest_path: str | Path, *, output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    rows = load_manifest(manifest_path)
    output_dir = Path(output_root) / _timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for row in rows:
        coherence_breakdown = _coherence_breakdown_for_row(row)
        bundle = _visual_evidence_bundle_for_row(row)
        visual_signature_payload = bundle.fused_visual_signature_payload
        clean_capture_decision = _clean_capture_decision_for_row(row)
        diagnosis = build_visual_diagnosis(
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
            screenshot_capture=_screenshot_capture_for_row(row),
            visual_signature_payload=visual_signature_payload,
            coherence_breakdown=coherence_breakdown,
            category_hint=str(row.get("category_hint") or ""),
        )
        diagnosis_payload = diagnosis.to_dict()
        source_comparison = _source_comparison_for_row(
            row,
            bundle=bundle,
            coherence_breakdown=coherence_breakdown,
        )
        signal_provenance = build_signal_provenance(
            diagnosis=diagnosis_payload,
            source_comparison=source_comparison,
            available_source_types=bundle.to_dict().get("available_source_types") or [],
        )
        result = {
            "brand_name": row["brand_name"],
            "website_url": row["website_url"],
            "category_hint": row.get("category_hint") or "",
            "human_review": _human_review_for_row(row),
            "page_state": _page_state_for_row(row),
            "clean_capture_decision": clean_capture_decision,
            "magnetism": {
                "coherence_breakdown": coherence_breakdown or {},
                "visual_identity": (coherence_breakdown or {}).get("visual_identity"),
            },
            "visual_evidence_bundle": bundle.to_dict(),
            "source_comparison": source_comparison,
            "signal_provenance": signal_provenance,
            "diagnosis": diagnosis_payload,
        }
        results.append(result)
        _write_json(output_dir / f"{_slug(str(row['brand_name']))}.json", result)

    summary = {
        "schema_version": "visual-diagnosis-lab-run-1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest_path": str(manifest_path),
        "brand_count": len(results),
        "results": results,
    }
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "comparison.json", _comparison_json(summary))
    (output_dir / "summary.md").write_text(_summary_markdown(summary) + "\n", encoding="utf-8")
    return {"output_dir": str(output_dir), "summary": summary}


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Visual Diagnosis Lab Summary",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Brand count: {summary['brand_count']}",
        "",
        "| Brand | Status | Profile | Identity read | Visual identity | Brand fit | Confidence | Anti-patterns |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in summary["results"]:
        diagnosis = row["diagnosis"]
        read = diagnosis["diagnosis"]
        signals = diagnosis["signals"]
        magnetism = row.get("magnetism") if isinstance(row.get("magnetism"), dict) else {}
        visual_identity = magnetism.get("visual_identity")
        visual_identity_text = "-" if visual_identity is None else str(visual_identity)
        antipatterns = ", ".join(signals.get("antipatterns") or []) or "-"
        lines.append(
            f"| {row['brand_name']} | {diagnosis['status']} | {read['reference_profile']} | "
            f"{read['identity_read']} | {visual_identity_text} | {read['brand_fit']} | "
            f"{diagnosis['confidence']} | {antipatterns} |"
        )
    return "\n".join(lines)


def _comparison_json(summary: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in summary["results"]:
        diagnosis = row["diagnosis"]
        read = diagnosis["diagnosis"]
        rows.append(
            {
                "brand_name": row["brand_name"],
                "website_url": row["website_url"],
                "category_hint": row.get("category_hint") or "",
                "visual_identity": (row.get("magnetism") or {}).get("visual_identity"),
                "status": diagnosis["status"],
                "reference_profile": read["reference_profile"],
                "identity_read": read["identity_read"],
                "brand_fit": read["brand_fit"],
                "confidence": diagnosis["confidence"],
                "human_review": row.get("human_review") or {},
                "page_state": row.get("page_state") or {},
                "clean_capture_decision": row.get("clean_capture_decision") or {},
                "antipatterns": diagnosis["signals"]["antipatterns"],
                "limitations": diagnosis["limitations"],
                "evidence_refs": diagnosis["evidence_refs"],
                "available_source_types": (row.get("visual_evidence_bundle") or {}).get("available_source_types") or [],
                "fusion_notes": (row.get("visual_evidence_bundle") or {}).get("fusion_notes") or [],
                "source_comparison": row.get("source_comparison") or [],
                "signal_provenance": row.get("signal_provenance") or [],
            }
        )
    return {
        "schema_version": "visual-diagnosis-comparison-v1",
        "generated_at": summary["generated_at"],
        "manifest_path": summary["manifest_path"],
        "brand_count": summary["brand_count"],
        "rows": rows,
    }


def _load_optional_json(value: Any) -> dict[str, Any] | None:
    if not value:
        return None
    payload = _load_json(Path(str(value)))
    if not isinstance(payload, dict):
        raise ValueError(f"{value} must contain a JSON object")
    return payload


def _row_payload(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    inline = row.get(key)
    if isinstance(inline, dict):
        return inline
    return _load_optional_json(row.get(f"{key}_path"))


def _human_review_for_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = _row_payload(row, "human_review")
    if not payload:
        return {}
    allowed = {
        "reviewer",
        "reviewed_at",
        "verdict",
        "profile_fit",
        "identity_read_fit",
        "notes",
        "disagreements",
        "recommended_changes",
    }
    return {key: value for key, value in payload.items() if key in allowed and value not in (None, "")}


def _page_state_for_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = _row_payload(row, "page_state")
    if payload:
        result = _filter_page_state_payload(payload)
    else:
        screenshot_payload = _row_payload(row, "screenshot_capture")
        result = _page_state_from_screenshot_capture(screenshot_payload)
    if not result:
        return {}
    obstructions = result.get("obstructions")
    if isinstance(obstructions, list):
        result["obstructions"] = [str(item) for item in obstructions if str(item).strip()]
    return result


def _filter_page_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "status",
        "obstructions",
        "capture_quality",
        "confidence",
        "source",
        "notes",
    }
    return {key: value for key, value in payload.items() if key in allowed and value not in (None, "")}


def _page_state_from_screenshot_capture(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    before = payload.get("before_obstruction") if isinstance(payload.get("before_obstruction"), dict) else {}
    after = payload.get("after_obstruction") if isinstance(payload.get("after_obstruction"), dict) else {}
    obstruction = after if after.get("present") is True else before
    if not obstruction:
        return {}
    status = _page_state_status_from_obstruction(obstruction)
    severity = str(obstruction.get("severity") or "").strip().lower()
    dismissal_successful = payload.get("dismissal_successful") is True
    if status == "clean":
        capture_quality = "clean"
    elif dismissal_successful and not after.get("present"):
        capture_quality = "clean_attempt"
    elif severity == "blocking":
        capture_quality = "blocked"
    else:
        capture_quality = "partial"
    notes = []
    if payload.get("dismissal_attempted") is True:
        notes.append("dismissal_attempted")
    if dismissal_successful:
        notes.append("dismissal_successful")
    block_reason = str(payload.get("dismissal_block_reason") or "").strip()
    if block_reason:
        notes.append(block_reason)
    return {
        "status": status,
        "obstructions": _page_state_obstructions_from_obstruction(obstruction),
        "capture_quality": capture_quality,
        "confidence": obstruction.get("confidence"),
        "source": "screenshot_capture",
        "notes": ", ".join(notes) if notes else None,
    }


def _clean_capture_decision_for_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = _row_payload(row, "screenshot_capture")
    return build_clean_capture_decision(payload)


def _page_state_status_from_obstruction(obstruction: dict[str, Any]) -> str:
    if obstruction.get("present") is not True:
        return "clean"
    obstruction_type = str(obstruction.get("type") or "").strip().lower()
    signals = " ".join(str(item).lower() for item in obstruction.get("signals") or [])
    combined = f"{obstruction_type} {signals}"
    if "cloudflare" in combined or "captcha" in combined or "verify human" in combined or "bot_check" in combined:
        return "bot_check_blocked"
    if "location" in combined:
        return "location_gated"
    if "cookie" in combined:
        return "cookie_obstructed"
    if "privacy" in combined or "consent" in combined:
        return "privacy_obstructed"
    if "promo" in combined or "promotion" in combined or "campaign" in combined:
        return "campaign_overlay"
    if "modal" in combined or "newsletter" in combined or "login_wall" in combined:
        return "modal_obstructed"
    return "unknown"


def _page_state_obstructions_from_obstruction(obstruction: dict[str, Any]) -> list[str]:
    obstruction_type = str(obstruction.get("type") or "").strip().lower()
    signals = " ".join(str(item).lower() for item in obstruction.get("signals") or [])
    combined = f"{obstruction_type} {signals}"
    obstructions = []
    if "cookie" in combined:
        obstructions.append("cookie_banner")
    if "privacy" in combined or "consent" in combined:
        obstructions.append("privacy_notice")
    if "location" in combined:
        obstructions.append("location_gate")
    if "cloudflare" in combined:
        obstructions.append("cloudflare_check")
    if "modal" in combined or "newsletter" in combined:
        obstructions.append("modal")
    if "promo" in combined or "promotion" in combined or "campaign" in combined:
        obstructions.append("campaign_overlay")
    return obstructions or [obstruction_type or "unknown"]


def _visual_signature_payload_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    return _visual_evidence_bundle_for_row(row).fused_visual_signature_payload


def _visual_evidence_bundle_for_row(row: dict[str, Any]) -> VisualEvidenceBundle:
    visual_signature = _row_payload(row, "visual_signature")
    screenshot_capture = _screenshot_capture_for_row(row)
    derive_screenshot = row.get("derive_visual_signature_from_screenshot") is True
    sources: list[VisualEvidenceSource] = []

    if visual_signature:
        sources.append(
            VisualEvidenceSource(
                source_id="visual_signature",
                source_type="visual_signature",
                available=True,
                visual_signature_payload=visual_signature,
                evidence_refs=["raw_inputs:visual_signature"],
            )
        )

    computed_style_snapshot = _row_payload(row, "computed_style_snapshot")
    computed_payload = None
    if computed_style_snapshot:
        computed_payload = computed_style_snapshot_to_visual_signature(
            computed_style_snapshot,
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
        )
        if derive_screenshot and screenshot_capture:
            computed_payload = enrich_visual_signature_with_local_screenshot(computed_payload, screenshot_capture)
        sources.append(
            VisualEvidenceSource(
                source_id="computed_style_snapshot",
                source_type="computed_style",
                available=True,
                visual_signature_payload=computed_payload,
                evidence_refs=["raw_inputs:computed_style_visual_evidence"],
                limitations=(computed_payload.get("extraction_confidence") or {}).get("limitations") or [],
            )
        )

    web_payload = _row_payload(row, "web_payload")
    web_visual_payload = None
    if web_payload:
        evidence = build_visual_evidence_from_local_inputs(
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
            web_payload=web_payload,
            screenshot_capture=screenshot_capture,
            derive_from_screenshot=derive_screenshot,
        )
        web_visual_payload = evidence.visual_signature_payload
        sources.append(
            VisualEvidenceSource(
                source_id="web_payload",
                source_type="web_payload",
                available=web_visual_payload is not None,
                visual_signature_payload=web_visual_payload,
                evidence_refs=["raw_inputs:web_visual_evidence"],
                limitations=evidence.limitations,
            )
        )

    screenshot_payload = None
    if derive_screenshot and screenshot_capture:
        screenshot_payload = screenshot_capture_to_visual_signature(
            screenshot_capture,
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
        )
        sources.append(
            VisualEvidenceSource(
                source_id="screenshot_capture",
                source_type="screenshot_vision",
                available=True,
                visual_signature_payload=screenshot_payload,
                evidence_refs=["raw_inputs:screenshot_capture"],
                limitations=["screenshot_vision_only"],
            )
        )

    external_legacy_payload = None
    external_legacy = _row_payload(row, "external_candidate_summary_legacy") or _row_payload(
        row, "contextdev_candidate_summary"
    )
    if external_legacy:
        external_legacy_payload = external_candidate_summary_legacy_to_visual_signature(
            external_legacy,
            website_url=str(row["website_url"]),
        )
        sources.append(
            VisualEvidenceSource(
                source_id="external_candidate_summary_legacy",
                source_type="external_candidate_summary_legacy",
                available=True,
                visual_signature_payload=external_legacy_payload,
                evidence_refs=["raw_inputs:external_candidate_summary_legacy"],
                limitations=(external_legacy_payload.get("extraction_confidence") or {}).get("limitations") or [],
            )
        )

    fused, notes = fuse_visual_signature_payloads(
        computed_payload=computed_payload,
        web_payload=web_visual_payload,
        screenshot_payload=screenshot_payload,
        visual_signature_payload=visual_signature,
        external_legacy_payload=external_legacy_payload,
    )
    return VisualEvidenceBundle(
        sources=sources,
        fused_visual_signature_payload=fused,
        fusion_notes=notes,
    )


def _source_comparison_for_row(
    row: dict[str, Any],
    *,
    bundle: VisualEvidenceBundle,
    coherence_breakdown: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    result = []
    screenshot_capture = _screenshot_capture_for_row(row)
    for source in bundle.sources:
        if not source.available or not source.visual_signature_payload:
            continue
        diagnosis = build_visual_diagnosis(
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
            screenshot_capture=screenshot_capture,
            visual_signature_payload=source.visual_signature_payload,
            coherence_breakdown=coherence_breakdown,
            category_hint=str(row.get("category_hint") or ""),
        ).to_dict()
        read = diagnosis["diagnosis"]
        result.append(
            {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "status": diagnosis["status"],
                "reference_profile": read["reference_profile"],
                "identity_read": read["identity_read"],
                "confidence": diagnosis["confidence"],
                "antipatterns": diagnosis["signals"]["antipatterns"],
                "limitations": diagnosis["limitations"],
                "evidence_refs": diagnosis["evidence_refs"],
            }
        )
    return result


def _screenshot_capture_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    payload = _row_payload(row, "screenshot_capture")
    if not payload:
        return None
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    if not capture:
        if payload.get("screenshot_url"):
            return payload
        screenshot_path = payload.get("raw_screenshot_path") or payload.get("screenshot_path")
        clean_decision = build_clean_capture_decision(payload)
        if clean_decision.get("use_clean_for_diagnosis") is True and payload.get("clean_attempt_screenshot_path"):
            screenshot_path = payload.get("clean_attempt_screenshot_path")
        if screenshot_path:
            normalized = {
                "screenshot_url": f"file://{screenshot_path}",
                "capture_type": payload.get("capture_type") or "viewport",
                "quality": "usable" if payload.get("status") == "ok" else payload.get("quality"),
                "source": payload.get("source"),
                "status": payload.get("status"),
            }
            return {key: value for key, value in normalized.items() if value is not None}
        return payload
    normalized = {
        "screenshot_url": capture.get("screenshot_url"),
        "capture_type": capture.get("capture_type") or payload.get("capture_type") or "viewport",
        "quality": capture.get("quality") or payload.get("quality"),
        "source": capture.get("source"),
        "status": capture.get("status"),
        "error_message": capture.get("error_message"),
        "error_type": capture.get("error_type"),
    }
    if capture.get("success") is True and not normalized["quality"]:
        normalized["quality"] = "usable"
    return {key: value for key, value in normalized.items() if value is not None}


def external_candidate_summary_legacy_to_visual_signature(
    payload: dict[str, Any],
    *,
    website_url: str,
) -> dict[str, Any]:
    """Map historical external visual candidates into lab visual evidence.

    This exists only for legacy local DB data. New probes should use local
    web payload, computed styles and screenshot evidence instead.
    """
    candidates = [
        item
        for item in payload.get("candidates") or []
        if isinstance(item, dict)
        and str(item.get("supports_channel") or "").startswith("visual")
        and _candidate_matches_domain(item, website_url)
    ]
    if not candidates:
        return {
            "interpretation_status": "not_interpretable",
            "source": "external_candidate_summary_legacy",
            "extraction_confidence": {
                "score": 0.0,
                "level": "low",
                "limitations": ["external_legacy_visual_candidates_missing"],
            },
        }

    colors = _external_legacy_colors(candidates)
    typography = _external_legacy_typography(candidates)
    components = _external_legacy_components(candidates)
    visual_candidate_count = len(candidates)
    has_component_signal = bool(components["components"] or components["primary_ctas"])
    has_typography_signal = bool(typography)
    has_color_signal = bool(colors["dominant_colors"] or colors["accent_candidates"])
    confidence_score = 0.35
    confidence_score += 0.12 if has_color_signal else 0
    confidence_score += 0.12 if has_typography_signal else 0
    confidence_score += 0.12 if has_component_signal else 0
    confidence_score += min(visual_candidate_count, 4) * 0.04
    confidence_score = min(round(confidence_score, 2), 0.78)

    return {
        "interpretation_status": "interpretable",
        "source": "external_candidate_summary_legacy",
        "assets": {
            "screenshot_available": False,
            "image_count": _external_legacy_image_signal_count(candidates),
        },
        "layout": {
            "has_navigation": False,
            "has_hero": True,
            "visual_density": "balanced",
            "layout_patterns": ["external_styleguide_summary"],
        },
        "logo": {},
        "components": components,
        "colors": colors,
        "typography": typography,
        "consistency": {"overall_consistency": confidence_score},
        "extraction_confidence": {
            "score": confidence_score,
            "level": "medium" if confidence_score >= 0.6 else "low",
            "limitations": ["external_candidate_summary_legacy_only"],
        },
        "semantics": {
            "status": "detected",
            "data": {
                "visual_polish_score": 7 if confidence_score >= 0.6 else 5,
                "visual_coherence": "detected",
            },
        },
        "vision": {},
        "external_candidate_summary_legacy": {
            "candidate_count": visual_candidate_count,
            "candidate_ids": [str(item.get("candidate_id") or "") for item in candidates if item.get("candidate_id")],
        },
    }


def contextdev_candidate_summary_to_visual_signature(
    payload: dict[str, Any],
    *,
    website_url: str,
) -> dict[str, Any]:
    """Backward-compatible alias for historical tests/manifests."""
    return external_candidate_summary_legacy_to_visual_signature(payload, website_url=website_url)


def _coherence_breakdown_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    explicit = _row_payload(row, "coherence_breakdown")
    magnetism_payload = _row_payload(row, "magnetism_payload")
    extracted = extract_coherence_breakdown(magnetism_payload or {})
    if explicit and extracted:
        return {**explicit, **extracted}
    return extracted or explicit


def extract_coherence_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract Magnetism coherence breakdown from known local lab payload shapes."""
    if not isinstance(payload, dict):
        return {}

    scanner = payload.get("scanner") if isinstance(payload.get("scanner"), dict) else {}
    normalized = scanner.get("score_coherence_breakdown")
    if isinstance(normalized, dict) and normalized:
        return dict(normalized)

    methodology = payload.get("methodology") if isinstance(payload.get("methodology"), dict) else {}
    score_breakdown = methodology.get("score_breakdown") if isinstance(methodology.get("score_breakdown"), dict) else {}
    coherence = score_breakdown.get("coherence")
    if isinstance(coherence, dict) and coherence:
        return dict(coherence)

    raw_score_breakdown = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
    raw_coherence = raw_score_breakdown.get("coherence")
    if isinstance(raw_coherence, dict) and raw_coherence:
        return dict(raw_coherence)

    coherence_score = payload.get("coherence_score")
    if coherence_score is not None:
        return {"visual_identity": coherence_score, "source": "coherence_score_fallback"}

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    if scores.get("coherence") is not None:
        return {"visual_identity": scores.get("coherence"), "source": "scores.coherence_fallback"}
    return {}


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _candidate_matches_domain(candidate: dict[str, Any], website_url: str) -> bool:
    expected = _domain(website_url)
    if not expected:
        return True
    source = _domain(str(candidate.get("source_url") or ""))
    if source and (source == expected or source.endswith(f".{expected}") or expected.endswith(f".{source}")):
        return True
    for note in candidate.get("notes") or []:
        text = str(note).lower()
        if text.startswith("contextdev_domain:"):
            noted = text.split(":", 1)[1].strip()
            if noted == expected or noted.endswith(f".{expected}") or expected.endswith(f".{noted}"):
                return True
    return False


def _external_legacy_colors(candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    dominant: list[str] = []
    accents: list[str] = []
    for candidate in candidates:
        if candidate.get("candidate_type") != "visual_colors":
            continue
        text = str(candidate.get("text") or "")
        data = _try_json_object(text)
        if not data:
            continue
        for key in ("background", "text"):
            if data.get(key):
                dominant.append(str(data[key]))
        if data.get("accent"):
            accents.append(str(data["accent"]))
    return {
        "dominant_colors": _dedupe(dominant),
        "accent_candidates": _dedupe(accents),
    }


def _external_legacy_typography(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("candidate_type") != "visual_typography":
            continue
        data = _try_json_object(str(candidate.get("text") or ""))
        headings = data.get("headings") if isinstance(data.get("headings"), dict) else {}
        h1 = headings.get("h1") if isinstance(headings.get("h1"), dict) else {}
        h2 = headings.get("h2") if isinstance(headings.get("h2"), dict) else {}
        h1_size = _css_px(h1.get("fontSize"))
        h2_size = _css_px(h2.get("fontSize"))
        heading_scale = "moderate"
        if h1_size and h2_size and h2_size and h1_size / h2_size < 1.25:
            heading_scale = "flat"
        return {
            "heading_scale": heading_scale,
            "heading_font": h1.get("fontFamily"),
            "body_font": (data.get("p") or {}).get("fontFamily") if isinstance(data.get("p"), dict) else None,
        }
    return {}


def _external_legacy_components(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(candidate.get("text") or "").lower() for candidate in candidates)
    components = []
    primary_ctas = []
    if "button" in text or "call-to-action" in text or "cta" in text:
        components.append({"type": "cta", "count": 1})
        primary_ctas.append("detected")
    if "card" in text:
        components.append({"type": "card", "count": 3})
    return {
        "primary_ctas": primary_ctas,
        "components": components,
    }


def _external_legacy_image_signal_count(candidates: list[dict[str, Any]]) -> int:
    return sum(1 for item in candidates if str(item.get("candidate_type") or "").startswith("visual_image"))


def _try_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _css_px(value: Any) -> float:
    text = str(value or "").strip().lower().removesuffix("px")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path or "").lower().strip()
    return host[4:] if host.startswith("www.") else host


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in normalized.split("-") if part) or "brand"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to lab manifest JSON.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory for generated lab output.")
    args = parser.parse_args()
    result = run_lab(args.manifest, output_root=args.output_root)
    print(result["output_dir"])


if __name__ == "__main__":
    main()
