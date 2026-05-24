from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.visual_signature.phase_one import (
    PHASE_ONE_ROOT,
    build_phase_one_bundle,
    export_phase_one_bundle,
    load_phase_one_sources,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase One outputs from real capture artifacts.")
    parser.add_argument("--capture-manifest", type=Path, default=Path("examples/visual_signature/screenshots/capture_manifest.json"))
    parser.add_argument("--dismissal-audit", type=Path, default=Path("examples/visual_signature/screenshots/dismissal_audit.json"))
    parser.add_argument("--output-root", type=Path, default=PHASE_ONE_ROOT)
    args = parser.parse_args(argv)

    sources = load_phase_one_sources(args.capture_manifest, args.dismissal_audit)
    bundles = [build_phase_one_bundle(source) for source in sources]
    manifest = export_phase_one_bundle(
        output_root=args.output_root,
        bundles=bundles,
        source_capture_manifest_path=str(args.capture_manifest),
        source_dismissal_audit_path=str(args.dismissal_audit),
    )

    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
