"""
Brand3 Scoring — CLI entry point.

The reusable implementation lives in `src.services.brand_service`.
This file keeps the command-line interface and exports wrappers so
tests and local tooling can keep importing `main.py`.
"""

from __future__ import annotations

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


def run(url: str, brand_name: str = None, use_llm: bool = True, use_social: bool = True) -> dict:
    return _delegate("run", url, brand_name=brand_name, use_llm=use_llm, use_social=use_social)


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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <url> [brand_name] [--no-llm] [--no-social]")
        print("       python3 main.py feedback <note> [--run-id N] [--brand NAME] [--url URL] [--dimension DIM] [--feature FEAT] [--expected N] [--actual N]")
        print("       python3 main.py learn [--run-id N] [--brand NAME] [--url URL]")
        print("       python3 main.py runs [--brand NAME] [--url URL] [--limit N]")
        print("       python3 main.py brands [--limit N]")
        print("       python3 main.py profiles")
        print("       python3 main.py benchmark --spec PATH [--profiles p1,p2] [--no-auto] [--no-llm] [--no-social]")
        print("       python3 main.py benchmark-compare --before PATH --after PATH")
        print("       python3 main.py annotations [--brand NAME]")
        print("       python3 main.py show-run --run-id N")
        print("       python3 main.py report --brand NAME [--limit N]")
        print("       python3 main.py propose --brand NAME [--limit N] [--persist]")
        print("       python3 main.py candidates [--brand NAME] [--status STATUS] [--limit N]")
        print("       python3 main.py review-candidate --id N --status approved|rejected|proposed")
        print("       python3 main.py apply-candidates [--brand NAME] [--ids 1,2,3]")
        print("       python3 main.py experiment --brand NAME [--ids 1,2,3]")
        print("       python3 main.py experiments [--brand NAME] [--limit N]")
        print("       python3 main.py versions [--limit N]")
        print("       python3 main.py rollback-version --id N")
        print("       python3 main.py promote-baseline --id N [--label TEXT] [--force]")
        print("       python3 main.py baselines [--limit N]")
        print("       python3 main.py compare-version --id N --brand NAME")
        print("       python3 main.py gate-config")
        print("       python3 main.py set-gate-config [--max-composite-drop N] [--dimension-drops JSON]")
        print("       python3 main.py jobs [--brand NAME] [--status STATUS] [--limit N]")
        print("       python3 main.py job --id N")
        print("       python3 main.py enqueue-job <url> [brand_name] [--no-llm] [--no-social]")
        print("       python3 main.py retry-job --id N")
        print("       python3 main.py cancel-job --id N")
        print("Example: python3 main.py https://stripe.com Stripe")
        print("         python3 main.py https://stripe.com Stripe --no-llm")
        print("         python3 main.py https://stripe.com Stripe --no-social")
        sys.exit(1)

    if sys.argv[1] == "feedback":
        if len(sys.argv) < 3:
            print("Usage: python3 main.py feedback <note> [--run-id N] [--brand NAME] [--url URL] [--dimension DIM] [--feature FEAT] [--expected N] [--actual N]")
            sys.exit(1)
        note = sys.argv[2]
        kwargs = {}
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--run-id":
                kwargs["run_id"] = int(args[i + 1]); i += 2
            elif arg == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif arg == "--url":
                kwargs["url"] = args[i + 1]; i += 2
            elif arg == "--dimension":
                kwargs["dimension_name"] = args[i + 1]; i += 2
            elif arg == "--feature":
                kwargs["feature_name"] = args[i + 1]; i += 2
            elif arg == "--expected":
                kwargs["expected_score"] = float(args[i + 1]); i += 2
            elif arg == "--actual":
                kwargs["actual_score"] = float(args[i + 1]); i += 2
            else:
                i += 1
        add_feedback(note, **kwargs)
        sys.exit(0)

    if sys.argv[1] == "learn":
        kwargs = {}
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--run-id":
                kwargs["run_id"] = int(args[i + 1]); i += 2
            elif arg == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif arg == "--url":
                kwargs["url"] = args[i + 1]; i += 2
            else:
                i += 1
        learn(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "runs":
        kwargs = {"limit": 20}
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif arg == "--url":
                kwargs["url"] = args[i + 1]; i += 2
            elif arg == "--limit":
                kwargs["limit"] = int(args[i + 1]); i += 2
            else:
                i += 1
        list_runs(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "brands":
        limit = 50
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--limit":
                limit = int(args[i + 1]); i += 2
            else:
                i += 1
        list_brands(limit=limit)
        sys.exit(0)

    if sys.argv[1] == "profiles":
        list_profiles()
        sys.exit(0)

    if sys.argv[1] == "benchmark":
        args = sys.argv[2:]
        spec_path = None
        profiles = None
        include_auto = True
        use_llm = True
        use_social = True
        i = 0
        while i < len(args):
            if args[i] == "--spec":
                spec_path = args[i + 1]; i += 2
            elif args[i] == "--profiles":
                profiles = [part.strip() for part in args[i + 1].split(",") if part.strip()]; i += 2
            elif args[i] == "--no-auto":
                include_auto = False; i += 1
            elif args[i] == "--no-llm":
                use_llm = False; i += 1
            elif args[i] == "--no-social":
                use_social = False; i += 1
            else:
                i += 1
        if not spec_path:
            print("Usage: python3 main.py benchmark --spec PATH [--profiles p1,p2] [--no-auto] [--no-llm] [--no-social]")
            sys.exit(1)
        benchmark_profiles(
            spec_path,
            profiles=profiles,
            include_auto=include_auto,
            use_llm=use_llm,
            use_social=use_social,
        )
        sys.exit(0)

    if sys.argv[1] == "benchmark-compare":
        args = sys.argv[2:]
        before_path = None
        after_path = None
        i = 0
        while i < len(args):
            if args[i] == "--before":
                before_path = args[i + 1]; i += 2
            elif args[i] == "--after":
                after_path = args[i + 1]; i += 2
            else:
                i += 1
        if not before_path or not after_path:
            print("Usage: python3 main.py benchmark-compare --before PATH --after PATH")
            sys.exit(1)
        compare_benchmarks(before_path, after_path)
        sys.exit(0)

    if sys.argv[1] == "annotations":
        kwargs = {}
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            else:
                i += 1
        list_feedback(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "show-run":
        args = sys.argv[2:]
        run_id = None
        i = 0
        while i < len(args):
            if args[i] == "--run-id":
                run_id = int(args[i + 1]); i += 2
            else:
                i += 1
        if run_id is None:
            print("Usage: python3 main.py show-run --run-id N")
            sys.exit(1)
        show_run(run_id)
        sys.exit(0)

    if sys.argv[1] == "report":
        args = sys.argv[2:]
        brand_name = None
        limit = 10
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                brand_name = args[i + 1]; i += 2
            elif args[i] == "--limit":
                limit = int(args[i + 1]); i += 2
            else:
                i += 1
        if not brand_name:
            print("Usage: python3 main.py report --brand NAME [--limit N]")
            sys.exit(1)
        brand_report(brand_name, limit=limit)
        sys.exit(0)

    if sys.argv[1] == "propose":
        args = sys.argv[2:]
        brand_name = None
        limit = 20
        persist = False
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                brand_name = args[i + 1]; i += 2
            elif args[i] == "--limit":
                limit = int(args[i + 1]); i += 2
            elif args[i] == "--persist":
                persist = True; i += 1
            else:
                i += 1
        if not brand_name:
            print("Usage: python3 main.py propose --brand NAME [--limit N] [--persist]")
            sys.exit(1)
        propose_calibration(brand_name, limit=limit, persist=persist)
        sys.exit(0)

    if sys.argv[1] == "candidates":
        args = sys.argv[2:]
        kwargs = {"limit": 50}
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif args[i] == "--status":
                kwargs["status"] = args[i + 1]; i += 2
            elif args[i] == "--limit":
                kwargs["limit"] = int(args[i + 1]); i += 2
            else:
                i += 1
        list_candidates(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "review-candidate":
        args = sys.argv[2:]
        candidate_id = None
        status = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                candidate_id = int(args[i + 1]); i += 2
            elif args[i] == "--status":
                status = args[i + 1]; i += 2
            else:
                i += 1
        if candidate_id is None or status is None:
            print("Usage: python3 main.py review-candidate --id N --status approved|rejected|proposed")
            sys.exit(1)
        review_candidate(candidate_id, status)
        sys.exit(0)

    if sys.argv[1] == "apply-candidates":
        args = sys.argv[2:]
        brand_name = None
        candidate_ids = None
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                brand_name = args[i + 1]; i += 2
            elif args[i] == "--ids":
                candidate_ids = [int(part) for part in args[i + 1].split(",") if part.strip()]; i += 2
            else:
                i += 1
        apply_candidates(candidate_ids=candidate_ids, brand_name=brand_name)
        sys.exit(0)

    if sys.argv[1] == "experiment":
        args = sys.argv[2:]
        brand_name = None
        candidate_ids = None
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                brand_name = args[i + 1]; i += 2
            elif args[i] == "--ids":
                candidate_ids = [int(part) for part in args[i + 1].split(",") if part.strip()]; i += 2
            else:
                i += 1
        if not brand_name:
            print("Usage: python3 main.py experiment --brand NAME [--ids 1,2,3]")
            sys.exit(1)
        run_experiment(brand_name=brand_name, candidate_ids=candidate_ids)
        sys.exit(0)

    if sys.argv[1] == "experiments":
        args = sys.argv[2:]
        kwargs = {"limit": 20}
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif args[i] == "--limit":
                kwargs["limit"] = int(args[i + 1]); i += 2
            else:
                i += 1
        list_experiments(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "versions":
        args = sys.argv[2:]
        limit = 20
        i = 0
        while i < len(args):
            if args[i] == "--limit":
                limit = int(args[i + 1]); i += 2
            else:
                i += 1
        list_versions(limit=limit)
        sys.exit(0)

    if sys.argv[1] == "rollback-version":
        args = sys.argv[2:]
        version_id = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                version_id = int(args[i + 1]); i += 2
            else:
                i += 1
        if version_id is None:
            print("Usage: python3 main.py rollback-version --id N")
            sys.exit(1)
        rollback_version(version_id)
        sys.exit(0)

    if sys.argv[1] == "promote-baseline":
        args = sys.argv[2:]
        version_id = None
        label = None
        force = False
        i = 0
        while i < len(args):
            if args[i] == "--id":
                version_id = int(args[i + 1]); i += 2
            elif args[i] == "--label":
                label = args[i + 1]; i += 2
            elif args[i] == "--force":
                force = True; i += 1
            else:
                i += 1
        if version_id is None:
            print("Usage: python3 main.py promote-baseline --id N [--label TEXT] [--force]")
            sys.exit(1)
        promote_baseline(version_id, label=label, force=force)
        sys.exit(0)

    if sys.argv[1] == "baselines":
        args = sys.argv[2:]
        limit = 20
        i = 0
        while i < len(args):
            if args[i] == "--limit":
                limit = int(args[i + 1]); i += 2
            else:
                i += 1
        list_baselines(limit=limit)
        sys.exit(0)

    if sys.argv[1] == "compare-version":
        args = sys.argv[2:]
        version_id = None
        brand_name = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                version_id = int(args[i + 1]); i += 2
            elif args[i] == "--brand":
                brand_name = args[i + 1]; i += 2
            else:
                i += 1
        if version_id is None or brand_name is None:
            print("Usage: python3 main.py compare-version --id N --brand NAME")
            sys.exit(1)
        compare_version(version_id, brand_name)
        sys.exit(0)

    if sys.argv[1] == "gate-config":
        get_gate_config()
        sys.exit(0)

    if sys.argv[1] == "set-gate-config":
        args = sys.argv[2:]
        max_composite_drop = None
        dimension_drops = None
        i = 0
        while i < len(args):
            if args[i] == "--max-composite-drop":
                max_composite_drop = float(args[i + 1]); i += 2
            elif args[i] == "--dimension-drops":
                dimension_drops = json.loads(args[i + 1]); i += 2
            else:
                i += 1
        set_gate_config(max_composite_drop=max_composite_drop, dimension_drops=dimension_drops)
        sys.exit(0)

    if sys.argv[1] == "jobs":
        kwargs = {"limit": 50}
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--brand":
                kwargs["brand_name"] = args[i + 1]; i += 2
            elif args[i] == "--status":
                kwargs["status"] = args[i + 1]; i += 2
            elif args[i] == "--limit":
                kwargs["limit"] = int(args[i + 1]); i += 2
            else:
                i += 1
        list_analysis_jobs(**kwargs)
        sys.exit(0)

    if sys.argv[1] == "job":
        args = sys.argv[2:]
        job_id = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                job_id = int(args[i + 1]); i += 2
            else:
                i += 1
        if job_id is None:
            print("Usage: python3 main.py job --id N")
            sys.exit(1)
        get_analysis_job(job_id)
        sys.exit(0)

    if sys.argv[1] == "enqueue-job":
        if len(sys.argv) < 3:
            print("Usage: python3 main.py enqueue-job <url> [brand_name] [--no-llm] [--no-social]")
            sys.exit(1)
        url = sys.argv[2]
        brand_name = None
        use_llm = True
        use_social = True
        for arg in sys.argv[3:]:
            if arg == "--no-llm":
                use_llm = False
            elif arg == "--no-social":
                use_social = False
            elif not arg.startswith("--"):
                brand_name = arg
        enqueue_analysis_job(url, brand_name=brand_name, use_llm=use_llm, use_social=use_social)
        sys.exit(0)

    if sys.argv[1] == "retry-job":
        args = sys.argv[2:]
        job_id = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                job_id = int(args[i + 1]); i += 2
            else:
                i += 1
        if job_id is None:
            print("Usage: python3 main.py retry-job --id N")
            sys.exit(1)
        retry_analysis_job(job_id)
        sys.exit(0)

    if sys.argv[1] == "cancel-job":
        args = sys.argv[2:]
        job_id = None
        i = 0
        while i < len(args):
            if args[i] == "--id":
                job_id = int(args[i + 1]); i += 2
            else:
                i += 1
        if job_id is None:
            print("Usage: python3 main.py cancel-job --id N")
            sys.exit(1)
        cancel_analysis_job(job_id)
        sys.exit(0)

    url = sys.argv[1]
    brand = None
    use_llm = True
    use_social = True

    for arg in sys.argv[2:]:
        if arg == "--no-llm":
            use_llm = False
        elif arg == "--no-social":
            use_social = False
        elif not arg.startswith("--"):
            brand = arg

    run(url, brand, use_llm, use_social)
