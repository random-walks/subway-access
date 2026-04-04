"""Audit the explicit public ``subway_access`` package surface."""

from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "subway_access"
API_DOC_PATH = ROOT / "docs" / "api.md"
PUBLIC_MODULES: Final[tuple[str, ...]] = (
    "subway_access",
    "subway_access.analysis",
    "subway_access.cli",
    "subway_access.export",
    "subway_access.io",
    "subway_access.models",
    "subway_access.pipeline",
)
DOC_DIRECTIVE_RE: Final[re.Pattern[str]] = re.compile(
    r"^:::\s+(subway_access(?:\.[a-z_]+)?)\s*$"
)
ALLOWED_PRIVATE_EXPORTS: Final[frozenset[str]] = frozenset({"__version__"})

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass(frozen=True)
class AuditRow:
    """Single public export row in the generated audit table."""

    public_module: str
    symbol_name: str
    origin_module: str
    kind: str


def _parse_module_ast(module_name: str) -> ast.Module:
    module_path = _module_path(module_name)
    return ast.parse(module_path.read_text(encoding="utf-8"))


def _module_path(module_name: str) -> Path:
    module_parts = module_name.split(".")[1:]
    if not module_parts:
        return PACKAGE_ROOT / "__init__.py"
    candidate_dir = PACKAGE_ROOT.joinpath(*module_parts)
    if candidate_dir.is_dir():
        return candidate_dir / "__init__.py"
    return PACKAGE_ROOT.joinpath(*module_parts).with_suffix(".py")


def _build_import_map(module_name: str) -> dict[str, str]:
    import_map: dict[str, str] = {}
    tree = _parse_module_ast(module_name)
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level > 0:
            module_parts = node.module.split(".") if node.module else []
            origin_module = ".".join([module_name, *module_parts]).rstrip(".")
        elif node.module is not None:
            origin_module = node.module
        else:
            continue

        for alias in node.names:
            import_map[alias.asname or alias.name] = origin_module
    return import_map


def _is_type_alias_expr(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Name):
        return node.id in builtins.__dict__ or node.id[:1].isupper()
    if isinstance(node, ast.Attribute):
        return True
    if isinstance(node, ast.Subscript):
        return _is_type_alias_expr(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_type_alias_expr(node.left) and _is_type_alias_expr(node.right)
    return False


def _build_definition_kinds(module_name: str) -> dict[str, str]:
    module_path = _origin_module_path(module_name)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    kinds: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            kinds[node.name] = "class"
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kinds[node.name] = "callable"
            continue
        if hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
            kinds[node.name.id] = "type_alias"
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    kinds[target.id] = (
                        "type_alias" if _is_type_alias_expr(node.value) else "value"
                    )
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            kinds[node.target.id] = (
                "type_alias" if _is_type_alias_expr(node.value) else "value"
            )
    return kinds


def _documented_public_modules() -> set[str]:
    modules: set[str] = set()
    for line in API_DOC_PATH.read_text(encoding="utf-8").splitlines():
        match = DOC_DIRECTIVE_RE.match(line.strip())
        if match:
            modules.add(match.group(1))
    return modules


def _validate_docs_api_coverage() -> None:
    documented = _documented_public_modules()
    if documented != set(PUBLIC_MODULES):
        raise ValueError(
            "docs/api.md public namespace coverage mismatch for `subway_access`."
        )


def _origin_module_path(module_name: str) -> Path:
    if module_name == "subway_access._version":
        return PACKAGE_ROOT / "_version.py"
    module_parts = module_name.split(".")[1:]
    candidate_dir = PACKAGE_ROOT.joinpath(*module_parts)
    if candidate_dir.is_dir():
        return candidate_dir / "__init__.py"
    return PACKAGE_ROOT.joinpath(*module_parts).with_suffix(".py")


def main() -> int:
    rows: list[AuditRow] = []
    for module_name in PUBLIC_MODULES:
        module = importlib.import_module(module_name)
        names = getattr(module, "__all__", None)
        if not isinstance(names, list):
            raise ValueError(f"{module_name} must define __all__ as a list.")

        import_map = _build_import_map(module_name)
        for symbol_name in names:
            if not isinstance(symbol_name, str):
                raise ValueError(f"{module_name}.__all__ must contain only strings.")
            if symbol_name.startswith("_") and symbol_name not in ALLOWED_PRIVATE_EXPORTS:
                raise ValueError(
                    f"{module_name}.__all__ must not export private name {symbol_name!r}."
                )
            if not hasattr(module, symbol_name):
                raise ValueError(
                    f"{module_name}.__all__ references missing symbol {symbol_name!r}."
                )

            symbol = getattr(module, symbol_name)
            origin_module = import_map.get(
                symbol_name,
                getattr(symbol, "__module__", module_name),
            )
            if symbol_name == "__version__":
                origin_module = "subway_access._version"

            definition_kinds = _build_definition_kinds(origin_module)
            if symbol_name in definition_kinds:
                kind = definition_kinds[symbol_name]
                if kind == "type_alias":
                    type_alias_type = getattr(__import__("typing"), "TypeAliasType", None)
                    if type_alias_type is None or not isinstance(symbol, type_alias_type):
                        kind = "value"
            elif inspect.isclass(symbol):
                kind = "class"
            elif callable(symbol):
                kind = "callable"
            else:
                kind = "value"
            rows.append(
                AuditRow(
                    public_module=module_name,
                    symbol_name=symbol_name,
                    origin_module=origin_module,
                    kind=kind,
                )
            )

    _validate_docs_api_coverage()

    lines = [
        "# subway_access public API audit",
        "",
        f"- public modules: {len(PUBLIC_MODULES)}",
        f"- public symbols: {len(rows)}",
        "",
        "| Public Module | Symbol | Origin | Kind |",
        "| --- | --- | --- | --- |",
        *[
            f"| `{row.public_module}` | `{row.symbol_name}` | `{row.origin_module}` | `{row.kind}` |"
            for row in rows
        ],
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
