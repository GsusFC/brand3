from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any
from urllib.parse import urlparse


NUMERIC_FIELDS = (
    "magnetism_score",
    "coherence_score",
    "brand3_score",
)


@dataclass(frozen=True)
class StabilityAuditOptions:
    min_repeats: int = 2
    days: int | None = None
    version: str | None = None
    limit_groups: int = 50
    group_by_day: bool = False


def analyze_scanner_stability(
    db_path: str | Path,
    *,
    options: StabilityAuditOptions | None = None,
) -> dict[str, Any]:
    opts = options or StabilityAuditOptions()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        samples = _load_samples(conn, opts)
    finally:
        conn.close()

    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        groups.setdefault(sample["group_key"], []).append(sample)

    group_reports = [
        _summarize_group(group_key, rows)
        for group_key, rows in groups.items()
        if len(rows) >= opts.min_repeats
    ]
    group_reports.sort(
        key=lambda item: (
            item["severity_rank"],
            item["max_numeric_range"],
            item["sample_count"],
        ),
        reverse=True,
    )
    if opts.limit_groups > 0:
        group_reports = group_reports[: opts.limit_groups]

    return {
        "schema_version": "scanner-stability-audit-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "options": {
            "min_repeats": opts.min_repeats,
            "days": opts.days,
            "version": opts.version,
            "limit_groups": opts.limit_groups,
            "group_by_day": opts.group_by_day,
        },
        "sample_count": len(samples),
        "repeated_group_count": len(group_reports),
        "unstable_group_count": sum(1 for group in group_reports if group["is_unstable"]),
        "groups": group_reports,
    }


def render_stability_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Scanner stability audit",
        "",
        f"- Samples: `{report['sample_count']}`",
        f"- Repeated groups: `{report['repeated_group_count']}`",
        f"- Unstable groups: `{report['unstable_group_count']}`",
        "",
    ]
    if not report["groups"]:
        lines.append("No repeated scanner groups found for the selected filters.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| group | scans | diagnosis | severity | max range | changing hashes | changing fields | score ranges |",
            "| --- | ---: | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for group in report["groups"]:
        score_ranges = ", ".join(
            f"{name}={stats['range']:.2f}"
            for name, stats in group["numeric_stats"].items()
            if stats["range"] > 0
        ) or "stable"
        changing_hashes = ", ".join(group["changing_hashes"]) or "stable"
        changing_fields = ", ".join(group["changing_fields"]) or "stable"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(group["display_name"]),
                    str(group["sample_count"]),
                    _md_cell(group["diagnosis_stage"]),
                    str(group["severity"]["rank"]),
                    f"{group['max_numeric_range']:.2f}",
                    _md_cell(changing_hashes),
                    _md_cell(changing_fields),
                    _md_cell(score_ranges),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _load_samples(conn: sqlite3.Connection, opts: StabilityAuditOptions) -> list[dict[str, Any]]:
    if not _table_exists(conn, "magnetism_scans"):
        return []

    where = ["status = 'ready'"]
    params: list[Any] = []
    if opts.days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=opts.days)
        where.append("created_at >= ?")
        params.append(cutoff.isoformat())
    query = f"""
        SELECT id, brand_name, url, magnetism_score, coherence_score, quadrant,
               raw_payload, created_at, source_run_id
        FROM magnetism_scans
        WHERE {' AND '.join(where)}
        ORDER BY created_at ASC, id ASC
    """
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    source_run_ids = {
        int(row["source_run_id"])
        for row in rows
        if row.get("source_run_id") is not None
    }
    sv9_by_run = (
        _load_sv9_by_source_run(conn, source_run_ids)
        if source_run_ids and _table_exists(conn, "sv9_scans")
        else {}
    )
    raw_inputs_by_run = (
        _load_raw_inputs_by_run(conn, source_run_ids)
        if source_run_ids and _table_exists(conn, "raw_inputs")
        else {}
    )

    samples: list[dict[str, Any]] = []
    for row in rows:
        payload = _loads_json(row.get("raw_payload"))
        sv9 = sv9_by_run.get(row.get("source_run_id")) or {}
        persisted_raw_inputs = raw_inputs_by_run.get(row.get("source_run_id"))
        raw_inputs = persisted_raw_inputs or _first_json_path(payload, _RAW_INPUT_PATHS)
        dimensions = _sample_dimensions(row, payload, sv9, opts, raw_inputs)
        version = dimensions["version_label"]
        if opts.version and opts.version.lower() not in version.lower():
            continue
        sample = {
            "scan_id": row["id"],
            "source_run_id": row.get("source_run_id"),
            "brand_name": row.get("brand_name") or "",
            "url": row.get("url") or "",
            "normalized_url": _normalize_url(row.get("url") or ""),
            "group_key": _group_key(dimensions),
            "group_dimensions": dimensions,
            "version": version,
            "created_day": dimensions["created_day"],
            "created_at": row.get("created_at"),
            "magnetism_score": _as_number(row.get("magnetism_score")),
            "coherence_score": _as_number(row.get("coherence_score")),
            "quadrant": row.get("quadrant") or "",
            "payload_magnetism_score": _as_number(payload.get("magnetism_score")),
            "payload_coherence_score": _as_number(payload.get("coherence_score")),
            "payload_quadrant": payload.get("quadrant") or "",
            "brand3_score": _as_number(sv9.get("brand3_score")),
            "sv9_scan_id": sv9.get("id"),
            "sv9_rubric_version": sv9.get("rubric_version"),
            "sv9_reliability_status": sv9.get("reliability_status"),
            "hashes": {
                "raw_payload_hash": _stable_hash(payload),
                "raw_inputs_hash": _stable_hash(raw_inputs),
                "research_pack_hash": _stable_hash(_first_json_path(payload, _RESEARCH_PACK_PATHS)),
                "analyst_tldr_hash": _stable_hash(_first_json_path(payload, _ANALYST_TLDR_PATHS)),
                "result_tldr_hash": _stable_hash(_first_json_path(payload, _RESULT_TLDR_PATHS)),
                "sv9_components_hash": _stable_hash(sv9.get("components")),
                "sv9_component_scores_hash": _stable_hash(_component_score_fingerprint(sv9.get("components"))),
            },
        }
        samples.append(sample)
    return samples


