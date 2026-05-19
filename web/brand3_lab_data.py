"""Static data builders for experimental Brand3 lab views."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.reports.entity_narrative_state import build_entity_narrative_state
from src.reports.narrative_harness import audit_report_narrative_payload
from src.storage.sqlite_store import SQLiteStore

from .storage import get_public_request_for_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_PATH = PROJECT_ROOT / "examples" / "brand3_platform" / "perceptual_narrative_evaluation.json"
COMPRESSION_EXPERIMENT_PATH = (
    PROJECT_ROOT
    / "examples"
    / "brand3_platform"
    / "perceptual_narrative_compression_experiment.json"
)
COMPRESSION_REVIEW_PATH = (
    PROJECT_ROOT
    / "examples"
    / "brand3_platform"
    / "perceptual_narrative_compression_review.json"
)
EDITORIAL_GATE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "brand3_platform"
    / "brand3_editorial_discipline_gate.json"
)
RUNTIME_SLICE_PLAN_PATH = (
    PROJECT_ROOT
    / "examples"
    / "brand3_platform"
    / "opt_in_perceptual_runtime_slice_plan.json"
)
SIGNAL_QUALITY_MODEL_PATH = (
    PROJECT_ROOT
    / "examples"
    / "brand3_lab"
    / "perceptual_signal_quality_model.json"
)
PATTERN_AUDIT_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "first_three_case_pattern_audit.json"
)
PATTERN_REGISTRY_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_pattern_registry.json"
)
READING_SEMANTICS_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_reading_semantics.json"
)
STRESS_TEST_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_reasoning_stress_test.json"
)
OVERREACH_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_overreach_taxonomy.json"
)
SHADOW_TRIAL_DIR = PROJECT_ROOT / "examples" / "reports" / "narrative_shadow_adapter_trial"
SHADOW_SOURCE_MANIFEST_PATH = (
    PROJECT_ROOT / "examples" / "reports" / "evidence_packet_candidate_integration_dry_path_v2_1" / "request_manifest.json"
)
SHADOW_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "narrative_shadow_adapter_trial.py"

GENERIC_PHRASES = [
    "premium",
    "polished",
    "sophisticated",
    "modern",
    "strong",
    "robust",
    "cohesive",
    "leadership",
    "trusted",
    "supportive",
    "accessible",
    "clear benefits",
    "clean interface",
    "differentiated",
]


def build_brand3_lab_home_model() -> dict[str, Any]:
    evaluation = _load_json(EVALUATION_PATH)
    compression_experiment = _load_json(COMPRESSION_EXPERIMENT_PATH)
    compression_review = _load_json(COMPRESSION_REVIEW_PATH)
    signal_model = _load_json(SIGNAL_QUALITY_MODEL_PATH)

    cases = _build_brand_cases(evaluation, compression_experiment, compression_review)
    layers = _research_layers()
    signal_depths = _signal_depths(signal_model)

    return {
        "title": "Brand3 Lab",
        "intro": (
            "Experimental research layer where every audited brand can receive "
            "a perceptual reading. The Lab classifies signal depth and signal "
            "quality instead of deciding whether a brand is eligible."
        ),
        "case_builder": {
            "label": "Lab Case Builder",
            "body": (
                "For this first version, Lab cases are built from the existing "
                "paired narrative evaluations and compression experiments. The "
                "builder reads baseline, perceptual, compressed, and review "
                "signals, then assigns depth, quality, valence, active layers, "
                "and evidence notes. Future audited brands should enter this "
                "same structure instead of being excluded for low signal."
            ),
            "steps": [
                "collect available narrative/evidence artifacts",
                "classify signal depth and quality",
                "apply research layers that have enough signal to say something",
                "surface negative, thin, or template-like readings as valid Lab outcomes",
                "link the case back to comparison/review evidence",
            ],
        },
        "research_map": [
            {
                "label": "Every brand becomes a case",
                "body": (
                    "Rich brands can produce pattern readings; thin or generic "
                    "brands still produce limitation, template, or negative "
                    "readings when the evidence supports them."
                ),
            },
            {
                "label": "Research is grouped, not scattered",
                "body": (
                    "The active artifacts are organized into four understandable "
                    "layers: grammar, safety, narrative voice, and runtime path."
                ),
            },
            {
                "label": "Production stays protected",
                "body": (
                    "Lab outputs do not change scoring, production reports, "
                    "prompts, Visual Signature, or global runtime behavior."
                ),
            },
        ],
        "layers": [_index_layer(layer) for layer in layers],
        "cases": [_index_case(case) for case in cases],
        "case_count": len(cases),
        "signal_depths": [_index_signal_depth(depth) for depth in signal_depths],
        "source_paths": [
            str(path.relative_to(PROJECT_ROOT))
            for path in (
                EVALUATION_PATH,
                COMPRESSION_EXPERIMENT_PATH,
                COMPRESSION_REVIEW_PATH,
                SIGNAL_QUALITY_MODEL_PATH,
                EDITORIAL_GATE_PATH,
                RUNTIME_SLICE_PLAN_PATH,
            )
            if path.exists()
        ],
    }


def build_brand3_lab_experiment_model(layer_id: str) -> dict[str, Any] | None:
    layers = _research_layers()
    layer = next((item for item in layers if item["id"] == layer_id), None)
    if not layer:
        return None

    cases = _load_cases()
    related_cases = [
        {
            "brand": case["brand"],
            "href": f"/brand3-lab/cases/{case['id']}",
            "status": _layer_status_for_case(layer["name"], case),
            "evidence": _layer_evidence_for_case(layer["name"], case),
        }
        for case in cases
    ]

    return {
        "title": layer["name"],
        "kind": "Active Experiment",
        "back_href": "/brand3-lab#active-experiments",
        "summary": layer["purpose"],
        "reads": layer["reads"],
        "adds_to_case": layer["adds_to_case"],
        "vocabulary": layer["vocabulary"],
        "how_llm_uses_it": layer["how_llm_uses_it"],
        "examples": layer["examples"],
        "artifacts": layer["artifacts"],
        "related_cases": related_cases,
        "guardrails": [
            "Lab-only research layer",
            "no scoring changes",
            "no report renderer changes",
            "no prompt rollout",
            "no Visual Signature runtime change",
        ],
    }


def build_brand3_lab_signal_depth_model(depth_id: str) -> dict[str, Any] | None:
    signal_model = _load_json(SIGNAL_QUALITY_MODEL_PATH)
    depths = _signal_depths(signal_model)
    depth = next((item for item in depths if item["id"] == depth_id), None)
    if not depth:
        return None

    cases = [
        case
        for case in _load_cases()
        if _normalize_depth_key(case["signal_depth"]) == _normalize_depth_key(depth["id"])
    ]

    return {
        "title": depth["label"],
        "kind": "Signal Depth Model",
        "back_href": "/brand3-lab#signal-depth-model",
        "summary": depth["definition"],
        "why_it_exists": (
            "The model stops Brand3 from treating perception as a yes/no eligibility "
            "gate. It keeps every analyzed brand in Lab, but changes the depth and "
            "confidence of the reading according to available evidence."
        ),
        "observable_markers": depth["observable_markers"],
        "valid_reading_posture": depth["valid_reading_posture"],
        "example_reading": depth["example_reading"],
        "flow": [
            "read available narrative, visual, copy, and review artifacts",
            "classify the amount and specificity of observable signal",
            "select a safe reading mode for the LLM",
            "suppress unsupported intent, emotion, and strategy claims",
            "render the case as rich, bounded, thin, generic, or negative instead of excluding it",
        ],
        "related_cases": [
            {
                "brand": case["brand"],
                "href": f"/brand3-lab/cases/{case['id']}",
                "signal_quality": case["signal_quality"],
                "reading_mode": case["reading_mode"],
            }
            for case in cases
        ],
        "source_path": str(SIGNAL_QUALITY_MODEL_PATH.relative_to(PROJECT_ROOT)),
    }


def build_brand3_lab_case_model(case_id: str) -> dict[str, Any] | None:
    evaluation = _load_json(EVALUATION_PATH)
    formatted_pairs = [
        _format_pair(index, pair)
        for index, pair in enumerate(evaluation.get("paired_outputs", []), start=1)
        if isinstance(pair, dict)
    ]
    case = next((item for item in _load_cases() if item["id"] == case_id), None)
    pair = next((item for item in formatted_pairs if item["id"] == case_id), None)
    if not case:
        return None

    return {
        "title": case["brand"],
        "kind": "Brand Case",
        "back_href": "/brand3-lab#brand-cases",
        "case": case,
        "pair": pair or {},
        "review_options": [
            "baseline_better",
            "perceptual_better",
            "mixed",
            "unsafe_overreach",
        ],
        "comparison_source_metadata": {
            "evaluation": str(EVALUATION_PATH.relative_to(PROJECT_ROOT)),
            "compression_experiment": str(COMPRESSION_EXPERIMENT_PATH.relative_to(PROJECT_ROOT)),
            "compression_review": str(COMPRESSION_REVIEW_PATH.relative_to(PROJECT_ROOT)),
        },
        "how_to_read": [
            "Start with the signal labels, not the score.",
            "Read classification evidence before interpreting the narrative.",
            "Treat low-confidence or obstructed material as a boundary, not as a defect.",
            "Use the comparison viewer for the baseline/perceptual side-by-side evidence.",
        ],
        "source_paths": [
            str(EVALUATION_PATH.relative_to(PROJECT_ROOT)),
            str(COMPRESSION_EXPERIMENT_PATH.relative_to(PROJECT_ROOT)),
            str(COMPRESSION_REVIEW_PATH.relative_to(PROJECT_ROOT)),
        ],
    }


def build_brand3_lab_audit_case_model(run_id: int) -> dict[str, Any] | None:
    """Build a read-only Brand3 Lab inspection model for one audit run."""
    snapshot = _load_run_snapshot(run_id)
    if snapshot is None:
        return None

    public_request = get_public_request_for_run(run_id)
    run = snapshot.get("run") or {}
    brand_profile = run.get("brand_profile") or {}
    report_narrative = _latest_report_narrative(snapshot)
    dimensions = _dimension_summaries(snapshot)
    evidence_coverage = _report_narrative_evidence_coverage(report_narrative)
    harness = (
        audit_report_narrative_payload(report_narrative, base_dossier=snapshot)
        if report_narrative
        else None
    )
    entity_state = (
        build_entity_narrative_state(
            report_narrative,
            payload_diagnostic=harness,
            snapshot={
                "brand": {
                    "name": run.get("brand_name") or brand_profile.get("name") or "unknown",
                    "url": run.get("url") or "",
                },
                "url": run.get("url") or "",
            },
        )
        if report_narrative
        else None
    )
    applied_reading = _applied_lab_reading(
        report_narrative=report_narrative,
        entity_state=entity_state,
    )

    return {
        "title": f"{run.get('brand_name') or brand_profile.get('name') or 'Brand'} Lab",
        "kind": "Applied Reading Candidates",
        "back_href": "/brand3-lab",
        "run_id": run_id,
        "brand": {
            "name": run.get("brand_name") or brand_profile.get("name") or "unknown",
            "domain": brand_profile.get("domain") or "unknown",
            "url": run.get("url") or "unknown",
        },
        "official_report": {
            "available": bool(public_request and public_request.get("token")),
            "href": f"/r/{public_request['token']}" if public_request and public_request.get("token") else "",
            "token": public_request.get("token") if public_request else "",
        },
        "score_summary": {
            "composite": run.get("composite_score"),
            "summary": run.get("summary") or "",
            "started_at": run.get("started_at") or "",
            "completed_at": run.get("completed_at") or "",
        },
        "dimensions": dimensions,
        "report_narrative": {
            "available": bool(report_narrative),
            "source": report_narrative.get("source") if report_narrative else "",
            "version": report_narrative.get("version") if report_narrative else "",
        },
        "applied_reading": applied_reading,
        "evidence_coverage": evidence_coverage,
        "narrative_harness": _harness_summary(harness),
        "entity_narrative_state": _entity_state_summary(entity_state),
        "layers": _per_audit_layer_statuses(
            report_narrative=report_narrative,
            harness=harness,
            entity_state=entity_state,
            applied_reading=applied_reading,
        ),
        "guardrails": [
            "Lab-only",
            "read-only",
            "diagnostic",
            "no scoring changes",
            "no report mutation",
            "no prompt rollout",
            "no persistence",
        ],
    }


def build_brand3_lab_audit_review_model(run_id: int) -> dict[str, Any] | None:
    """Build a draft-only review input model for one audit run."""
    model = build_brand3_lab_audit_case_model(run_id)
    if model is None:
        return None

    review_dimensions = _review_dimensions(model.get("applied_reading") or {})
    return {
        **model,
        "kind": "Lab Review Input",
        "title": f"{model['brand']['name']} Lab Review",
        "case_id": f"run-{run_id}",
        "review": {
            "schema_version": "brand3-lab-state-first-review-draft-1",
            "source_artifacts": {
                "run_id": run_id,
                "report_narrative": model["report_narrative"],
                "narrative_harness": {
                    "available": model["narrative_harness"]["available"],
                    "status": model["narrative_harness"]["status"],
                },
                "entity_narrative_state": model["entity_narrative_state"],
                "applied_reading": {
                    "available": model["applied_reading"]["available"],
                    "status": model["applied_reading"]["status"],
                    "variant_count": model["applied_reading"]["variant_count"],
                },
            },
            "dimension_decisions": [
                "baseline_better",
                "lab_better",
                "mixed",
                "unsafe_overreach",
                "no_safe_candidate",
            ],
            "reason_tags": [
                "stronger_evidence_binding",
                "reduced_caveat_repetition",
                "clearer_entity_boundary",
                "better_uncertainty_handling",
                "too_generic",
                "false_confidence",
                "unsupported_claim",
                "missing_evidence",
                "requires_human_review",
            ],
            "overall_decisions": [
                "baseline_wins",
                "lab_wins",
                "mixed",
                "unsafe",
                "needs_more_evidence",
            ],
            "dimensions": review_dimensions,
            "available": bool(review_dimensions),
            "unavailable_reason": (
                ""
                if review_dimensions
                else model["applied_reading"].get("unavailable_reason") or "no safe Lab candidate yet"
            ),
        },
    }


def build_perceptual_narrative_comparison_model() -> dict[str, Any]:
    evaluation = _load_json(EVALUATION_PATH)
    stress_test = _load_json(STRESS_TEST_PATH)
    taxonomy = _load_json(OVERREACH_TAXONOMY_PATH)

    pairs = [
        _format_pair(index, pair)
        for index, pair in enumerate(evaluation.get("paired_outputs", []), start=1)
        if isinstance(pair, dict)
    ]
    failure_modes = [
        {
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "warning_signs": _string_list(item.get("observable_warning_signs"))[:3],
        }
        for item in taxonomy.get("failure_modes", [])
        if isinstance(item, dict)
    ]

    return {
        "title": "Perceptual Narrative Comparison",
        "intro": (
            "Aggregate index for the perceptual narrative comparison experiment. "
            "Per-brand review now lives inside each Brand3 Lab case."
        ),
        "guardrails": [
            "experimental lab only",
            "draft only",
            "no persistence",
            "no scoring impact",
            "no prompt changes",
            "no report renderer changes",
            "no Visual Signature changes",
        ],
        "pairs": pairs,
        "case_links": [
            {
                "brand": pair["brand"],
                "id": pair["id"],
                "href": f"/brand3-lab/cases/{pair['id']}#case-comparison",
                "brand3_confidence": pair["brand3_confidence"],
                "risk_count": len(pair["overreach_risks"]),
                "gain_count": len(pair["perceptual_gains"]),
            }
            for pair in pairs
        ],
        "pair_count": len(pairs),
        "review_options": [
            "baseline_better",
            "perceptual_better",
            "mixed",
            "unsafe_overreach",
        ],
        "aggregate": evaluation.get("aggregate_assessment", {}),
        "recommendation": evaluation.get("recommendation", {}),
        "safe_deployment_zones": _string_list(stress_test.get("safe_deployment_zones")),
        "unsafe_deployment_zones": _string_list(stress_test.get("unsafe_deployment_zones")),
        "failure_modes": failure_modes,
        "source_paths": [
            str(EVALUATION_PATH.relative_to(PROJECT_ROOT)),
            str(STRESS_TEST_PATH.relative_to(PROJECT_ROOT)),
            str(OVERREACH_TAXONOMY_PATH.relative_to(PROJECT_ROOT)),
        ],
    }


def _research_layers() -> list[dict[str, Any]]:
    return [
        {
            "id": "perceptual-grammar",
            "name": "Perceptual Grammar",
            "purpose": (
                "How Brand3 identifies surface signals, groups them into "
                "patterns, and turns them into bounded perceptual readings."
            ),
            "reads": [
                "observable signals",
                "signal clusters",
                "recurring patterns",
                "claim/signal relationships",
            ],
            "adds_to_case": (
                "A case-level perceptual reading: what surface mechanisms are "
                "visible, what pattern they may support, and what remains only "
                "a bounded interpretation."
            ),
            "vocabulary": [
                "surface signal",
                "signal cluster",
                "perceptual pattern",
                "productive tension",
                "bounded interpretation",
            ],
            "how_llm_uses_it": [
                "name visible mechanisms before interpretation",
                "group repeated signals into a stable pattern",
                "separate observation from narrative implication",
                "avoid declaring strategic intent unless the source states it",
            ],
            "examples": [
                "Product objects plus controlled whitespace can support a product-first hierarchy reading.",
                "Dense navigation plus code surfaces can support an operational complexity reading.",
            ],
            "artifacts": [
                _artifact("Pattern audit", PATTERN_AUDIT_PATH),
                _artifact("Perceptual Pattern Registry", PATTERN_REGISTRY_PATH),
                _artifact("Perceptual Reading Semantics", READING_SEMANTICS_PATH),
            ],
        },
        {
            "id": "safety-boundaries",
            "name": "Safety & Boundaries",
            "purpose": (
                "How Brand3 avoids invented intent, unsupported emotion, "
                "generic sophistication, and exclusion of weak-signal brands."
            ),
            "reads": [
                "overreach risks",
                "signal depth",
                "weak evidence",
                "generic or absent signals",
            ],
            "adds_to_case": (
                "A safety classification: what the Lab can safely say, what "
                "must stay conditional, and whether the reading should be rich, "
                "bounded, thin, or absence/template-based."
            ),
            "vocabulary": [
                "overreach",
                "weak evidence amplification",
                "template-like surface",
                "low specificity",
                "negative perceptual reading",
            ],
            "how_llm_uses_it": [
                "downgrade unsupported emotional or strategic claims",
                "say when there is no usable signal",
                "preserve weak readings as valid Lab outcomes",
                "flag obstructed or copy-only evidence before prose becomes too confident",
            ],
            "examples": [
                "A generic SaaS surface can produce an absence reading instead of an invented pattern.",
                "A wellness brand can invite calm visually without proving therapeutic support.",
            ],
            "artifacts": [
                _artifact("Overreach Taxonomy", OVERREACH_TAXONOMY_PATH),
                _artifact("Stress Test", STRESS_TEST_PATH),
                _artifact("Signal Quality Model", SIGNAL_QUALITY_MODEL_PATH),
            ],
        },
        {
            "id": "narrative-voice",
            "name": "Narrative Voice",
            "purpose": (
                "How Brand3 compresses perceptual analysis into shorter, "
                "sharper, evidence-bound prose."
            ),
            "reads": [
                "baseline prose",
                "raw perceptual prose",
                "compressed perceptual prose",
                "editorial gate risks",
            ],
            "adds_to_case": (
                "A voice decision: which version reads more Brand3/FLOC*, "
                "where the prose gets too generic, and what rewrite would stay "
                "shorter and evidence-bound."
            ),
            "vocabulary": [
                "compressed perceptual prose",
                "editorial discipline",
                "generic AI verbosity",
                "false sophistication",
                "evidence-bound rewrite",
            ],
            "how_llm_uses_it": [
                "prefer shorter paragraphs with fewer disclaimers",
                "keep one clear observation and one implication per paragraph",
                "remove empty premium/sophisticated language",
                "retain confidence boundaries without turning prose into legal caveats",
            ],
            "examples": [
                "Replace broad praise with the visible mechanism creating the effect.",
                "Keep the tension when compressing; remove only meta-language.",
            ],
            "artifacts": [
                _artifact("Perceptual Narrative Compression", COMPRESSION_EXPERIMENT_PATH),
                _artifact("Compression Review", COMPRESSION_REVIEW_PATH),
                _artifact("Editorial Discipline Gate", EDITORIAL_GATE_PATH),
            ],
        },
        {
            "id": "runtime-path",
            "name": "Runtime Path",
            "purpose": (
                "How a future implementation could remain opt-in, gated, "
                "and isolated from scoring or production defaults."
            ),
            "reads": [
                "safe activation conditions",
                "fallback behavior",
                "monitoring requirements",
                "rollback conditions",
            ],
            "adds_to_case": (
                "A rollout boundary: whether this case is suitable only for "
                "Lab review or could later be part of an explicit opt-in "
                "runtime experiment."
            ),
            "vocabulary": [
                "opt-in runtime slice",
                "fallback behavior",
                "confidence gate",
                "rollback condition",
                "baseline-only output",
            ],
            "how_llm_uses_it": [
                "keep production reports baseline unless explicitly enabled",
                "apply augmentation only to eligible finding text",
                "fall back identically when hints are missing or unsafe",
                "never mutate scoring or Visual Signature output",
            ],
            "examples": [
                "A rich case may later be eligible for opt-in compressed findings.",
                "A thin case remains useful in Lab but should not automatically alter reports.",
            ],
            "artifacts": [
                _artifact("Opt-in compressed runtime slice plan", RUNTIME_SLICE_PLAN_PATH),
            ],
        },
    ]


def _artifact(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "status": "available" if path.exists() else "missing",
    }


def _load_cases() -> list[dict[str, Any]]:
    return _build_brand_cases(
        _load_json(EVALUATION_PATH),
        _load_json(COMPRESSION_EXPERIMENT_PATH),
        _load_json(COMPRESSION_REVIEW_PATH),
    )


def _index_layer(layer: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": layer["id"],
        "name": layer["name"],
        "purpose": layer["purpose"],
        "reads": layer["reads"],
        "adds_to_case": layer["adds_to_case"],
        "artifact_count": len(layer["artifacts"]),
        "href": f"/brand3-lab/experiments/{layer['id']}",
    }


def _index_signal_depth(depth: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": depth["id"],
        "label": depth["label"],
        "definition": depth["definition"],
        "reading_posture": depth["reading_posture"],
        "href": f"/brand3-lab/signal-depth/{depth['id']}",
    }


def _index_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "brand": case["brand"],
        "signal_depth": case["signal_depth"],
        "signal_quality": case["signal_quality"],
        "reading_valence": case["reading_valence"],
        "reading_mode": case["reading_mode"],
        "safe_output_mode": case["safe_output_mode"],
        "brand3_confidence": case["brand3_confidence"],
        "href": f"/brand3-lab/cases/{case['id']}",
        "comparison_href": case["comparison_href"],
    }


def _layer_status_for_case(layer_name: str, case: dict[str, Any]) -> str:
    for layer in case.get("active_layers", []):
        if isinstance(layer, dict) and layer.get("name") == layer_name:
            return str(layer.get("status") or "unknown")
    return "not_linked"


def _layer_evidence_for_case(layer_name: str, case: dict[str, Any]) -> str:
    for layer in case.get("active_layers", []):
        if isinstance(layer, dict) and layer.get("name") == layer_name:
            return str(layer.get("evidence") or "")
    return "This layer is not yet linked to the case."


def _normalize_depth_key(value: str) -> str:
    normalized = value.lower().replace("-", "_")
    if normalized == "rich":
        return "rich_perceptual_signal"
    if normalized == "moderate":
        return "moderate_perceptual_signal"
    if normalized == "thin":
        return "thin_perceptual_signal"
    if normalized in {"absent_or_generic", "generic"}:
        return "absent_or_generic_signal"
    return normalized


def _build_brand_cases(
    evaluation: dict[str, Any],
    compression_experiment: dict[str, Any],
    compression_review: dict[str, Any],
) -> list[dict[str, Any]]:
    compressed_by_brand = {
        str(item.get("brand") or ""): item
        for item in compression_experiment.get("paired_examples", [])
        if isinstance(item, dict)
    }
    winners_by_brand = {
        str(item.get("brand") or ""): item
        for item in compression_review.get("version_winners", [])
        if isinstance(item, dict)
    }

    cases: list[dict[str, Any]] = []
    for index, pair in enumerate(evaluation.get("paired_outputs", []), start=1):
        if not isinstance(pair, dict):
            continue
        brand = str(pair.get("brand") or f"Case {index}")
        comparison = pair.get("comparison") if isinstance(pair.get("comparison"), dict) else {}
        compressed = compressed_by_brand.get(brand, {})
        winner = winners_by_brand.get(brand, {})
        signal_depth, signal_quality, reading_valence = _infer_case_signal_labels(
            brand,
            pair,
            compressed if isinstance(compressed, dict) else {},
            winner if isinstance(winner, dict) else {},
        )
        reading_mode, safe_output_mode = _case_modes(signal_depth, signal_quality, brand)
        active_layers = _active_case_layers(signal_depth, signal_quality, compressed)
        cases.append(
            {
                "id": _slugify(brand),
                "brand": brand,
                "signal_depth": signal_depth,
                "signal_quality": signal_quality,
                "reading_valence": reading_valence,
                "reading_mode": reading_mode,
                "safe_output_mode": safe_output_mode,
                "brand3_confidence": str(
                    comparison.get("feels_brand3_floc_confidence") or "unrated"
                ).replace("_", " "),
                "active_layers": active_layers,
                "comparison_href": f"/brand3-lab/perceptual-narrative-comparison#pair-{_slugify(brand)}",
                "summary": _case_summary(brand, pair, compressed if isinstance(compressed, dict) else {}),
                "classification_evidence": _classification_evidence(
                    brand,
                    pair,
                    compressed if isinstance(compressed, dict) else {},
                    winner if isinstance(winner, dict) else {},
                    signal_depth,
                    signal_quality,
                ),
            }
        )
    return cases


def _infer_case_signal_labels(
    brand: str,
    pair: dict[str, Any],
    compressed: dict[str, Any],
    winner: dict[str, Any],
) -> tuple[str, str, str]:
    text = " ".join(
        str(value)
        for value in (
            pair.get("perceptual_augmented_narrative"),
            pair.get("baseline_narrative"),
            compressed.get("compressed_perceptual_narrative"),
            winner.get("residual_risk"),
        )
        if value
    ).lower()

    if "example company" in brand.lower() or "thin" in text or "weak corroboration" in text:
        return ("thin", "low_specificity", "diagnostic")
    if "headspace" in brand.lower() or "mental-health" in text or "wellness" in text:
        return ("moderate", "mixed", "mixed")
    if "notion" in brand.lower():
        return ("moderate", "mixed", "diagnostic")
    if "screenshot-limited" in text or "copy-supported" in text or "obstructed" in text:
        return ("moderate", "obstructed", "diagnostic")
    if "template" in text or "generic" in text:
        return ("absent_or_generic", "generic", "negative")
    return ("rich", "distinctive", "mixed")


def _case_modes(
    signal_depth: str,
    signal_quality: str,
    brand: str,
) -> tuple[str, str]:
    if signal_depth == "rich":
        return ("full_pattern_reading", "compressed_perceptual")
    if signal_depth == "moderate" and signal_quality == "obstructed":
        return ("bounded_pattern_reading", "raw_perceptual_with_caution")
    if signal_depth == "moderate":
        return ("bounded_pattern_reading", "compressed_perceptual")
    if signal_depth == "thin":
        return ("limitation_reading", "lab_only_review")
    if signal_depth == "absent_or_generic":
        return ("absence_or_template_reading", "lab_only_review")
    if "example" in brand.lower():
        return ("limitation_reading", "lab_only_review")
    return ("bounded_pattern_reading", "raw_perceptual_with_caution")


def _active_case_layers(
    signal_depth: str,
    signal_quality: str,
    compressed: dict[str, Any],
) -> list[dict[str, str]]:
    layers = [
        {
            "name": "Perceptual Grammar",
            "status": "applied",
            "evidence": "Baseline and perceptual narratives are compared for observable surface signals and pattern language.",
        },
        {
            "name": "Safety & Boundaries",
            "status": "applied",
            "evidence": f"Signal depth is classified as {signal_depth}; signal quality is classified as {signal_quality}.",
        },
    ]
    if compressed.get("compressed_perceptual_narrative"):
        layers.append(
            {
                "name": "Narrative Voice",
                "status": "applied",
                "evidence": "Compressed perceptual prose exists for this case and can be compared against baseline/raw prose.",
            }
        )
    else:
        layers.append(
            {
                "name": "Narrative Voice",
                "status": "partial",
                "evidence": "No compressed narrative exists yet, so the case uses raw perceptual comparison only.",
            }
        )
    layers.append(
        {
            "name": "Runtime Path",
            "status": "not_active",
            "evidence": "Runtime integration remains a plan; this Lab case does not change reports or scoring.",
        }
    )
    return layers


def _classification_evidence(
    brand: str,
    pair: dict[str, Any],
    compressed: dict[str, Any],
    winner: dict[str, Any],
    signal_depth: str,
    signal_quality: str,
) -> list[str]:
    evidence: list[str] = []
    text = " ".join(
        str(value)
        for value in (
            pair.get("perceptual_augmented_narrative"),
            compressed.get("compressed_perceptual_narrative"),
            winner.get("residual_risk"),
        )
        if value
    ).lower()

    if signal_depth == "rich":
        evidence.append("Repeated concrete surface mechanisms are present in the narrative evidence.")
    elif signal_depth == "moderate":
        evidence.append("The case has usable surface signals, but confidence stays bounded by partial, sensitive, or obstructed evidence.")
    elif signal_depth == "thin":
        evidence.append("The case is useful as a limitation reading because evidence is sparse or weakly corroborated.")
    elif signal_depth == "absent_or_generic":
        evidence.append("The case is useful as a template/absence reading rather than a full pattern reading.")

    if "copy-supported" in text:
        evidence.append("The reading explicitly preserves copy-supported boundaries.")
    if "screenshot-limited" in text or "obstructed" in text:
        evidence.append("Visual evidence is obstructed or screenshot-limited, so product behavior cannot be asserted as fact.")
    if "mental-health" in text or "wellness" in text:
        evidence.append("Wellness or support claims remain sensitive and require visible caution.")
    if "low specificity" in text or "weak corroboration" in text:
        evidence.append("Low specificity or weak corroboration is treated as signal quality, not business failure.")
    if compressed.get("compressed_perceptual_narrative"):
        evidence.append("A compressed version exists, so Narrative Voice can be applied visibly in the Lab.")
    if not evidence:
        evidence.append(f"{brand} has enough paired narrative material to become a Lab case.")
    return evidence[:5]


def _case_summary(brand: str, pair: dict[str, Any], compressed: dict[str, Any]) -> str:
    if compressed.get("compressed_perceptual_narrative"):
        return str(compressed["compressed_perceptual_narrative"])
    perceptual = str(pair.get("perceptual_augmented_narrative") or "")
    if perceptual:
        return perceptual
    return f"{brand} is available as a Brand3 Lab case."


def _signal_depths(signal_model: dict[str, Any]) -> list[dict[str, Any]]:
    depths = []
    for item in signal_model.get("signal_depth_classes", []):
        if not isinstance(item, dict):
            continue
        depths.append(
            {
                "label": str(item.get("label") or item.get("id") or ""),
                "definition": str(item.get("definition") or ""),
                "id": str(item.get("id") or ""),
                "observable_markers": _string_list(item.get("observable_markers")),
                "valid_reading_posture": _string_list(item.get("valid_reading_posture")),
                "reading_posture": "; ".join(_string_list(item.get("valid_reading_posture"))[:3]),
                "example_reading": str(item.get("example_reading") or ""),
            }
        )
    return depths


def _format_pair(index: int, pair: dict[str, Any]) -> dict[str, Any]:
    brand = str(pair.get("brand") or f"Case {index}")
    baseline = str(pair.get("baseline_narrative") or "")
    perceptual = str(pair.get("perceptual_augmented_narrative") or "")
    comparison = pair.get("comparison") if isinstance(pair.get("comparison"), dict) else {}
    strengths = _string_list(pair.get("strengths"))
    weaknesses = _string_list(pair.get("weaknesses"))
    overreach_flags = _string_list(pair.get("overreach_flags"))

    perceptual_gains = [
        _humanize_metric(key, value)
        for key, value in comparison.items()
        if key.endswith("_delta") and str(value).startswith(("improves", "reduced", "lower"))
    ]

    return {
        "id": _slugify(brand),
        "index": index,
        "brand": brand,
        "baseline_narrative": baseline,
        "perceptual_augmented_narrative": perceptual,
        "better_specificity": _better_specificity(comparison),
        "perceptual_gains": perceptual_gains[:6],
        "overreach_risks": [*overreach_flags, *weaknesses],
        "generic_phrases": _find_generic_phrases(baseline, perceptual),
        "comparison": comparison,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overreach_flags": overreach_flags,
        "brand3_confidence": str(comparison.get("feels_brand3_floc_confidence") or "unrated"),
    }


def _better_specificity(comparison: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for key in (
        "specificity_delta",
        "observational_grounding_delta",
        "tension_quality_delta",
    ):
        value = str(comparison.get(key) or "")
        if value:
            items.append(_humanize_metric(key, value))
    return items


def _humanize_metric(key: str, value: Any) -> str:
    label = key.replace("_delta", "").replace("_", " ")
    return f"{label}: {str(value).replace('_', ' ')}"


def _find_generic_phrases(*texts: str) -> list[str]:
    haystack = " ".join(texts).lower()
    found = [phrase for phrase in GENERIC_PHRASES if phrase in haystack]
    return sorted(set(found))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_run_snapshot(run_id: int) -> dict[str, Any] | None:
    store = SQLiteStore(str(BRAND3_DB_PATH))
    try:
        return store.get_run_snapshot(run_id)
    finally:
        store.close()


def _latest_report_narrative(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if not isinstance(item, dict):
            continue
        if item.get("source") != "report_narrative":
            continue
        payload = item.get("payload")
        if isinstance(payload, dict):
            return payload
    return None


def _dimension_summaries(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for score in snapshot.get("scores") or []:
        if not isinstance(score, dict):
            continue
        dimensions.append(
            {
                "name": str(score.get("dimension_name") or "unknown"),
                "score": score.get("score"),
                "insight_count": len(_json_list(score.get("insights_json"))),
                "rule_count": len(_json_list(score.get("rules_json"))),
            }
        )
    return dimensions


def _json_list(raw_value: Any) -> list[Any]:
    if isinstance(raw_value, list):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _report_narrative_evidence_coverage(payload: dict[str, Any] | None) -> dict[str, Any]:
    findings = _flatten_report_findings(payload)
    total = len(findings)
    without_urls = [finding for finding in findings if not finding["evidence_urls"]]
    affected_dimensions = sorted({finding["dimension"] for finding in without_urls})
    return {
        "finding_count": total,
        "findings_with_evidence_urls": total - len(without_urls),
        "findings_without_evidence_urls": len(without_urls),
        "coverage_level": _coverage_level(total, len(without_urls)),
        "affected_dimensions": affected_dimensions,
    }


def _flatten_report_findings(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw_by_dimension = payload.get("findings_by_dimension")
    if not isinstance(raw_by_dimension, dict):
        return []

    findings: list[dict[str, Any]] = []
    for dimension, raw_findings in raw_by_dimension.items():
        if not isinstance(raw_findings, list):
            continue
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            findings.append(
                {
                    "dimension": str(dimension),
                    "index": len(findings),
                    "title": str(item.get("title") or ""),
                    "observation": str(item.get("observation") or item.get("prose") or ""),
                    "implication": str(item.get("implication") or ""),
                    "typical_decision": str(item.get("typical_decision") or ""),
                    "evidence_urls": [
                        str(url)
                        for url in (item.get("evidence_urls") or [])
                        if isinstance(url, str) and url.strip()
                    ],
                }
            )
    return findings


_GENERIC_DECISION_SPACE_PREFIXES = (
    "teams in this position typically",
    "companies in this position typically",
    "companies in this situation typically",
    "brands facing such",
    "teams with such",
)

_GENERIC_DECISION_SPACE_PHRASES = (
    "the optimal path depends on market reception, competitive landscape, and available resources",
    "the choice depends on strategic priorities and available resources",
    "the best approach depends on the nature of the concerns and the brand's risk tolerance",
)


def _review_dimensions(applied_reading: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for dimension in applied_reading.get("dimensions") or []:
        if not isinstance(dimension, dict):
            continue
        findings = [item for item in dimension.get("findings") or [] if isinstance(item, dict)]
        if not findings:
            continue
        evidence_urls: list[str] = []
        unavailable_reasons: list[str] = []
        requires_human_review = False
        lab_candidate_count = 0
        for finding in findings:
            for url in finding.get("evidence_urls") or []:
                if isinstance(url, str) and url and url not in evidence_urls:
                    evidence_urls.append(url)
            reason = str(finding.get("unavailable_reason") or "")
            if reason and reason not in unavailable_reasons:
                unavailable_reasons.append(reason)
            if finding.get("requires_human_review"):
                requires_human_review = True
            if finding.get("lab_variant_available"):
                lab_candidate_count += 1

        dimensions.append(
            {
                "id": _slugify(str(dimension.get("name") or "unknown")),
                "name": str(dimension.get("name") or "unknown"),
                "findings": findings,
                "lab_candidate_count": lab_candidate_count,
                "finding_count": len(findings),
                "candidate_available": lab_candidate_count > 0,
                "evidence_urls": evidence_urls,
                "requires_human_review": requires_human_review,
                "unavailable_reasons": unavailable_reasons,
            }
        )
    return dimensions


def _applied_lab_reading(
    *,
    report_narrative: dict[str, Any] | None,
    entity_state: dict[str, Any] | None,
) -> dict[str, Any]:
    findings = _flatten_report_findings(report_narrative)
    if not findings:
        return {
            "available": False,
            "status": "unavailable",
            "summary": "No safe Lab-applied reading candidate exists because this run has no persisted findings in report_narrative.",
            "unavailable_reason": "no report narrative",
            "variant_count": 0,
            "dimensions": [],
        }

    state = entity_state.get("state") if isinstance(entity_state, dict) else {}
    entity_needs_review = bool(
        isinstance(state, dict)
        and isinstance(state.get("entity_aliases"), dict)
        and state["entity_aliases"].get("needs_review")
    )

    grouped: dict[str, list[dict[str, Any]]] = {}
    variant_count = 0
    for finding in findings:
        item = _applied_lab_finding(
            finding,
            entity_needs_review=entity_needs_review,
        )
        if item["lab_variant_available"]:
            variant_count += 1
        grouped.setdefault(finding["dimension"], []).append(item)

    return {
        "available": variant_count > 0,
        "status": "generated_offline" if variant_count > 0 else "unavailable",
        "summary": (
            "Lab generated read-only candidate recompositions from existing findings; no new facts, scores, prompts, or report prose were created."
            if variant_count > 0
            else "No safe Lab-applied reading candidates were generated from the persisted findings."
        ),
        "unavailable_reason": "" if variant_count > 0 else "no safe Lab candidate yet",
        "variant_count": variant_count,
        "dimensions": [
            {"name": dimension, "findings": items}
            for dimension, items in grouped.items()
        ],
    }


def _applied_lab_finding(
    finding: dict[str, Any],
    *,
    entity_needs_review: bool,
) -> dict[str, Any]:
    observation = _clean_display_text(finding.get("observation"))
    implication = _clean_display_text(finding.get("implication"))
    decision = _clean_display_text(finding.get("typical_decision"))
    evidence_urls = finding.get("evidence_urls") or []
    official_parts = [observation, implication, decision]
    official_text = " ".join(part for part in official_parts if part).strip()
    lab_parts = [observation, implication]
    show_decision = _should_show_lab_decision_space(decision)
    if show_decision:
        lab_parts.append(f"Decision space: {decision}")
    lab_text = " ".join(part for part in lab_parts if part).strip()
    generic_decision_hidden = bool(decision and not show_decision)
    caveat_present = _contains_any(
        f"{observation} {implication} {decision}",
        (
            "no external corroboration",
            "without external corroboration",
            "based only on self-description",
        ),
    )
    owned_claim_present = _contains_any(
        f"{observation} {implication}",
        (
            "the brand describes itself",
            "the brand claims",
            "the brand says",
        ),
    )

    change_notes = []
    if generic_decision_hidden:
        change_notes.append("Generic Decision Space is demoted instead of repeated as analysis.")
    if caveat_present:
        change_notes.append("Repeated caveat language is kept as a risk boundary, not expanded into more prose.")
    if owned_claim_present:
        change_notes.append("Owned claims remain attributed; the Lab candidate does not treat them as external validation.")
    if evidence_urls:
        change_notes.append("Evidence URL chips remain attached to the finding.")
    else:
        change_notes.append("Missing evidence URLs are surfaced as a risk rather than hidden.")
    if observation and implication:
        change_notes.append("Observation and implication remain separated inside the applied reading candidate.")

    risk_notes = []
    if not evidence_urls:
        risk_notes.append("Missing evidence URLs; human review is needed before treating this as production-safe.")
    if caveat_present:
        risk_notes.append("Corroboration caveat present; uncertainty must remain visible.")
    if entity_needs_review:
        risk_notes.append("Entity or related-surface ambiguity requires human review.")
    if generic_decision_hidden:
        risk_notes.append("Generic decision framing was suppressed, not solved at generation level.")
    if not risk_notes:
        risk_notes.append("No obvious Lab risk detected from deterministic checks.")

    lab_variant_available = bool(lab_text and (lab_text != official_text or change_notes))
    if not lab_variant_available:
        risk_notes.append("No safe Lab-applied reading candidate could be derived from this finding.")

    confidence = "medium" if evidence_urls and not entity_needs_review else "low"
    if not lab_variant_available:
        confidence = "unavailable"

    return {
        "dimension": finding.get("dimension") or "unknown",
        "title": finding.get("title") or "Untitled finding",
        "official_text": official_text or "No official finding prose is available.",
        "lab_applied_text": lab_text if lab_variant_available else "",
        "lab_variant_available": lab_variant_available,
        "unavailable_reason": "" if lab_variant_available else "no safe Lab candidate yet",
        "candidate_status": "experimental_lab_only_not_official_not_persisted" if lab_variant_available else "unavailable",
        "candidate_generation_mode": "deterministic_recomposition" if lab_variant_available else "unavailable",
        "candidate_label": "recomposed candidate" if lab_variant_available else "unavailable",
        "decision_space_visible": show_decision,
        "evidence_urls": evidence_urls,
        "change_notes": change_notes,
        "risk_notes": risk_notes,
        "confidence": confidence,
        "requires_human_review": bool(not evidence_urls or entity_needs_review or caveat_present),
        "layers_used": [
            "report_narrative",
            "Narrative Harness",
            "EntityNarrativeState",
            "Editorial Discipline Gate",
        ],
    }


def _clean_display_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _contains_any(value: str, phrases: tuple[str, ...]) -> bool:
    normalized = " ".join(value.lower().split())
    return any(phrase in normalized for phrase in phrases)


def _should_show_lab_decision_space(value: str) -> bool:
    normalized = " ".join(value.lower().split())
    if not normalized:
        return False
    if normalized.startswith(_GENERIC_DECISION_SPACE_PREFIXES):
        return False
    if any(phrase in normalized for phrase in _GENERIC_DECISION_SPACE_PHRASES):
        return False
    return True


def _coverage_level(total: int, missing: int) -> str:
    if total <= 0:
        return "unavailable"
    if missing == 0:
        return "complete"
    if missing >= total:
        return "missing"
    return "mixed"


def _harness_summary(harness: dict[str, Any] | None) -> dict[str, Any]:
    if not harness:
        return {
            "available": False,
            "status": "unavailable",
            "warning_count": 0,
            "error_count": 0,
            "summary": {},
            "visible_checks": [],
        }
    checks = [
        {
            "id": str(check.get("check_id") or check.get("id") or ""),
            "status": str(check.get("status") or ""),
            "message": str(check.get("message") or ""),
        }
        for check in harness.get("checks", [])
        if isinstance(check, dict) and check.get("status") != "pass"
    ]
    metrics = harness.get("metrics") if isinstance(harness.get("metrics"), dict) else {}
    families = metrics.get("observation_repetition_family_counts")
    if not isinstance(families, dict):
        families = {}
    return {
        "available": True,
        "status": harness.get("status") or "unknown",
        "warning_count": int((harness.get("summary") or {}).get("warnings") or 0),
        "error_count": int((harness.get("summary") or {}).get("errors") or 0),
        "summary": harness.get("summary") or {},
        "metrics": {
            "findings_count": metrics.get("findings_count", 0),
            "findings_without_evidence_urls": metrics.get("findings_without_evidence_urls", 0),
            "safe_attribution_total": metrics.get("safe_attribution_total", 0),
            "observation_repetition_families": ", ".join(sorted(families)) if families else "none",
        },
        "visible_checks": checks[:6],
    }


def _entity_state_summary(entity_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(entity_state, dict):
        return {
            "available": False,
            "status": "unavailable",
            "case_family": "unknown",
            "requires_review": False,
        }
    state = entity_state.get("state") if isinstance(entity_state.get("state"), dict) else {}
    aliases = state.get("entity_aliases") if isinstance(state.get("entity_aliases"), dict) else {}
    return {
        "available": True,
        "status": "generated_offline",
        "case_family": (entity_state.get("metadata") or {}).get("case_family") or "unknown",
        "requires_review": bool(aliases.get("needs_review")),
    }


def _per_audit_layer_statuses(
    *,
    report_narrative: dict[str, Any] | None,
    harness: dict[str, Any] | None,
    entity_state: dict[str, Any] | None,
    applied_reading: dict[str, Any],
) -> list[dict[str, str]]:
    narrative_available = bool(report_narrative)
    harness_available = bool(harness)
    entity_state_available = bool(entity_state)
    applied_reading_available = bool(applied_reading.get("available"))
    return [
        {
            "id": "narrative_harness",
            "name": "Narrative Harness",
            "status": "generated_offline" if harness_available else "unavailable",
            "summary": (
                "Payload-level narrative diagnostics ran in memory for this view."
                if harness_available
                else "Unavailable because this run has no persisted report_narrative payload."
            ),
        },
        {
            "id": "render_aware_diagnostics",
            "name": "Render-aware diagnostics",
            "status": "unavailable",
            "summary": "Not generated in this first slice; rendered output is not inspected here.",
        },
        {
            "id": "entity_narrative_state",
            "name": "EntityNarrativeState",
            "status": "generated_offline" if entity_state_available else "blocked",
            "summary": (
                "Built in memory for this Lab view as a composition-state constraint."
                if entity_state_available
                else "Blocked until report_narrative exists."
            ),
        },
        {
            "id": "state_aware_findings_experiment",
            "name": "State-aware findings experiment",
            "status": "generated_offline" if applied_reading_available else "unavailable",
            "summary": (
                "Applied as deterministic Lab reading candidates for this run."
                if applied_reading_available
                else "No safe per-run Lab reading candidate is available yet."
            ),
        },
        {
            "id": "signal_depth_model",
            "name": "Signal Depth Model",
            "status": "unavailable",
            "summary": "Not applied to this audit run in the first slice.",
        },
        {
            "id": "perceptual_pattern_registry",
            "name": "Perceptual Pattern Registry",
            "status": "unavailable",
            "summary": "No reviewed perceptual case record is attached to this run.",
        },
        {
            "id": "overreach_taxonomy",
            "name": "Overreach Taxonomy",
            "status": "unavailable",
            "summary": "Not applied as a per-run diagnostic in this first slice.",
        },
        {
            "id": "editorial_discipline_gate",
            "name": "Editorial Discipline Gate",
            "status": "unavailable",
            "summary": "Not applied as a per-run diagnostic in this first slice.",
        },
    ]


def run_narrative_shadow_adapter_trial(
    *,
    execute: bool,
    run_id: int | None,
    source_mode: str = "benchmark",
) -> dict[str, Any]:
    """Run the lab-only shadow adapter trial script from web UI."""
    mode = "run" if source_mode == "run" else "benchmark"
    if mode == "run" and run_id is None:
        return {
            "ok": False,
            "return_code": 2,
            "elapsed_ms": 0,
            "execute": execute,
            "run_id": None,
            "source_mode": mode,
            "command": "",
            "stdout_tail": "",
            "stderr_tail": "run_id is required when source_mode=run",
        }
    cmd = [str(PROJECT_ROOT / ".venv" / "bin" / "python"), str(SHADOW_SCRIPT_PATH)]
    cmd.extend(["--source", mode])
    if execute:
        cmd.append("--execute")
    if run_id is not None:
        cmd.extend(["--run-id", str(run_id)])

    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    elapsed_ms = int((time.time() - started) * 1000)
    return {
        "ok": proc.returncode == 0,
        "return_code": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "execute": execute,
        "run_id": run_id,
        "source_mode": mode,
        "command": " ".join(cmd),
        "stdout_tail": (proc.stdout or "").strip()[-4000:],
        "stderr_tail": (proc.stderr or "").strip()[-4000:],
    }


def build_narrative_shadow_adapter_model(
    *,
    last_run: dict[str, Any] | None = None,
    run_id: int | None = None,
    source_mode: str = "benchmark",
) -> dict[str, Any]:
    """Build UI model for shadow adapter lab trial page."""
    source_manifest = _load_json(SHADOW_SOURCE_MANIFEST_PATH)
    request_manifest = _load_json(SHADOW_TRIAL_DIR / "request_manifest.json")
    raw_outputs = _load_json(SHADOW_TRIAL_DIR / "raw_outputs.json")
    comparison = _load_json(SHADOW_TRIAL_DIR / "comparison.json")
    cost = _load_json(SHADOW_TRIAL_DIR / "cost_observation.json")
    review = _load_json(PROJECT_ROOT / "docs" / "brand3_narrative_shadow_adapter_trial_review.json")

    available_runs: list[dict[str, Any]] = []
    for row in source_manifest.get("requests", []) if isinstance(source_manifest, dict) else []:
        rid = row.get("run_id")
        if rid is None:
            continue
        available_runs.append(
            {
                "run_id": int(rid),
                "label": f"{row.get('case_id','unknown')}::{row.get('dimension','unknown')} (run {rid})",
            }
        )
    seen = set()
    deduped_runs = []
    for row in available_runs:
        rid = row["run_id"]
        if rid in seen:
            continue
        seen.add(rid)
        deduped_runs.append(row)
    for row in _recent_brand_runs(limit=30):
        rid = row["run_id"]
        if rid in seen:
            continue
        seen.add(rid)
        deduped_runs.append(row)

    selected_run = run_id
    selected_source_mode = "run" if source_mode == "run" else "benchmark"
    per_case_rows = []
    findings_by_dimension: dict[str, list[dict[str, Any]]] = {}
    raw_results = raw_outputs.get("results", []) if isinstance(raw_outputs, dict) else []
    per_case = comparison.get("per_case", {}) if isinstance(comparison, dict) else {}
    for key, row in per_case.items():
        if selected_run is not None and int((row or {}).get("run_id") or -1) != selected_run:
            continue
        summary = (row or {}).get("summary", {})
        per_case_rows.append(
            {
                "key": key,
                "case_id": row.get("case_id"),
                "dimension": row.get("dimension"),
                "readiness_status": row.get("readiness_status"),
                "finding_count": summary.get("finding_count", 0),
                "limits_present": summary.get("limits_field_present"),
                "risky_outside_count": len(summary.get("risky_terms_outside_limits", []) or []),
                "urls_valid": summary.get("evidence_url_validity"),
                "delta_non_regressive": row.get("delta_non_regressive"),
            }
        )
    for result in raw_results:
        if selected_run is not None and int((result or {}).get("run_id") or -1) != selected_run:
            continue
        dimension = str((result or {}).get("dimension") or "unknown")
        case_id = str((result or {}).get("case_id") or "unknown")
        status = str((result or {}).get("readiness_status") or "")
        raw_response = (result or {}).get("raw_response") or {}
        findings = raw_response.get("findings") if isinstance(raw_response, dict) else None
        if not isinstance(findings, list) or not findings:
            findings_by_dimension.setdefault(dimension, []).append(
                {
                    "case_id": case_id,
                    "readiness_status": status,
                    "title": "",
                    "evidence_anchor": "",
                    "observation": "",
                    "bounded_interpretation": "",
                    "limits": "",
                    "evidence_urls": [],
                    "is_empty": True,
                }
            )
            continue
        for item in findings:
            if not isinstance(item, dict):
                continue
            findings_by_dimension.setdefault(dimension, []).append(
                {
                    "case_id": case_id,
                    "readiness_status": status,
                    "title": str(item.get("title") or ""),
                    "evidence_anchor": str(item.get("evidence_anchor") or ""),
                    "observation": str(item.get("observation") or ""),
                    "bounded_interpretation": str(item.get("bounded_interpretation") or ""),
                    "limits": str(item.get("limits") or ""),
                    "evidence_urls": [str(url) for url in (item.get("evidence_urls") or []) if str(url).strip()],
                    "is_empty": False,
                }
            )

    findings_sections = []
    preferred_order = ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
    for dimension in preferred_order:
        rows = findings_by_dimension.get(dimension)
        if rows:
            findings_sections.append({"dimension": dimension, "rows": rows})
    for dimension in sorted(findings_by_dimension.keys()):
        if dimension in preferred_order:
            continue
        findings_sections.append({"dimension": dimension, "rows": findings_by_dimension[dimension]})

    dimension_overview: list[dict[str, Any]] = []
    for section in findings_sections:
        dimension = section["dimension"]
        related_cases = [row for row in per_case_rows if row.get("dimension") == dimension]
        statuses = [str(row.get("readiness_status") or "") for row in related_cases]
        primary_status = (
            "ready"
            if "ready" in statuses
            else "thin"
            if "thin" in statuses
            else "blocked"
            if "blocked" in statuses
            else "abstain"
        )
        total_findings = sum(int(row.get("finding_count") or 0) for row in related_cases)
        risks = sum(int(row.get("risky_outside_count") or 0) for row in related_cases)
        dimension_overview.append(
            {
                "dimension": dimension,
                "status": primary_status,
                "cases": len(related_cases),
                "findings": total_findings,
                "risk_signals": risks,
            }
        )

    return {
        "title": "Narrative Shadow Adapter Trial",
        "intro": (
            "Lab-only shadow path that consumes prompt_input_candidate evidence and runs bounded findings generation "
            "without touching production narrative runtime."
        ),
        "source_manifest_path": str(SHADOW_SOURCE_MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "trial_dir": str(SHADOW_TRIAL_DIR.relative_to(PROJECT_ROOT)),
        "selected_run_id": selected_run,
        "selected_source_mode": selected_source_mode,
        "available_runs": sorted(deduped_runs, key=lambda x: x["run_id"], reverse=True),
        "last_run": last_run,
        "artifacts": {
            "request_manifest": request_manifest,
            "raw_outputs": raw_outputs,
            "comparison": comparison,
            "cost_observation": cost,
            "review": review,
        },
        "summary": {
            "executed": comparison.get("executed"),
            "trial_pass": comparison.get("trial_pass"),
            "requests_executed": comparison.get("requests_executed"),
            "requests_skipped": comparison.get("requests_skipped"),
            "parse_failures_unrecovered": comparison.get("parse_failures_unrecovered"),
            "pass_flags": comparison.get("pass_flags", {}),
        },
        "per_case_rows": per_case_rows,
        "dimension_overview": dimension_overview,
        "findings_sections": findings_sections,
    }


def _recent_brand_runs(limit: int = 20) -> list[dict[str, Any]]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        rows = store.list_runs(limit=limit)
    finally:
        store.close()
    out: list[dict[str, Any]] = []
    for row in rows:
        rid = row.get("id")
        if rid is None:
            continue
        brand = str(row.get("brand_name") or "unknown")
        out.append(
            {
                "run_id": int(rid),
                "label": f"{brand} (run {int(rid)})",
            }
        )
    return out


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _slugify(value: str) -> str:
    out = []
    last_dash = False
    for char in value.lower():
        if char.isalnum():
            out.append(char)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-") or "case"
