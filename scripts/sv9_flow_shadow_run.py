#!/usr/bin/env python3
"""Build an SV9 Flow candidate from an existing audit run.

This is a validation harness, not a product scanner:

- reads the current audit snapshot from the existing DB;
- may reuse existing SV9 Pass 1 detection cache;
- may run live detection when explicitly requested;
- emits JSON to stdout or a file;
- does not create routes, tables, jobs, scans, or public scores.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from src.config import BRAND3_DB_PATH
from src.sv9_flow._utils import unique_strings
from src.sv9_flow.block_evidence_worker import build_block_evidence_shortlists
from src.sv9_flow.contracts import BrandInterpretation, Sv9FlowCandidate
from src.sv9_flow.evidence_worker import build_evidence_pack_from_snapshot
from src.sv9_flow.interpretation_llm_worker import build_brand_interpretation_with_llm
from src.sv9_flow.orchestrator import build_flow_candidate_from_current_outputs
from src.sv9_flow.reporting import build_flow_report
from src.sv9_flow.tile_signal_worker import build_tile_signals_from_interpretation

SV9_FLOW_SHADOW_RUN_VERSION = "sv9-flow-shadow-run-v1"
INTERPRETATION_SOURCES = ("cached-pass1", "live-pass1", "provided-tldr", "flow-llm")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", type=int)
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Run live Pass 1 detection if no cached detection is available.",
    )
    parser.add_argument(
        "--force-detect",
        action="store_true",
        help="Run live Pass 1 detection even when cached detection exists.",
    )
    parser.add_argument(
        "--tldr",
        default="",
        help="Optional local JSON file with a tldr_brand3/Magnetism payload. Overrides cache/detection.",
    )
    parser.add_argument(
        "--interpretation-source",
        choices=INTERPRETATION_SOURCES,
        default="cached-pass1",
        help="Interpretation source to validate.",
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--report", action="store_true", help="Emit compact report envelope.")
    parser.add_argument("--env-file", default="", help="Optional dotenv-style file to load before LLM calls.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        _load_env_file(args.env_file)
    envelope = build_shadow_flow_for_run(
        args.run_id,
        db_path=args.db_path,
        detect=args.detect,
        force_detect=args.force_detect,
        interpretation_source=args.interpretation_source,
        tldr_payload=_load_optional_json(args.tldr),
        report_only=args.report,
    )
    rendered = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_shadow_flow_for_run(
    run_id: int,
    *,
    db_path: str = BRAND3_DB_PATH,
    detect: bool = False,
    force_detect: bool = False,
    interpretation_source: str = "cached-pass1",
    tldr_payload: dict[str, Any] | None = None,
    report_only: bool = False,
    load_snapshot_fn: Callable[..., dict[str, Any]] | None = None,
    get_cached_detection_fn: Callable[[int, str], dict[str, Any] | None] | None = None,
    detect_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    visual_signature_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    flow_interpretation_fn: Callable[[Any], tuple[BrandInterpretation, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build a connected shadow candidate while keeping side effects out."""

    load_snapshot_fn = load_snapshot_fn or _load_snapshot
    get_cached_detection_fn = get_cached_detection_fn or _get_cached_detection
    detect_fn = detect_fn or _detect_for_snapshot
    visual_signature_fn = visual_signature_fn or _visual_signature_evidence_from_snapshot
    flow_interpretation_fn = flow_interpretation_fn or _flow_interpretation_with_default_llm

    snapshot = load_snapshot_fn(run_id, db_path=db_path)
    visual_signature = visual_signature_fn(snapshot)
    llm_payload: dict[str, Any] | None = None
    detection_source = "missing"

    if interpretation_source == "flow-llm":
        evidence_pack = build_evidence_pack_from_snapshot(
            snapshot,
            visual_signature_evidence=visual_signature,
        )
        interpretation, llm_payload = flow_interpretation_fn(evidence_pack)
        tile_signals = build_tile_signals_from_interpretation(
            interpretation,
            visual_signature_evidence=visual_signature,
        )
        candidate = Sv9FlowCandidate(
            evidence_pack=evidence_pack,
            interpretation=interpretation,
            tile_signals=tile_signals,
            limitations=unique_strings(list(evidence_pack.limitations) + list(interpretation.limitations)),
        )
        detection_source = "flow_llm"
    else:
        if interpretation_source == "provided-tldr" or tldr_payload is not None:
            detection_source = "provided_tldr" if tldr_payload is not None else "missing_provided_tldr"
        elif interpretation_source == "cached-pass1" and not force_detect:
            tldr_payload = get_cached_detection_fn(run_id, db_path)
            if tldr_payload is not None:
                detection_source = "sv9_detection_cache"
        if interpretation_source == "live-pass1" or ((force_detect or tldr_payload is None) and detect):
            tldr_payload = detect_fn(snapshot)
            detection_source = "live_detection"

        candidate = build_flow_candidate_from_current_outputs(
            snapshot=snapshot,
            tldr_payload=tldr_payload,
            visual_signature_evidence=visual_signature,
        )
        _mark_compatibility_candidate(candidate, detection_source=detection_source)
    report = build_flow_report(candidate)

    payload: dict[str, Any] = {
        "schema_version": SV9_FLOW_SHADOW_RUN_VERSION,
        "source_run_id": run_id,
        "db_path": db_path,
        "detection_source": detection_source,
        "interpretation_source": interpretation_source,
        "visual_signature_present": visual_signature is not None,
        "report": report,
    }
    if llm_payload is not None:
        payload["llm_payload"] = llm_payload
    if not report_only:
        payload["candidate"] = candidate.to_dict()
    return payload


def _load_snapshot(run_id: int, *, db_path: str) -> dict[str, Any]:
    from src.services.magnetism_service import load_brand_audit_snapshot

    return load_brand_audit_snapshot(run_id, db_path=db_path)


def _mark_compatibility_candidate(candidate: Sv9FlowCandidate, *, detection_source: str) -> None:
    limitation = {
        "sv9_detection_cache": "cached_pass1_compatibility_only",
        "provided_tldr": "provided_tldr_compatibility_only",
        "live_detection": "live_pass1_compatibility_only",
    }.get(detection_source)
    if not limitation:
        return
    candidate.interpretation.limitations = unique_strings(
        list(candidate.interpretation.limitations) + [limitation]
    )
    candidate.limitations = unique_strings(list(candidate.limitations) + [limitation])


def _get_cached_detection(run_id: int, db_path: str) -> dict[str, Any] | None:
    from src.sv9.store import Sv9Store

    with Sv9Store(db_path) as store:
        return store.get_detection(run_id)


def _detect_for_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    from src.sv9.service import detect_for_snapshot

    return detect_for_snapshot(snapshot)


def _flow_interpretation_with_default_llm(evidence_pack: Any) -> tuple[BrandInterpretation, dict[str, Any]]:
    from src.features.llm_analyzer import LLMAnalyzer

    shortlists = build_block_evidence_shortlists(evidence_pack)
    interpretation, debug = build_brand_interpretation_with_llm(
        evidence_pack,
        llm=LLMAnalyzer(),
        block_evidence_shortlists=shortlists,
    )
    debug["block_evidence_shortlists"] = shortlists
    return interpretation, debug


def _visual_signature_evidence_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    from src.sv9.signals import visual_signature_evidence_from_snapshot

    return visual_signature_evidence_from_snapshot(snapshot)


def _load_optional_json(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_env_file(path: str) -> None:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
