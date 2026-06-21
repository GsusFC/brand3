from __future__ import annotations

import concurrent.futures
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

_LLM_METRICS_LOCK = threading.Lock()


@dataclass
class ScreenshotResult:
    screenshot_url: str | None
    limitation: str | None
    capture: dict[str, object]


@dataclass
class FeatureExtractionResult:
    features_by_dim: dict[str, dict]
    screenshot_capture: dict[str, object]


def _feature_parallelism() -> int:
    raw_value = os.environ.get("BRAND3_FEATURE_PARALLELISM", "1")
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(value, 4))


def _timed_dimension_extract(
    timings_ms: dict[str, float],
    dimension: str,
    extract: Callable[[], dict],
) -> dict:
    started = perf_counter()
    try:
        return extract()
    finally:
        timings_ms[dimension] = (perf_counter() - started) * 1000.0


def _run_dimension_tasks(
    tasks: list[tuple[str, Callable[[], dict]]],
    *,
    timings_ms: dict[str, float],
    max_workers: int,
) -> dict[str, dict]:
    if max_workers <= 1 or len(tasks) <= 1:
        return {
            dimension: _timed_dimension_extract(timings_ms, dimension, extract)
            for dimension, extract in tasks
        }

    results: dict[str, dict] = {}
    task_by_dimension = dict(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_dimension = {
            pool.submit(_timed_dimension_extract, timings_ms, dimension, extract): dimension
            for dimension, extract in tasks
        }
        for future in concurrent.futures.as_completed(future_to_dimension):
            dimension = future_to_dimension[future]
            try:
                results[dimension] = future.result()
            except Exception as exc:
                print(
                    f"  {dimension}: parallel extraction failed "
                    f"({type(exc).__name__}); retrying sequentially"
                )
                results[dimension] = _timed_dimension_extract(
                    timings_ms,
                    dimension,
                    task_by_dimension[dimension],
                )

    return {dimension: results[dimension] for dimension, _ in tasks}


def _clone_llm_for_parallel(llm):
    if llm is None:
        return None
    try:
        clone = type(llm)(
            api_key=getattr(llm, "api_key"),
            base_url=getattr(llm, "base_url"),
            model=getattr(llm, "model"),
        )
    except Exception:
        return llm
    if hasattr(llm, "timeout_seconds"):
        clone.timeout_seconds = llm.timeout_seconds
    return clone


def _merge_llm_metrics(target, source) -> None:
    if target is None or source is None or target is source:
        return
    with _LLM_METRICS_LOCK:
        for attr in ("cache_hits", "cache_misses", "cache_writes"):
            setattr(target, attr, int(getattr(target, attr, 0) or 0) + int(getattr(source, attr, 0) or 0))
        if hasattr(target, "call_failures"):
            target.call_failures.extend(list(getattr(source, "call_failures", []) or []))


def capture_screenshot(
    *,
    url: str,
    skip_visual_analysis: bool,
    take_screenshot_with_budget,
    screenshot_capture_diagnostic,
) -> ScreenshotResult:
    if skip_visual_analysis:
        print("  Screenshot: skipped (benchmark mode)")
        return ScreenshotResult(
            screenshot_url=None,
            limitation=None,
            capture=screenshot_capture_diagnostic(
                attempted=False,
                skipped_reason="benchmark_mode",
            ),
        )

    try:
        screenshot_data, limitation = take_screenshot_with_budget(url)
        screenshot_url = screenshot_data.get("screenshot_url")
        capture = screenshot_capture_diagnostic(
            attempted=True,
            screenshot_data=screenshot_data,
            limitation=limitation,
        )
        if screenshot_url:
            print("  Screenshot: captured")
        elif limitation:
            print(f"  Screenshot: skipped ({limitation})")
        else:
            print(f"  Screenshot: skipped ({capture['error_type']})")
        return ScreenshotResult(
            screenshot_url=screenshot_url,
            limitation=limitation,
            capture=capture,
        )
    except Exception as e:
        print(f"  Screenshot: skipped ({e})")
        return ScreenshotResult(
            screenshot_url=None,
            limitation="error",
            capture=screenshot_capture_diagnostic(
                attempted=True,
                screenshot_data={"error": str(e)},
                limitation="error",
            ),
        )


def _extract_with_llm_metrics(parent_llm, task_llm, extract: Callable[[object], dict]) -> dict:
    try:
        return extract(task_llm)
    finally:
        _merge_llm_metrics(parent_llm, task_llm)