def _load_raw_inputs_by_run(
    conn: sqlite3.Connection,
    source_run_ids: set[int],
) -> dict[int, list[dict[str, Any]]]:
    if not source_run_ids:
        return {}
    placeholders = _placeholders(source_run_ids)
    rows = conn.execute(
        f"""
        SELECT run_id, source, payload_json
        FROM raw_inputs
        WHERE run_id IN ({placeholders})
        ORDER BY run_id ASC, source ASC, id ASC
        """,
        sorted(source_run_ids),
    ).fetchall()
    by_run: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_run.setdefault(int(row["run_id"]), []).append(
            {
                "source": row["source"],
                "payload": _loads_json(row["payload_json"]),
            }
        )
    return by_run


def _load_sv9_by_source_run(
    conn: sqlite3.Connection,
    source_run_ids: set[int],
) -> dict[int, dict[str, Any]]:
    if not source_run_ids:
        return {}
    placeholders = _placeholders(source_run_ids)
    rows = conn.execute(
        f"""
        SELECT *
        FROM sv9_scans
        WHERE source_run_id IS NOT NULL
          AND source_run_id IN ({placeholders})
        ORDER BY created_at ASC, id ASC
        """,
        sorted(source_run_ids),
    ).fetchall()
    by_run: dict[int, dict[str, Any]] = {}
    has_components = _table_exists(conn, "sv9_component_scores")
    for row in rows:
        payload = dict(row)
        if has_components:
            component_rows = conn.execute(
                "SELECT * FROM sv9_component_scores WHERE scan_id = ? ORDER BY component ASC, id ASC",
                (payload["id"],),
            ).fetchall()
            payload["components"] = [_component_row_to_dict(component) for component in component_rows]
        by_run[int(payload["source_run_id"])] = payload
    return by_run


