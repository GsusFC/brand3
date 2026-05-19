"""Offline diagnostics for Brand3 report narrative payloads.

The harness is intentionally read-only. It does not call LLMs, mutate report
payloads, persist diagnostics, change scoring, or participate in rendering.
"""

from __future__ import annotations

import re
from html import unescape
from collections import Counter
from typing import Any

VERSION = 1

GENERIC_FILLER_PHRASES = (
    "strong positioning",
    "compelling",
    "robust",
    "world-class",
    "best-in-class",
    "sophisticated",
    "premier",
    "successful",
    "innovative",
    "leading platform",
    "teams in this position typically",
)

UNSUPPORTED_PRESCRIPTION_PHRASES = (
    "the brand should",
    "needs to",
    "must",
    "the right move is",
    "should focus on",
    "should prioritize",
)

SAFE_ATTRIBUTION_PHRASES = (
    "the brand describes itself",
    "the brand says",
    "the brand claims",
    "based only on self-description",
)

SAFE_ATTRIBUTION_OVERUSE_THRESHOLD = 3
OBSERVATION_REPETITION_FAMILY_THRESHOLD = 3

OBSERVATION_REPETITION_FAMILIES = {
    "safe_attribution_repetition": (
        "the brand describes itself",
        "the brand claims",
        "based only on self-description",
    ),
    "fallback_evidence_opening_repetition": (
        "the available sources",
        "available evidence",
        "the evidence pool",
    ),
    "external_corroboration_caveat_repetition": (
        "no external corroboration",
        "without external corroboration",
        "based only on self-description",
    ),
}

