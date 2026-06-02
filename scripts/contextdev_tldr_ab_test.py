#!/usr/bin/env python3
"""Run an Analyst TLDR A/B test for original vs Context.dev-enriched packs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.analyst_tldr import TLDR_KEYS, run_analyst_tldr_pass


def main() -> int:
    args = _parse_args()
    input_payload = json.loads(args.dry_run.read_text(encoding="utf-8"))
    dry_run = input_payload.get("dry_run") if isinstance(input_payload.get("dry_run"), dict) else input_payload
    brand_name = str(args.brand_name or dry_run.get("brand_name") or _pack_brand_name(dry_run.get("original_pack")) or "")
    url = str(args.url or _pack_url(dry_run.get("original_pack")) or "")
    llm = LLMAnalyzer()

    original = _run_variant(llm=llm, brand_name=brand_name, url=url, pack=dry_run["original_pack"], variant="original")
    enriched = _run_variant(llm=llm, brand_name=brand_name, url=url, pack=dry_run["enriched_pack"], variant="enriched")
    report = {
        "version": "contextdev_tldr_ab_test_v0_1",
        "brand_name": brand_name,
        "url": url,
        "source_dry_run": str(args.dry_run),
        "promotion_summary": dry_run.get("promotion_report", {}).get("status_counts", {}),
        "field_update_count": len(dry_run.get("field_updates") or []),
        "field_updates": dry_run.get("field_updates") or [],
        "variants": {
            "original": original,
            "enriched": enriched,
        },
        "comparison": _compare_tldr(original.get("validated"), enriched.get("validated")),
        "llm": {
            "model": llm.model,
            "base_url": llm.base_url,
            "cache_hits": llm.cache_hits,
            "cache_misses": llm.cache_misses,
            "cache_writes": llm.cache_writes,
            "failures": llm.call_failures,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    comparison = report["comparison"]
    print(
        "Summary: "
        f"changed_blocks={len(comparison['changed_blocks'])} "
        f"original_detected={comparison['original_metrics']['detected_blocks']} "
        f"enriched_detected={comparison['enriched_metrics']['detected_blocks']} "
        f"evidence_delta={comparison['evidence_source_delta']}"
    )
    return 0


def _run_variant(*, llm: LLMAnalyzer, brand_name: str, url: str, pack: dict[str, Any], variant: str) -> dict[str, Any]:
    result = run_analyst_tldr_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        research_pack=pack,
        current_tldr={},
    )
    return {
        "variant": variant,
        "analysis_error": result.get("analysis_error"),
        "validated": result.get("validated"),
        "normalized": result.get("normalized"),
        "raw": result.get("raw"),
        "metrics": _tldr_metrics(result.get("validated")),
    }


def _compare_tldr(original: dict[str, Any] | None, enriched: dict[str, Any] | None) -> dict[str, Any]:
    original_blocks = _blocks(original)
    enriched_blocks = _blocks(enriched)
    changed_blocks = []
    for key in TLDR_KEYS:
        before = original_blocks.get(key, {})
        after = enriched_blocks.get(key, {})
        if _block_signature(before) == _block_signature(after):
            continue
        changed_blocks.append(
            {
                "block": key,
                "original": _block_summary(before),
                "enriched": _block_summary(after),
            }
        )
    original_metrics = _tldr_metrics(original)
    enriched_metrics = _tldr_metrics(enriched)
    return {
        "original_metrics": original_metrics,
        "enriched_metrics": enriched_metrics,
        "changed_blocks": changed_blocks,
        "detected_block_delta": enriched_metrics["detected_blocks"] - original_metrics["detected_blocks"],
        "evidence_source_delta": enriched_metrics["evidence_source_count"] - original_metrics["evidence_source_count"],
        "human_review_delta": enriched_metrics["human_review_count"] - original_metrics["human_review_count"],
    }


def _tldr_metrics(payload: dict[str, Any] | None) -> dict[str, Any]:
    blocks = _blocks(payload)
    detected = 0
    evidence_sources = 0
    human_review = 0
    confidence_counts: dict[str, int] = {}
    claim_type_counts: dict[str, int] = {}
    for key in TLDR_KEYS:
        block = blocks.get(key, {})
        answer = block.get("answer")
        claim_type = str(block.get("claim_type") or "absent")
        confidence = str(block.get("confidence") or "low")
        if answer and claim_type != "absent":
            detected += 1
        evidence_sources += len(block.get("evidence_sources") or [])
        if block.get("human_review_recommended"):
            human_review += 1
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        claim_type_counts[claim_type] = claim_type_counts.get(claim_type, 0) + 1
    return {
        "detected_blocks": detected,
        "evidence_source_count": evidence_sources,
        "human_review_count": human_review,
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "claim_type_counts": dict(sorted(claim_type_counts.items())),
    }


def _blocks(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    blocks = payload.get("tldr_brand3")
    return blocks if isinstance(blocks, dict) else {}


def _block_signature(block: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(block.get("answer") or ""),
        str(block.get("claim_type") or ""),
        str(block.get("confidence") or ""),
        str(block.get("reasoning") or ""),
    )


def _block_summary(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": block.get("answer"),
        "claim_type": block.get("claim_type"),
        "confidence": block.get("confidence"),
        "human_review_recommended": block.get("human_review_recommended"),
        "evidence_sources": block.get("evidence_sources") or [],
    }


def _pack_brand_name(pack: Any) -> str:
    if not isinstance(pack, dict):
        return ""
    resolved = pack.get("resolved_entity")
    if isinstance(resolved, dict):
        return str(resolved.get("resolved_entity") or "")
    return ""


def _pack_url(pack: Any) -> str:
    return str(pack.get("input_url") or "") if isinstance(pack, dict) else ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", type=Path, required=True)
    parser.add_argument("--brand-name", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--output", type=Path, default=Path("out/contextdev_tldr_ab_test/report.json"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
