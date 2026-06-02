#!/usr/bin/env python3
"""Run a local Context.dev capability benchmark.

This lab script is intentionally outside the production flow. It probes
Context.dev endpoints by capability and writes JSON/Markdown artifacts so we can
decide which outputs deserve integration into Brand3 contracts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://api.context.dev/v1"
DEFAULT_CAPABILITIES = (
    "retrieve_brand",
    "styleguide",
    "fonts",
    "images",
    "screenshot",
    "products",
)
USER_AGENT = "Brand3-Lab/0.1"


@dataclass(frozen=True)
class ContextDevBenchmarkCase:
    brand: str
    url: str
    label: str = ""

    @property
    def domain(self) -> str:
        parsed = urlparse(self.url if "://" in self.url else f"https://{self.url}")
        return (parsed.netloc or parsed.path).removeprefix("www.").strip("/")

    def to_dict(self) -> dict[str, str]:
        return {"brand": self.brand, "url": self.url, "label": self.label or _slugify(self.brand), "domain": self.domain}


class ContextDevClient:
    def __init__(self, api_key: str, timeout_seconds: int = 150):
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    def get(self, path: str, params: dict[str, object]) -> dict[str, Any]:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        return self._request("GET", f"{BASE_URL}{path}?{query}" if query else f"{BASE_URL}{path}")

    def post(self, path: str, payload: dict[str, object]) -> dict[str, Any]:
        return self._request("POST", f"{BASE_URL}{path}", payload=payload)

    def _request(self, method: str, url: str, payload: dict[str, object] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            return {"status": "error", "code": exc.code, "error": _http_error_message(exc)}
        except Exception as exc:
            return {"status": "error", "code": 0, "error": str(exc)}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "code": 0, "error": "invalid_json_response", "raw_preview": raw[:500]}
        return parsed if isinstance(parsed, dict) else {"status": "ok", "data": parsed}


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.cases_file)
    capabilities = _parse_csv(args.capabilities) or list(DEFAULT_CAPABILITIES)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("CONTEXT_DEV_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("CONTEXT_DEV_API_KEY not set")
    client = ContextDevClient(api_key=api_key, timeout_seconds=args.timeout_seconds)

    payloads = []
    for case in cases:
        payload = run_case(client, case, capabilities)
        payloads.append(payload)
        case_path = output_dir / f"{_slugify(case.label or case.brand)}.json"
        case_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {case_path}")

    summary = summarize_contextdev_capability_benchmark(payloads)
    (output_dir / "benchmark.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "benchmark.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {output_dir / 'benchmark.json'}")
    print(f"Wrote {output_dir / 'benchmark.md'}")
    print(
        "Summary:"
        f" cases={summary['case_count']}"
        f" successful_capabilities={summary['successful_capability_count']}"
        f" failed_capabilities={summary['failed_capability_count']}"
    )
    return 0


def run_case(client: ContextDevClient, case: ContextDevBenchmarkCase, capabilities: list[str]) -> dict[str, Any]:
    outputs: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        print(f"Running {case.label or case.brand}: {capability}")
        outputs[capability] = _run_capability(client, case, capability)
    return {
        "case": case.to_dict(),
        "capabilities_requested": list(capabilities),
        "outputs": outputs,
        "summary": summarize_case_outputs(outputs),
    }


def _run_capability(client: ContextDevClient, case: ContextDevBenchmarkCase, capability: str) -> dict[str, Any]:
    if capability == "retrieve_brand":
        return client.get("/brand/retrieve", {"domain": case.domain, "timeoutMS": 150000})
    if capability == "styleguide":
        return client.get("/web/styleguide", {"domain": case.domain, "timeoutMS": 150000})
    if capability == "fonts":
        return client.get("/web/fonts", {"domain": case.domain, "timeoutMS": 150000})
    if capability == "images":
        return client.get("/web/scrape/images", {"url": case.url, "maxAgeMs": 0, "timeoutMS": 150000})
    if capability == "screenshot":
        return client.get("/web/screenshot", {"domain": case.domain, "fullScreenshot": "false"})
    if capability == "products":
        return client.post(
            "/brand/ai/products",
            {"domain": case.domain, "maxProducts": 6, "maxAgeMs": 0, "timeoutMS": 150000},
        )
    raise ValueError(f"Unsupported Context.dev capability: {capability}")


def summarize_case_outputs(outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summaries = {capability: summarize_capability_payload(capability, payload) for capability, payload in outputs.items()}
    return {
        "capabilities": summaries,
        "successful_capabilities": [key for key, row in summaries.items() if row["status"] == "ok"],
        "failed_capabilities": [key for key, row in summaries.items() if row["status"] != "ok"],
        "brand3_channel_candidates": _brand3_channel_candidates(summaries),
    }


def summarize_capability_payload(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    if _is_error(payload):
        return {"status": "error", "signal_count": 0, "error": str(payload.get("error") or payload.get("message") or payload.get("status"))}
    if capability == "retrieve_brand":
        brand = _dict(payload.get("brand"))
        return {
            "status": "ok",
            "signal_count": _count_present(brand, ("title", "description", "slogan", "domain")),
            "title": str(brand.get("title") or ""),
            "logo_count": len(_list(brand.get("logos"))),
            "color_count": len(_list(brand.get("colors"))),
            "social_count": len(_dict(brand.get("socials")) or _dict(brand.get("links"))),
            "has_industries": bool(brand.get("industries")),
        }
    if capability == "styleguide":
        styleguide = _dict(payload.get("styleguide"))
        colors = _dict(styleguide.get("colors"))
        components = _dict(styleguide.get("components"))
        typography = _dict(styleguide.get("typography"))
        return {
            "status": "ok",
            "signal_count": len(colors) + len(components) + len(typography),
            "color_count": len(colors),
            "component_count": len(components),
            "typography_sections": sorted(typography),
        }
    if capability == "fonts":
        fonts = _list(payload.get("fonts"))
        return {
            "status": "ok",
            "signal_count": len(fonts),
            "font_count": len(fonts),
            "top_fonts": [str(item.get("font") or "") for item in fonts[:5] if isinstance(item, dict)],
        }
    if capability == "images":
        images = _extract_images(payload)
        return {"status": "ok", "signal_count": len(images), "image_count": len(images), "sample_images": images[:5]}
    if capability == "screenshot":
        screenshot = str(payload.get("screenshot") or payload.get("url") or "")
        return {
            "status": "ok",
            "signal_count": 1 if screenshot else 0,
            "has_screenshot": bool(screenshot),
            "screenshot_type": str(payload.get("screenshotType") or ""),
        }
    if capability == "products":
        products = _list(payload.get("products"))
        return {
            "status": "ok",
            "signal_count": len(products),
            "product_count": len(products),
            "product_names": [str(item.get("name") or "") for item in products[:8] if isinstance(item, dict)],
        }
    return {"status": "ok", "signal_count": len(payload)}


def summarize_contextdev_capability_benchmark(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    capability_rows: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "error": 0, "signal_total": 0})
    channel_counts: Counter[str] = Counter()
    case_rows = []
    for payload in payloads:
        case_summary = payload["summary"]
        case_rows.append(
            {
                "brand": payload["case"]["brand"],
                "domain": payload["case"]["domain"],
                "successful_capabilities": case_summary["successful_capabilities"],
                "failed_capabilities": case_summary["failed_capabilities"],
                "brand3_channel_candidates": case_summary["brand3_channel_candidates"],
            }
        )
        channel_counts.update(case_summary["brand3_channel_candidates"])
        for capability, row in case_summary["capabilities"].items():
            status = "ok" if row["status"] == "ok" else "error"
            capability_rows[capability][status] += 1
            capability_rows[capability]["signal_total"] += int(row.get("signal_count") or 0)
    return {
        "case_count": len(payloads),
        "successful_capability_count": sum(row["ok"] for row in capability_rows.values()),
        "failed_capability_count": sum(row["error"] for row in capability_rows.values()),
        "capability_metrics": dict(sorted(capability_rows.items())),
        "brand3_channel_candidate_counts": dict(sorted(channel_counts.items())),
        "cases": case_rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Context.dev Capability Benchmark",
        "",
        f"- Cases: {summary['case_count']}",
        f"- Successful capabilities: {summary['successful_capability_count']}",
        f"- Failed capabilities: {summary['failed_capability_count']}",
        "",
        "## Capabilities",
        "",
        "| Capability | OK | Error | Signal Total |",
        "| --- | --- | --- | --- |",
    ]
    for capability, row in summary["capability_metrics"].items():
        lines.append(f"| {capability} | {row['ok']} | {row['error']} | {row['signal_total']} |")
    lines.extend(["", "## Cases", "", "| Brand | Domain | OK | Error | Brand3 Candidates |", "| --- | --- | --- | --- | --- |"])
    for row in summary["cases"]:
        lines.append(
            "| {brand} | {domain} | {ok} | {error} | {candidates} |".format(
                brand=row["brand"],
                domain=row["domain"],
                ok=", ".join(row["successful_capabilities"]) or "none",
                error=", ".join(row["failed_capabilities"]) or "none",
                candidates=", ".join(row["brand3_channel_candidates"]) or "none",
            )
        )
    if summary["brand3_channel_candidate_counts"]:
        lines.extend(["", "## Brand3 Candidate Channels", ""])
        for channel, count in summary["brand3_channel_candidate_counts"].items():
            lines.append(f"- {channel}: {count}")
    return "\n".join(lines).strip() + "\n"


def _brand3_channel_candidates(summaries: dict[str, dict[str, Any]]) -> list[str]:
    candidates = []
    if summaries.get("retrieve_brand", {}).get("status") == "ok":
        candidates.extend(["entity_resolution", "industry_classification"])
    if summaries.get("styleguide", {}).get("signal_count", 0) or summaries.get("fonts", {}).get("signal_count", 0):
        candidates.append("visual_identity")
    if summaries.get("images", {}).get("signal_count", 0) or summaries.get("screenshot", {}).get("signal_count", 0):
        candidates.append("visual_evidence")
    if summaries.get("products", {}).get("signal_count", 0):
        candidates.append("product_extraction")
    return sorted(set(candidates))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-file", type=Path, default=Path("examples/benchmarks/contextdev_capabilities/cases.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/contextdev_capability_benchmark"))
    parser.add_argument("--capabilities", default=",".join(DEFAULT_CAPABILITIES))
    parser.add_argument("--timeout-seconds", type=int, default=150)
    return parser.parse_args()


def _load_cases(path: Path) -> list[ContextDevBenchmarkCase]:
    if not path.exists():
        return [
            ContextDevBenchmarkCase("ChatGPT", "https://chatgpt.com", label="chatgpt"),
            ContextDevBenchmarkCase("LangChain", "https://www.langchain.com", label="langchain"),
        ]
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        ContextDevBenchmarkCase(
            brand=str(item.get("brand") or ""),
            url=str(item.get("url") or ""),
            label=str(item.get("label") or ""),
        )
        for item in raw
    ]


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _http_error_message(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return f"HTTP {exc.code}: {exc.reason}"
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("error") or f"HTTP {exc.code}: {exc.reason}")
    return f"HTTP {exc.code}: {exc.reason}"


def _extract_images(payload: dict[str, Any]) -> list[str]:
    for key in ("images", "image_urls", "urls"):
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item.get("url") if isinstance(item, dict) else item) for item in value if item]
    return []


def _is_error(payload: dict[str, Any]) -> bool:
    return bool(payload.get("status") == "error" or payload.get("error"))


def _count_present(payload: dict[str, Any], keys: tuple[str, ...]) -> int:
    return sum(1 for key in keys if payload.get(key))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "brand"


if __name__ == "__main__":
    raise SystemExit(main())