def _summarize_group(group_key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_stats = {
        field: stats
        for field in NUMERIC_FIELDS
        if (stats := _numeric_stats([row.get(field) for row in rows])) is not None
    }
    changing_hashes = [
        name
        for name in sorted({key for row in rows for key in row["hashes"]})
        if len({row["hashes"].get(name) for row in rows if row["hashes"].get(name)}) > 1
    ]
    changing_fields = [
        field
        for field in ("quadrant", "sv9_reliability_status")
        if len({row.get(field) for row in rows if row.get(field) not in (None, "")}) > 1
    ]
    if any(_has_payload_storage_mismatch(row) for row in rows):
        changing_fields.append("storage_payload_mismatch")
    max_numeric_range = max((stats["range"] for stats in numeric_stats.values()), default=0.0)
    diagnosis_stage = _diagnosis_stage(changing_hashes, numeric_stats, changing_fields)
    severity = _severity(diagnosis_stage, max_numeric_range, changing_hashes, changing_fields, numeric_stats)
    examples = [
        {
            "scan_id": row["scan_id"],
            "source_run_id": row["source_run_id"],
            "created_at": row["created_at"],
            "magnetism_score": row["magnetism_score"],
            "coherence_score": row["coherence_score"],
            "brand3_score": row["brand3_score"],
            "quadrant": row["quadrant"],
            "payload_magnetism_score": row["payload_magnetism_score"],
            "payload_coherence_score": row["payload_coherence_score"],
            "payload_quadrant": row["payload_quadrant"],
            "hashes": row["hashes"],
        }
        for row in rows
    ]
    return {
        "group_key": group_key,
        "display_name": _display_name(rows[0]),
        "sample_count": len(rows),
        "brand_name": rows[0]["brand_name"],
        "url": rows[0]["url"],
        "version": rows[0]["version"],
        "group_dimensions": rows[0]["group_dimensions"],
        "created_days": sorted({row["created_day"] for row in rows if row.get("created_day")}),
        "first_seen": min(row["created_at"] for row in rows if row.get("created_at")),
        "last_seen": max(row["created_at"] for row in rows if row.get("created_at")),
        "numeric_stats": numeric_stats,
        "max_numeric_range": max_numeric_range,
        "changing_hashes": changing_hashes,
        "changing_fields": changing_fields,
        "diagnosis_stage": diagnosis_stage,
        "likely_layer": diagnosis_stage,
        "severity": severity,
        "severity_rank": severity["rank"],
        "is_unstable": bool(changing_hashes or changing_fields or max_numeric_range > 0),
        "examples": examples,
    }


def _diagnosis_stage(
    changing_hashes: list[str],
    numeric_stats: dict[str, dict[str, float]],
    changing_fields: list[str],
) -> str:
    changing = set(changing_hashes)
    score_changed = any(stats["range"] > 0 for stats in numeric_stats.values())
    if "storage_payload_mismatch" in changing_fields:
        return "persistence_drift"
    if "raw_inputs_hash" in changing:
        return "acquisition_drift"
    if "research_pack_hash" in changing:
        return "evidence_pack_drift"
    if {"analyst_tldr_hash", "result_tldr_hash"} & changing:
        return "interpretation_drift"
    if {"sv9_components_hash", "sv9_component_scores_hash"} & changing or score_changed:
        return "scoring_drift"
    if changing_fields:
        return "presentation_drift"
    if "raw_payload_hash" in changing:
        return "non_critical_payload_drift"
    return "stable"


def _severity(
    stage: str,
    max_numeric_range: float,
    changing_hashes: list[str],
    changing_fields: list[str],
    numeric_stats: dict[str, dict[str, float]],
) -> dict[str, Any]:
    changing = set(changing_hashes)
    score_changed = any(stats["range"] > 0 for stats in numeric_stats.values())
    reasons: list[str] = []
    if stage == "persistence_drift":
        reasons.append("stored_columns_disagree_with_raw_payload")
    if score_changed and not ({"raw_inputs_hash", "research_pack_hash", "analyst_tldr_hash", "result_tldr_hash"} & changing):
        reasons.append("same_raw_research_tldr_but_score_changed")
    if score_changed and {"analyst_tldr_hash", "result_tldr_hash"} & changing and not ({"raw_inputs_hash", "research_pack_hash"} & changing):
        reasons.append("same_raw_research_but_tldr_and_score_changed")
    if "quadrant" in changing_fields:
        reasons.append("quadrant_changed")
    if "raw_inputs_hash" in changing:
        reasons.append("raw_inputs_changed")
    if "research_pack_hash" in changing:
        reasons.append("research_pack_changed")

    base = {
        "persistence_drift": 6,
        "scoring_drift": 6,
        "interpretation_drift": 5,
        "evidence_pack_drift": 4,
        "acquisition_drift": 4,
        "presentation_drift": 3,
        "non_critical_payload_drift": 1,
        "stable": 0,
    }.get(stage, 0)
    rank = base + (1 if max_numeric_range >= 10 else 0)
    label = "critical" if rank >= 6 else "high" if rank >= 5 else "medium" if rank >= 3 else "low" if rank else "none"
    return {
        "rank": rank,
        "label": label,
        "reasons": reasons,
    }


def _numeric_stats(values: list[Any]) -> dict[str, float] | None:
    nums = [_as_number(value) for value in values]
    nums = [num for num in nums if num is not None]
    if not nums:
        return None
    return {
        "min": min(nums),
        "max": max(nums),
        "range": max(nums) - min(nums),
        "mean": mean(nums),
        "pstdev": pstdev(nums) if len(nums) > 1 else 0.0,
    }


def _group_key(dimensions: dict[str, str]) -> str:
    keys = (
        "identity",
        "scanner_version",
        "rubric_version",
        "model_versions",
        "lang",
        "visual_signature_version",
        "tldr_prompt_version",
        "research_pack_builder_version",
        "exa_strategy",
        "capture_strategy",
        "created_day_bucket",
    )
    return "|".join(str(dimensions.get(key) or "unknown") for key in keys)


def _display_name(row: dict[str, Any]) -> str:
    label = row.get("brand_name") or row.get("normalized_url") or row.get("url") or "unknown"
    return f"{label} [{row.get('version') or 'unknown-version'}]"


def _sample_version(payload: dict[str, Any], sv9: dict[str, Any]) -> str:
    candidates = [
        sv9.get("rubric_version"),
        sv9.get("model"),
        sv9.get("evaluator_model"),
        _first_json_path(payload, _VERSION_PATHS),
    ]
    parts = [str(value) for value in candidates if value not in (None, "", [], {})]
    return "+".join(parts) if parts else "unknown-version"


def _sample_dimensions(
    row: dict[str, Any],
    payload: dict[str, Any],
    sv9: dict[str, Any],
    opts: StabilityAuditOptions,
    raw_inputs: Any,
) -> dict[str, str]:
    created_day = _created_day(row.get("created_at"))
    scanner_version = str(_first_json_path(payload, _SCANNER_VERSION_PATHS) or "unknown")
    rubric_version = str(sv9.get("rubric_version") or _first_json_path(payload, _RUBRIC_VERSION_PATHS) or "unknown")
    model_versions = "+".join(
        str(value)
        for value in (
            sv9.get("model"),
            sv9.get("evaluator_model"),
            _first_json_path(payload, _MODEL_VERSION_PATHS),
        )
        if value not in (None, "", [], {})
    ) or "unknown"
    return {
        "identity": _normalize_url(row.get("url") or "") or _normalize_text(row.get("brand_name") or ""),
        "normalized_brand_or_url": _normalize_url(row.get("url") or "") or _normalize_text(row.get("brand_name") or ""),
        "scanner_version": scanner_version,
        "rubric_version": rubric_version,
        "model_versions": model_versions,
        "lang": str(_first_json_path(payload, _LANG_PATHS) or "unknown"),
        "visual_signature_version": str(_first_json_path(payload, _VISUAL_SIGNATURE_VERSION_PATHS) or "unknown"),
        "tldr_prompt_version": str(_first_json_path(payload, _TLDR_PROMPT_VERSION_PATHS) or "unknown"),
        "research_pack_builder_version": str(_first_json_path(payload, _RESEARCH_PACK_BUILDER_VERSION_PATHS) or "unknown"),
        "exa_strategy": str(_exa_strategy(raw_inputs, payload) or "unknown"),
        "capture_strategy": str(_first_json_path(payload, _CAPTURE_STRATEGY_PATHS) or "unknown"),
        "created_day": created_day,
        "created_day_bucket": created_day if opts.group_by_day else "all",
        "version_label": _sample_version(payload, sv9),
    }


def _component_score_fingerprint(components: Any) -> list[dict[str, Any]]:
    if not isinstance(components, list):
        return []
    return [
        {
            "component": item.get("component"),
            "score": item.get("score"),
            "points": item.get("points"),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
            "veredicto": item.get("veredicto"),
        }
        for item in components
        if isinstance(item, dict)
    ]


def _has_payload_storage_mismatch(row: dict[str, Any]) -> bool:
    comparisons = (
        ("magnetism_score", "payload_magnetism_score"),
        ("coherence_score", "payload_coherence_score"),
        ("quadrant", "payload_quadrant"),
    )
    for stored_key, payload_key in comparisons:
        stored = row.get(stored_key)
        payload = row.get(payload_key)
        if payload in (None, ""):
            continue
        if stored != payload:
            return True
    return False


def _component_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    for key in ("tile_profile_json", "rung_profile_json", "evidence_json"):
        if key in payload:
            payload[key] = _loads_json(payload[key])
    return payload


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _placeholders(values: set[int]) -> str:
    return ",".join("?" for _ in values)


def _normalize_url(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.strip("/")
    if path and parsed.netloc:
        return f"{host}/{path}".rstrip("/")
    return host.rstrip("/")


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _created_day(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    return value.strip().replace("T", " ").split(" ", 1)[0]


def _loads_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _stable_hash(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _first_json_path(payload: Any, paths: tuple[tuple[str, ...], ...]) -> Any:
    for path in paths:
        value = _json_path(payload, path)
        if value not in (None, "", [], {}):
            return value
    return None


def _exa_strategy(raw_inputs: Any, payload: dict[str, Any]) -> Any:
    exa_payload = _raw_input_payload(raw_inputs, "exa")
    return _first_json_path(exa_payload, _EXA_STRATEGY_PATHS) or _first_json_path(payload, _EXA_STRATEGY_PATHS)


def _raw_input_payload(raw_inputs: Any, source: str) -> Any:
    if isinstance(raw_inputs, list):
        for item in raw_inputs:
            if not isinstance(item, dict) or item.get("source") != source:
                continue
            payload = item.get("payload")
            if payload is not None:
                return payload
            payload_json = item.get("payload_json")
            if payload_json is not None:
                return _loads_json(payload_json)
    if isinstance(raw_inputs, dict):
        payload = raw_inputs.get(source)
        if isinstance(payload, dict) and "payload" in payload:
            return payload.get("payload")
        return payload
    return None


def _json_path(payload: Any, path: tuple[str, ...]) -> Any:
    value = payload
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


_RAW_INPUT_PATHS = (
    ("debug", "raw_inputs"),
    ("audit_snapshot", "debug", "raw_inputs"),
    ("audit", "raw_inputs"),
    ("raw_inputs",),
)
_RESEARCH_PACK_PATHS = (
    ("debug", "normalized_payload", "research_pack"),
    ("normalized_payload", "research_pack"),
    ("research_pack",),
)
_ANALYST_TLDR_PATHS = (
    ("debug", "normalized_payload", "analyst_tldr_validated"),
    ("normalized_payload", "analyst_tldr_validated"),
    ("analyst_tldr_validated",),
)
_RESULT_TLDR_PATHS = (
    ("tldr_brand3",),
    ("result", "tldr_brand3"),
    ("debug", "normalized_payload", "tldr_brand3"),
)
_VERSION_PATHS = (
    ("scanner_version",),
    ("version",),
    ("schema_version",),
    ("debug", "normalized_payload", "schema_version"),
    ("debug", "normalized_payload", "version"),
    ("scan_mode", "mode"),
)
_SCANNER_VERSION_PATHS = (
    ("scanner_version",),
    ("version",),
    ("schema_version",),
    ("scan_mode", "mode"),
)
_RUBRIC_VERSION_PATHS = (
    ("rubric_version",),
    ("sv9", "rubric_version"),
    ("metrics", "rubric_version"),
)
_MODEL_VERSION_PATHS = (
    ("model",),
    ("evaluator_model",),
    ("metrics", "model"),
    ("debug", "normalized_payload", "model"),
)
_LANG_PATHS = (
    ("lang",),
    ("language",),
    ("request", "lang"),
)
_VISUAL_SIGNATURE_VERSION_PATHS = (
    ("visual_signature_version",),
    ("metrics", "visual_signature_version"),
    ("visual_signature", "version"),
)
_TLDR_PROMPT_VERSION_PATHS = (
    ("tldr_prompt_version",),
    ("analyst_tldr_raw", "prompt_version"),
    ("analyst_tldr_validated", "prompt_version"),
    ("debug", "normalized_payload", "tldr_prompt_version"),
)
_RESEARCH_PACK_BUILDER_VERSION_PATHS = (
    ("research_pack_builder_version",),
    ("research_pack", "builder_version"),
    ("research_pack", "version"),
    ("evidence_graph_summary", "version"),
)
_EXA_STRATEGY_PATHS = (
    ("diagnostics", "strategy"),
    ("exa", "diagnostics", "strategy"),
    ("raw_inputs", "exa", "diagnostics", "strategy"),
)
_CAPTURE_STRATEGY_PATHS = (
    ("capture_strategy",),
    ("source",),
    ("research_pack_source",),
    ("canonical_evidence_source",),
)
