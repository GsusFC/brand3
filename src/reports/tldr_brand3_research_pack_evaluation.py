"""Deterministic evaluation for the TLDR Brand3 research-pack benchmark.

The goal of this module is to compare the legacy scanner TLDR and the Analyst
Pass TLDR against the manual gold notes without using an LLM. The scoring is
simple and reproducible:

- evidence_correctness: evidence sufficiency and cleanliness
- block_answer_quality: text similarity to the gold answer
- claim_type_correctness: alignment with the gold claim type
- confidence_reasonableness: confidence level proximity to the gold
- noise_avoidance: whether the block avoids chrome, feed, and other noise
- strategic_usefulness: weighted composite of the above

The output is a JSON structure plus a Markdown report that can be checked into
the benchmark bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
import argparse
import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack" / "dataset.json"
DEFAULT_GOLD_PATH = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack" / "gold.json"
DEFAULT_OUT_DIR = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack"
DEFAULT_JSON_PATH = DEFAULT_OUT_DIR / "evaluation.json"
DEFAULT_MD_PATH = DEFAULT_OUT_DIR / "evaluation.md"
DEFAULT_STRATEGIC_QUALITY_CASES_PATH = DEFAULT_OUT_DIR / "strategic_quality_cases.json"

TLDR_KEYS = [
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "the",
    "their",
    "to",
    "we",
    "with",
    "without",
    "that",
    "this",
    "these",
    "those",
    "they",
    "them",
    "you",
    "your",
    "their",
    "via",
    "into",
    "than",
    "through",
    "over",
    "under",
    "more",
    "most",
    "less",
    "very",
    "not",
    "no",
    "so",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
}

NOISE_TERMS = {
    "article",
    "blog",
    "feed",
    "footer",
    "header",
    "hero",
    "menu",
    "navigation",
    "page chrome",
    "sidebar",
    "chrome",
    "prediction",
    "scrape",
    "scraper",
    "tab",
    "ui chrome",
}

DECLARED_OR_LITERAL_SOURCE_TYPES = {
    "owned_official",
    "owned_product",
    "owned_about",
    "owned_security_trust",
}

CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(slots=True)
class BlockComparison:
    """One block comparison against the gold reference."""

    block: str
    gold_answer: str
    gold_claim_type: str
    gold_confidence: str
    scanner_answer: str | None
    scanner_claim_type: str | None
    scanner_confidence: str | None
    scanner_metrics: dict[str, float | None]
    scanner_taxonomy: list[str] = field(default_factory=list)
    analyst_answer: str | None = None
    analyst_claim_type: str | None = None
    analyst_confidence: str | None = None
    analyst_metrics: dict[str, float | None] = field(default_factory=dict)
    analyst_taxonomy: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaseComparison:
    """Aggregate comparison for one brand case."""

    source_url: str
    slug: str
    source_kind: str
    brand_audit_run_id: int | None
    magnetism_scan_id: int | None
    manual_notes: str
    gold_summary: str
    differences_summary: str
    scanner_available: bool
    benchmark_taxonomy: list[str]
    scanner_average: dict[str, float | None]
    analyst_average: dict[str, float | None]
    delta_average: dict[str, float | None]
    block_comparisons: list[BlockComparison]
    benchmark_taxonomy_counts: dict[str, int]
    scanner_taxonomy_counts: dict[str, int]
    analyst_taxonomy_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "slug": self.slug,
            "source_kind": self.source_kind,
            "brand_audit_run_id": self.brand_audit_run_id,
            "magnetism_scan_id": self.magnetism_scan_id,
            "manual_notes": self.manual_notes,
            "gold_summary": self.gold_summary,
            "differences_summary": self.differences_summary,
            "scanner_available": self.scanner_available,
            "benchmark_taxonomy": self.benchmark_taxonomy,
            "scanner_average": self.scanner_average,
            "analyst_average": self.analyst_average,
            "delta_average": self.delta_average,
            "block_comparisons": [block.to_dict() for block in self.block_comparisons],
            "benchmark_taxonomy_counts": self.benchmark_taxonomy_counts,
            "scanner_taxonomy_counts": self.scanner_taxonomy_counts,
            "analyst_taxonomy_counts": self.analyst_taxonomy_counts,
        }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_text(text: Any | None) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"\s+", " ", text.strip().lower())


def _normalize_tokens(text: str | None) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", _normalize_text(text))
    tokens: list[str] = []
    for token in cleaned.split():
        if token in STOPWORDS:
            continue
        stem = token
        for suffix in ("ing", "edly", "edly", "ed", "es", "s", "ly"):
            if len(stem) > 4 and stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        if stem:
            tokens.append(stem)
    return tokens


def _token_f1(reference: str | None, observed: str | None) -> float:
    ref_tokens = _normalize_tokens(reference)
    obs_tokens = _normalize_tokens(observed)
    if not ref_tokens and not obs_tokens:
        return 100.0
    if not ref_tokens or not obs_tokens:
        return 0.0
    ref_set = set(ref_tokens)
    obs_set = set(obs_tokens)
    overlap = len(ref_set & obs_set)
    precision = overlap / len(obs_set)
    recall = overlap / len(ref_set)
    if precision == 0.0 or recall == 0.0:
        return 0.0
    return 100.0 * (2 * precision * recall / (precision + recall))


def _text_similarity(reference: str | None, observed: str | None) -> float:
    ref = _normalize_text(reference)
    obs = _normalize_text(observed)
    if not ref and not obs:
        return 100.0
    if not ref or not obs:
        return 0.0
    token_score = _token_f1(ref, obs)
    seq_score = SequenceMatcher(None, ref, obs).ratio() * 100.0
    score = (token_score * 0.6) + (seq_score * 0.4)
    return max(0.0, min(100.0, score))


def _score_claim_type(observed: str | None, gold: str | None) -> float:
    observed = observed or "absent"
    gold = gold or "absent"
    if observed == gold:
        return 100.0
    if {observed, gold} <= {"absent", "not_detected"}:
        return 100.0
    if {observed, gold} <= {"declared", "inferred"}:
        return 60.0
    if "needs_human_review" in {observed, gold} and gold != "absent":
        return 40.0
    if observed == "absent" or gold == "absent":
        return 0.0
    if observed == "interpreted" or gold == "interpreted":
        return 50.0
    return 0.0


def _score_confidence(observed: str | None, gold: str | None) -> float:
    observed = (observed or "").strip().lower()
    gold = (gold or "").strip().lower()
    if observed == gold:
        return 100.0
    if not observed or not gold:
        return 0.0
    if observed == "absent" and gold == "absent":
        return 100.0
    if observed not in CONFIDENCE_ORDER or gold not in CONFIDENCE_ORDER:
        return 0.0
    delta = abs(CONFIDENCE_ORDER[observed] - CONFIDENCE_ORDER[gold])
    return max(0.0, 100.0 - (delta * 50.0))


def _has_noise(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(term in normalized for term in NOISE_TERMS)


def _evidence_source_types(block: dict[str, Any]) -> set[str]:
    source_types: set[str] = set()
    for source in block.get("evidence_sources") or []:
        if isinstance(source, dict):
            source_types.add(str(source.get("source_type") or "").strip())
    return {item for item in source_types if item}


def _score_evidence(block: dict[str, Any], gold_claim_type: str) -> float:
    observed_claim_type = str(block.get("claim_type") or "absent")
    if gold_claim_type == "absent":
        return 100.0 if observed_claim_type == "absent" else 0.0
    evidence_used = block.get("evidence_used") or []
    source_types = _evidence_source_types(block)
    score = 100.0 if evidence_used else 0.0
    if source_types & {"noise"}:
        score -= 40.0
    if not block.get("answer"):
        score -= 20.0
    if observed_claim_type == "declared" and not (source_types & DECLARED_OR_LITERAL_SOURCE_TYPES):
        score -= 20.0
    return max(0.0, min(100.0, score))


def _score_noise(block: dict[str, Any], source_type: str) -> float:
    score = 100.0
    answer = block.get("answer")
    evidence_text = " ".join(str(item) for item in (block.get("evidence_used") or []))
    if source_type == "scanner" and _has_noise(answer):
        score -= 50.0
    if source_type == "scanner" and _has_noise(evidence_text):
        score -= 30.0
    if any(src.get("source_type") == "noise" for src in (block.get("evidence_sources") or []) if isinstance(src, dict)):
        score -= 40.0
    if source_type == "analyst" and _has_noise(answer):
        score -= 15.0
    return max(0.0, min(100.0, score))


def _score_strategic_usefulness(
    *,
    answer_quality: float,
    claim_type_correctness: float,
    confidence_reasonableness: float,
    evidence_correctness: float,
    noise_avoidance: float,
) -> float:
    score = (
        answer_quality * 0.30
        + claim_type_correctness * 0.15
        + confidence_reasonableness * 0.15
        + evidence_correctness * 0.20
        + noise_avoidance * 0.20
    )
    return max(0.0, min(100.0, score))


def _audience_terms(text: str | None) -> set[str]:
    tokens = set(_normalize_tokens(text))
    return tokens & {
        "builder",
        "founder",
        "founders",
        "team",
        "teams",
        "marketer",
        "marketers",
        "creator",
        "creators",
        "user",
        "users",
        "operator",
        "operators",
        "investor",
        "investors",
        "developer",
        "developers",
        "company",
    }


def _detect_taxonomy(
    *,
    case: dict[str, Any],
    output_block: dict[str, Any],
    gold_block: dict[str, Any],
    source_type: str,
) -> list[str]:
    tags: set[str] = set()
    answer = str(output_block.get("answer") or "")
    answer_norm = _normalize_text(answer)
    gold_answer = str(gold_block.get("answer") or "")
    gold_answer_norm = _normalize_text(gold_answer)
    claim_type = str(output_block.get("claim_type") or "absent")
    confidence = str(output_block.get("confidence") or "low")
    entity_type = str(case.get("research_pack", {}).get("entity_type") or "")
    parent_brand = str(case.get("research_pack", {}).get("parent_brand") or "")
    source_map = case.get("research_pack", {}).get("source_map") or {}

    if source_type == "scanner" and (
        _has_noise(answer)
        or any(src.get("source_type") == "noise" for src in (output_block.get("evidence_sources") or []) if isinstance(src, dict))
        or any(term in answer_norm for term in ("feed", "article", "navigation", "chrome", "header", "footer", "sidebar"))
    ):
        tags.add("structural_noise_selected")

    if output_block.get("block") == "personality" and any(
        term in answer_norm for term in ("founder", "press", "exit", "investor", "proof")
    ):
        tags.add("proof_point_as_personality")

    if parent_brand and entity_type in {"product", "sub_brand"} and output_block.get("block") in {"core_purpose", "mission", "vision"}:
        if claim_type in {"declared", "high"} or (gold_block.get("claim_type") == "absent" and claim_type != "absent"):
            tags.add("entity_context_missing")

    if output_block.get("block") == "brand_idea":
        quality = _text_similarity(gold_answer, answer)
        if quality < 45.0:
            tags.add("weak_brand_idea")

    if output_block.get("block") == "vision":
        if any(term in answer_norm for term in ("future", "will", "become", "eventually", "next", "predict", "prediction")):
            if claim_type in {"declared", "high"}:
                tags.add("false_vision")

    if output_block.get("block") == "value_proposition":
        gold_audience = _audience_terms(gold_answer)
        observed_audience = _audience_terms(answer)
        if gold_audience and not observed_audience:
            tags.add("missing_audience")

    if claim_type == "declared" and gold_block.get("claim_type") == "inferred":
        tags.add("overclaim")
    elif claim_type == "high" and gold_block.get("confidence") in {"medium", "low"}:
        tags.add("overclaim")
    elif confidence == "high" and gold_block.get("confidence") in {"medium", "low"}:
        tags.add("overclaim")

    if output_block.get("claim_type") == "absent" and gold_block.get("claim_type") != "absent":
        tags.add("weak_brand_idea")

    if source_type == "scanner" and any(
        isinstance(source, dict) and source.get("source_type") == "noise"
        for source in (output_block.get("evidence_sources") or [])
    ):
        tags.add("structural_noise_selected")

    if source_type == "scanner" and output_block.get("block") == "vision" and answer_norm and gold_answer_norm:
        if "prediction" in answer_norm or "feed" in answer_norm:
            tags.add("false_vision")

    if source_type == "scanner" and parent_brand and entity_type in {"product", "sub_brand"} and output_block.get("block") in {"mission", "vision"}:
        if "parent" not in answer_norm and "company" not in answer_norm and "brand" not in answer_norm:
            tags.add("entity_context_missing")

    return sorted(tags)


def _compare_block(
    *,
    case: dict[str, Any],
    block_name: str,
    gold_block: dict[str, Any],
    scanner_block: dict[str, Any] | None,
    analyst_block: dict[str, Any] | None,
) -> BlockComparison:
    scanner_block = scanner_block or {}
    analyst_block = analyst_block or {}
    scanner_answer = scanner_block.get("answer")
    analyst_answer = analyst_block.get("answer")

    scanner_metrics = {
        "evidence_correctness": _score_evidence(scanner_block, str(gold_block.get("claim_type") or "absent")) if scanner_block else None,
        "block_answer_quality": _text_similarity(gold_block.get("answer"), scanner_answer) if scanner_block else None,
        "claim_type_correctness": _score_claim_type(scanner_block.get("claim_type"), gold_block.get("claim_type")) if scanner_block else None,
        "confidence_reasonableness": _score_confidence(scanner_block.get("confidence"), gold_block.get("confidence")) if scanner_block else None,
        "noise_avoidance": _score_noise(scanner_block, "scanner") if scanner_block else None,
        "strategic_usefulness": None,
    }
    if scanner_block:
        scanner_metrics["strategic_usefulness"] = _score_strategic_usefulness(
            answer_quality=float(scanner_metrics["block_answer_quality"] or 0.0),
            claim_type_correctness=float(scanner_metrics["claim_type_correctness"] or 0.0),
            confidence_reasonableness=float(scanner_metrics["confidence_reasonableness"] or 0.0),
            evidence_correctness=float(scanner_metrics["evidence_correctness"] or 0.0),
            noise_avoidance=float(scanner_metrics["noise_avoidance"] or 0.0),
        )

    analyst_metrics = {
        "evidence_correctness": _score_evidence(analyst_block, str(gold_block.get("claim_type") or "absent")) if analyst_block else None,
        "block_answer_quality": _text_similarity(gold_block.get("answer"), analyst_answer) if analyst_block else None,
        "claim_type_correctness": _score_claim_type(analyst_block.get("claim_type"), gold_block.get("claim_type")) if analyst_block else None,
        "confidence_reasonableness": _score_confidence(analyst_block.get("confidence"), gold_block.get("confidence")) if analyst_block else None,
        "noise_avoidance": _score_noise(analyst_block, "analyst") if analyst_block else None,
        "strategic_usefulness": None,
    }
    if analyst_block:
        analyst_metrics["strategic_usefulness"] = _score_strategic_usefulness(
            answer_quality=float(analyst_metrics["block_answer_quality"] or 0.0),
            claim_type_correctness=float(analyst_metrics["claim_type_correctness"] or 0.0),
            confidence_reasonableness=float(analyst_metrics["confidence_reasonableness"] or 0.0),
            evidence_correctness=float(analyst_metrics["evidence_correctness"] or 0.0),
            noise_avoidance=float(analyst_metrics["noise_avoidance"] or 0.0),
        )

    scanner_taxonomy = _detect_taxonomy(
        case=case,
        output_block=scanner_block,
        gold_block=gold_block,
        source_type="scanner",
    ) if scanner_block else []
    analyst_taxonomy = _detect_taxonomy(
        case=case,
        output_block=analyst_block,
        gold_block=gold_block,
        source_type="analyst",
    ) if analyst_block else []

    return BlockComparison(
        block=block_name,
        gold_answer=str(gold_block.get("answer") or ""),
        gold_claim_type=str(gold_block.get("claim_type") or "absent"),
        gold_confidence=str(gold_block.get("confidence") or "low"),
        scanner_answer=str(scanner_answer) if scanner_block else None,
        scanner_claim_type=str(scanner_block.get("claim_type")) if scanner_block else None,
        scanner_confidence=str(scanner_block.get("confidence")) if scanner_block else None,
        scanner_metrics=scanner_metrics,
        scanner_taxonomy=scanner_taxonomy,
        analyst_answer=str(analyst_answer) if analyst_block else None,
        analyst_claim_type=str(analyst_block.get("claim_type")) if analyst_block else None,
        analyst_confidence=str(analyst_block.get("confidence")) if analyst_block else None,
        analyst_metrics=analyst_metrics,
        analyst_taxonomy=analyst_taxonomy,
    )


def _avg_metric(rows: list[dict[str, float | None]], metric: str) -> float | None:
    values = [row[metric] for row in rows if row.get(metric) is not None]
    if not values:
        return None
    return round(mean(float(value) for value in values), 2)


def _delta_metric(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 2)


def _count_taxonomy(blocks: list[BlockComparison], source: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        taxonomies = block.scanner_taxonomy if source == "scanner" else block.analyst_taxonomy
        for tag in taxonomies:
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_evaluation_report(dataset: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    gold_cases = gold.get("cases") or {}
    case_evaluations: list[CaseComparison] = []
    for case in dataset.get("cases") or []:
        source_url = str(case.get("source_url") or "")
        gold_case = gold_cases.get(source_url)
        if not isinstance(gold_case, dict):
            continue
        gold_blocks = gold_case.get("blocks") or {}
        scanner_tldr = (case.get("scanner_current_tldr") or {}).get("tldr_brand3") if case.get("scanner_current_tldr") else None
        analyst_tldr = (case.get("analyst_tldr") or {}).get("tldr_brand3") if case.get("analyst_tldr") else None
        block_comparisons: list[BlockComparison] = []
        for block_name in TLDR_KEYS:
            gold_block = gold_blocks.get(block_name) or {}
            scanner_block = scanner_tldr.get(block_name) if isinstance(scanner_tldr, dict) else None
            analyst_block = analyst_tldr.get(block_name) if isinstance(analyst_tldr, dict) else None
            block_comparisons.append(
                _compare_block(
                    case=case,
                    block_name=block_name,
                    gold_block=gold_block,
                    scanner_block=scanner_block,
                    analyst_block=analyst_block,
                )
            )

        scanner_rows = [block.scanner_metrics for block in block_comparisons if block.scanner_metrics["strategic_usefulness"] is not None]
        analyst_rows = [block.analyst_metrics for block in block_comparisons if block.analyst_metrics["strategic_usefulness"] is not None]
        benchmark_taxonomy = sorted(
            set([str(tag) for tag in ((case.get("differences") or {}).get("error_taxonomy") or [])])
            | set([str(tag) for tag in (gold_case.get("error_taxonomy") or [])])
        )
        scanner_average = {
            metric: _avg_metric(scanner_rows, metric)
            for metric in [
                "evidence_correctness",
                "block_answer_quality",
                "claim_type_correctness",
                "confidence_reasonableness",
                "noise_avoidance",
                "strategic_usefulness",
            ]
        }
        analyst_average = {
            metric: _avg_metric(analyst_rows, metric)
            for metric in [
                "evidence_correctness",
                "block_answer_quality",
                "claim_type_correctness",
                "confidence_reasonableness",
                "noise_avoidance",
                "strategic_usefulness",
            ]
        }
        delta_average = {
            metric: _delta_metric(analyst_average.get(metric), scanner_average.get(metric))
            for metric in analyst_average
        }
        case_evaluations.append(
            CaseComparison(
                source_url=source_url,
                slug=str(case.get("slug") or source_url),
                source_kind=str(case.get("source_kind") or ""),
                brand_audit_run_id=case.get("brand_audit_run_id"),
                magnetism_scan_id=case.get("magnetism_scan_id"),
                manual_notes=str(case.get("manual_notes") or ""),
                gold_summary=str(gold_case.get("summary") or ""),
                differences_summary=str((case.get("differences") or {}).get("summary") or ""),
                scanner_available=bool(case.get("scanner_current_tldr")),
                benchmark_taxonomy=benchmark_taxonomy,
                scanner_average=scanner_average,
                analyst_average=analyst_average,
                delta_average=delta_average,
                block_comparisons=block_comparisons,
                benchmark_taxonomy_counts=_count_tags(benchmark_taxonomy),
                scanner_taxonomy_counts=_count_taxonomy(block_comparisons, "scanner"),
                analyst_taxonomy_counts=_count_taxonomy(block_comparisons, "analyst"),
            )
        )

    block_summaries: list[dict[str, Any]] = []
    for block_name in TLDR_KEYS:
        scanner_rows: list[dict[str, float | None]] = []
        analyst_rows: list[dict[str, float | None]] = []
        for case in case_evaluations:
            block = next(item for item in case.block_comparisons if item.block == block_name)
            if block.scanner_metrics["strategic_usefulness"] is not None:
                scanner_rows.append(block.scanner_metrics)
            if block.analyst_metrics["strategic_usefulness"] is not None:
                analyst_rows.append(block.analyst_metrics)
        scanner_average = {
            metric: _avg_metric(scanner_rows, metric)
            for metric in [
                "evidence_correctness",
                "block_answer_quality",
                "claim_type_correctness",
                "confidence_reasonableness",
                "noise_avoidance",
                "strategic_usefulness",
            ]
        }
        analyst_average = {
            metric: _avg_metric(analyst_rows, metric)
            for metric in [
                "evidence_correctness",
                "block_answer_quality",
                "claim_type_correctness",
                "confidence_reasonableness",
                "noise_avoidance",
                "strategic_usefulness",
            ]
        }
        block_summaries.append(
            {
                "block": block_name,
                "scanner_average": scanner_average,
                "analyst_average": analyst_average,
                "delta_average": {
                    metric: _delta_metric(analyst_average.get(metric), scanner_average.get(metric))
                    for metric in analyst_average
                },
            }
        )

    taxonomy_counts: dict[str, dict[str, int]] = {"scanner": {}, "analyst": {}}
    for source in taxonomy_counts:
        for case in case_evaluations:
            counts = case.scanner_taxonomy_counts if source == "scanner" else case.analyst_taxonomy_counts
            for tag, value in counts.items():
                taxonomy_counts[source][tag] = taxonomy_counts[source].get(tag, 0) + value
        taxonomy_counts[source] = dict(sorted(taxonomy_counts[source].items(), key=lambda item: (-item[1], item[0])))

    benchmark_taxonomy_counts: dict[str, int] = {}
    for case in case_evaluations:
        for tag, value in case.benchmark_taxonomy_counts.items():
            benchmark_taxonomy_counts[tag] = benchmark_taxonomy_counts.get(tag, 0) + value
    benchmark_taxonomy_counts = dict(sorted(benchmark_taxonomy_counts.items(), key=lambda item: (-item[1], item[0])))

    return {
        "version": "tldr_brand3_research_pack_evaluation_v0_1",
        "dataset_version": str(dataset.get("version") or ""),
        "gold_version": str(gold.get("version") or ""),
        "blocks": TLDR_KEYS,
        "case_count": len(case_evaluations),
        "case_evaluations": [case.to_dict() for case in case_evaluations],
        "block_summaries": block_summaries,
        "benchmark_taxonomy_counts": benchmark_taxonomy_counts,
        "taxonomy_counts": taxonomy_counts,
        "recommendations": _build_recommendations(taxonomy_counts, block_summaries),
    }


def _count_tags(tags: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tag in tags:
        counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _build_recommendations(
    taxonomy_counts: dict[str, dict[str, int]],
    block_summaries: list[dict[str, Any]],
) -> list[str]:
    recs: list[str] = []
    analyst_taxonomy = taxonomy_counts.get("analyst") or {}
    scanner_taxonomy = taxonomy_counts.get("scanner") or {}
    if scanner_taxonomy.get("structural_noise_selected", 0) > analyst_taxonomy.get("structural_noise_selected", 0):
        recs.append("Tighten noise rejection before block interpretation; chrome, feed, and article fragments still leak into the legacy scanner.")
    if analyst_taxonomy.get("entity_context_missing", 0) > 0:
        recs.append("Expand parent-brand resolution before interpreting mission and vision on subdomains or product surfaces.")
    if analyst_taxonomy.get("overclaim", 0) > 0:
        recs.append("Degrade confidence more aggressively when outputs move from inferred evidence to declared language without owned support.")
    if analyst_taxonomy.get("weak_brand_idea", 0) > 0:
        recs.append("Strengthen the brand-idea synthesis rule so weak conceptual glue is marked reviewable instead of promoted as strategic fact.")
    if analyst_taxonomy.get("missing_audience", 0) > 0:
        recs.append("Require the value proposition block to preserve the audience when the manual gold notes make it explicit.")
    if not recs:
        recs.append("The Analyst Pass is broadly stable on this benchmark; next work should focus on residual case-specific misreads.")
    # Use block summaries to add one targeted note when the analyst underperforms on a block.
    worst_block = None
    worst_delta = math.inf
    for block_summary in block_summaries:
        delta = block_summary["delta_average"].get("strategic_usefulness")
        if delta is not None and delta < worst_delta:
            worst_delta = delta
            worst_block = block_summary["block"]
    if worst_block and worst_delta < 0:
        recs.append(f"Revisit the {worst_block} prompt and normalization path; it is the clearest negative delta in the current comparison.")
    return recs


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}"


def _truncate(text: str | None, limit: int = 88) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return "—"
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    def fmt_row(row: list[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)) + " |"
    lines = [fmt_row(headers), "| " + " | ".join("-" * width for width in widths) + " |"]
    lines.extend(fmt_row(row) for row in rows)
    return "\n".join(lines)


def build_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# TLDR Brand3 Research Pack evaluation",
        "",
        f"- Dataset version: `{report['dataset_version']}`",
        f"- Gold version: `{report['gold_version']}`",
        f"- Cases evaluated: `{report['case_count']}`",
        "",
        "## Summary",
    ]

    scanner_strategy = _avg_metric([case["scanner_average"] for case in report["case_evaluations"] if case["scanner_available"]], "strategic_usefulness")
    analyst_strategy = _avg_metric([case["analyst_average"] for case in report["case_evaluations"]], "strategic_usefulness")
    delta_strategy = _delta_metric(analyst_strategy, scanner_strategy)
    lines.extend(
        [
            f"- Legacy scanner strategic usefulness: `{_fmt_num(scanner_strategy)}`",
            f"- Analyst Pass strategic usefulness: `{_fmt_num(analyst_strategy)}`",
            f"- Delta: `{_fmt_delta(delta_strategy)}`",
            "",
        ]
    )

    top_block_gains = sorted(
        (
            (summary["block"], summary["delta_average"]["strategic_usefulness"])
            for summary in report["block_summaries"]
            if summary["delta_average"]["strategic_usefulness"] is not None
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if top_block_gains:
        lines.append("### Biggest block gains")
        for block, delta in top_block_gains[:3]:
            lines.append(f"- `{block}`: `{_fmt_delta(delta)}`")
        lines.append("")

    worsening_cases = [
        case for case in report["case_evaluations"]
        if case["scanner_available"]
        and case["delta_average"]["strategic_usefulness"] is not None
        and case["delta_average"]["strategic_usefulness"] < 0
    ]
    lines.append("### Cases where the Analyst Pass worsens")
    if worsening_cases:
        for case in worsening_cases:
            lines.append(
                f"- `{case['source_url']}`: `{_fmt_delta(case['delta_average']['strategic_usefulness'])}`"
            )
    else:
        lines.append("- None in this benchmark set.")
    lines.append("")

    lines.append("### Next adjustments")
    for item in report["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")

    case_rows = []
    for case in report["case_evaluations"]:
        case_rows.append(
            [
                case["source_url"].replace("https://", ""),
                _fmt_num(case["scanner_average"]["strategic_usefulness"]) if case["scanner_available"] else "n/a",
                _fmt_num(case["analyst_average"]["strategic_usefulness"]),
                _fmt_delta(case["delta_average"]["strategic_usefulness"]) if case["scanner_available"] else "n/a",
                ", ".join(case["benchmark_taxonomy"][:3]) or "—",
                ", ".join(sorted(case["scanner_taxonomy_counts"].keys())[:3]) or "—",
                ", ".join(sorted(case["analyst_taxonomy_counts"].keys())[:3]) or "—",
            ]
        )
    lines.extend([
        "## Case summary",
        "",
        _render_table(
            ["case", "scanner", "analyst", "delta", "benchmark taxonomy", "scanner taxonomy", "analyst taxonomy"],
            case_rows,
        ),
        "",
    ])

    block_rows = []
    for summary in report["block_summaries"]:
        block_rows.append(
            [
                summary["block"],
                _fmt_num(summary["scanner_average"]["strategic_usefulness"]),
                _fmt_num(summary["analyst_average"]["strategic_usefulness"]),
                _fmt_delta(summary["delta_average"]["strategic_usefulness"]),
                _fmt_delta(summary["delta_average"]["noise_avoidance"]),
            ]
        )
    lines.extend([
        "## Block summary",
        "",
        _render_table(
            ["block", "scanner", "analyst", "delta", "noise delta"],
            block_rows,
        ),
        "",
    ])

    lines.append("## Detailed case tables")
    lines.append("")
    for case in report["case_evaluations"]:
        lines.append(f"### `{case['source_url']}`")
        lines.append("")
        lines.append(f"{case['manual_notes']}")
        lines.append("")
        lines.append(f"Gold summary: {case['gold_summary']}")
        if case["differences_summary"]:
            lines.append(f"Dataset difference note: {case['differences_summary']}")
        lines.append("")
        rows = []
        for block in case["block_comparisons"]:
            rows.append(
                [
                    block["block"],
                    _truncate(block["gold_answer"], 58),
                    _truncate(block["scanner_answer"], 58),
                    _truncate(block["analyst_answer"], 58),
                    _fmt_num(block["scanner_metrics"]["strategic_usefulness"]) if block["scanner_metrics"]["strategic_usefulness"] is not None else "n/a",
                    _fmt_num(block["analyst_metrics"]["strategic_usefulness"]) if block["analyst_metrics"]["strategic_usefulness"] is not None else "n/a",
                    _fmt_delta(
                        (
                            block["analyst_metrics"]["strategic_usefulness"] - block["scanner_metrics"]["strategic_usefulness"]
                        )
                        if block["scanner_metrics"]["strategic_usefulness"] is not None and block["analyst_metrics"]["strategic_usefulness"] is not None
                        else None
                    ),
                    ", ".join(block["scanner_taxonomy"]) or "—",
                    ", ".join(block["analyst_taxonomy"]) or "—",
                ]
            )
        lines.append(
            _render_table(
                ["block", "gold", "scanner", "analyst", "scanner score", "analyst score", "delta", "scanner tags", "analyst tags"],
                rows,
            )
        )
        lines.append("")
    lines.append("## Taxonomy counts")
    lines.append("")
    taxonomy_rows = []
    all_taxa = sorted(
        set(report["benchmark_taxonomy_counts"].keys())
        | set(report["taxonomy_counts"]["scanner"].keys())
        | set(report["taxonomy_counts"]["analyst"].keys())
    )
    for tag in all_taxa:
        taxonomy_rows.append(
            [
                tag,
                str(report["benchmark_taxonomy_counts"].get(tag, 0)),
                str(report["taxonomy_counts"]["scanner"].get(tag, 0)),
                str(report["taxonomy_counts"]["analyst"].get(tag, 0)),
            ]
        )
    if taxonomy_rows:
        lines.append(_render_table(["taxonomy", "benchmark", "scanner", "analyst"], taxonomy_rows))
    else:
        lines.append("No taxonomy tags were detected.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_evaluation_artifacts(report: dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "evaluation.json"
    md_path = out_dir / "evaluation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    gold_path: Path = DEFAULT_GOLD_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> dict[str, Any]:
    dataset = _load_json(dataset_path)
    gold = _load_json(gold_path)
    report = build_evaluation_report(dataset, gold)
    write_evaluation_artifacts(report, out_dir=out_dir)
    return report


def build_strategic_quality_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate Analyst Pass TLDR output against explicit strategic expectations."""

    case_reports = [_evaluate_strategic_quality_case(case) for case in cases]
    dimension_scores: dict[str, float] = {}
    dimensions = ["offer", "audience", "differentiation", "personality", "vision", "frictions", "evidence_traceability", "entity_separation"]
    for dimension in dimensions:
        scores = [
            row["score"]
            for case in case_reports
            for row in case["dimension_results"]
            if row["dimension"] == dimension
        ]
        dimension_scores[dimension] = round(mean(scores), 2) if scores else 100.0

    taxonomy_counts: dict[str, int] = {}
    for case in case_reports:
        for failure in case["failures"]:
            tag = failure.split(":", 1)[0]
            taxonomy_counts[tag] = taxonomy_counts.get(tag, 0) + 1
    taxonomy_counts = dict(sorted(taxonomy_counts.items(), key=lambda item: (-item[1], item[0])))

    return {
        "version": "tldr_brand3_strategic_quality_v0_1",
        "case_count": len(case_reports),
        "case_evaluations": case_reports,
        "dimension_scores": dict(sorted(dimension_scores.items())),
        "taxonomy_counts": taxonomy_counts,
        "total_score": round(mean(dimension_scores.values()), 2) if dimension_scores else 0.0,
        "recommendations": _strategic_quality_recommendations(taxonomy_counts),
    }


