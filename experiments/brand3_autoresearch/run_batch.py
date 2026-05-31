"""Run a batch of Brand3 AutoResearch comparisons and persist history."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.brand3_autoresearch.run_benchmark import candidate_variant_score, evaluate_candidate_variant, load_json, resolve_candidate_slug  # noqa: E402
from src.reports.tldr_brand3_research_pack_evaluation import DEFAULT_DATASET_PATH, DEFAULT_GOLD_PATH  # noqa: E402


ROOT = Path(__file__).resolve().parent
DEFAULT_HISTORY_DIR = ROOT / "history"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(path: str | Path | None, base_dir: Path) -> Path | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def resolve_batch_slug(candidate_file: Path | None, candidate_slug: str | None, candidate_dir: Path | None = None, fallback_slug: str | None = None) -> str | None:
    slug = (candidate_slug or fallback_slug or (candidate_file.stem if candidate_file is not None else "") or (candidate_dir.name if candidate_dir is not None else "")).strip()
    return slug or None


def load_batch_spec(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_summary(result: dict[str, Any]) -> dict[str, Any]:
    decision = result["decision"]
    case_delta = result["case_delta_summary"]
    report = result["report"]
    return {
        "decision": decision["decision"],
        "retain": decision["retain"],
        "scanner_average": decision["scanner_average"],
        "analyst_average": decision["analyst_average"],
        "structural_noise_delta": decision["structural_noise_delta"],
        "case_count": decision["case_count"],
        "improvements": case_delta["improvements"],
        "regressions": case_delta["regressions"],
        "block_count": len(report.get("block_summaries") or []),
    }


def execute_spec(
    spec: dict[str, Any],
    *,
    dataset: dict[str, Any],
    gold: dict[str, Any],
    base_dir: Path,
) -> dict[str, Any]:
    candidate_dir = _resolve_path(spec.get("candidate_dir"), base_dir)
    candidate_dir_b = _resolve_path(spec.get("candidate_dir_b"), base_dir)
    candidate_file = _resolve_path(spec.get("candidate_file"), base_dir)
    candidate_file_b = _resolve_path(spec.get("candidate_file_b"), base_dir)
    candidate_slug = spec.get("candidate_slug")
    candidate_slug_b = spec.get("candidate_slug_b")
    name = str(spec.get("name") or candidate_slug or (candidate_dir.name if candidate_dir else "run"))

    if candidate_dir_b is not None or candidate_file_b is not None:
        result_a = evaluate_candidate_variant(
            dataset=dataset,
            gold=gold,
            candidate_dir=candidate_dir,
            candidate_file=candidate_file,
            candidate_slug=resolve_batch_slug(candidate_file, candidate_slug, candidate_dir),
        )
        result_b = evaluate_candidate_variant(
            dataset=dataset,
            gold=gold,
            candidate_dir=candidate_dir_b or candidate_dir,
            candidate_file=candidate_file_b,
            candidate_slug=resolve_batch_slug(candidate_file_b, candidate_slug_b, candidate_dir_b or candidate_dir, candidate_slug),
        )
        score_a = candidate_variant_score(result_a)
        score_b = candidate_variant_score(result_b)
        winner = "tie"
        if score_a > score_b:
            winner = "a"
        elif score_b > score_a:
            winner = "b"
        comparison = {
            "winner": winner,
            "score_a": list(score_a),
            "score_b": list(score_b),
            "margin": round(score_b[1] - score_a[1], 4),
            "retain_a": bool(result_a["decision"]["retain"]),
            "retain_b": bool(result_b["decision"]["retain"]),
            "critical_regression_a": float(score_a[2]),
            "critical_regression_b": float(score_b[2]),
        }
        return {
            "name": name,
            "mode": "compare",
            "timestamp": _now(),
            "candidate_a": {
                "dir": str(candidate_dir) if candidate_dir else None,
                "file": str(candidate_file) if candidate_file else None,
                "slug": resolve_batch_slug(candidate_file, candidate_slug, candidate_dir),
            },
            "candidate_b": {
                "dir": str(candidate_dir_b or candidate_dir) if (candidate_dir_b or candidate_dir) else None,
                "file": str(candidate_file_b) if candidate_file_b else None,
                "slug": resolve_batch_slug(candidate_file_b, candidate_slug_b, candidate_dir_b or candidate_dir, candidate_slug),
            },
            "comparison": comparison,
            "candidate_a_summary": candidate_summary(result_a),
            "candidate_b_summary": candidate_summary(result_b),
        }

    result = evaluate_candidate_variant(
        dataset=dataset,
        gold=gold,
        candidate_dir=candidate_dir,
        candidate_file=candidate_file,
        candidate_slug=resolve_batch_slug(candidate_file, candidate_slug, candidate_dir),
    )
    return {
        "name": name,
        "mode": "single",
        "timestamp": _now(),
        "candidate": {
            "dir": str(candidate_dir) if candidate_dir else None,
            "file": str(candidate_file) if candidate_file else None,
            "slug": resolve_batch_slug(candidate_file, candidate_slug, candidate_dir),
        },
        "summary": candidate_summary(result),
    }


def append_history(history_path: Path, records: list[dict[str, Any]]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history(history_path: Path) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def summarize_history(records: list[dict[str, Any]], *, min_runs_for_recommendation: int = 5) -> dict[str, Any]:
    compare_records = [record for record in records if record.get("mode") == "compare" and isinstance(record.get("comparison"), dict)]
    if not compare_records:
        return {
            "total_runs": len(records),
            "compare_runs": 0,
            "single_runs": len(records),
            "wins": {},
            "winner_rate": {},
            "average_margin": None,
            "average_critical_regression_a": None,
            "average_critical_regression_b": None,
            "recommendation": {
                "status": "insufficient_data",
                "reason": "no compare runs",
            },
        }

    wins = Counter(record["comparison"]["winner"] for record in compare_records)
    total_compare = len(compare_records)
    win_rates = {key: round(value / total_compare, 3) for key, value in wins.items()}
    margins = [float(record["comparison"]["margin"]) for record in compare_records if isinstance(record["comparison"].get("margin"), (int, float))]
    average_margin = round(mean(margins), 4) if margins else None
    a_critical = [float(record["comparison"]["critical_regression_a"]) for record in compare_records]
    b_critical = [float(record["comparison"]["critical_regression_b"]) for record in compare_records]
    avg_critical_a = round(mean(a_critical), 4) if a_critical else None
    avg_critical_b = round(mean(b_critical), 4) if b_critical else None
    sufficient_data = total_compare >= min_runs_for_recommendation

    if not sufficient_data:
        recommendation = {
            "status": "insufficient_data",
            "reason": f"need at least {min_runs_for_recommendation} compare runs",
        }
    elif win_rates.get("b", 0.0) >= 0.6 and (average_margin or 0.0) > 0:
        recommendation = {
            "status": "prefer_b",
            "reason": "variant b wins often enough and has a positive average margin",
        }
    elif win_rates.get("a", 0.0) >= 0.6 and (average_margin or 0.0) < 0:
        recommendation = {
            "status": "prefer_a",
            "reason": "variant a wins often enough and has a negative average margin for b",
        }
    else:
        recommendation = {
            "status": "hold",
            "reason": "no clear winner yet",
        }

    return {
        "total_runs": len(records),
        "compare_runs": total_compare,
        "single_runs": len(records) - total_compare,
        "wins": dict(wins),
        "winner_rate": win_rates,
        "average_margin": average_margin,
        "average_critical_regression_a": avg_critical_a,
        "average_critical_regression_b": avg_critical_b,
        "sufficient_data": sufficient_data,
        "recommendation": recommendation,
    }


def write_summary_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Brand3 AutoResearch batch summary",
        "",
        f"- Total runs: `{summary['total_runs']}`",
        f"- Compare runs: `{summary['compare_runs']}`",
        f"- Single runs: `{summary['single_runs']}`",
        f"- Winner rates: `{summary['winner_rate']}`",
        f"- Average margin: `{summary['average_margin']}`",
        f"- Critical regression A: `{summary['average_critical_regression_a']}`",
        f"- Critical regression B: `{summary['average_critical_regression_b']}`",
        f"- Recommendation: `{summary['recommendation']['status']}`",
        f"- Reason: {summary['recommendation']['reason']}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a batch of Brand3 AutoResearch experiments.")
    parser.add_argument("--spec-file", type=Path, required=True)
    parser.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_DIR)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--min-runs", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    args = parser.parse_args()

    spec_path = args.spec_file.resolve()
    base_dir = spec_path.parent
    spec = load_batch_spec(spec_path)
    dataset = load_json(_resolve_path(spec.get("dataset"), base_dir) or args.dataset)
    gold = load_json(_resolve_path(spec.get("gold"), base_dir) or args.gold)
    runs = spec.get("runs") or []
    if not isinstance(runs, list):
        raise SystemExit("spec file must contain a 'runs' list")

    records = [execute_spec(run if isinstance(run, dict) else {}, dataset=dataset, gold=gold, base_dir=base_dir) for run in runs]
    history_path = args.history_dir / "batch_history.jsonl"
    append_history(history_path, records)

    all_records = load_history(history_path)
    summary = summarize_history(all_records, min_runs_for_recommendation=args.min_runs)
    summary_path = args.history_dir / "batch_summary.json"
    summary_md_path = args.history_dir / "batch_summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary_markdown(summary, summary_md_path)

    payload = {
        "batch": records,
        "summary": summary,
        "history_path": str(history_path),
        "summary_path": str(summary_path),
        "summary_markdown_path": str(summary_md_path),
    }

    if args.emit_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"batch runs: {len(records)}")
        print(f"- history: {history_path}")
        print(f"- recommendation: {summary['recommendation']['status']}")
        print(f"- reason: {summary['recommendation']['reason']}")
        print(f"- summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
