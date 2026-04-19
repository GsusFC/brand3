"""
Brand3 Scoring — CLI entry point.

The reusable implementation lives in `src.services.brand_service`.
This file keeps the command-line interface and exports wrappers so
tests and local tooling can keep importing `main.py`.
"""

from __future__ import annotations

import argparse
import json
import sys

from src.config import (
    BRAND3_DB_PATH,
    BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
    BRAND3_PROMOTION_MAX_DIMENSION_DROPS,
)
from src.services import brand_service


DIMENSIONS_PATH = brand_service.DIMENSIONS_PATH
ENGINE_PATH = brand_service.ENGINE_PATH


def _sync_service_config() -> None:
    brand_service.BRAND3_DB_PATH = BRAND3_DB_PATH
    brand_service.BRAND3_PROMOTION_MAX_COMPOSITE_DROP = BRAND3_PROMOTION_MAX_COMPOSITE_DROP
    brand_service.BRAND3_PROMOTION_MAX_DIMENSION_DROPS = BRAND3_PROMOTION_MAX_DIMENSION_DROPS
    brand_service.DIMENSIONS_PATH = DIMENSIONS_PATH
    brand_service.ENGINE_PATH = ENGINE_PATH


def _delegate(fn_name: str, *args, **kwargs):
    _sync_service_config()
    return getattr(brand_service, fn_name)(*args, **kwargs)


def _build_run_audit_context(*args, **kwargs):
    return _delegate("_build_run_audit_context", *args, **kwargs)


def run(
    url: str,
    brand_name: str = None,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
) -> dict:
    return _delegate(
        "run",
        url,
        brand_name=brand_name,
        use_llm=use_llm,
        use_social=use_social,
        use_competitors=use_competitors,
    )


def add_feedback(*args, **kwargs):
    return _delegate("add_feedback", *args, **kwargs)


def learn(*args, **kwargs):
    return _delegate("learn", *args, **kwargs)


def list_runs(*args, **kwargs):
    return _delegate("list_runs", *args, **kwargs)


def list_brands(*args, **kwargs):
    return _delegate("list_brands", *args, **kwargs)


def list_profiles(*args, **kwargs):
    return _delegate("list_profiles", *args, **kwargs)


def benchmark_profiles(*args, **kwargs):
    return _delegate("benchmark_profiles", *args, **kwargs)


def compare_benchmarks(*args, **kwargs):
    return _delegate("compare_benchmarks", *args, **kwargs)


def list_feedback(*args, **kwargs):
    return _delegate("list_feedback", *args, **kwargs)


def show_run(*args, **kwargs):
    return _delegate("show_run", *args, **kwargs)


def brand_report(*args, **kwargs):
    return _delegate("brand_report", *args, **kwargs)


def propose_calibration(*args, **kwargs):
    return _delegate("propose_calibration", *args, **kwargs)


def list_candidates(*args, **kwargs):
    return _delegate("list_candidates", *args, **kwargs)


def review_candidate(*args, **kwargs):
    return _delegate("review_candidate", *args, **kwargs)


def apply_candidates(*args, **kwargs):
    return _delegate("apply_candidates", *args, **kwargs)