def build_strategic_quality_cases_from_benchmark(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    """Build strategic-quality cases from the existing TLDR benchmark dataset."""

    strategic_case_urls = {
        "https://base44.com",
        "https://creatify.ai/es/",
        "https://lab.naturaumana.ai",
    }
    cases: list[dict[str, Any]] = []
    for case in dataset.get("cases") or []:
        if not isinstance(case, dict):
            continue
        source_url = str(case.get("source_url") or "")
        if source_url not in strategic_case_urls:
            continue
        analyst_tldr = case.get("analyst_tldr") if isinstance(case.get("analyst_tldr"), dict) else {}
        tldr = analyst_tldr.get("tldr_brand3") if isinstance(analyst_tldr.get("tldr_brand3"), dict) else {}
        value_answer = str((tldr.get("value_proposition") or {}).get("answer") or "")
        idea_answer = str((tldr.get("brand_idea") or {}).get("answer") or "")
        cases.append(
            {
                "slug": str(case.get("slug") or source_url),
                "source_url": source_url,
                "archetype": str(case.get("source_kind") or "benchmark"),
                "research_pack": case.get("research_pack") or {},
                "analyst_tldr": analyst_tldr,
                "strategic_expectations": {
                    "offer": {"must_include_any": [[_first_significant_token(value_answer)]]},
                    "audience": {"must_include_any": [["teams", "users", "founders", "creators", "customers", "brands", "people"]]},
                    "differentiation": {"must_include_any": [[_first_significant_token(idea_answer)]]},
                    "frictions": {"must_acknowledge": ["thin", "absent", "missing", "unclear"], "require_counter_evidence": False},
                    "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                    "entity_separation": {"forbid_press_as_declared_mission": True},
                },
            }
        )
    return cases


def build_strategic_quality_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# TLDR Brand3 strategic quality evaluation",
        "",
        f"- Cases evaluated: `{report['case_count']}`",
        f"- Total score: `{_fmt_num(float(report['total_score']))}`",
        "",
        "## Dimension Scores",
        "",
    ]
    rows = [
        [dimension, _fmt_num(float(score))]
        for dimension, score in sorted((report.get("dimension_scores") or {}).items())
    ]
    lines.append(_render_table(["dimension", "score"], rows))
    lines.extend(["", "## Taxonomy Counts", ""])
    taxonomy_rows = [[tag, str(count)] for tag, count in (report.get("taxonomy_counts") or {}).items()]
    lines.append(_render_table(["taxonomy", "count"], taxonomy_rows) if taxonomy_rows else "No taxonomy failures.")
    lines.extend(["", "## Recommendations", ""])
    for item in report.get("recommendations") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Cases", ""])
    for case in report.get("case_evaluations") or []:
        lines.append(f"- `{case['slug']}`: `{_fmt_num(float(case['total_score']))}`; failures={len(case['failures'])}")
    return "\n".join(lines).rstrip() + "\n"


