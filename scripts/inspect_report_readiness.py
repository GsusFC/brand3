#!/usr/bin/env python3
"""Inspect report readiness for existing Brand3 output JSON files."""

from __future__ import annotations

import json
import sys
import importlib.util
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _load_build_report_context():
    _load_reports_submodule_without_package_init("editorial_policy")
    module_path = ROOT / "src" / "reports" / "derivation.py"
    spec = importlib.util.spec_from_file_location("brand3_report_derivation", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load derivation module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.build_report_context


def _load_reports_submodule_without_package_init(name: str) -> None:
    package_name = "src.reports"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(ROOT / "src" / "reports")]
        sys.modules[package_name] = package

    full_name = f"{package_name}.{name}"
    if full_name in sys.modules:
        return
    module_path = ROOT / "src" / "reports" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {full_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)


build_report_context = _load_build_report_context()


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: python scripts/inspect_report_readiness.py output/file.json [output/other.json ...]")
        return 2

    exit_code = 0
    for index, raw_path in enumerate(argv):
        if index:
            print()
        path = Path(raw_path)
        result = inspect_path(path)
        if not result["ok"]:
            exit_code = 1
        print_result(result)
    return exit_code


def inspect_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "path": str(path), "error": "missing_file"}
    if not path.is_file():
        return {"ok": False, "path": str(path), "error": "not_a_file"}

    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "path": str(path), "error": f"invalid_json: {exc}"}
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": f"read_error: {exc}"}

    try:
        context = build_report_context(snapshot, theme="dark")
    except Exception as exc:  # pragma: no cover - diagnostic CLI should keep batch running.
        return {"ok": False, "path": str(path), "error": f"context_error: {exc}"}

    readiness = context.get("readiness") or {}
    return {
        "ok": True,
        "path": str(path),
        "brand": _brand_name(snapshot, context),
        "report_mode": readiness.get("report_mode"),
        "diagnostic_summary": readiness.get("diagnostic_summary") or "",
        "blockers": readiness.get("blockers") or [],
        "warnings": readiness.get("warnings") or [],
        "dimension_states": readiness.get("dimension_states") or {},
        "fallback_detected": readiness.get("fallback_detected") or {},
        "missing_high_weight_features": readiness.get("missing_high_weight_features") or {},
    }


def _brand_name(snapshot: dict[str, Any], context: dict[str, Any]) -> str:
    snapshot_brand = snapshot.get("brand")
    if isinstance(snapshot_brand, str) and snapshot_brand.strip():
        return snapshot_brand.strip()

    context_brand = context.get("brand")
    if isinstance(context_brand, dict):
        name = context_brand.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(context_brand, str) and context_brand.strip():
        return context_brand.strip()

    return "(unknown)"


def print_result(result: dict[str, Any]) -> None:
    print(f"path: {result['path']}")
    if not result["ok"]:
        print(f"error: {result['error']}")
        return

    print(f"brand: {result['brand']}")
    print(f"report_mode: {result['report_mode']}")
    print(f"diagnostic_summary: {result['diagnostic_summary'] or '(none)'}")
    print(f"blockers: {_format_value(result['blockers'])}")
    print(f"warnings: {_format_value(result['warnings'])}")
    print("dimension_states:")
    for name, state in sorted(result["dimension_states"].items()):
        print(f"  {name}: {state}")
    print(f"fallback_detected: {_format_value(result['fallback_detected'])}")
    print(f"missing_high_weight_features: {_format_value(result['missing_high_weight_features'])}")


def _format_value(value: Any) -> str:
    if value in ({}, []):
        return "none"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
