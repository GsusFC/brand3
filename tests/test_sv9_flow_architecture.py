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
    for path in sorted(SV9_FLOW_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for imported in _imports(tree):
            if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path}:{imported}")

    assert violations == []


def test_sv9_flow_adapter_stays_a_thin_facade() -> None:
    path = SV9_FLOW_ROOT / "adapters.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    forbidden_nodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.For,
        ast.While,
        ast.If,
        ast.Try,
        ast.With,
    )
    body_nodes = [node for node in tree.body if not isinstance(node, (ast.Expr, ast.ImportFrom, ast.Assign))]

    assert not any(isinstance(node, forbidden_nodes) for node in body_nodes)


def _imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
