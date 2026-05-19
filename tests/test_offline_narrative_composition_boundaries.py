import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _tree(relative_path: str) -> ast.Module:
    return ast.parse((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def _source(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _imported_modules(relative_path: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(_tree(relative_path)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.add(module)
    return modules


def _called_names(relative_path: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(relative_path)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _assert_no_forbidden_imports(relative_path: str, forbidden: set[str]) -> None:
    imports = _imported_modules(relative_path)
    violations = {
        module
        for module in imports
        for forbidden_module in forbidden
        if module == forbidden_module or module.startswith(f"{forbidden_module}.")
    }
    assert not violations, f"{relative_path} imports forbidden modules: {sorted(violations)}"


def test_narrative_harness_stays_offline_and_decoupled():
    _assert_no_forbidden_imports(
        "src/reports/narrative_harness.py",
        {
            "src.features",
            "src.scoring",
            "src.visual_signature",
            "src.reports.renderer",
            "src.reports.dossier",
            "src.reports.narrative",
            "src.reports.entity_narrative_state",
            "src.reports.experimental_perceptual_narrative",
        },
    )


def test_entity_narrative_state_builder_stays_offline_and_decoupled():
    _assert_no_forbidden_imports(
        "src/reports/entity_narrative_state.py",
        {
            "src.features",
            "src.scoring",
            "src.visual_signature",
            "src.reports.renderer",
            "src.reports.dossier",
            "src.reports.narrative",
            "src.reports.narrative_harness",
            "src.reports.experimental_perceptual_narrative",
        },
    )


def test_state_first_findings_generator_stays_offline_and_decoupled():
    _assert_no_forbidden_imports(
        "src/reports/state_first_findings_generator.py",
        {
            "src.features",
            "src.scoring",
            "src.visual_signature",
            "src.reports.renderer",
            "src.reports.dossier",
            "src.reports.narrative",
            "src.reports.narrative_harness",
            "src.reports.entity_narrative_state",
            "src.reports.experimental_perceptual_narrative",
        },
    )


def test_state_first_prose_generator_stays_offline_and_decoupled():
    _assert_no_forbidden_imports(
        "src/reports/state_first_prose_generator.py",
        {
            "src.features",
            "src.scoring",
            "src.visual_signature",
            "src.reports.renderer",
            "src.reports.dossier",
            "src.reports.narrative",
            "src.reports.narrative_harness",
            "src.reports.entity_narrative_state",
            "src.reports.state_first_findings_generator",
            "src.reports.experimental_perceptual_narrative",
        },
    )


def test_report_renderer_does_not_import_lab_diagnostics_or_entity_state():
    _assert_no_forbidden_imports(
        "src/reports/renderer.py",
        {
            "src.reports.entity_narrative_state",
            "src.reports.narrative_harness",
        },
    )
    assert "entity_narrative_state" not in _source("src/reports/renderer.py")
    assert "build_entity_narrative_state" not in _source("src/reports/renderer.py")
    assert "narrative_harness" not in _source("src/reports/renderer.py")
    assert "audit_report_narrative_payload" not in _source("src/reports/renderer.py")


def test_dossier_generation_does_not_call_entity_narrative_state_builder():
    _assert_no_forbidden_imports(
        "src/reports/dossier.py",
        {"src.reports.entity_narrative_state"},
    )
    assert "build_entity_narrative_state" not in _called_names("src/reports/dossier.py")
    assert "build_entity_narrative_state" not in _source("src/reports/dossier.py")
