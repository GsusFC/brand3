import ast
from pathlib import Path


SV9_FLOW_ROOT = Path("src/sv9_flow")

FORBIDDEN_IMPORT_PREFIXES = (
    "fastapi",
    "sqlite3",
    "web",
    "src.storage",
    "src.services.magnetism_service",
    "src.sv9.service",
    "src.sv9.store",
)


def test_sv9_flow_does_not_import_routes_db_or_current_sv9_runtime() -> None:
    violations: list[str] = []
    for path in sorted(SV9_FLOW_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for imported in _imports(tree):
            if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path}:{imported}")

    assert violations == []


def test_current_sv9_runtime_imports_only_flow_contracts() -> None:
    """src/sv9 may consume the flow contract, never the flow workers."""

    violations: list[str] = []
    for path in sorted(Path("src/sv9").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for imported in _imports(tree):
            if imported.startswith("src.sv9_flow") and imported != "src.sv9_flow.contracts":
                violations.append(f"{path}:{imported}")

    assert violations == []


def test_sv9_flow_package_has_no_tldr_input_path() -> None:
    """Pass 1/TLDR compatibility lives only in scripts/sv9_flow_legacy_compat.py.

    The canonical package must not accept or unwrap TLDR payloads.
    """

    offenders: list[str] = []
    for path in sorted(SV9_FLOW_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "tldr_payload" in text or "from_tldr" in text:
            offenders.append(str(path))

    assert offenders == []


def _imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
