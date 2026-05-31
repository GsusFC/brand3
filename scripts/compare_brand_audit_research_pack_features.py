"""Compare stored Brand Audit feature output with Research Pack re-evaluation.

This is an operator script for validating whether the Research Pack input
improves feature-level LLM evidence without re-scraping the target site.
It reads an existing run snapshot, rebuilds the Research Pack from the same
snapshot, and re-runs only the Brand Audit features that now accept that pack.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import fields
from typing import Any

from src.collectors.competitor_collector import CompetitorData, CompetitorInfo, ComparisonResult
from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData
from src.config import BRAND3_DB_PATH
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.research_prompt_input import research_pack_prompt_input
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.storage.sqlite_store import SQLiteStore


MIGRATED_FEATURES = (
    ("diferenciacion", "positioning_clarity"),
    ("diferenciacion", "uniqueness"),
    ("coherencia", "messaging_consistency"),
    ("coherencia", "tone_consistency"),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="+", type=int, help="Existing Brand Audit run IDs.")
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument("--summary", action="store_true", help="Emit compact per-feature summary rows.")
    args = parser.parse_args()

    store = SQLiteStore(args.db_path)
    reports = [_compare_run(store, run_id) for run_id in args.run_ids]
    if args.summary:
        print(json.dumps(_summary(reports), indent=2, ensure_ascii=False))
    elif len(reports) == 1:
        print(json.dumps(reports[0], indent=2, ensure_ascii=False))
    else:
        print(json.dumps(reports, indent=2, ensure_ascii=False))


def _compare_run(store: SQLiteStore, run_id: int) -> dict[str, Any]:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        raise SystemExit(f"No run snapshot found for run_id={run_id}")

    web = _web_data(_raw_source(snapshot, "web"))
    exa = _exa_data(_raw_source(snapshot, "exa"))
    competitors = _competitor_data(_raw_source(snapshot, "competitors"))
    pack = build_brand_research_pack_from_graph(
        build_evidence_graph_from_snapshot(snapshot)
    )

    llm = LLMAnalyzer()
    diff = DiferenciacionExtractor(llm=llm)
    coh = CoherenciaExtractor(llm=llm, skip_visual_analysis=True)

    after = {
        ("diferenciacion", "positioning_clarity"): diff._positioning_clarity(
            web, competitors, pack
        ),
        ("diferenciacion", "uniqueness"): diff._uniqueness(web, competitors, pack),
        ("coherencia", "messaging_consistency"): coh._messaging_consistency(
            web, exa, research_pack=pack
        ),
        ("coherencia", "tone_consistency"): coh._tone_consistency(
            web, exa, research_pack=pack
        ),
    }

    raw_markdown = web.markdown_content or ""
    prompt = research_pack_prompt_input(pack, feature="positioning_clarity")
    report: dict[str, Any] = {
        "run_id": run_id,
        "brand": snapshot["run"]["brand_name"],
        "url": snapshot["run"]["url"],
        "raw_markdown_chars": len(raw_markdown),
        "pack_prompt_chars": len(prompt),
        "pack_core": {
            "entity_type": pack.entity_type,
            "resolved_entity": getattr(pack.resolved_entity, "resolved_entity", ""),
            "category": pack.category,
            "offer": pack.offer,
            "audience": pack.audience,
            "outcome": pack.outcome,
            "proof_points_count": len(pack.proof_points),
            "noise_rejected_count": len(pack.noise_rejected),
            "evidence_gaps": pack.evidence_gaps[:4],
        },
        "comparisons": {},
        "llm_failures": llm.call_failures,
        "llm_cache": {
            "hits": llm.cache_hits,
            "misses": llm.cache_misses,
            "writes": llm.cache_writes,
        },
    }

    for key, feature_value in after.items():
        dim, feature = key
        before = _stored_feature(snapshot, dim, feature)
        report["comparisons"][f"{dim}.{feature}"] = {
            "before_source": before.get("source"),
            "before_confidence": before.get("confidence"),
            "before_raw": before.get("raw_value"),
            "after_source": feature_value.source,
            "after_confidence": feature_value.confidence,
            "after_value": feature_value.value,
            "after_raw": feature_value.raw_value,
        }

    return report


def _summary(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in reports:
        for feature, comparison in (report.get("comparisons") or {}).items():
            before = comparison.get("before_raw") if isinstance(comparison.get("before_raw"), dict) else {}
            after = comparison.get("after_raw") if isinstance(comparison.get("after_raw"), dict) else {}
            rows.append({
                "run_id": report.get("run_id"),
                "brand": report.get("brand"),
                "feature": feature,
                "before": _verdict(before),
                "after": _verdict(after),
                "before_confidence": comparison.get("before_confidence"),
                "after_confidence": comparison.get("after_confidence"),
                "after_value": comparison.get("after_value"),
                "after_reason": after.get("reason"),
                "proof_points_count": (report.get("pack_core") or {}).get("proof_points_count"),
                "noise_rejected_count": (report.get("pack_core") or {}).get("noise_rejected_count"),
                "evidence_gaps": (report.get("pack_core") or {}).get("evidence_gaps"),
            })
    return rows


def _verdict(raw: dict[str, Any]) -> str:
    return str(raw.get("verdict") or raw.get("gap_signal") or "")


def _raw_source(snapshot: dict[str, Any], source: str) -> dict[str, Any]:
    for item in snapshot.get("raw_inputs") or []:
        if item.get("source") == source:
            payload = item.get("payload")
            return payload if isinstance(payload, dict) else {}
    return {}


def _dataclass_from(cls, payload: dict[str, Any] | None):
    allowed = {field.name for field in fields(cls)}
    return cls(**{k: v for k, v in (payload or {}).items() if k in allowed})


def _web_data(payload: dict[str, Any]) -> WebData:
    return _dataclass_from(WebData, payload)


def _exa_result(payload: dict[str, Any] | None) -> ExaResult:
    return _dataclass_from(ExaResult, payload)


def _exa_data(payload: dict[str, Any]) -> ExaData:
    data = dict(payload or {})
    for key in ("mentions", "competitors", "ai_visibility_results", "news"):
        data[key] = [_exa_result(item) for item in data.get(key) or []]
    return _dataclass_from(ExaData, data)


def _competitor_data(payload: dict[str, Any]) -> CompetitorData:
    data = dict(payload or {})
    data["brand_web"] = _web_data(data.get("brand_web") or {}) if data.get("brand_web") else None
    competitors = []
    for item in data.get("competitors") or []:
        comp = dict(item or {})
        comp["exa_result"] = _exa_result(comp.get("exa_result")) if comp.get("exa_result") else None
        comp["web_data"] = _web_data(comp.get("web_data") or {}) if comp.get("web_data") else None
        competitors.append(_dataclass_from(CompetitorInfo, comp))
    data["competitors"] = competitors
    data["comparisons"] = [
        _dataclass_from(ComparisonResult, item or {})
        for item in data.get("comparisons") or []
    ]
    return _dataclass_from(CompetitorData, data)


def _stored_feature(snapshot: dict[str, Any], dim: str, feature: str) -> dict[str, Any]:
    for item in snapshot.get("features") or []:
        if item.get("dimension_name") == dim and item.get("feature_name") == feature:
            out = dict(item)
            raw = out.get("raw_value")
            if isinstance(raw, str):
                try:
                    out["raw_value"] = ast.literal_eval(raw)
                except (SyntaxError, ValueError):
                    pass
            return out
    return {}


if __name__ == "__main__":
    main()
