#!/usr/bin/env python3
"""Brand3 validation quick summary."""
import json
import sys
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser


def main():
    parser = ArgumentParser()
    parser.add_argument("--since", type=str)
    parser.add_argument("--output-dir", type=str, default="output")
    args = parser.parse_args()

    since = None
    if args.since:
        since = datetime.fromisoformat(args.since).date()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"Output dir {output_dir} not found", file=sys.stderr)
        sys.exit(1)

    results = []
    for f in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        ts = data.get("timestamp") or data.get("analyzed_at")
        if since and ts:
            try:
                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                if d < since:
                    continue
            except ValueError:
                pass
        results.append((f.name, data))

    if not results:
        print("No results found.")
        return

    DIMS = ["coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"]
    print()
    print(f"{'BRAND':<22} {'COMP':>5}  {'COH':>5} {'PRE':>5} {'PER':>5} {'DIF':>5} {'VIT':>5}  PROFILE")
    print("-" * 88)
    for fname, data in results:
        brand = str(data.get("brand", fname))[:20]
        composite = float(data.get("composite_score", 0.0))
        dims = data.get("dimensions", {})
        scores = [f"{float(dims.get(d, 0.0)):>5.1f}" for d in DIMS]
        profile = data.get("calibration_profile", "?")
        print(f"{brand:<22} {composite:>5.1f}  {' '.join(scores)}  {profile}")

    print()
    print(f"Total: {len(results)} runs")


if __name__ == "__main__":
    main()
