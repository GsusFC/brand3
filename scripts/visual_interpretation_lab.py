#!/usr/bin/env python3
"""Run Lab-only multimodal visual interpretation over local evidence packs."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.visual_interpretation import GeminiVisionClient
from src.visual_interpretation.gemini import DEFAULT_VISUAL_ADJUDICATOR_MODEL, DEFAULT_VISUAL_INTERPRETATION_MODEL
from src.visual_interpretation.models import EvidenceUse, VisualEvidencePack, VisualInterpretation
from src.visual_interpretation.validation import validate_visual_interpretation


DEFAULT_OUTPUT_ROOT = Path("out") / "visual_interpretation_lab"

SYSTEM_PROMPT = """You are a senior visual brand strategist.
You interpret website screenshots using only the provided visual evidence pack and image.
You must separate direct visual observations from inferred brand judgement.
Return only valid JSON matching the requested contract.
If the screenshot is missing, blocked, or not evaluable, return status "not_evaluable" with low confidence."""


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(Path(path))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
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


def run_lab(
    manifest_path: str | Path,
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    execute: bool = False,
    model: str = DEFAULT_VISUAL_INTERPRETATION_MODEL,
    adjudicate: bool = False,
    adjudicator_model: str = DEFAULT_VISUAL_ADJUDICATOR_MODEL,
) -> dict[str, Any]:
    rows = load_manifest(manifest_path)
    output_dir = Path(output_root) / _timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    client = GeminiVisionClient(model=model)
    adjudicator = GeminiVisionClient(model=adjudicator_model) if adjudicate else None
    results = []
    for row in rows:
        pack = build_visual_evidence_pack(row)
        client.last_usage_metadata = {}
        client.last_failure = None
        started = time.perf_counter()
        interpretation = _interpret_pack(pack, client=client, execute=execute)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        usage_metadata = dict(client.last_usage_metadata)
        provider_failure = client.last_failure
        validation = validate_visual_interpretation(pack, interpretation)

        adjudicated = False
        if execute and adjudicator and pack.status != "not_evaluable" and (not validation.valid or interpretation.confidence == "low"):
            adjudicator.last_usage_metadata = {}
            adjudicator.last_failure = None
            adjudicator_started = time.perf_counter()
            candidate = _interpret_pack(pack, client=adjudicator, execute=True)
            elapsed_ms += int((time.perf_counter() - adjudicator_started) * 1000)
            candidate_validation = validate_visual_interpretation(pack, candidate)
            if candidate_validation.valid:
                interpretation = candidate
                interpretation.adjudicator_model = adjudicator_model
                validation = candidate_validation
                usage_metadata = _sum_usage_metadata(usage_metadata, adjudicator.last_usage_metadata)
                provider_failure = adjudicator.last_failure
                adjudicated = True

        result = {
            "brand_name": pack.brand_name,
            "website_url": pack.website_url,
            "category_hint": pack.category_hint,
            "mode": "gemini" if execute else "dry_run",
            "model": interpretation.model or model,
            "adjudicated": adjudicated,
            "latency_ms": elapsed_ms,
            "usage_metadata": usage_metadata,
            "provider_failure": provider_failure,
            "visual_evidence_pack": pack.to_dict(),
            "interpretation": interpretation.to_dict(),
            "validation": validation.to_dict(),
        }
        results.append(result)
        _write_json(output_dir / f"{_slug(pack.brand_name)}.json", result)

    summary = {
        "schema_version": "visual-interpretation-lab-run-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest_path": str(manifest_path),
        "mode": "gemini" if execute else "dry_run",
        "model": model,
        "adjudicator_model": adjudicator_model if adjudicate else None,
        "brand_count": len(results),
        "metrics": _metrics(results),
        "results": results,
    }
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "metrics.json", summary["metrics"])
    _write_json(output_dir / "comparison.json", _comparison_json(summary))
    (output_dir / "summary.md").write_text(_summary_markdown(summary) + "\n", encoding="utf-8")
    return {"output_dir": str(output_dir), "summary": summary}


def build_visual_evidence_pack(row: dict[str, Any]) -> VisualEvidencePack:
    screenshot_capture = _row_payload(row, "screenshot_capture") or {}
    page_state = _row_payload(row, "page_state") or _page_state_from_screenshot_capture(screenshot_capture)
    human_review = _row_payload(row, "human_review") or {}
    visual_signature = _row_payload(row, "visual_signature") or _load_optional_json(row.get("visual_signature_path")) or {}
    computed_style = _row_payload(row, "computed_style") or _load_optional_json(row.get("computed_style_path")) or {}
    clean_capture_decision = _row_payload(row, "clean_capture_decision") or {}

    screenshot_path = _screenshot_path(screenshot_capture)
    screenshot_available = bool(screenshot_path and _path_exists(screenshot_path))
    capture_quality = _capture_quality(screenshot_capture, page_state, screenshot_available=screenshot_available)
    status = _pack_status(capture_quality, screenshot_available=screenshot_available)
    evidence_refs = []
    limitations = []
    if screenshot_available:
        evidence_refs.append("screenshot:viewport")
    else:
        limitations.append("screenshot_missing")
    if visual_signature:
        evidence_refs.append("visual_signature:summary")
    if computed_style:
        evidence_refs.append("computed_style:summary")
    if page_state:
        evidence_refs.append("page_state")
    if human_review:
        evidence_refs.append("human_review")
    if capture_quality in {"blocked", "missing"}:
        limitations.append(f"capture_quality:{capture_quality}")

    return VisualEvidencePack(
        brand_name=str(row["brand_name"]),
        website_url=str(row["website_url"]),
        category_hint=str(row.get("category_hint") or ""),
        status=status,
        capture_quality=capture_quality,
        screenshot_path=screenshot_path,
        screenshot_mime_type=mimetypes.guess_type(str(screenshot_path))[0] if screenshot_path else None,
        screenshot_available=screenshot_available,
        page_state=_compact_dict(page_state),
        clean_capture_decision=_compact_dict(clean_capture_decision),
        visual_signature_summary=_visual_signature_summary(visual_signature),
        computed_style_summary=_computed_style_summary(computed_style),
        human_review=_compact_dict(human_review),
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _interpret_pack(pack: VisualEvidencePack, *, client: GeminiVisionClient, execute: bool) -> VisualInterpretation:
    if not execute or pack.status == "not_evaluable":
        return _dry_run_interpretation(pack, model=client.model)
    return client.interpret(pack, system_prompt=SYSTEM_PROMPT, user_prompt=_user_prompt(pack))


def _dry_run_interpretation(pack: VisualEvidencePack, *, model: str) -> VisualInterpretation:
    if pack.status == "not_evaluable":
        return VisualInterpretation(
            brand_name=pack.brand_name,
            website_url=pack.website_url,
            status="not_evaluable",
            confidence="low",
            limitations=pack.limitations or ["visual_evidence_not_evaluable"],
            model=model,
        )

    reference_profile = _profile_from_hint(pack.category_hint)
    identity_read = {
        "premium_luxury": "controlled premium visual system",
        "developer_first": "functional product-led visual clarity",
        "editorial_media": "editorial identity with recognizable pacing",
        "ai_native": "restrained AI-native institutional clarity",
        "wellness_lifestyle": "soft lifestyle coherence",
        "template_saas": "polished but familiar SaaS composition",
    }.get(reference_profile, "visual system requires model interpretation")
    strengths = ["visible screenshot evidence is available"]
    if pack.visual_signature_summary.get("colors"):
        strengths.append("visual signature includes palette evidence")
    if pack.visual_signature_summary.get("layout"):
        strengths.append("visual signature includes layout evidence")

    return VisualInterpretation(
        brand_name=pack.brand_name,
        website_url=pack.website_url,
        status="limited" if pack.status == "limited" else "usable",
        reference_profile=reference_profile,
        identity_read=identity_read,
        confidence="medium",
        visual_positioning=f"{pack.brand_name} appears closest to {reference_profile} based on the available screenshot and local visual evidence.",
        strengths=strengths,
        risks=["dry_run_result_requires_gemini_review"],
        antipatterns=[],
        evidence_used=[EvidenceUse(ref=ref, observation=f"Used {ref}") for ref in pack.evidence_refs],
        recommendations=["Run execute mode with Gemini before using this result for product decisions."],
        limitations=["dry_run_not_a_model_judgement"],
        model=model,
    )


def _user_prompt(pack: VisualEvidencePack) -> str:
    payload = pack.to_dict()
    payload.pop("human_review", None)
    return f"""Interpret this website visual evidence.

