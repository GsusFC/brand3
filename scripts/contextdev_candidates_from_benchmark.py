#!/usr/bin/env python3
"""Build candidate evidence summaries from Context.dev benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.contextdev_candidates import build_contextdev_candidates, summarize_contextdev_candidates


def main() -> int:
    args = _parse_args()
    candidates = []
    for path in _case_files(args.input_dirs):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.extend(build_contextdev_candidates(payload))

    summary = summarize_contextdev_candidates(candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Summary: candidates={summary['candidate_count']} channels={len(summary['by_channel'])}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dirs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("out/contextdev_candidates/summary.json"))
    return parser.parse_args()


def _case_files(input_dirs: list[Path]) -> list[Path]:
    files = []
    for input_dir in input_dirs:
        files.extend(
            path
            for path in sorted(input_dir.glob("*.json"))
            if path.name != "benchmark.json"
        )
    return files


if __name__ == "__main__":
    raise SystemExit(main())
