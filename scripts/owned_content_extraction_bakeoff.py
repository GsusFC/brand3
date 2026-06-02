"""Run an offline owned-content extraction bake-off.

The input is a JSON file with cases shaped as:
[
  {
    "id": "case-id",
    "html": "<html>...</html>",
    "expected_terms": ["product promise"],
    "rejected_terms": ["login"]
  }
]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.quality.owned_content_extraction import evaluate_owned_content_extraction


DEFAULT_CASES = PROJECT_ROOT / "examples" / "benchmarks" / "owned_content_extraction" / "dataset.json"


def load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("cases") or []
    return [item for item in payload if isinstance(item, dict)]


def run_bakeoff(cases: list[dict]) -> list[dict]:
    results = []
    for case in cases:
        result = evaluate_owned_content_extraction(
            case_id=str(case.get("id") or "unknown"),
            html=str(case.get("html") or ""),
            expected_terms=[str(item) for item in case.get("expected_terms") or []],
            rejected_terms=[str(item) for item in case.get("rejected_terms") or []],
            noise_terms=[str(item) for item in case.get("noise_terms") or []] or None,
            strategic_terms=[str(item) for item in case.get("strategic_terms") or []] or None,
        )
        results.append(result.as_dict())
    return results


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# Owned Content Extraction Bake-off",
        "",
        f"- cases: {len(results)}",
        "",
    ]
    for case in results:
        lines.extend([
            f"## {case['case_id']}",
            "",
            f"- winner: {case['winner']}",
            "",
            "| method | score | chars | expected_hits | rejected_hits | noise_hits | strategic_hits |",
            "|---|---:|---:|---|---|---|---|",
        ])
        for item in case["results"]:
            lines.append(
                "| {method} | {score:.4f} | {text_chars} | {expected} | {rejected} | {noise} | {strategic} |".format(
                    method=item["method"],
                    score=float(item["score"]),
                    text_chars=item["text_chars"],
                    expected=", ".join(item["expected_hits"]),
                    rejected=", ".join(item["rejected_hits"]),
                    noise=", ".join(item["noise_hits"]),
                    strategic=", ".join(item["strategic_hits"]),
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Brand3 owned-content extraction bake-off")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--json-out", default="")
    parser.add_argument("--md-out", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = run_bakeoff(load_cases(Path(args.cases)))

    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    markdown = render_markdown(results)
    if args.md_out:
        path = Path(args.md_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
