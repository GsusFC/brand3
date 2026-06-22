"""Narrative orchestration for report generation.

This module keeps the public narrative orchestration behavior and cache semantics
that are used by report rendering paths. Runtime LLM calls and prompt helpers live
in `narrative_runtime` and `narrative_support`.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any

from .derivation import DimensionEvidences, Evidence
from .experimental_perceptual_narrative import (
    PerceptualNarrativeHints,
    build_perceptual_narrative_hints,
)
from .narrative_runtime import (
    _fallback_findings,
    _fallback_synthesis,
    _try_findings,
    _try_synthesis,
    _try_tensions,
)
from .narrative_types import Finding, SynthesisContext
from .narrative_support import _default_analyzer

log = logging.getLogger("brand3.reports.narrative")


# In-memory cache — keyed by (run_id, function_name, extra). TTL = process life.
_CACHE: dict[tuple, Any] = {}

_SYNTHESIS_MAX_TOKENS = 1200
_FINDINGS_MAX_TOKENS = 3500  # 4-field structure + acknowledgment clauses.
_TENSIONS_MAX_TOKENS = 1200
_FINDINGS_CALL_TIMEOUT_S = 30


def generate_synthesis(
    context: SynthesisContext,
    analyzer=None,
    run_id: int | None = None,
) -> str:
    """§1 prose (4-6 lines in English). Falls back to a deterministic summary."""
    cache_key = ("synthesis", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    prose = _try_synthesis(context, analyzer) or _fallback_synthesis(context)
    if cache_key is not None:
        _CACHE[cache_key] = prose
    return prose


def generate_dimension_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    analysis_date: str | None = None,
    perceptual_hints: PerceptualNarrativeHints | None = None,
    packet: dict | None = None,
) -> list[Finding]:
    """§3 sub-findings for one dimension. Empty list if no evidences at all."""
    cache_mode = "perceptual" if perceptual_hints and not perceptual_hints.empty() else "base"
    cache_key = ("findings", run_id, dim.dimension, cache_mode) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    if not dim.evidences:
        result: list[Finding] = []
    else:
        result = _try_findings(dim, brand, analyzer, analysis_date, perceptual_hints, packet)
        if result is None:
            log.warning(
                "findings: _try_findings returned None for %s (run_id=%s) — using fallback",
                dim.dimension,
                run_id,
            )
            result = _fallback_findings(dim, reason="llm_unavailable_or_empty")

    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    analysis_date: str | None = None,
) -> str | None:
    """§4 cross-dimension tension, or None if nothing relevant to say."""
    cache_key = ("tensions", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    result = _try_tensions(dimensions, brand, analyzer, analysis_date)
    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_all_findings(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    max_workers: int = 1,
    analysis_date: str | None = None,
    enable_perceptual_narrative: bool = False,
    packet: dict | None = None,
) -> dict[str, list[Finding]]:
    """Run generate_dimension_findings for all dimensions.

    Sequential by default (max_workers=1). Why:
    On macOS, parallel LLM HTTP calls via ThreadPoolExecutor trigger an
    Objective-C fork-safety crash when one worker forks a subprocess while
    another thread is initializing macOS frameworks (NSCharacterSet via
    getproxies_macosx_sysconf in urllib). Running findings serially avoids
    the race entirely.

    Cost: about 5 dims x 5s = 20s extra wall-clock per run. Acceptable for an
    editorial tool. On Linux/prod, pass max_workers > 1 explicitly to
    re-enable parallelism; the bug is macOS-specific.

    The per-call timeout (_FINDINGS_CALL_TIMEOUT_S) is preserved in the
    parallel path so a hung LLM call cannot block the run indefinitely.
    """
    out: dict[str, list[Finding]] = {}
    if not dimensions:
        return out

    if max_workers <= 1:
        for d in dimensions:
            try:
                perceptual_hints = (
                    build_perceptual_narrative_hints(d.dimension)
                    if enable_perceptual_narrative
                    else None
                )
                out[d.dimension] = generate_dimension_findings(
                    d, brand, analyzer, run_id, analysis_date, perceptual_hints, packet
                )
            except Exception as exc:
                log.warning("findings call for %s failed: %s", d.dimension, exc)
                out[d.dimension] = _fallback_findings(
                    d, reason=f"exception:{type(exc).__name__}"
                )
        return out

    dim_by_name = {d.dimension: d for d in dimensions}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_to_name = {
            pool.submit(
                generate_dimension_findings,
                d,
                brand,
                analyzer,
                run_id,
                analysis_date,
                build_perceptual_narrative_hints(d.dimension)
                if enable_perceptual_narrative
                else None,
                packet,
            ): d.dimension
            for d in dimensions
        }
        done, not_done = concurrent.futures.wait(
            future_to_name.keys(),
            timeout=_FINDINGS_CALL_TIMEOUT_S,
            return_when=concurrent.futures.ALL_COMPLETED,
        )
        for fut in done:
            name = future_to_name[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:
                log.warning("findings call for %s failed: %s", name, exc)
                out[name] = _fallback_findings(
                    dim_by_name[name], reason=f"exception:{type(exc).__name__}"
                )
        for fut in not_done:
            name = future_to_name[fut]
            log.warning(
                "findings call for %s exceeded %ss timeout — using fallback",
                name, _FINDINGS_CALL_TIMEOUT_S,
            )
            fut.cancel()
            out[name] = _fallback_findings(dim_by_name[name], reason="timeout")
    finally:
        pool.shutdown(wait=False)

    return out


def clear_cache() -> None:
    """Drop the in-memory cache. Mostly useful for tests."""
    _CACHE.clear()