def run_strategic_quality_evaluation(
    *,
    cases_path: Path = DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
    from_benchmark: bool = False,
    dataset_path: Path = DEFAULT_DATASET_PATH,
) -> dict[str, Any]:
    if from_benchmark:
        cases = build_strategic_quality_cases_from_benchmark(_load_json(dataset_path))
    else:
        payload = _load_json(cases_path)
        cases = payload.get("cases") if isinstance(payload.get("cases"), list) else []
    report = build_strategic_quality_report(cases)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "strategic_quality.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "strategic_quality.md").write_text(build_strategic_quality_markdown_report(report), encoding="utf-8")
    return report


def evaluate_strategic_quality_gate(
    report: dict[str, Any],
    *,
    min_total: float = 85.0,
    min_dimension: float = 80.0,
) -> dict[str, Any]:
    failures: list[str] = []
    total = float(report.get("total_score") or 0.0)
    if total < min_total:
        failures.append(f"total_score {total:.1f} below {min_total:.1f}")
    for dimension, score_value in (report.get("dimension_scores") or {}).items():
        score = float(score_value or 0.0)
        if score <= min_dimension:
            failures.append(f"dimension {dimension} score {score:.1f} not above {min_dimension:.1f}")
    critical_taxonomy = {"founder_press_as_declared_mission", "forbidden_source_type"}
    for tag in critical_taxonomy:
        if int((report.get("taxonomy_counts") or {}).get(tag) or 0) > 0:
            failures.append(f"critical taxonomy {tag} present")
    return {"passed": not failures, "failures": failures}


