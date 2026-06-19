#!/usr/bin/env python3
"""Find sourced replacements for provenance repair records.

This consumes ``repair_board.json`` and targets records whose repair packet
contains source backfill queries. In dry-run mode it only inventories work. In
execute mode it searches Exa and writes candidate source suggestions. It does
not mutate Brand3 data or complete decisions.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from src.collectors.exa_collector import ExaCollector, ExaResult
from src.config import EXA_API_KEY


SearchFn = Callable[[str, dict[str, Any]], list[Any]]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    board = json.loads(Path(args.repair_board).read_text(encoding="utf-8"))
    searcher: SearchFn | None = None
    if args.execute:
        collector = ExaCollector(api_key=EXA_API_KEY)
        searcher = lambda query, context: collector.search(
            query,
            num_results=args.results,
            intent="enrichment",
            brand_name=str(context.get("brand_name") or ""),
            brand_url=None,
        )

    payload = build_source_backfill(
        board,
        execute=bool(args.execute),
        searcher=searcher,
        max_results=args.results,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "source_backfill.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "source_backfill.md").write_text(render_source_backfill_markdown(payload), encoding="utf-8")
    print(
        "source_backfill records={records} queries={queries} candidates={candidates} execute={execute}".format(
            records=payload["summary"]["record_count"],
            queries=payload["summary"]["query_count"],
            candidates=payload["summary"]["candidate_count"],
            execute=str(bool(args.execute)).lower(),
        )
    )
    return 0


def build_source_backfill(
    repair_board: dict[str, Any],
    *,
    execute: bool = False,
    searcher: SearchFn | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    records = _source_backfill_records(repair_board)
    rows: list[dict[str, Any]] = []
    for record in records:
        query_rows: list[dict[str, Any]] = []
        for query in record["queries"]:
            results = searcher(query, record)[:max_results] if execute and searcher else []
            candidates = [_candidate(row, query=query, record=record) for row in results]
            query_rows.append(
                {
                    "query": query,
                    "status": "searched" if execute else "planned",
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                }
            )
        rows.append(
            {
                "record_id": record["record_id"],
                "run_id": record.get("run_id"),
                "brand_name": record.get("brand_name") or "",
                "recommended_decision": record.get("recommended_decision") or "",
                "quote_text": record.get("quote_text") or "",
                "queries": query_rows,
                "best_candidate": _best_candidate(query_rows),
            }
        )
        rows[-1]["suggested_record_patch"] = _suggested_record_patch(record, rows[-1]["best_candidate"])
    return {
        "version": "evidence_source_backfill_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "execute": bool(execute),
        "rows": rows,
        "summary": _summary(rows),
    }


def render_source_backfill_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Evidence Source Backfill",
        "",
        f"- Runtime effect: `{str(bool(payload.get('runtime_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(payload.get('persistence_effect'))).lower()}`",
        f"- Execute: `{str(bool(payload.get('execute'))).lower()}`",
        "",
        "## Summary",
        "",
    ]
    for key in ("record_count", "query_count", "candidate_count", "suggested_patch_count", "decision_counts", "best_action_counts"):
        lines.append(f"- `{key}`: `{summary.get(key)}`")
    lines.extend(["", "## Rows", ""])
    lines.append("| Run | Brand | Record | Best action | Best URL | Patch | Score |")
    lines.append("| --- | --- | --- | --- | --- | --- | ---: |")
    for row in payload.get("rows") or []:
        best = row.get("best_candidate") if isinstance(row.get("best_candidate"), dict) else {}
        lines.append(
            "| {run_id} | {brand} | {record_id} | {action} | {url} | {patch} | {score} |".format(
                run_id=row.get("run_id") or "",
                brand=_md_cell(row.get("brand_name") or ""),
                record_id=_md_cell(row.get("record_id") or ""),
                action=_md_cell(best.get("suggested_decision") or ""),
                url=_md_cell(best.get("url") or ""),
                patch=str(bool(row.get("suggested_record_patch"))).lower(),
                score=best.get("claim_overlap_score") or 0,
            )
        )
    lines.append("")
    return "\n".join(lines)


def _source_backfill_records(repair_board: dict[str, Any]) -> list[dict[str, Any]]:
    cards = repair_board.get("cards") if isinstance(repair_board.get("cards"), list) else []
    out: list[dict[str, Any]] = []
    for card in cards:
        queries = [str(item) for item in card.get("source_backfill_queries") or [] if str(item).strip()]
        if not queries:
            continue
        record = card.get("record") if isinstance(card.get("record"), dict) else {}
        out.append(
            {
                "record_id": str(card.get("record_id") or ""),
                "run_id": card.get("run_id"),
                "brand_name": str(card.get("brand_name") or ""),
                "recommended_decision": str(card.get("recommended_decision") or ""),
                "quote_text": str(record.get("quote_text") or ""),
                "queries": queries,
            }
        )
    return out


def _candidate(result: Any, *, query: str, record: dict[str, Any]) -> dict[str, Any]:
    url = str(getattr(result, "url", "") or _get(result, "url") or "")
    title = str(getattr(result, "title", "") or _get(result, "title") or "")
    text = _result_text(result)
    quote = _quoted_query_text(query) or str(record.get("quote_text") or "")
    overlap = _claim_overlap_score(quote, f"{title} {text}")
    exact = bool(quote and _normalize_text(quote) in _normalize_text(f"{title} {text}"))
    source_class = str(getattr(result, "source_class", "") or _get(result, "source_class") or "")
    requires_review = bool(getattr(result, "requires_human_review", False) or _get(result, "requires_human_review"))
    suggested_decision = _suggested_decision(
        exact=exact,
        overlap=overlap,
        source_class=source_class,
        requires_review=requires_review,
    )
    return {
        "url": url,
        "title": title,
        "text_preview": _truncate(text, 500),
        "published_date": str(getattr(result, "published_date", "") or _get(result, "published_date") or ""),
        "source_class": source_class,
        "requires_human_review": requires_review,
        "claim_overlap_score": overlap,
        "exact_quote_match": exact,
        "suggested_decision": suggested_decision,
    }


def _best_candidate(query_rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        candidate
        for row in query_rows
        for candidate in row.get("candidates") or []
        if isinstance(candidate, dict)
    ]
    if not candidates:
        return {}
    return sorted(
        candidates,
        key=lambda item: (
            1 if item.get("suggested_decision") in {"source_url_attached", "replace_with_sourced_equivalent"} else 0,
            1 if item.get("exact_quote_match") else 0,
            float(item.get("claim_overlap_score") or 0.0),
        ),
        reverse=True,
    )[0]


def _suggested_record_patch(record: dict[str, Any], best_candidate: dict[str, Any]) -> dict[str, Any]:
    decision = str(best_candidate.get("suggested_decision") or "")
    if decision not in {"source_url_attached", "replace_with_sourced_equivalent"}:
        return {}
    patch = {
        "record_id": record.get("record_id") or "",
        "run_id": record.get("run_id"),
        "decision": decision,
        "source_url": best_candidate.get("url") or "",
        "rationale": _patch_rationale(decision, best_candidate),
    }
    if decision == "replace_with_sourced_equivalent":
        patch["replacement_quote"] = _replacement_quote(best_candidate, str(record.get("quote_text") or ""))
    return patch


def _patch_rationale(decision: str, candidate: dict[str, Any]) -> str:
    score = candidate.get("claim_overlap_score") or 0
    if decision == "source_url_attached":
        return f"Exact quote match found in source candidate with overlap score {score}."
    return f"No exact quote match found; candidate supports an equivalent sourced claim with overlap score {score}."


def _replacement_quote(candidate: dict[str, Any], original_quote: str) -> str:
    text = str(candidate.get("text_preview") or "")
    if not text:
        return str(candidate.get("title") or "")
    chunks = _candidate_quote_chunks(text, title=str(candidate.get("title") or ""))
    if not chunks:
        return _truncate(text, 300)
    best = sorted(
        chunks,
        key=lambda item: (
            _claim_overlap_score(original_quote, item),
            min(len(item), 260),
        ),
        reverse=True,
    )[0]
    return _truncate(best, 300)


def _candidate_quote_chunks(text: str, *, title: str = "") -> list[str]:
    cleaned = " ".join(str(text or "").split())
    title_clean = " ".join(str(title or "").split())
    raw_chunks = re.split(r"(?<=[.!?])\s+|\s+#\s+|\s+\|\s+", cleaned)
    chunks: list[str] = []
    for chunk in raw_chunks:
        chunk = chunk.strip(" -•●")
        if not chunk or len(chunk) < 60:
            continue
        if title_clean and _normalize_text(chunk) == _normalize_text(title_clean):
            continue
        if title_clean and _normalize_text(chunk).startswith(_normalize_text(title_clean)):
            chunk = chunk[len(title_clean) :].strip(" -:|#•●")
        if len(chunk) >= 60:
            chunks.append(chunk)
    if chunks:
        return chunks
    return [cleaned] if cleaned else []


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts: Counter[str] = Counter()
    best_action_counts: Counter[str] = Counter()
    query_count = 0
    candidate_count = 0
    suggested_patch_count = 0
    for row in rows:
        decision_counts.update([str(row.get("recommended_decision") or "")])
        for query in row.get("queries") or []:
            query_count += 1
            candidate_count += int(query.get("candidate_count") or 0)
        best = row.get("best_candidate") if isinstance(row.get("best_candidate"), dict) else {}
        if best.get("suggested_decision"):
            best_action_counts.update([str(best["suggested_decision"])])
        if row.get("suggested_record_patch"):
            suggested_patch_count += 1
    return {
        "record_count": len(rows),
        "query_count": query_count,
        "candidate_count": candidate_count,
        "suggested_patch_count": suggested_patch_count,
        "decision_counts": _count_dict(decision_counts),
        "best_action_counts": _count_dict(best_action_counts),
    }


def _suggested_decision(*, exact: bool, overlap: float, source_class: str, requires_review: bool) -> str:
    if requires_review or source_class in {"related_unresolved", "noise", "technical_internal"}:
        return "keep_unsourced_or_review"
    if exact:
        return "source_url_attached"
    if overlap >= 0.28:
        return "replace_with_sourced_equivalent"
    return "keep_searching"


def _claim_overlap_score(claim: str, candidate_text: str) -> float:
    claim_tokens = _tokens(claim)
    if not claim_tokens:
        return 0.0
    candidate_tokens = _tokens(candidate_text)
    if not candidate_tokens:
        return 0.0
    overlap = len(claim_tokens & candidate_tokens)
    return round(overlap / len(claim_tokens), 4)


def _tokens(text: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "are",
        "was",
        "were",
        "into",
        "onto",
        "its",
        "their",
        "your",
        "you",
        "but",
        "not",
        "existing",
    }
    return {
        item
        for item in re.findall(r"[a-z0-9]{3,}", _normalize_text(text))
        if item not in stopwords
    }


def _quoted_query_text(query: str) -> str:
    match = re.search(r'"([^"]+)"', query or "")
    return match.group(1) if match else ""


def _result_text(result: Any) -> str:
    text = str(getattr(result, "text", "") or _get(result, "text") or "")
    summary = str(getattr(result, "summary", "") or _get(result, "summary") or "")
    highlights = getattr(result, "highlights", None)
    if highlights is None:
        highlights = _get(result, "highlights") or []
    if isinstance(highlights, list):
        highlight_text = " ".join(str(item) for item in highlights)
    else:
        highlight_text = ""
    return " ".join(part for part in (text, summary, highlight_text) if part)


def _get(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return None


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def _count_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])) if key}


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-board", type=Path, required=True, help="Path to repair_board.json.")
    parser.add_argument("--output-dir", type=Path, default=Path("out/evidence_vnext/source_backfill"))
    parser.add_argument("--execute", action="store_true", help="Call Exa. Omit for dry-run inventory.")
    parser.add_argument("--results", type=int, default=5, help="Results per query.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
