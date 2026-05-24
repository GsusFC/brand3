"""Summarize the latest Brand3 output JSON files by modification time."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_SLUGS = ["openai", "claude", "base"]


def main(argv: list[str]) -> int:
    slugs = argv or DEFAULT_SLUGS
    for index, slug in enumerate(slugs):
        if index:
            print()
        summarize_slug(slug)
    return 0


def summarize_slug(slug: str) -> None:
    path = latest_output_path(slug)
    if path is None:
        print(f"{slug}: no output files found")
        return

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    entity = payload.get("entity_discovery") or {}
    plan = payload.get("discovery_search_plan") or {}
    hint = payload.get("discovery_calibration_hint") or {}
    decision = payload.get("discovery_calibration_decision") or {}
    trust_basis = payload.get("discovery_trust_basis") or {}
    trust = payload.get("trust_summary") or {}

    print(f"file: {path}")
    print(f"brand: {payload.get('brand')}")
    print(f"url: {payload.get('url')}")
    print(
        "entity: "
        f"{entity.get('entity_name') or entity.get('canonical_brand_name')} / "
        f"{entity.get('analysis_scope')} / "
        f"{plan.get('primary_entity')}"
    )
    print(
        "discovery_calibration_hint: "
        f"{hint.get('recommended_profile')} "
        f"(confidence={hint.get('confidence')})"
    )
    print(
        "discovery_calibration_decision: "
        f"applied={decision.get('applied')} "
        f"profile={decision.get('calibration_profile')} "
        f"source={decision.get('profile_source')} "
        f"reason={decision.get('reason')}"
    )
    print(
        "previous_calibration: "
        f"profile={decision.get('previous_calibration_profile')} "
        f"source={decision.get('previous_profile_source')}"
    )
    print(f"discovery_trust_basis: {trust_basis.get('basis')}")
    print(f"composite_score: {payload.get('composite_score')}")
    print(f"dimensions: {payload.get('dimensions')}")
    print(f"trust overall_status: {trust.get('overall_status')}")


def latest_output_path(slug: str) -> Path | None:
    matches = list(OUTPUT_DIR.glob(f"{slug}-*.json"))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
