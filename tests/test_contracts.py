"""Consumer contract tests — verify every public symbol is importable and well-formed."""

from __future__ import annotations

import importlib
from dataclasses import fields

PUBLIC_MODULES = (
    "subway_access",
    "subway_access.analysis",
    "subway_access.cli",
    "subway_access.export",
    "subway_access.factors",
    "subway_access.helpers",
    "subway_access.io",
    "subway_access.models",
    "subway_access.pipeline",
    "subway_access.temporal",
)


def test_all_modules_importable() -> None:
    for name in PUBLIC_MODULES:
        module = importlib.import_module(name)
        assert hasattr(module, "__all__"), f"{name} must define __all__"


def test_all_symbols_importable() -> None:
    for name in PUBLIC_MODULES:
        module = importlib.import_module(name)
        for symbol_name in module.__all__:
            assert hasattr(module, symbol_name), (
                f"{name}.{symbol_name} declared in __all__ but missing"
            )


def test_model_dataclasses_are_frozen() -> None:
    models = importlib.import_module("subway_access.models")
    for symbol_name in models.__all__:
        obj = getattr(models, symbol_name)
        if not isinstance(obj, type):
            continue
        try:
            dc_fields = fields(obj)
        except TypeError:
            continue
        params = obj.__dataclass_params__  # type: ignore[attr-defined]
        assert params.frozen, f"{symbol_name} must be frozen"
        if dc_fields and hasattr(params, "slots"):
            assert params.slots, f"{symbol_name} must use slots"