def run_experiment(*args, **kwargs):
    _sync_service_config()
    brand_name = kwargs.get("brand_name")
    candidate_ids = kwargs.get("candidate_ids")
    if args:
        brand_name = args[0]
    store = brand_service.SQLiteStore(BRAND3_DB_PATH)
    try:
        before_run_id = store.get_latest_run_id(brand_name=brand_name)
        if not before_run_id:
            raise ValueError(f"No runs found for brand {brand_name}")
        before_snapshot = store.get_run_snapshot(before_run_id)
        if not before_snapshot:
            raise ValueError(f"Run {before_run_id} not found")
        baseline = before_snapshot["run"]
    finally:
        store.close()

    applied_results = apply_candidates(candidate_ids=candidate_ids, brand_name=brand_name)
    applied_candidate_ids = [item["candidate_id"] for item in applied_results if item.get("applied")]
    if not applied_candidate_ids:
        raise ValueError("No approved candidates were applied; experiment aborted")
    applied_version_before_id = next(
        (item["version_before_id"] for item in applied_results if item.get("applied") and item.get("version_before_id")),
        None,
    )
    applied_version_after_id = None
    for item in applied_results:
        if item.get("applied") and item.get("version_after_id"):
            applied_version_after_id = item["version_after_id"]

    rerun_result = run(
        baseline["url"],
        brand_name=baseline["brand_name"],
        use_llm=bool(baseline["use_llm"]),
        use_social=bool(baseline["use_social"]),
    )
    after_run_id = rerun_result.get("run_id")
    if not after_run_id:
        raise ValueError("Rerun did not produce a persisted run_id")

    store = brand_service.SQLiteStore(BRAND3_DB_PATH)
    try:
        after_snapshot = store.get_run_snapshot(after_run_id)
        if not after_snapshot:
            raise ValueError(f"Run {after_run_id} not found after rerun")
        summary = brand_service._build_experiment_summary(before_snapshot, after_snapshot, applied_results)
        experiment_id = store.save_experiment(
            brand_name=baseline["brand_name"],
            url=baseline["url"],
            before_run_id=before_run_id,
            after_run_id=after_run_id,
            candidate_ids=applied_candidate_ids,
            summary=summary,
            version_before_id=applied_version_before_id,
            version_after_id=applied_version_after_id,
            before_scoring_state_fingerprint=before_snapshot["run"].get("scoring_state_fingerprint"),
            after_scoring_state_fingerprint=after_snapshot["run"].get("scoring_state_fingerprint"),
        )
        payload = {
            "experiment_id": experiment_id,
            "apply_results": applied_results,
            "summary": summary,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_experiments(*args, **kwargs):
    return _delegate("list_experiments", *args, **kwargs)


def list_versions(*args, **kwargs):
    return _delegate("list_versions", *args, **kwargs)


def rollback_version(*args, **kwargs):
    return _delegate("rollback_version", *args, **kwargs)


def promote_baseline(*args, **kwargs):
    return _delegate("promote_baseline", *args, **kwargs)


def list_baselines(*args, **kwargs):
    return _delegate("list_baselines", *args, **kwargs)


def get_gate_config(*args, **kwargs):
    return _delegate("get_gate_config", *args, **kwargs)


def set_gate_config(*args, **kwargs):
    return _delegate("set_gate_config", *args, **kwargs)


def compare_version(*args, **kwargs):
    return _delegate("compare_version", *args, **kwargs)


def enqueue_analysis_job(*args, **kwargs):
    return _delegate("enqueue_analysis_job", *args, **kwargs)


def get_analysis_job(*args, **kwargs):
    return _delegate("get_analysis_job", *args, **kwargs)


def list_analysis_jobs(*args, **kwargs):
    return _delegate("list_analysis_jobs", *args, **kwargs)


def execute_analysis_job(*args, **kwargs):
    return _delegate("execute_analysis_job", *args, **kwargs)


def cancel_analysis_job(*args, **kwargs):
    return _delegate("cancel_analysis_job", *args, **kwargs)


def retry_analysis_job(*args, **kwargs):
    return _delegate("retry_analysis_job", *args, **kwargs)


def _cmd_analyze(a: argparse.Namespace) -> None:
    run(a.url, a.brand_name, a.use_llm, a.use_social)


def _cmd_feedback(a: argparse.Namespace) -> None:
    kwargs = {
        k: v
        for k, v in {
            "run_id": a.run_id,
            "brand_name": a.brand_name,
            "url": a.url,
            "dimension_name": a.dimension_name,
            "feature_name": a.feature_name,
            "expected_score": a.expected_score,
            "actual_score": a.actual_score,
        }.items()
        if v is not None
    }
    add_feedback(a.note, **kwargs)


def _cmd_learn(a: argparse.Namespace) -> None:
    kwargs = {
        k: v
        for k, v in {"run_id": a.run_id, "brand_name": a.brand_name, "url": a.url}.items()
        if v is not None
    }
    learn(**kwargs)


def _cmd_runs(a: argparse.Namespace) -> None:
    kwargs = {"limit": a.limit}
    if a.brand_name:
        kwargs["brand_name"] = a.brand_name
    if a.url:
        kwargs["url"] = a.url
    list_runs(**kwargs)


def _cmd_brands(a: argparse.Namespace) -> None:
    list_brands(limit=a.limit)


def _cmd_profiles(_a: argparse.Namespace) -> None:
    list_profiles()


def _cmd_benchmark(a: argparse.Namespace) -> None:
    benchmark_profiles(
        a.spec,
        profiles=a.profiles,
        include_auto=a.include_auto,
        use_llm=a.use_llm,
        use_social=a.use_social,
        use_competitors=a.use_competitors,
    )


def _cmd_benchmark_compare(a: argparse.Namespace) -> None:
    compare_benchmarks(a.before, a.after)


def _cmd_annotations(a: argparse.Namespace) -> None:
    kwargs = {}
    if a.brand_name:
        kwargs["brand_name"] = a.brand_name
    list_feedback(**kwargs)


def _cmd_show_run(a: argparse.Namespace) -> None:
    show_run(a.run_id)


def _cmd_report(a: argparse.Namespace) -> None:
    brand_report(a.brand_name, limit=a.limit)


def _cmd_render_report(a: argparse.Namespace) -> None:
    from src.reports.renderer import render_latest, render_run

    if a.latest:
        path = render_latest(theme=a.theme)
    else:
        path = render_run(a.run_id, theme=a.theme)
    print(f"Rendered HTML report: {path}")


def _cmd_propose(a: argparse.Namespace) -> None:
    propose_calibration(a.brand_name, limit=a.limit, persist=a.persist)


def _cmd_candidates(a: argparse.Namespace) -> None:
    kwargs = {"limit": a.limit}
    if a.brand_name:
        kwargs["brand_name"] = a.brand_name
    if a.status:
        kwargs["status"] = a.status
    list_candidates(**kwargs)


def _cmd_review_candidate(a: argparse.Namespace) -> None:
    review_candidate(a.id, a.status)


def _cmd_apply_candidates(a: argparse.Namespace) -> None:
    apply_candidates(candidate_ids=a.ids, brand_name=a.brand_name)


def _cmd_experiment(a: argparse.Namespace) -> None:
    run_experiment(brand_name=a.brand_name, candidate_ids=a.ids)


def _cmd_experiments(a: argparse.Namespace) -> None:
    kwargs = {"limit": a.limit}
    if a.brand_name:
        kwargs["brand_name"] = a.brand_name
    list_experiments(**kwargs)


def _cmd_versions(a: argparse.Namespace) -> None:
    list_versions(limit=a.limit)


def _cmd_rollback_version(a: argparse.Namespace) -> None:
    rollback_version(a.id)


def _cmd_promote_baseline(a: argparse.Namespace) -> None:
    promote_baseline(a.id, label=a.label, force=a.force)


def _cmd_baselines(a: argparse.Namespace) -> None:
    list_baselines(limit=a.limit)


def _cmd_compare_version(a: argparse.Namespace) -> None:
    compare_version(a.id, a.brand_name)


def _cmd_gate_config(_a: argparse.Namespace) -> None:
    get_gate_config()


def _cmd_set_gate_config(a: argparse.Namespace) -> None:
    dimension_drops = json.loads(a.dimension_drops) if a.dimension_drops else None
    set_gate_config(max_composite_drop=a.max_composite_drop, dimension_drops=dimension_drops)


def _cmd_jobs(a: argparse.Namespace) -> None:
    kwargs = {"limit": a.limit}
    if a.brand_name:
        kwargs["brand_name"] = a.brand_name
    if a.status:
        kwargs["status"] = a.status
    list_analysis_jobs(**kwargs)


def _cmd_job(a: argparse.Namespace) -> None:
    get_analysis_job(a.id)


def _cmd_enqueue_job(a: argparse.Namespace) -> None:
    enqueue_analysis_job(a.url, brand_name=a.brand_name, use_llm=a.use_llm, use_social=a.use_social)


def _cmd_retry_job(a: argparse.Namespace) -> None:
    retry_analysis_job(a.id)


def _cmd_cancel_job(a: argparse.Namespace) -> None:
    cancel_analysis_job(a.id)


def _add_int_ids(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ids", type=lambda s: [int(p) for p in s.split(",") if p.strip()])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brand3", description="Brand3 Scoring CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze", help="Score a brand from its URL")
    p.add_argument("url")
    p.add_argument("brand_name", nargs="?", default=None)
    p.add_argument("--no-llm", dest="use_llm", action="store_false")
    p.add_argument("--no-social", dest="use_social", action="store_false")
    p.set_defaults(func=_cmd_analyze)

    p = sub.add_parser("feedback", help="Record a feedback note")
    p.add_argument("note")
    p.add_argument("--run-id", type=int)
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--url")
    p.add_argument("--dimension", dest="dimension_name")
    p.add_argument("--feature", dest="feature_name")
    p.add_argument("--expected", type=float, dest="expected_score")
    p.add_argument("--actual", type=float, dest="actual_score")
    p.set_defaults(func=_cmd_feedback)

    p = sub.add_parser("learn")
    p.add_argument("--run-id", type=int)
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--url")
    p.set_defaults(func=_cmd_learn)

    p = sub.add_parser("runs")
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--url")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_runs)

    p = sub.add_parser("brands")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=_cmd_brands)

    p = sub.add_parser("profiles")
    p.set_defaults(func=_cmd_profiles)

    p = sub.add_parser("benchmark")
    p.add_argument("--spec", required=True)
    p.add_argument("--profiles", type=lambda s: [part.strip() for part in s.split(",") if part.strip()])
    p.add_argument("--no-auto", dest="include_auto", action="store_false")
    p.add_argument("--no-llm", dest="use_llm", action="store_false")
    p.add_argument("--no-social", dest="use_social", action="store_false")
    p.add_argument("--no-competitors", "--fast", dest="use_competitors", action="store_false")
    p.set_defaults(func=_cmd_benchmark)

    p = sub.add_parser("benchmark-compare")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.set_defaults(func=_cmd_benchmark_compare)

    p = sub.add_parser("annotations")
    p.add_argument("--brand", dest="brand_name")
    p.set_defaults(func=_cmd_annotations)

    p = sub.add_parser("show-run")
    p.add_argument("--run-id", type=int, required=True)
    p.set_defaults(func=_cmd_show_run)

    p = sub.add_parser("report")
    p.add_argument("--brand", dest="brand_name", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=_cmd_report)

    # REVIEW: D4 — `report` (history listing) already taken; new command is `render-report`.
    p = sub.add_parser("render-report", help="Render a run as self-contained HTML")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", type=int)
    group.add_argument("--latest", action="store_true")
    p.add_argument("--theme", choices=["dark", "light"], default="dark")
    p.set_defaults(func=_cmd_render_report)

    p = sub.add_parser("propose")
    p.add_argument("--brand", dest="brand_name", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--persist", action="store_true")
    p.set_defaults(func=_cmd_propose)

    p = sub.add_parser("candidates")
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=_cmd_candidates)

    p = sub.add_parser("review-candidate")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", required=True, choices=["approved", "rejected", "proposed"])
    p.set_defaults(func=_cmd_review_candidate)

    p = sub.add_parser("apply-candidates")
    p.add_argument("--brand", dest="brand_name")
    _add_int_ids(p)
    p.set_defaults(func=_cmd_apply_candidates)

    p = sub.add_parser("experiment")
    p.add_argument("--brand", dest="brand_name", required=True)
    _add_int_ids(p)
    p.set_defaults(func=_cmd_experiment)

    p = sub.add_parser("experiments")
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_experiments)

    p = sub.add_parser("versions")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_versions)

    p = sub.add_parser("rollback-version")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=_cmd_rollback_version)

    p = sub.add_parser("promote-baseline")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--label")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=_cmd_promote_baseline)

    p = sub.add_parser("baselines")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_baselines)

    p = sub.add_parser("compare-version")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--brand", dest="brand_name", required=True)
    p.set_defaults(func=_cmd_compare_version)

    p = sub.add_parser("gate-config")
    p.set_defaults(func=_cmd_gate_config)

    p = sub.add_parser("set-gate-config")
    p.add_argument("--max-composite-drop", type=float)
    p.add_argument("--dimension-drops")
    p.set_defaults(func=_cmd_set_gate_config)

    p = sub.add_parser("jobs")
    p.add_argument("--brand", dest="brand_name")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=_cmd_jobs)

    p = sub.add_parser("job")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=_cmd_job)

    p = sub.add_parser("enqueue-job")
    p.add_argument("url")
    p.add_argument("brand_name", nargs="?", default=None)
    p.add_argument("--no-llm", dest="use_llm", action="store_false")
    p.add_argument("--no-social", dest="use_social", action="store_false")
    p.set_defaults(func=_cmd_enqueue_job)

    p = sub.add_parser("retry-job")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=_cmd_retry_job)

    p = sub.add_parser("cancel-job")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=_cmd_cancel_job)

    return parser


_KNOWN_COMMANDS = {
    "analyze", "feedback", "learn", "runs", "brands", "profiles", "benchmark",
    "benchmark-compare", "annotations", "show-run", "report", "render-report",
    "propose", "candidates", "review-candidate", "apply-candidates", "experiment",
    "experiments", "versions", "rollback-version", "promote-baseline",
    "baselines", "compare-version", "gate-config", "set-gate-config", "jobs",
    "job", "enqueue-job", "retry-job", "cancel-job",
    "-h", "--help",
}


def _normalize_argv(argv: list[str]) -> list[str]:
    """Shim legacy URL-as-first-arg form into `analyze <url> [...]`."""
    if len(argv) >= 2 and argv[1] not in _KNOWN_COMMANDS and not argv[1].startswith("-"):
        return [argv[0], "analyze", *argv[1:]]
    return argv


def main(argv: list[str] | None = None) -> None:
    argv = _normalize_argv(sys.argv if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == "__main__":
    main()