VisualEvidencePack:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Return JSON with this exact shape:
{{
  "brand_name": "{pack.brand_name}",
  "website_url": "{pack.website_url}",
  "status": "usable | limited | not_evaluable",
  "reference_profile": "template_saas | premium_luxury | developer_first | editorial_media | ai_native | wellness_lifestyle | ecommerce_mass_market | local_service | unknown",
  "identity_read": "short operational visual diagnosis",
  "confidence": "high | medium | low",
  "visual_positioning": "one sentence about what the visual system communicates",
  "strengths": ["specific visual strength"],
  "risks": ["specific visual risk"],
  "antipatterns": ["specific anti-pattern, if present"],
  "evidence_used": [
    {{"ref": "one of the VisualEvidencePack evidence_refs", "observation": "direct observation grounded in that evidence"}}
  ],
  "recommendations": ["specific next step"],
  "limitations": ["evidence or interpretation limitation"]
}}"""


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        "total": len(results),
        "valid": 0,
        "invalid": 0,
        "usable": 0,
        "limited": 0,
        "not_evaluable": 0,
        "human_reviewed": 0,
        "human_identity_fit_yes_or_partial": 0,
        "human_identity_fit_no": 0,
        "missing_screenshot": 0,
        "provider_failures": 0,
        "adjudicated": 0,
        "total_latency_ms": 0,
        "avg_latency_ms": 0,
        "prompt_token_count": 0,
        "candidates_token_count": 0,
        "total_token_count": 0,
    }
    for row in results:
        validation = row["validation"]
        interpretation = row["interpretation"]
        pack = row["visual_evidence_pack"]
        metrics["valid" if validation["valid"] else "invalid"] += 1
        metrics[interpretation["status"]] += 1
        if not pack["screenshot_available"]:
            metrics["missing_screenshot"] += 1
        if row.get("provider_failure"):
            metrics["provider_failures"] += 1
        if row.get("adjudicated"):
            metrics["adjudicated"] += 1
        metrics["total_latency_ms"] += int(row.get("latency_ms") or 0)
        usage = row.get("usage_metadata") if isinstance(row.get("usage_metadata"), dict) else {}
        metrics["prompt_token_count"] += int(usage.get("promptTokenCount") or 0)
        metrics["candidates_token_count"] += int(usage.get("candidatesTokenCount") or 0)
        metrics["total_token_count"] += int(usage.get("totalTokenCount") or 0)
        human_review = pack.get("human_review") or {}
        if human_review:
            metrics["human_reviewed"] += 1
            fit = str(human_review.get("identity_read_fit") or "").lower()
            if fit in {"yes", "partial"}:
                metrics["human_identity_fit_yes_or_partial"] += 1
            elif fit == "no":
                metrics["human_identity_fit_no"] += 1
    if results:
        metrics["avg_latency_ms"] = int(metrics["total_latency_ms"] / len(results))
    return metrics


def _comparison_json(summary: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in summary["results"]:
        interpretation = row["interpretation"]
        pack = row["visual_evidence_pack"]
        rows.append(
            {
                "brand_name": row["brand_name"],
                "website_url": row["website_url"],
                "category_hint": row.get("category_hint") or "",
                "pack_status": pack["status"],
                "capture_quality": pack["capture_quality"],
                "screenshot_available": pack["screenshot_available"],
                "interpretation_status": interpretation["status"],
                "reference_profile": interpretation["reference_profile"],
                "identity_read": interpretation["identity_read"],
                "confidence": interpretation["confidence"],
                "validation": row["validation"],
                "human_review": pack.get("human_review") or {},
            }
        )
    return {
        "schema_version": "visual-interpretation-comparison-v1",
        "generated_at": summary["generated_at"],
        "brand_count": summary["brand_count"],
        "metrics": summary["metrics"],
        "rows": rows,
    }


def _sum_usage_metadata(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "promptTokenCount",
        "candidatesTokenCount",
        "totalTokenCount",
        "thoughtsTokenCount",
    }
    result: dict[str, Any] = {}
    for key in keys:
        total = int((left or {}).get(key) or 0) + int((right or {}).get(key) or 0)
        if total:
            result[key] = total
    return result


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Visual Interpretation Lab Summary",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Mode: {summary['mode']}",
        f"- Model: {summary['model']}",
        f"- Brand count: {summary['brand_count']}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in summary["metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Brand | Pack | Capture | Interpretation | Profile | Confidence | Valid |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary["results"]:
        pack = row["visual_evidence_pack"]
        interpretation = row["interpretation"]
        validation = row["validation"]
        lines.append(
            f"| {row['brand_name']} | {pack['status']} | {pack['capture_quality']} | "
            f"{interpretation['status']} | {interpretation['reference_profile']} | "
            f"{interpretation['confidence']} | {validation['valid']} |"
        )
    return "\n".join(lines)


def _profile_from_hint(category_hint: str) -> str:
    text = category_hint.lower()
    if "luxury" in text or "premium" in text:
        return "premium_luxury"
    if "developer" in text or "documentation" in text or "infrastructure" in text:
        return "developer_first"
    if "editorial" in text or "media" in text:
        return "editorial_media"
    if re.search(r"\bai\b", text) or "artificial intelligence" in text:
        return "ai_native"
    if "wellness" in text or "lifestyle" in text:
        return "wellness_lifestyle"
    if "saas" in text or "productivity" in text:
        return "template_saas"
    if "commerce" in text or "retail" in text:
        return "ecommerce_mass_market"
    return "unknown"


def _visual_signature_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        return {}
    return {
        "interpretation_status": payload.get("interpretation_status"),
        "assets": payload.get("assets") or {},
        "colors": (payload.get("colors") or {}),
        "layout": (payload.get("layout") or {}),
        "typography": (payload.get("typography") or {}),
        "components": (payload.get("components") or {}),
        "consistency": (payload.get("consistency") or {}),
        "vision": (payload.get("vision") or {}),
    }


def _computed_style_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        return {}
    elements = payload.get("elements") if isinstance(payload.get("elements"), list) else []
    return {
        "schema_version": payload.get("schema_version"),
        "url": payload.get("url"),
        "colors": payload.get("colors") or [],
        "element_count": len(elements),
        "sample_elements": elements[:10],
    }


def _capture_quality(
    screenshot_capture: dict[str, Any],
    page_state: dict[str, Any],
    *,
    screenshot_available: bool,
) -> str:
    if not screenshot_available:
        return "missing"
    quality = str(screenshot_capture.get("quality") or page_state.get("capture_quality") or "").lower()
    if quality in {"clean", "usable", "partial", "blocked"}:
        return quality
    if page_state.get("status") == "blocked":
        return "blocked"
    return "usable"


def _pack_status(capture_quality: str, *, screenshot_available: bool) -> str:
    if not screenshot_available or capture_quality in {"blocked", "missing"}:
        return "not_evaluable"
    if capture_quality == "partial":
        return "limited"
    return "ready"


def _screenshot_path(payload: dict[str, Any]) -> str | None:
    value = payload.get("screenshot_url") or payload.get("path")
    if not value:
        return None
    text = str(value)
    if text.startswith("file://"):
        stripped = text.removeprefix("file://")
        if stripped and not stripped.startswith("/"):
            return stripped
        parsed = urlparse(text)
        return parsed.path or stripped
    return text


def _page_state_from_screenshot_capture(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if payload.get("quality") == "usable":
        return {"status": "clean", "capture_quality": "usable", "source": "screenshot_capture"}
    return {}


def _row_payload(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    inline = row.get(key)
    if isinstance(inline, dict):
        return inline
    return _load_optional_json(row.get(f"{key}_path"))


def _load_optional_json(value: Any) -> dict[str, Any] | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.exists():
        return None
    payload = _load_json(path)
    return payload if isinstance(payload, dict) else None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


def _path_exists(value: str) -> bool:
    return Path(value).exists()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-") or "brand"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--execute", action="store_true", help="Call Gemini. Default is deterministic dry-run.")
    parser.add_argument("--model", default=DEFAULT_VISUAL_INTERPRETATION_MODEL)
    parser.add_argument("--adjudicate", action="store_true", help="Use Gemini Pro adjudicator for low-confidence/invalid rows.")
    parser.add_argument("--adjudicator-model", default=DEFAULT_VISUAL_ADJUDICATOR_MODEL)
    args = parser.parse_args()

    result = run_lab(
        args.manifest,
        output_root=args.output_root,
        execute=args.execute,
        model=args.model,
        adjudicate=args.adjudicate,
        adjudicator_model=args.adjudicator_model,
    )
    print(result["output_dir"])


if __name__ == "__main__":
    main()