SELF_DESCRIPTION_VALIDATION_PATTERNS = (
    r"\bthe brand is (?:a |an |the )?(?:leading|premier|best|top)\b",
    r"\bthe brand has established\b",
    r"\bthe brand demonstrates\b",
    r"\bthe brand proves\b",
    r"\bthe brand validates\b",
    r"\bthe brand is recognized as\b",
    r"\bpositions itself successfully\b",
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def audit_report_narrative_payload(
    payload: dict,
    *,
    base_dossier: dict | None = None,
) -> dict:
    """Return a stable diagnostic dict for an existing report narrative payload."""
    safe_payload = payload if isinstance(payload, dict) else {}
    findings = _flatten_findings(safe_payload.get("findings_by_dimension"))
    synthesis = _clean_text(
        safe_payload.get("synthesis_prose") or safe_payload.get("summary") or ""
    )
    tension = _clean_text(safe_payload.get("tensions_prose") or "")

    checks = [
        _check_repeated_sentence_openings(findings),
        _check_generic_filler(synthesis, tension, findings),
        _check_unsupported_prescriptions(synthesis, tension, findings),
        _check_missing_evidence_urls(findings),
        _check_self_description_validation(synthesis, tension, findings),
        _check_safe_attribution_overuse(synthesis, tension, findings),
        _check_observation_repetition_families(findings),
        _check_synthesis_tension_mismatch(synthesis, tension),
    ]
    metrics = _build_metrics(synthesis, tension, findings, checks)
    summary = _build_summary(checks)

    return {
        "version": VERSION,
        "status": _overall_status(summary),
        "summary": summary,
        "checks": checks,
        "metrics": metrics,
        "input_metadata": _input_metadata(safe_payload, base_dossier, findings),
    }


def audit_report_narrative_render(
    payload: dict,
    rendered_output: str,
    *,
    base_dossier: dict | None = None,
    rendered_as_html: bool = True,
) -> dict:
    """Compare payload-level narrative risk with visible rendered risk.

    This is an offline diagnostic helper. It accepts already-rendered HTML or
    text and never calls renderers, LLMs, storage, scoring, or runtime hooks.
    """
    payload_diagnostic = audit_report_narrative_payload(
        payload,
        base_dossier=base_dossier,
    )
    visible_text = _rendered_text(rendered_output, rendered_as_html=rendered_as_html)
    visible_metrics = _build_visible_render_metrics(visible_text, rendered_output)
    payload_metrics = payload_diagnostic["metrics"]
    suppressed = _suppressed_by_rendering(payload_metrics, visible_metrics)
    still_visible = _still_visible_risks(visible_metrics)
    summary = {
        "payload_status": payload_diagnostic["status"],
        "visible_render_status": "warning" if still_visible else "pass",
        "suppressed_risk_count": len(suppressed),
        "still_visible_risk_count": len(still_visible),
    }
    return {
        "version": VERSION,
        "status": "warning" if payload_diagnostic["status"] == "warning" or still_visible else "pass",
        "summary": summary,
        "payload_metrics": payload_metrics,
        "visible_render_metrics": visible_metrics,
        "suppressed_by_rendering": suppressed,
        "still_visible_risks": still_visible,
        "payload_diagnostic_summary": payload_diagnostic["summary"],
        "input_metadata": {
            **payload_diagnostic["input_metadata"],
            "rendered_as_html": rendered_as_html,
            "visible_text_chars": len(visible_text),
        },
    }


def _flatten_findings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    out: list[dict[str, Any]] = []
    for dimension, raw_findings in value.items():
        if not isinstance(raw_findings, list):
            continue
        for index, item in enumerate(raw_findings):
            if not isinstance(item, dict):
                continue
            finding = {
                "dimension": str(dimension),
                "index": index,
                "title": _clean_text(item.get("title") or ""),
                "observation": _clean_text(item.get("observation") or item.get("prose") or ""),
                "implication": _clean_text(item.get("implication") or ""),
                "typical_decision": _clean_text(item.get("typical_decision") or ""),
                "evidence_urls": [
                    str(url)
                    for url in (item.get("evidence_urls") or [])
                    if isinstance(url, str) and url.strip()
                ],
            }
            out.append(finding)
    return out


def _check_repeated_sentence_openings(findings: list[dict[str, Any]]) -> dict:
    openings: list[tuple[str, str, str]] = []
    for finding in findings:
        for field in ("observation", "implication", "typical_decision"):
            text = finding.get(field) or ""
            opening = _sentence_opening(text)
            if opening:
                path = _finding_path(finding, field)
                openings.append((opening, path, _excerpt(text)))

    counts = Counter(opening for opening, _, _ in openings)
    repeated = {opening: count for opening, count in counts.items() if count >= 3}
    evidence = [
        {"path": path, "excerpt": excerpt, "opening": opening}
        for opening, path, excerpt in openings
        if opening in repeated
    ]
    if repeated:
        return _check(
            "repeated_sentence_openings",
            "warning",
            "warning",
            "Repeated sentence openings detected across narrative fields.",
            evidence,
        )
    return _check(
        "repeated_sentence_openings",
        "warning",
        "pass",
        "No repeated sentence opening exceeded the v1 threshold.",
        [],
    )


def _check_generic_filler(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
) -> dict:
    matches = _phrase_matches(_all_text_items(synthesis, tension, findings), GENERIC_FILLER_PHRASES)
    if matches:
        return _check(
            "generic_strategic_filler",
            "warning",
            "warning",
            "Generic strategic filler phrases were detected.",
            matches,
        )
    return _check(
        "generic_strategic_filler",
        "warning",
        "pass",
        "No configured generic strategic filler phrases were detected.",
        [],
    )


def _check_unsupported_prescriptions(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
) -> dict:
    matches = _phrase_matches(
        _all_text_items(synthesis, tension, findings),
        UNSUPPORTED_PRESCRIPTION_PHRASES,
    )
    if matches:
        return _check(
            "unsupported_prescription_language",
            "warning",
            "warning",
            "Potentially unsupported prescription language was detected.",
            matches,
        )
    return _check(
        "unsupported_prescription_language",
        "warning",
        "pass",
        "No configured unsupported prescription phrases were detected.",
        [],
    )


def _check_missing_evidence_urls(findings: list[dict[str, Any]]) -> dict:
    evidence = []
    for finding in findings:
        has_text = any(
            finding.get(field)
            for field in ("observation", "implication", "typical_decision")
        )
        if has_text and not finding.get("evidence_urls"):
            evidence.append(
                {
                    "path": _finding_path(finding, "evidence_urls"),
                    "excerpt": _excerpt(finding.get("observation") or finding.get("title") or ""),
                }
            )

    if evidence:
        return _check(
            "missing_evidence_urls",
            "warning",
            "warning",
            "Findings with narrative text and no evidence URLs were detected.",
            evidence,
        )
    return _check(
        "missing_evidence_urls",
        "warning",
        "pass",
        "All findings with narrative text include at least one evidence URL.",
        [],
    )


def _check_self_description_validation(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
) -> dict:
    items = _all_text_items(synthesis, tension, findings)
    evidence = []
    for item in items:
        text = item["text"]
        lowered = text.lower()
        if "the brand describes itself" in lowered or "the brand says" in lowered:
            continue
        for pattern in SELF_DESCRIPTION_VALIDATION_PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                evidence.append(
                    {
                        "path": item["path"],
                        "excerpt": _excerpt(text),
                        "pattern": pattern,
                    }
                )
                break

    if evidence:
        return _check(
            "self_description_as_validation",
            "warning",
            "warning",
            "Potential self-description validation language was detected.",
            evidence,
        )
    return _check(
        "self_description_as_validation",
        "warning",
        "pass",
        "No configured self-description validation patterns were detected.",
        [],
    )


def _check_safe_attribution_overuse(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
) -> dict:
    """Warn when correct owned-claim attribution becomes structurally repetitive."""
    items = _all_text_items(synthesis, tension, findings)
    evidence = []
    total = 0
    for item in items:
        lowered = item["text"].lower()
        for phrase in SAFE_ATTRIBUTION_PHRASES:
            count = _count_phrase(lowered, phrase)
            if not count:
                continue
            total += count
            evidence.append(
                {
                    "path": item["path"],
                    "excerpt": _excerpt(item["text"]),
                    "phrase": phrase,
                    "count": count,
                }
            )

    if total >= SAFE_ATTRIBUTION_OVERUSE_THRESHOLD:
        return _check(
            "safe_attribution_overuse",
            "warning",
            "warning",
            "Safe attribution language is repeated enough to create a cohesion risk.",
            evidence,
        )
    return _check(
        "safe_attribution_overuse",
        "warning",
        "pass",
        "Safe attribution language stayed below the v1 overuse threshold.",
        [],
    )


def _check_observation_repetition_families(findings: list[dict[str, Any]]) -> dict:
    items = [
        {
            "path": _finding_path(finding, "observation"),
            "text": finding.get("observation") or "",
        }
        for finding in findings
        if finding.get("observation")
    ]
    family_counts = _repetition_family_counts(items)
    evidence = []
    for family, data in family_counts.items():
        if data["total"] < OBSERVATION_REPETITION_FAMILY_THRESHOLD:
            continue
        evidence.append(
            {
                "family": family,
                "total": data["total"],
                "phrase_counts": data["phrases"],
                "matches": data["matches"],
            }
        )

    if evidence:
        return _check(
            "observation_repetition_families",
            "warning",
            "warning",
            "Observation-level repetition families exceeded the v1 threshold.",
            evidence,
        )
    return _check(
        "observation_repetition_families",
        "warning",
        "pass",
        "Observation-level repetition families stayed below the v1 threshold.",
        [],
    )


def _check_synthesis_tension_mismatch(synthesis: str, tension: str) -> dict:
    if not synthesis or not tension:
        return _check(
            "synthesis_tension_lexical_mismatch",
            "warning",
            "pass",
            "Synthesis/tension comparison skipped because one side is empty.",
            [],
        )

    synthesis_tokens = _content_tokens(synthesis)
    tension_tokens = _content_tokens(tension)
    if not synthesis_tokens or not tension_tokens:
        return _check(
            "synthesis_tension_lexical_mismatch",
            "warning",
            "pass",
            "Synthesis/tension comparison skipped because content tokens were insufficient.",
            [],
        )

    overlap = synthesis_tokens & tension_tokens
    ratio = len(overlap) / max(1, min(len(synthesis_tokens), len(tension_tokens)))
    if ratio < 0.15:
        return _check(
            "synthesis_tension_lexical_mismatch",
            "warning",
            "warning",
            "Synthesis and tension share very little lexical signal.",
            [
                {
                    "path": "synthesis_prose + tensions_prose",
                    "excerpt": f"overlap_ratio={ratio:.2f}",
                    "shared_terms": sorted(overlap)[:12],
                }
            ],
        )
    return _check(
        "synthesis_tension_lexical_mismatch",
        "warning",
        "pass",
        "Synthesis and tension share enough lexical signal for v1.",
        [],
    )


def _build_visible_render_metrics(visible_text: str, rendered_output: str) -> dict:
    text = _clean_text(visible_text)
    text_items = [{"path": "visible_render", "text": text}] if text else []
    visible_blocks = _visible_narrative_blocks(rendered_output)
    visible_block_items = [
        {"path": f"visible_render.blocks[{index}]", "text": block}
        for index, block in enumerate(visible_blocks)
    ] or text_items
    generic_counts = {
        phrase: _count_phrase(text, phrase)
        for phrase in GENERIC_FILLER_PHRASES
    }
    generic_counts = {k: v for k, v in generic_counts.items() if v}
    safe_attribution_counts = {
        phrase: _count_phrase(text, phrase)
        for phrase in SAFE_ATTRIBUTION_PHRASES
    }
    safe_attribution_counts = {k: v for k, v in safe_attribution_counts.items() if v}
    opening_counts = _visible_sentence_opening_counts_from_blocks(visible_blocks or [text])
    repeated_opening_counts = {
        opening: count for opening, count in opening_counts.items() if count >= 3
    }
    return {
        "visible_text_chars": len(text),
        "visible_link_count": _visible_link_count(rendered_output),
        "visible_evidence_chip_link_count": _visible_evidence_chip_link_count(rendered_output),
        "visible_decision_space_count": _count_phrase(text, "decision space"),
        "visible_teams_in_this_position_typically_count": _count_phrase(
            text,
            "teams in this position typically",
        ),
        "visible_the_brand_count": _count_phrase(text, "the brand"),
        "visible_no_external_corroboration_count": _count_phrase(
            text,
            "no external corroboration",
        ),
        "sentence_opening_counts": dict(sorted(opening_counts.items())),
        "repeated_sentence_opening_counts": dict(sorted(repeated_opening_counts.items())),
        "generic_phrase_counts": generic_counts,
        "safe_attribution_phrase_counts": safe_attribution_counts,
        "safe_attribution_total": sum(safe_attribution_counts.values()),
        "observation_repetition_family_counts": _compact_family_counts(
            _repetition_family_counts(visible_block_items)
        ),
        "warning_signals": _visible_warning_signals(text_items, repeated_opening_counts),
    }


def _suppressed_by_rendering(payload_metrics: dict, visible_metrics: dict) -> list[dict]:
    suppressed = []
    payload_generic = payload_metrics.get("generic_phrase_counts") or {}
    visible_generic = visible_metrics.get("generic_phrase_counts") or {}
    for phrase, payload_count in sorted(payload_generic.items()):
        visible_count = int(visible_generic.get(phrase) or 0)
        if payload_count > visible_count:
            suppressed.append(
                {
                    "risk": "generic_strategic_filler",
                    "phrase": phrase,
                    "payload_count": payload_count,
                    "visible_count": visible_count,
                    "suppressed_count": payload_count - visible_count,
                }
            )
    payload_openings = payload_metrics.get("sentence_opening_counts") or {}
    visible_openings = visible_metrics.get("sentence_opening_counts") or {}
    for opening, payload_count in sorted(payload_openings.items()):
        visible_count = int(visible_openings.get(opening) or 0)
        if payload_count >= 3 and visible_count < payload_count:
            suppressed.append(
                {
                    "risk": "repeated_sentence_opening",
                    "opening": opening,
                    "payload_count": payload_count,
                    "visible_count": visible_count,
                    "suppressed_count": payload_count - visible_count,
                }
            )
    return suppressed


def _still_visible_risks(visible_metrics: dict) -> list[dict]:
    risks = []
    if visible_metrics.get("visible_teams_in_this_position_typically_count", 0):
        risks.append(
            {
                "risk": "visible_generic_strategic_filler",
                "phrase": "teams in this position typically",
                "visible_count": visible_metrics["visible_teams_in_this_position_typically_count"],
            }
        )
    if visible_metrics.get("safe_attribution_total", 0) >= SAFE_ATTRIBUTION_OVERUSE_THRESHOLD:
        risks.append(
            {
                "risk": "visible_safe_attribution_overuse",
                "visible_count": visible_metrics["safe_attribution_total"],
                "phrase_counts": visible_metrics.get("safe_attribution_phrase_counts") or {},
            }
        )
    for opening, count in (visible_metrics.get("repeated_sentence_opening_counts") or {}).items():
        risks.append(
            {
                "risk": "visible_repeated_sentence_opening",
                "opening": opening,
                "visible_count": count,
            }
        )
    if visible_metrics.get("visible_no_external_corroboration_count", 0) >= 3:
        risks.append(
            {
                "risk": "visible_external_corroboration_repetition",
                "phrase": "no external corroboration",
                "visible_count": visible_metrics["visible_no_external_corroboration_count"],
            }
        )
    for family, data in (
        visible_metrics.get("observation_repetition_family_counts") or {}
    ).items():
        if data.get("total", 0) >= OBSERVATION_REPETITION_FAMILY_THRESHOLD:
            risks.append(
                {
                    "risk": "visible_observation_repetition_family",
                    "family": family,
                    "visible_count": data["total"],
                    "phrase_counts": data.get("phrases") or {},
                }
            )
    return risks


def _visible_warning_signals(
    items: list[dict[str, str]],
    repeated_opening_counts: dict[str, int],
) -> dict:
    matches = _phrase_matches(items, GENERIC_FILLER_PHRASES + SAFE_ATTRIBUTION_PHRASES)
    return {
        "repeated_sentence_openings": repeated_opening_counts,
        "phrase_matches": matches,
    }


def _build_metrics(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
    checks: list[dict],
) -> dict:
    text_items = _all_text_items(synthesis, tension, findings)
    opening_counts = Counter()
    for item in text_items:
        opening = _sentence_opening(item["text"])
        if opening:
            opening_counts[opening] += 1

    generic_counts = {
        phrase: sum(
            _count_phrase(item["text"], phrase)
            for item in text_items
        )
        for phrase in GENERIC_FILLER_PHRASES
    }
    generic_counts = {k: v for k, v in generic_counts.items() if v}

    prescription_counts = {
        phrase: sum(
            _count_phrase(item["text"], phrase)
            for item in text_items
        )
        for phrase in UNSUPPORTED_PRESCRIPTION_PHRASES
    }
    prescription_counts = {k: v for k, v in prescription_counts.items() if v}

    safe_attribution_counts = {
        phrase: sum(
            _count_phrase(item["text"], phrase)
            for item in text_items
        )
        for phrase in SAFE_ATTRIBUTION_PHRASES
    }
    safe_attribution_counts = {k: v for k, v in safe_attribution_counts.items() if v}

    return {
        "findings_count": len(findings),
        "findings_without_evidence_urls": sum(
            1
            for finding in findings
            if any(finding.get(field) for field in ("observation", "implication", "typical_decision"))
            and not finding.get("evidence_urls")
        ),
        "sentence_opening_counts": dict(sorted(opening_counts.items())),
        "generic_phrase_counts": generic_counts,
        "unsupported_prescription_counts": prescription_counts,
        "safe_attribution_phrase_counts": safe_attribution_counts,
        "safe_attribution_total": sum(safe_attribution_counts.values()),
        "observation_repetition_family_counts": _compact_family_counts(
            _repetition_family_counts(
                [
                    {
                        "path": _finding_path(finding, "observation"),
                        "text": finding.get("observation") or "",
                    }
                    for finding in findings
                    if finding.get("observation")
                ]
            )
        ),
        "warning_count": sum(1 for check in checks if check["status"] == "warning"),
        "error_count": sum(1 for check in checks if check["status"] == "error"),
    }


def _build_summary(checks: list[dict]) -> dict:
    warnings = sum(1 for check in checks if check["status"] == "warning")
    errors = sum(1 for check in checks if check["status"] == "error")
    passed = sum(1 for check in checks if check["status"] == "pass")
    return {
        "total_checks": len(checks),
        "passed": passed,
        "warnings": warnings,
        "errors": errors,
    }


def _input_metadata(
    payload: dict,
    base_dossier: dict | None,
    findings: list[dict[str, Any]],
) -> dict:
    brand = None
    if isinstance(base_dossier, dict):
        brand_obj = base_dossier.get("brand") or {}
        if isinstance(brand_obj, dict):
            brand = brand_obj.get("name")
    return {
        "payload_version": payload.get("version"),
        "payload_source": payload.get("source"),
        "run_id": payload.get("run_id"),
        "brand": brand,
        "has_base_dossier": isinstance(base_dossier, dict),
        "has_synthesis": bool(_clean_text(payload.get("synthesis_prose") or payload.get("summary") or "")),
        "has_tension": bool(_clean_text(payload.get("tensions_prose") or "")),
        "dimensions_count": len(payload.get("findings_by_dimension") or {})
        if isinstance(payload.get("findings_by_dimension"), dict)
        else 0,
        "findings_count": len(findings),
    }


def _overall_status(summary: dict) -> str:
    if summary["errors"]:
        return "error"
    if summary["warnings"]:
        return "warning"
    return "pass"


def _check(
    check_id: str,
    severity: str,
    status: str,
    message: str,
    evidence: list[dict],
) -> dict:
    return {
        "check_id": check_id,
        "severity": severity,
        "status": status,
        "message": message,
        "evidence": evidence,
    }


def _all_text_items(
    synthesis: str,
    tension: str,
    findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    items = []
    if synthesis:
        items.append({"path": "synthesis_prose", "text": synthesis})
    if tension:
        items.append({"path": "tensions_prose", "text": tension})
    for finding in findings:
        for field in ("title", "observation", "implication", "typical_decision"):
            text = finding.get(field) or ""
            if text:
                items.append({"path": _finding_path(finding, field), "text": text})
    return items


def _phrase_matches(items: list[dict[str, str]], phrases: tuple[str, ...]) -> list[dict]:
    evidence = []
    for item in items:
        lowered = item["text"].lower()
        for phrase in phrases:
            count = _count_phrase(lowered, phrase)
            if count:
                evidence.append(
                    {
                        "path": item["path"],
                        "excerpt": _excerpt(item["text"]),
                        "phrase": phrase,
                        "count": count,
                    }
                )
    return evidence


def _repetition_family_counts(items: list[dict[str, str]]) -> dict[str, dict]:
    families = {}
    for family, phrases in OBSERVATION_REPETITION_FAMILIES.items():
        phrase_counts = {}
        matches = []
        total = 0
        for item in items:
            lowered = item["text"].lower()
            for phrase in phrases:
                count = _count_phrase(lowered, phrase)
                if not count:
                    continue
                total += count
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + count
                matches.append(
                    {
                        "path": item["path"],
                        "excerpt": _excerpt(item["text"]),
                        "phrase": phrase,
                        "count": count,
                    }
                )
        if total:
            families[family] = {
                "total": total,
                "phrases": dict(sorted(phrase_counts.items())),
                "matches": matches,
            }
    return families


def _compact_family_counts(families: dict[str, dict]) -> dict[str, dict]:
    return {
        family: {
            "total": data["total"],
            "phrases": data["phrases"],
        }
        for family, data in sorted(families.items())
    }


def _count_phrase(text: str, phrase: str) -> int:
    return text.lower().count(phrase.lower())


def _sentence_opening(text: str, words: int = 3) -> str:
    cleaned = _clean_text(text).lower()
    if not cleaned:
        return ""
    first_sentence = re.split(r"[.!?]", cleaned, maxsplit=1)[0]
    tokens = re.findall(r"[a-z0-9']+", first_sentence)
    if len(tokens) < 2:
        return ""
    return " ".join(tokens[:words])


def _visible_sentence_opening_counts(text: str, words: int = 3) -> Counter:
    counts: Counter = Counter()
    for sentence in re.split(r"[.!?]+", _clean_text(text).lower()):
        tokens = re.findall(r"[a-z0-9']+", sentence)
        if len(tokens) >= 2:
            counts[" ".join(tokens[:words])] += 1
    return counts


def _visible_sentence_opening_counts_from_blocks(blocks: list[str], words: int = 3) -> Counter:
    counts: Counter = Counter()
    for block in blocks:
        opening = _sentence_opening(block, words=words)
        if opening:
            counts[opening] += 1
    return counts


def _visible_narrative_blocks(rendered_output: Any) -> list[str]:
    if not isinstance(rendered_output, str):
        return []
    blocks = []
    for pattern in (
        r"<p\b[^>]*class=[\"'][^\"']*\bfinding-primary\b[^\"']*[\"'][^>]*>.*?</p>",
        r"<p\b[^>]*class=[\"'][^\"']*\bfinding-decision\b[^\"']*[\"'][^>]*>.*?</p>",
        r"<div\b[^>]*class=[\"'][^\"']*\bprose\b[^\"']*[\"'][^>]*>.*?</div>",
    ):
        for match in re.findall(pattern, rendered_output, flags=re.IGNORECASE | re.DOTALL):
            text = _rendered_text(match, rendered_as_html=True)
            if text:
                blocks.append(text)
    return blocks


def _rendered_text(rendered_output: Any, *, rendered_as_html: bool) -> str:
    if not isinstance(rendered_output, str):
        return ""
    if not rendered_as_html:
        return _clean_text(rendered_output)
    without_scripts = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        rendered_output,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    return _clean_text(unescape(without_tags))


def _visible_link_count(rendered_output: Any) -> int:
    if not isinstance(rendered_output, str):
        return 0
    return len(re.findall(r"<a\b[^>]*\bhref=", rendered_output, flags=re.IGNORECASE))


def _visible_evidence_chip_link_count(rendered_output: Any) -> int:
    if not isinstance(rendered_output, str):
        return 0
    total = 0
    for block in re.findall(
        r"<ul\b[^>]*class=[\"'][^\"']*\bchips\b[^\"']*[\"'][^>]*>.*?</ul>",
        rendered_output,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        total += _visible_link_count(block)
    return total


def _content_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9']+", text.lower())
    return {token for token in tokens if token not in STOPWORDS and len(token) > 3}


def _finding_path(finding: dict[str, Any], field: str) -> str:
    return f"findings_by_dimension.{finding['dimension']}[{finding['index']}].{field}"


def _excerpt(text: str, limit: int = 160) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "..."


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()
