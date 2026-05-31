"""Materialize two candidate variants from a base candidate set and optional overlays."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def deep_merge(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = deepcopy(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(overlay)


def load_candidate_map(source_file: Path | None, source_dir: Path | None, slug: str | None) -> dict[str, dict[str, Any]]:
    if source_dir is not None:
        mapping: dict[str, dict[str, Any]] = {}
        for candidate_path in sorted(source_dir.glob("*.json")):
            mapping[candidate_path.stem] = load_json(candidate_path)
        return mapping
    if source_file is not None:
        candidate = load_json(source_file)
        candidate_slug = (slug or source_file.stem).strip()
        if not candidate_slug:
            raise ValueError("candidate slug cannot be empty")
        return {candidate_slug: candidate}
    raise ValueError("either source_file or source_dir must be provided")


def load_overlay_map(overlay_dir: Path | None) -> dict[str, Any]:
    if overlay_dir is None:
        return {}
    overlays: dict[str, Any] = {}
    for overlay_path in sorted(overlay_dir.glob("*.json")):
        overlays[overlay_path.stem] = load_json(overlay_path)
    return overlays


def materialize_variant(
    *,
    source_map: dict[str, dict[str, Any]],
    overlay_map: dict[str, Any],
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug, candidate in source_map.items():
        payload = deepcopy(candidate)
        overlay = overlay_map.get(slug)
        if overlay is not None:
            payload = deep_merge(payload, overlay)
        output_path = output_dir / f"{slug}.json"
        write_json(output_path, payload)
        written.append(output_path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize candidate variants for Brand3 AutoResearch.")
    parser.add_argument("--source-file", type=Path, default=None)
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--slug", type=str, default=None)
    parser.add_argument("--overlay-dir-a", type=Path, default=None)
    parser.add_argument("--overlay-dir-b", type=Path, default=None)
    parser.add_argument("--output-a", type=Path, required=True)
    parser.add_argument("--output-b", type=Path, required=True)
    args = parser.parse_args()

    if args.source_file is None and args.source_dir is None:
        raise SystemExit("either --source-file or --source-dir must be provided")

    source_map = load_candidate_map(args.source_file, args.source_dir, args.slug)
    overlay_a = load_overlay_map(args.overlay_dir_a)
    overlay_b = load_overlay_map(args.overlay_dir_b)

    written_a = materialize_variant(source_map=source_map, overlay_map=overlay_a, output_dir=args.output_a)
    written_b = materialize_variant(source_map=source_map, overlay_map=overlay_b, output_dir=args.output_b)

    print(json.dumps({"output_a": [str(path) for path in written_a], "output_b": [str(path) for path in written_b]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