def _evaluate_strategic_quality_case(case: dict[str, Any]) -> dict[str, Any]:
    expectations = case.get("strategic_expectations") if isinstance(case.get("strategic_expectations"), dict) else {}
    tldr = ((case.get("analyst_tldr") or {}).get("tldr_brand3") or {}) if isinstance(case.get("analyst_tldr"), dict) else {}
    dimension_results = [
        _dimension_result("offer", _check_text_expectation("offer", _block_answer(tldr, "value_proposition"), expectations.get("offer") or {})),
        _dimension_result("audience", _check_text_expectation("audience", _block_answer(tldr, "value_proposition"), expectations.get("audience") or {})),
        _dimension_result("differentiation", _check_text_expectation("differentiation", _block_answer(tldr, "brand_idea"), expectations.get("differentiation") or {})),
        _dimension_result("personality", _check_text_expectation("personality", _block_answer(tldr, "personality"), expectations.get("personality") or {})),
        _dimension_result("vision", _check_text_expectation("vision", _block_answer(tldr, "vision"), expectations.get("vision") or {})),
        _dimension_result("frictions", _check_frictions(tldr, expectations.get("frictions") or {})),
        _dimension_result("evidence_traceability", _check_traceability(tldr, expectations.get("evidence_traceability") or {})),
        _dimension_result("entity_separation", _check_entity_separation(tldr, expectations.get("entity_separation") or {})),
    ]
    failures = [failure for item in dimension_results for failure in item["failures"]]
    return {
        "slug": str(case.get("slug") or case.get("source_url") or ""),
        "source_url": str(case.get("source_url") or ""),
        "archetype": str(case.get("archetype") or ""),
        "dimension_results": dimension_results,
        "failures": failures,
        "total_score": round(mean([item["score"] for item in dimension_results]), 2),
        "recommendations": ["Review fixture expectations and TLDR block evidence for strategic mismatch."] if failures else [],
    }


