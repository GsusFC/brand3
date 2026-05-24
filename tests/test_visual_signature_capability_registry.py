from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.governance import (
    build_capability_registry,
    capability_registry_markdown,
    validate_capability_registry,
    write_capability_registry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_capability_registry.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_registry_is_consistent():
    registry = build_capability_registry()

    assert registry.capability_count == 9
    assert registry.governance_scope == "visual_signature"
    assert registry.schema_version == "visual-signature-capability-registry-1"
    assert registry.registry_version == "visual-signature-capability-registry-1"
    assert len(registry.capabilities) == registry.capability_count
    assert all(not capability.scoring_impact for capability in registry.capabilities)
    assert all(not capability.runtime_mutation for capability in registry.capabilities)
    assert all(not capability.production_enabled for capability in registry.capabilities)
    for capability in registry.capabilities:
        assert set(capability.allowed_scopes).isdisjoint(capability.prohibited_scopes)


def test_registry_validation_and_markdown():
    registry = build_capability_registry()
    payload = registry.model_dump(mode="json")

    assert validate_capability_registry(payload) == []
    markdown = capability_registry_markdown(registry)
    assert "Not a production enablement list" in markdown
    assert "Capability presence != production approval" in markdown
    assert "Readiness is scope-dependent" in markdown
    assert "evidence-only governance registry" in markdown.lower()


def test_registry_script_writes_outputs(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_capability_registry")
    output_root = tmp_path / "governance"

    assert script.main(["--output-root", str(output_root)]) == 0

    json_path = output_root / "capability_registry.json"
    md_path = output_root / "capability_registry.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["capability_count"] == 9
    assert payload["governance_scope"] == "visual_signature"
    assert payload["registry_version"] == "visual-signature-capability-registry-1"
    assert validate_capability_registry(payload) == []
    assert "Not a production enablement list" in md_path.read_text(encoding="utf-8")


def test_registry_rejects_scope_overlap():
    registry = build_capability_registry().model_dump(mode="json")
    registry["capabilities"][0]["prohibited_scopes"].append(registry["capabilities"][0]["allowed_scopes"][0])

    errors = validate_capability_registry(registry)
    assert errors
    assert "overlap" in errors[0].lower()


def test_registry_rejects_wrong_count():
    registry = build_capability_registry().model_dump(mode="json")
    registry["capability_count"] = registry["capability_count"] + 1

    errors = validate_capability_registry(registry)
    assert errors
    assert "capability_count does not match" in errors[0]
