"""
Build the report dossier/view-model from a run snapshot.

This module owns the orchestration that combines:
  - deterministic context derivation from the SQLite snapshot
  - narrative overlays (synthesis, findings, tensions)

The renderer should stay presentation-only and consume the dossier returned
here without needing to know about snapshot internals.
"""

from __future__ import annotations

import logging

from .derivation import (
    Evidence,
    build_report_base,
    build_report_context_from_base,
    collect_evidences,
    derive_data_quality,
    group_by_dimension,
)
from .narrative import (
    SynthesisContext,
    generate_all_findings,
    generate_synthesis,
    generate_tensions,
)

log = logging.getLogger("brand3.reports.dossier")


def build_brand_dossier(snapshot: dict, theme: str = "dark", analyzer=None) -> dict:
    """Build the full report dossier from a run snapshot.

    The returned dict keeps the legacy flat report keys for template
    compatibility, but it is now built from a richer base dossier shape
    (`brand`, `evaluation`, `narrative`, `sources`, `audit`, `ui`) that other
    surfaces can reuse directly later.
    """
    base = build_report_base(snapshot, theme=theme)
    _apply_narrative(base, snapshot, analyzer)
    return build_report_context_from_base(base)


def _pick_top_evidences(evidences: list[Evidence], limit: int = 4) -> list[Evidence]:
    """Pick up to `limit` evidences with a non-empty quote, maximizing diversity
    of source_type. Fills the remainder with whatever is left once every bucket
    has been represented once.
    """
    with_quote = [ev for ev in evidences if ev.quote]
    if not with_quote:
        return []
    seen_types: set[str] = set()
    picked: list[Evidence] = []
    for ev in with_quote:
        if ev.source_type in seen_types:
            continue
        seen_types.add(ev.source_type)
        picked.append(ev)
        if len(picked) >= limit:
            return picked
    for ev in with_quote:
        if ev in picked:
            continue
        picked.append(ev)
        if len(picked) >= limit:
            break
    return picked


def _apply_narrative(base: dict, snapshot: dict, analyzer) -> None:
    """Mutate the structured base dossier with LLM-generated narrative overlays.

    On any failure the relevant slot keeps the deterministic placeholder
    already populated by `build_report_base`.
    """
    run = snapshot.get("run") or {}
    brand = base["brand"]["name"]
    run_id = run.get("id")
    composite = run.get("composite_score")
    if composite is not None and not isinstance(composite, (int, float)):
        composite = None

    evidences = collect_evidences(snapshot)
    dim_evs = group_by_dimension(evidences, snapshot)
    data_quality = derive_data_quality(snapshot)
    context_readiness = (base.get("evaluation") or {}).get("context_readiness", {})
    context_status = context_readiness.get("status")
    if context_readiness.get("available") and context_status == "insufficient_data":
        base["narrative"]["summary"] = (
            base["narrative"]["summary"]
            + " Context pre-scan found insufficient machine-readable coverage."
        )
        base["narrative"]["synthesis_prose"] = base["narrative"]["summary"]
        return

    synth_ctx = SynthesisContext(
        brand=brand,
        url=base["brand"].get("url") or "",
        composite_score=composite,
        dimensions=dim_evs,
        data_quality=data_quality,
        top_evidences=_pick_top_evidences(evidences, limit=4),
    )
    try:
        synthesis = generate_synthesis(synth_ctx, analyzer=analyzer, run_id=run_id)
    except Exception as exc:
        log.warning("narrative.generate_synthesis failed: %s", exc)
        synthesis = None
    if synthesis:
        base["narrative"]["synthesis_prose"] = synthesis
        base["narrative"]["summary"] = synthesis

    try:
        findings_by_dim = generate_all_findings(
            dim_evs, brand, analyzer=analyzer, run_id=run_id
        )
    except Exception as exc:
        log.warning("narrative.generate_all_findings failed: %s", exc)
        findings_by_dim = {}
    for dim in base["dimensions"]:
        dim["findings"] = findings_by_dim.get(dim["name"], [])

    try:
        tensions = generate_tensions(dim_evs, brand, analyzer=analyzer, run_id=run_id)
    except Exception as exc:
        log.warning("narrative.generate_tensions failed: %s", exc)
        tensions = None
    base["narrative"]["tensions_prose"] = tensions
