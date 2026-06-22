"""Dismissal audit builders for Visual Signature capture runs.

This is internal reporting support used by the screenshot capture script.
It is intentionally outside ``src.visual_signature.capture`` so the capture
package stays focused on capture/runtime contracts.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature.capture.clean_capture import clean_attempt_quality


def build_dismissal_audit(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in manifest.get("results") or [] if isinstance(row, dict)]
    attempted = [row for row in rows if row.get("dismissal_attempted")]
    successful = [row for row in attempted if row.get("dismissal_successful")]
    failed = [row for row in attempted if not row.get("dismissal_successful")]
    eligibility_distribution = _string_distribution(rows, key="dismissal_eligibility")
    block_reason_distribution = _string_distribution(rows, key="dismissal_block_reason")
    state_distribution = _string_distribution(rows, key="perceptual_state")
    transition_reason_distribution = _transition_reason_distribution(rows)
    affordance_category_distribution = _affordance_distribution(rows, key="affordance_category")
    interaction_policy_distribution = _affordance_distribution(rows, key="interaction_policy")
    affordance_owner_distribution = _affordance_distribution(rows, key="affordance_owner")
    safe_to_dismiss_candidates_not_clicked = _affordance_count(
        rows,
        target_key="rejected_click_targets",
        field_key="interaction_policy",
        expected="safe_to_dismiss",
    )
    unsafe_to_mutate_candidates_encountered = _affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="unsafe_to_mutate",
    )
    requires_human_review_candidates_encountered = _affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="requires_human_review",
    )
    material_changes = [
        row for row in attempted if _material_viewport_change(row.get("raw_viewport_metrics"), row.get("clean_attempt_metrics"))
    ]
    clean_attempt_quality_distribution = _clean_attempt_quality_distribution(attempted)
    return {
        "schema_version": "visual-signature-dismissal-audit-1",
        "generated_at": datetime.now().isoformat(),
        "total_results": len(rows),
        "attempted": len(attempted),
        "successful": len(successful),
        "failed": len(failed),
        "dismissal_success_rate": _rate(len(successful), len(attempted)),
        "mutation_summary": {
            "attempted": len(attempted),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": _rate(len(successful), len(attempted)),
        },
        "failed_dismissals": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "before_severity": (row.get("before_obstruction") or {}).get("severity"),
                "after_severity": (row.get("after_obstruction") or {}).get("severity"),
                "notes": row.get("evidence_integrity_notes") or [],
            }
            for row in failed
        ],
        "materially_changed_cases": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "clean_attempt_quality": clean_attempt_quality(row),
                "before": row.get("raw_viewport_metrics"),
                "after": row.get("clean_attempt_metrics"),
                "before_obstruction": row.get("before_obstruction"),
                "after_obstruction": row.get("after_obstruction"),
            }
            for row in material_changes
        ],
        "before_severity_distribution": _severity_distribution(rows, key="before_obstruction"),
        "after_severity_distribution": _severity_distribution(rows, key="after_obstruction"),
        "eligibility_distribution": eligibility_distribution,
        "block_reason_distribution": block_reason_distribution,
        "state_distribution": state_distribution,
        "transition_reason_distribution": transition_reason_distribution,
        "clean_attempt_quality_distribution": clean_attempt_quality_distribution,
        "affordance_category_distribution": affordance_category_distribution,
        "interaction_policy_distribution": interaction_policy_distribution,
        "affordance_owner_distribution": affordance_owner_distribution,
        "safe_to_dismiss_candidates_not_clicked": safe_to_dismiss_candidates_not_clicked,
        "unsafe_to_mutate_candidates_encountered": unsafe_to_mutate_candidates_encountered,
        "requires_human_review_candidates_encountered": requires_human_review_candidates_encountered,
        "results": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "dismissal_eligibility": row.get("dismissal_eligibility"),
                "dismissal_block_reason": row.get("dismissal_block_reason"),
                "candidate_click_targets": row.get("candidate_click_targets") or [],
                "rejected_click_targets": row.get("rejected_click_targets") or [],
                "affordance_category_distribution": _target_distribution(row, key="affordance_category"),
                "interaction_policy_distribution": _target_distribution(row, key="interaction_policy"),
                "affordance_owner_distribution": _target_distribution(row, key="affordance_owner"),
                "capture_variant": row.get("capture_variant"),
                "clean_attempt_capture_variant": row.get("clean_attempt_capture_variant"),
                "clean_attempt_quality": clean_attempt_quality(row),
                "raw_screenshot_path": row.get("raw_screenshot_path"),
                "clean_attempt_screenshot_path": row.get("clean_attempt_screenshot_path"),
                "perceptual_state": row.get("perceptual_state"),
                "perceptual_transitions": row.get("perceptual_transitions") or [],
                "mutation_audit": row.get("mutation_audit"),
            }
            for row in rows
        ],
    }


def dismissal_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Dismissal Audit",
        "",
        "Evidence-quality diagnostics only. Raw viewport remains the primary evidence.",
        "",
        f"- Total results: {audit.get('total_results', 0)}",
        f"- Dismissal attempts: {audit.get('attempted', 0)}",
        f"- Successful dismissals: {audit.get('successful', 0)}",
        f"- Failed dismissals: {audit.get('failed', 0)}",
        f"- Dismissal success rate: {_format_percent(audit.get('dismissal_success_rate'))}",
        f"- Mutation summary: {json.dumps(audit.get('mutation_summary') or {}, sort_keys=True)}",
        "",
        "## Severity Transitions",
        "",
        f"- Before: {json.dumps(audit.get('before_severity_distribution') or {}, sort_keys=True)}",
        f"- After: {json.dumps(audit.get('after_severity_distribution') or {}, sort_keys=True)}",
        f"- Eligibility: {json.dumps(audit.get('eligibility_distribution') or {}, sort_keys=True)}",
        f"- Block reasons: {json.dumps(audit.get('block_reason_distribution') or {}, sort_keys=True)}",
        f"- Perceptual states: {json.dumps(audit.get('state_distribution') or {}, sort_keys=True)}",
        f"- Transition reasons: {json.dumps(audit.get('transition_reason_distribution') or {}, sort_keys=True)}",
        f"- Clean attempt quality: {json.dumps(audit.get('clean_attempt_quality_distribution') or {}, sort_keys=True)}",
        f"- Affordance categories: {json.dumps(audit.get('affordance_category_distribution') or {}, sort_keys=True)}",
        f"- Interaction policies: {json.dumps(audit.get('interaction_policy_distribution') or {}, sort_keys=True)}",
        f"- Affordance owners: {json.dumps(audit.get('affordance_owner_distribution') or {}, sort_keys=True)}",
        f"- Safe-to-dismiss candidates not clicked: {audit.get('safe_to_dismiss_candidates_not_clicked', 0)}",
        f"- Unsafe-to-mutate candidates encountered: {audit.get('unsafe_to_mutate_candidates_encountered', 0)}",
        f"- Requires-human-review candidates encountered: {audit.get('requires_human_review_candidates_encountered', 0)}",
        "",
        "## Material Viewport Changes",
        "",
    ]
    changed = audit.get("materially_changed_cases") or []
    if not changed:
        lines.append("- None")
    else:
        for row in changed:
            lines.append(f"- {row.get('brand_name')} ({row.get('website_url')})")
    lines.extend(["", "## Failed Dismissals", "", "| Brand | Method | Clicked Text | Before | After |", "| --- | --- | --- | --- | --- |"])
    failed = audit.get("failed_dismissals") or []
    if not failed:
        lines.append("| - | - | - | - | - |")
    else:
        for row in failed:
            lines.append(
                f"| {row.get('brand_name')} | {row.get('dismissal_method') or '-'} | {row.get('clicked_text') or '-'} | "
                f"{row.get('before_severity') or '-'} | {row.get('after_severity') or '-'} |"
            )
    return "\n".join(lines)


def _severity_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        obstruction = row.get(key) or {}
        if not isinstance(obstruction, dict):
            continue
        severity = str(obstruction.get("severity") or "none")
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))


def _string_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "none")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _transition_reason_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        transitions = row.get("perceptual_transitions") or []
        if not isinstance(transitions, list):
            continue
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            reason = str(transition.get("reason") or "none")
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _affordance_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for record in _all_diagnostic_targets(row):
            value = str(record.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _affordance_count(
    rows: list[dict[str, Any]],
    *,
    target_key: str | None,
    field_key: str,
    expected: str,
) -> int:
    total = 0
    for row in rows:
        if target_key is None:
            records = _all_diagnostic_targets(row)
        else:
            records = row.get(target_key) or []
            if not isinstance(records, list):
                continue
        for record in records:
            if not isinstance(record, dict):
                continue
            if str(record.get(field_key) or "") == expected:
                total += 1
    return total


def _target_distribution(row: dict[str, Any], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _all_diagnostic_targets(row):
        value = str(record.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _all_diagnostic_targets(row: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for key in ("candidate_click_targets", "rejected_click_targets"):
        records = row.get(key) or []
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                targets.append(record)
    return targets


def _clean_attempt_quality_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        quality = clean_attempt_quality(row)
        counts[quality] = counts.get(quality, 0) + 1
    return dict(sorted(counts.items()))


def _material_viewport_change(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    before_density = str(before.get("viewport_visual_density") or "")
    after_density = str(after.get("viewport_visual_density") or "")
    before_whitespace = _float_or_none(before.get("viewport_whitespace_ratio"))
    after_whitespace = _float_or_none(after.get("viewport_whitespace_ratio"))
    before_palette = _float_or_none(before.get("palette_color_count"))
    after_palette = _float_or_none(after.get("palette_color_count"))
    return (
        before_density != after_density
        or (before_whitespace is not None and after_whitespace is not None and abs(after_whitespace - before_whitespace) >= 0.08)
        or (before_palette is not None and after_palette is not None and abs(after_palette - before_palette) >= 3)
    )


def _rate(successful: int, attempted: int) -> float:
    if attempted <= 0:
        return 0.0
    return round(successful / attempted, 3)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"
