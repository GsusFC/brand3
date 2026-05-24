from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.visual_signature.phase_two import (
    PHASE_TWO_ROOT,
    export_phase_two_bundle,
    join_phase_one_and_reviews,
    load_phase_one_eligibility_records,
    load_review_records,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase Two human review outputs.")
    parser.add_argument("--phase-one-root", type=Path, default=Path("examples/visual_signature/phase_one"))
    parser.add_argument("--reviews-path", type=Path, default=PHASE_TWO_ROOT / "reviews" / "review_records.json")
    parser.add_argument("--output-root", type=Path, default=PHASE_TWO_ROOT)
    args = parser.parse_args(argv)

    phase_one_records = load_phase_one_eligibility_records(args.phase_one_root)
    review_records = load_review_records(args.reviews_path)
    bundles = join_phase_one_and_reviews(phase_one_records, review_records)
    manifest = export_phase_two_bundle(
        output_root=args.output_root,
        bundles=bundles,
        source_phase_one_root=str(args.phase_one_root),
        source_reviews_path=str(args.reviews_path),
    )

    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
