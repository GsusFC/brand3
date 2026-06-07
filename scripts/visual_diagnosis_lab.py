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
        visual_signature_payload = _visual_signature_payload_for_row(row)
        diagnosis = build_visual_diagnosis(
            brand_name=str(row["brand_name"]),
            website_url=str(row["website_url"]),
            screenshot_capture=_screenshot_capture_for_row(row),
            visual_signature_payload=visual_signature_payload,
            coherence_breakdown=coherence_breakdown,
            category_hint=str(row.get("category_hint") or ""),
        )
        result = {
            "brand_name": row["brand_name"],
            "website_url": row["website_url"],
            "category_hint": row.get("category_hint") or "",
            "magnetism": {
                "coherence_breakdown": coherence_breakdown or {},
                "visual_identity": (coherence_breakdown or {}).get("visual_identity"),
            },
            "diagnosis": diagnosis.to_dict(),
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


def _visual_signature_payload_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    visual_signature = _row_payload(row, "visual_signature")
    if visual_signature:
        return visual_signature
    contextdev_summary = _row_payload(row, "contextdev_candidate_summary")
    if contextdev_summary:
        return contextdev_candidate_summary_to_visual_signature(
            contextdev_summary,
            website_url=str(row["website_url"]),
        )
    if row.get("derive_visual_signature_from_screenshot") is True:
        screenshot_capture = _screenshot_capture_for_row(row)
        if screenshot_capture:
            return screenshot_capture_to_visual_signature(
                screenshot_capture,
                brand_name=str(row["brand_name"]),
                website_url=str(row["website_url"]),
            )
    return None


def _screenshot_capture_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    payload = _row_payload(row, "screenshot_capture")
    if not payload:
        return None
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    if not capture:
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


def screenshot_capture_to_visual_signature(
    screenshot_capture: dict[str, Any],
    *,
    brand_name: str,
    website_url: str,
) -> dict[str, Any]:
    """Build lab-only visual evidence from an existing local screenshot."""
    base_payload: dict[str, Any] = {
        "brand_name": brand_name,
        "website_url": website_url,
        "interpretation_status": "interpretable",
        "source": "screenshot_vision_lab",
        "assets": {"screenshot_available": True},
        "layout": {},
        "logo": {},
        "components": {"primary_ctas": [], "components": []},
        "colors": {},
        "typography": {},
        "consistency": {},
        "extraction_confidence": {
            "score": 0.1,
            "level": "low",
            "limitations": ["screenshot_vision_only"],
        },
    }
    try:
        from src.visual_signature.vision import enrich_visual_signature_with_vision

        enriched = enrich_visual_signature_with_vision(
            visual_signature_payload=base_payload,
            screenshot_payload=screenshot_capture,
        )
    except Exception as exc:
        return {
            **base_payload,
            "interpretation_status": "not_interpretable",
            "extraction_confidence": {
                "score": 0.0,
                "level": "low",
                "limitations": [f"screenshot_vision_failed: {exc}"],
            },
        }
    return _promote_vision_evidence(enriched)


def contextdev_candidate_summary_to_visual_signature(
    payload: dict[str, Any],
    *,
    website_url: str,
) -> dict[str, Any]:
    """Map Context.dev visual candidates into the lab visual evidence shape.

    This is intentionally a lab adapter, not a production Visual Signature
    replacement. It preserves provenance and only uses candidates for the
    requested domain.
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
            "source": "contextdev_candidate_summary",
            "extraction_confidence": {
                "score": 0.0,
                "level": "low",
                "limitations": ["contextdev_visual_candidates_missing"],
            },
        }

    colors = _contextdev_colors(candidates)
    typography = _contextdev_typography(candidates)
    components = _contextdev_components(candidates)
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
        "source": "contextdev_candidate_summary",
        "assets": {
            "screenshot_available": False,
            "image_count": _contextdev_image_signal_count(candidates),
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
            "limitations": ["contextdev_visual_summary_only"],
        },
        "semantics": {
            "status": "detected",
            "data": {
                "visual_polish_score": 7 if confidence_score >= 0.6 else 5,
                "visual_coherence": "detected",
            },
        },
        "vision": {},
        "contextdev": {
            "candidate_count": visual_candidate_count,
            "candidate_ids": [str(item.get("candidate_id") or "") for item in candidates if item.get("candidate_id")],
        },
    }


def _promote_vision_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    viewport_palette = vision.get("viewport_palette") if isinstance(vision.get("viewport_palette"), dict) else {}
    viewport_composition = (
        vision.get("viewport_composition") if isinstance(vision.get("viewport_composition"), dict) else {}
    )
    viewport_confidence = (
        vision.get("viewport_confidence") if isinstance(vision.get("viewport_confidence"), dict) else {}
    )
    if not screenshot.get("available"):
        payload["interpretation_status"] = "not_interpretable"
        payload["extraction_confidence"] = {
            "score": 0.0,
            "level": "low",
            "limitations": ["screenshot_vision_unavailable"],
        }
        return payload

    dominant_colors = [
        str(item.get("hex"))
        for item in viewport_palette.get("dominant_colors") or []
        if isinstance(item, dict) and item.get("hex")
    ]
    density = str(viewport_composition.get("visual_density") or "unknown")
    confidence_score = _bounded_float(viewport_confidence.get("score"), default=0.45)
    payload["assets"] = {
        **(payload.get("assets") if isinstance(payload.get("assets"), dict) else {}),
        "screenshot_available": True,
        "image_count": 1,
    }
    payload["colors"] = {
        "dominant_colors": dominant_colors[:6],
        "accent_candidates": dominant_colors[6:8],
    }
    payload["layout"] = {
        "has_navigation": False,
        "has_hero": False,
        "visual_density": density,
        "layout_patterns": ["screenshot_vision"],
    }
    payload["consistency"] = {
        "overall_consistency": round(max(0.1, min(0.85, confidence_score)), 3),
    }
    payload["extraction_confidence"] = {
        "score": round(max(0.1, min(0.75, confidence_score)), 3),
        "level": "medium" if confidence_score >= 0.55 else "low",
        "limitations": ["screenshot_vision_only"],
    }
    return payload


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


def _contextdev_colors(candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
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


def _contextdev_typography(candidates: list[dict[str, Any]]) -> dict[str, Any]:
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


def _contextdev_components(candidates: list[dict[str, Any]]) -> dict[str, Any]:
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


def _contextdev_image_signal_count(candidates: list[dict[str, Any]]) -> int:
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


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))


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
