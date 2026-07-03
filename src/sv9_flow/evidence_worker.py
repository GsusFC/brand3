"""Evidence worker for the parallel SV9 Flow."""

from __future__ import annotations

import json
from typing import Any

from src.sv9_flow.evidence_source import classify_source
from src.sv9_flow._utils import feature_confidence, first_string, unique_strings
from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord

_RAW_INPUT_CONTENT_CHARS = 700
_WEB_CHUNK_CHARS = 900
_WEB_CHUNK_OVERLAP = 100
_MAX_WEB_SUBPAGE_CHUNKS = 6
_BOILERPLATE_MIN_PAGES = 3


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

    raw_records, duplicate_count = _dedup_raw_input_records(
        _evidence_from_raw_inputs(snapshot.get("raw_inputs") or [])
    )
    records.extend(raw_records)
    records.extend(_evidence_from_features(snapshot.get("features") or []))
    records.extend(_evidence_from_visual_signature(visual_signature_evidence))

    if duplicate_count:
        limitations.append(f"deduplicated_raw_input_records:{duplicate_count}")
    if not records:
        limitations.append("no_evidence_records")

    return BrandEvidencePack(
        brand_name=brand_name,
        url=url,
        evidence=records,
        limitations=unique_strings(limitations),
    )


def _dedup_raw_input_records(records: list[EvidenceRecord]) -> tuple[list[EvidenceRecord], int]:
    """Drop raw-input records whose text already appeared under another ref.

    Multi-pass captures re-fetch the same pages; identical text would waste
    block shortlist slots (capped at 5 refs), so only the first occurrence
    stays citable and keeps the duplicate refs in its metadata.
    """

    kept: list[EvidenceRecord] = []
    first_by_content: dict[str, EvidenceRecord] = {}
    dropped = 0
    for record in records:
        key = " ".join(record.content.split()).lower()
        if not key:
            kept.append(record)
            continue
        existing = first_by_content.get(key)
        if existing is None:
            first_by_content[key] = record
            kept.append(record)
            continue
        dropped += 1
        duplicate_refs = existing.metadata.setdefault("duplicate_refs", [])
        if len(duplicate_refs) < 5:
            duplicate_refs.append(record.ref)
    return kept, dropped


