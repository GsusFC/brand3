"""Evidence worker for the parallel SV9 Flow."""

from __future__ import annotations

import json
from typing import Any

from src.sv9_flow._utils import feature_confidence, first_string, unique_strings
from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord


def build_evidence_pack_from_snapshot(
    snapshot: dict[str, Any],
    *,
    visual_signature_evidence: dict[str, Any] | None = None,
) -> BrandEvidencePack:
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    brand_name = str(run.get("brand_name") or snapshot.get("brand_name") or "")
    url = str(run.get("url") or snapshot.get("url") or "")
    limitations: list[str] = []
    records: list[EvidenceRecord] = []

    if not snapshot:
        limitations.append("missing_snapshot")
    if not brand_name:
        limitations.append("missing_brand_name")
    if not url:
        limitations.append("missing_url")

    records.extend(_evidence_from_raw_inputs(snapshot.get("raw_inputs") or []))
    records.extend(_evidence_from_features(snapshot.get("features") or []))
    records.extend(_evidence_from_visual_signature(visual_signature_evidence))

    if not records:
        limitations.append("no_evidence_records")

    return BrandEvidencePack(
        brand_name=brand_name,
        url=url,
        evidence=records,
        limitations=unique_strings(limitations),
    )


def _evidence_from_raw_inputs(raw_inputs: list[Any]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for index, row in enumerate(raw_inputs):
        entry = row if isinstance(row, dict) else {}
        source = str(entry.get("source") or f"raw_input_{index}")
        payload = _payload_dict(entry)
        url = first_string(payload.get("url"), payload.get("source_url"), payload.get("page_url"))
        text = _summarize_payload(payload)
        if not text:
            continue
        records.append(
            EvidenceRecord(
                ref=f"raw_inputs.{index}",
                source=source,
                evidence_type="raw_input",
                content=text,
                url=url,
                confidence="medium",
            )
        )
    return records


def _evidence_from_features(features: list[Any]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for index, row in enumerate(features):
        feature = row if isinstance(row, dict) else {}
        feature_name = str(feature.get("feature_name") or "")
        dimension_name = str(feature.get("dimension_name") or "")
        if not feature_name and not dimension_name:
            continue
        value = feature.get("raw_value") or feature.get("value")
        content = str(value or "").strip()
        if not content:
            continue
        records.append(
            EvidenceRecord(
                ref=f"features.{index}",
                source="legacy_feature",
                evidence_type=f"{dimension_name}.{feature_name}".strip("."),
                content=content[:700],
                confidence=feature_confidence(feature.get("confidence")),
            )
        )
    return records


def _evidence_from_visual_signature(evidence: dict[str, Any] | None) -> list[EvidenceRecord]:
    if not isinstance(evidence, dict):
        return []
    if evidence.get("schema_version") != "visual-signature-evidence-v1":
        return []
    records: list[EvidenceRecord] = []
    capture = evidence.get("capture") if isinstance(evidence.get("capture"), dict) else {}
    records.append(
        EvidenceRecord(
            ref="visual_signature.capture",
            source="visual_signature",
            evidence_type="visual_capture",
            content=f"capture_status={capture.get('status')}; first_fold_evaluable={capture.get('first_fold_evaluable')}",
            confidence="medium",
            metadata={"capture": capture},
        )
    )
    for index, tile_signal in enumerate(evidence.get("tile_signals") or []):
        if not isinstance(tile_signal, dict):
            continue
        records.append(
            EvidenceRecord(
                ref=f"visual_signature.tile_signals.{index}",
                source="visual_signature",
                evidence_type="visual_tile_signal",
                content=str(tile_signal.get("rationale") or tile_signal.get("effect") or "")[:700],
                confidence=feature_confidence(tile_signal.get("confidence")),
                metadata={
                    "tile": tile_signal.get("tile"),
                    "effect": tile_signal.get("effect"),
                    "source": tile_signal.get("source"),
                },
            )
        )
    return records


def _payload_dict(entry: dict[str, Any]) -> dict[str, Any]:
    payload = entry.get("payload")
    if isinstance(payload, dict):
        return payload
    payload_json = entry.get("payload_json")
    if isinstance(payload_json, str):
        try:
            parsed = json.loads(payload_json)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _summarize_payload(payload: dict[str, Any]) -> str:
    for key in ("text", "content", "markdown", "summary", "title"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:700]
    if payload:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:700]
    return ""
