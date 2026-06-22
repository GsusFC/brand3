"""Shared helpers for TLDR Brand3 strategic quality evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

import json
import re


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack" / "dataset.json"
DEFAULT_GOLD_PATH = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack" / "gold.json"
DEFAULT_OUT_DIR = ROOT / "examples" / "benchmarks" / "tldr_brand3_research_pack"
DEFAULT_STRATEGIC_QUALITY_CASES_PATH = DEFAULT_OUT_DIR / "strategic_quality_cases.json"

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


@dataclass(slots=True)
class BlockComparison:
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    worst_block = None
    worst_delta = float("inf")
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


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