def _evidence_from_raw_inputs(raw_inputs: list[Any]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for index, row in enumerate(raw_inputs):
        entry = row if isinstance(row, dict) else {}
        source = str(entry.get("source") or f"raw_input_{index}")
        payload = _payload_dict(entry)
        if source == "web":
            records.extend(_evidence_from_web_payload(index=index, source=source, payload=payload))
            continue
        url = first_string(payload.get("url"), payload.get("source_url"), payload.get("page_url"))
        text = _summarize_payload(payload)
        if not text:
            continue
        records.append(_raw_input_record(index=index, source=source, content=text, url=url))
    return records


def _evidence_from_web_payload(*, index: int, source: str, payload: dict[str, Any]) -> list[EvidenceRecord]:
    text = _summarize_payload(payload, limit=None)
    if not text:
        return []
    url = first_string(payload.get("url"), payload.get("source_url"), payload.get("page_url"))
    homepage, subpages = _split_web_subpages(text)
    subpages = _strip_cross_page_boilerplate(homepage, subpages)
    records: list[EvidenceRecord] = []
    if homepage:
        records.append(_raw_input_record(index=index, source=source, content=homepage[:_RAW_INPUT_CONTENT_CHARS], url=url))
    for subpage_index, (subpage_url, subpage_text) in enumerate(subpages, start=1):
        for chunk_index, chunk in enumerate(_chunk_text(subpage_text), start=1):
            records.append(
                _raw_input_record(
                    index=index,
                    source=source,
                    content=chunk,
                    url=subpage_url or url,
                    ref=f"raw_inputs.{index}.subpage.{subpage_index}.chunk.{chunk_index}",
                    metadata={"subpage_url": subpage_url},
                )
            )
    return records


def _raw_input_record(
    *,
    index: int,
    source: str,
    content: str,
    url: str = "",
    ref: str = "",
    metadata: dict[str, Any] | None = None,
) -> EvidenceRecord:
    record_ref = ref or f"raw_inputs.{index}"
    trimmed = str(content or "").strip()[:_RAW_INPUT_CONTENT_CHARS]
    record_metadata = dict(metadata or {})
    record_metadata["source_class"] = classify_source(
        ref=record_ref,
        source=source,
        evidence_type="raw_input",
        content=trimmed,
    )
    return EvidenceRecord(
        ref=record_ref,
        source=source,
        evidence_type="raw_input",
        content=trimmed,
        url=url,
        confidence="medium",
        metadata=record_metadata,
    )


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
        ref = f"features.{index}"
        evidence_type = f"{dimension_name}.{feature_name}".strip(".")
        records.append(
            EvidenceRecord(
                ref=ref,
                source="legacy_feature",
                evidence_type=evidence_type,
                content=content[:700],
                confidence=feature_confidence(feature.get("confidence")),
                metadata={
                    "source_class": classify_source(
                        ref=ref,
                        source="legacy_feature",
                        evidence_type=evidence_type,
                        content=content[:700],
                    )
                },
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
            metadata={"capture": capture, "source_class": "visual_signal"},
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
                    "source_class": "visual_signal",
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


def _strip_cross_page_boilerplate(
    homepage: str,
    subpages: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Drop lines repeated across several captured pages from subpage text.

    Captures ingest shared chrome (nav menus, footers) on every page; those
    lines are template, not evidence, and their keyword noise outranks real
    strategy copy in block shortlists. The homepage keeps one copy untouched.
    """

    pages = [homepage] + [text for _, text in subpages]
    if len(pages) < _BOILERPLATE_MIN_PAGES:
        return subpages
    counts: dict[str, int] = {}
    for page in pages:
        for line in {_normalized_line(raw) for raw in page.splitlines()}:
            if line:
                counts[line] = counts.get(line, 0) + 1
    boilerplate = {line for line, count in counts.items() if count >= _BOILERPLATE_MIN_PAGES}
    if not boilerplate:
        return subpages
    cleaned: list[tuple[str, str]] = []
    for subpage_url, text in subpages:
        kept = [raw for raw in text.splitlines() if _normalized_line(raw) not in boilerplate]
        cleaned_text = "\n".join(kept).strip()
        if cleaned_text:
            cleaned.append((subpage_url, cleaned_text))
    return cleaned


def _normalized_line(line: str) -> str:
    return " ".join(line.split()).lower()


def _split_web_subpages(text: str) -> tuple[str, list[tuple[str, str]]]:
    marker = "\n---\n## Subpage: "
    if marker not in text:
        return text.strip(), []
    first, *raw_subpages = text.split(marker)
    subpages: list[tuple[str, str]] = []
    for raw_subpage in raw_subpages:
        lines = raw_subpage.splitlines()
        if not lines:
            continue
        subpage_url = lines[0].strip()
        subpage_text = "\n".join(lines[1:]).strip()
        if subpage_text and not _is_not_found_page(subpage_text):
            subpages.append((subpage_url, subpage_text))
    return first.strip(), subpages


def _is_not_found_page(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized:
        return False
    first_slice = normalized[:240]
    return (
        "404 not found" in first_slice
        or first_slice.startswith("not found the requested url was not found")
        or "the requested url was not found on this server" in first_slice
    )


def _chunk_text(text: str) -> list[str]:
    clean = str(text or "").strip()
    if not clean:
        return []
    chunks: list[str] = []
    step = max(1, _WEB_CHUNK_CHARS - _WEB_CHUNK_OVERLAP)
    for start in range(0, len(clean), step):
        chunk = clean[start : start + _WEB_CHUNK_CHARS].strip()
        if chunk:
            chunks.append(chunk)
        if len(chunks) >= _MAX_WEB_SUBPAGE_CHUNKS or start + _WEB_CHUNK_CHARS >= len(clean):
            break
    return chunks


def _summarize_payload(payload: dict[str, Any], *, limit: int | None = _RAW_INPUT_CONTENT_CHARS) -> str:
    for key in ("text", "content", "markdown", "markdown_content", "summary", "title"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if limit is None else text[:limit]
    if payload:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return text if limit is None else text[:limit]
    return ""