def _dimension_result(dimension: str, failures: list[str]) -> dict[str, Any]:
    score = max(0.0, 100.0 - (35.0 * len(failures)))
    return {"dimension": dimension, "score": score, "passed": not failures, "failures": failures}


def _check_text_expectation(dimension: str, answer: str, expectation: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not expectation:
        return failures
    low = _normalize_text(answer)
    for term in _str_list(expectation.get("must_include")):
        if _normalize_text(term) not in low:
            failures.append(f"{dimension}_missing_required_term: expected '{term}'")
    for group in _list(expectation.get("must_include_any")):
        terms = [str(term) for term in _list(group) if str(term)]
        if terms and not any(_normalize_text(term) in low for term in terms):
            failures.append(f"{dimension}_missing_required_concept: expected one of {terms}")
    for term in _str_list(expectation.get("must_not_include")):
        if _normalize_text(term) in low:
            failures.append(f"{dimension}_contains_forbidden_term: found '{term}'")
    return failures


def _check_frictions(tldr: dict[str, Any], expectation: dict[str, Any]) -> list[str]:
    failures = _check_text_expectation("frictions", _all_block_text(tldr), {"must_include_any": [expectation.get("must_acknowledge") or []]})
    if expectation.get("require_counter_evidence"):
        if not any((block or {}).get("counter_evidence") for block in tldr.values() if isinstance(block, dict)):
            failures.append("frictions_missing_counter_evidence")
    return failures


def _check_traceability(tldr: dict[str, Any], expectation: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    forbidden = set(_str_list(expectation.get("forbid_source_types")))
    require_sources = bool(expectation.get("require_traceable_sources"))
    for block_name, block in tldr.items():
        if not isinstance(block, dict):
            continue
        sources = [source for source in _list(block.get("evidence_sources")) if isinstance(source, dict)]
        if require_sources and block.get("answer") and not sources:
            failures.append(f"missing_traceable_source: {block_name}")
        for source in sources:
            source_type = str(source.get("source_type") or "")
            if source_type in forbidden:
                failures.append(f"forbidden_source_type: {source_type}")
    return failures


def _check_entity_separation(tldr: dict[str, Any], expectation: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    value_answer = _block_answer(tldr, "value_proposition")
    for term in _str_list(expectation.get("company_offer_must_not_include")):
        if _normalize_text(term) in _normalize_text(value_answer):
            failures.append(f"product_offer_used_as_company_offer: found '{term}'")
    if expectation.get("forbid_press_as_declared_mission"):
        mission = tldr.get("mission") if isinstance(tldr.get("mission"), dict) else {}
        source_types = {str(source.get("source_type") or "") for source in _list(mission.get("evidence_sources")) if isinstance(source, dict)}
        if mission.get("claim_type") == "declared" and "press_or_founder" in source_types:
            failures.append("founder_press_as_declared_mission")
    if expectation.get("require_parent_context"):
        combined = _normalize_text(_block_answer(tldr, "value_proposition") + " " + _block_answer(tldr, "brand_idea"))
        if "parent" not in combined and "backed" not in combined:
            failures.append("missing_parent_context")
    return failures


def _strategic_quality_recommendations(taxonomy_counts: dict[str, int]) -> list[str]:
    recs: list[str] = []
    if any(tag.startswith("offer_") for tag in taxonomy_counts):
        recs.append("Separate the core offer from proof metrics and preserve the expected offer category.")
    if any(tag.startswith("differentiation_") for tag in taxonomy_counts):
        recs.append("Strengthen brand_idea checks so weak metaphors or generic product mechanics do not pass as differentiation.")
    if "founder_press_as_declared_mission" in taxonomy_counts:
        recs.append("Keep founder, funding, and press context out of declared mission unless owned evidence supports it.")
    if any(tag.startswith("vision_") for tag in taxonomy_counts):
        recs.append("Downgrade vision when future language is over-broad or not directly supported by owned evidence.")
    return recs or ["Strategic quality checks passed for the current fixture set."]


def _block_answer(tldr: dict[str, Any], block: str) -> str:
    payload = tldr.get(block) if isinstance(tldr.get(block), dict) else {}
    return str(payload.get("answer") or "")


def _all_block_text(tldr: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in tldr.values():
        if isinstance(block, dict):
            parts.append(str(block.get("answer") or ""))
            parts.extend(str(item) for item in _list(block.get("counter_evidence")))
    return " ".join(parts)


def _first_significant_token(text: str) -> str:
    for token in _normalize_tokens(text):
        if len(token) > 3:
            return token
    return ""


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the TLDR Brand3 research-pack benchmark.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Path to the dataset JSON.")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD_PATH), help="Path to the gold JSON.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for evaluation artifacts.")
    parser.add_argument("--strategic-quality", action="store_true", help="Run the strategic quality fixture evaluator.")
    parser.add_argument("--strategic-quality-from-benchmark", action="store_true", help="Derive strategic quality cases from benchmark outputs.")
    parser.add_argument("--strategic-quality-gate", action="store_true", help="Fail with code 2 when the strategic quality gate fails.")
    parser.add_argument("--strategic-quality-min-total", type=float, default=85.0)
    parser.add_argument("--strategic-quality-min-dimension", type=float, default=80.0)
    args = parser.parse_args(argv)
    if args.strategic_quality:
        report = run_strategic_quality_evaluation(
            out_dir=Path(args.out_dir),
            from_benchmark=args.strategic_quality_from_benchmark,
            dataset_path=Path(args.dataset),
        )
        gate = evaluate_strategic_quality_gate(
            report,
            min_total=args.strategic_quality_min_total,
            min_dimension=args.strategic_quality_min_dimension,
        )
        print(f"Strategic quality evaluated {report['case_count']} cases.")
        print(f"JSON: {(Path(args.out_dir) / 'strategic_quality.json').resolve()}")
        print(f"Markdown: {(Path(args.out_dir) / 'strategic_quality.md').resolve()}")
        if args.strategic_quality_gate and not gate["passed"]:
            print("Strategic quality gate failed:")
            for failure in gate["failures"]:
                print(f"- {failure}")
            return 2
        return 0
    report = run_evaluation(
        dataset_path=Path(args.dataset),
        gold_path=Path(args.gold),
        out_dir=Path(args.out_dir),
    )
    print(f"Evaluated {report['case_count']} cases.")
    print(f"JSON: {(Path(args.out_dir) / 'evaluation.json').resolve()}")
    print(f"Markdown: {(Path(args.out_dir) / 'evaluation.md').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
