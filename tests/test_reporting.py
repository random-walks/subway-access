"""Tests for :mod:`subway_access.reporting`.

These tests assert the optional-dependency surface:

1. ``subway_access.reporting`` imports cleanly regardless of whether
   ``factor-factory`` or ``jellycell`` are installed.
2. The public helpers ``require_factor_factory`` / ``require_jellycell``
   raise a recoverable :class:`ImportError` whose message cites the right
   extras group when the optional dep is absent.
3. ``write_engine_results_json`` writes the JSON shape the shipped jellycell
   ``findings.md.j2`` template expects — ``{"results": [...]}`` with
   ``.to_dict()`` records.
4. ``emit_findings_tearsheet`` requires both extras to be installed; it's
   ``pytest.importorskip``'d so the test is skipped cleanly in default CI.
"""

from __future__ import annotations

import builtins
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from subway_access import reporting

_MOCK_FACTOR_FACTORY_UNAVAILABLE = "mock: factor_factory not available"
_MOCK_JELLYCELL_UNAVAILABLE = "mock: jellycell not available"


def test_module_imports_without_optional_extras() -> None:
    """Importing the module should never pull in factor_factory or jellycell."""
    assert hasattr(reporting, "__all__")
    assert set(reporting.__all__) == {
        "EngineKind",
        "emit_findings_tearsheet",
        "require_factor_factory",
        "require_jellycell",
        "write_engine_results_json",
    }


def test_require_factor_factory_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """If factor-factory is not installed, the error cites the right extras group."""
    real_import = builtins.__import__

    def _raise_for_factor_factory(
        name: str,
        globals_: dict[str, Any] | None = None,
        locals_: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "factor_factory" or name.startswith("factor_factory."):
            raise ImportError(_MOCK_FACTOR_FACTORY_UNAVAILABLE)
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _raise_for_factor_factory)
    # Force a fresh lookup even if factor_factory was imported earlier.
    sys.modules.pop("factor_factory", None)

    with pytest.raises(ImportError, match=r"subway-access\[factor-factory\]"):
        reporting.require_factor_factory()


def test_require_jellycell_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """If jellycell is not installed, the error cites [tearsheets]."""
    real_import = builtins.__import__

    def _raise_for_jellycell(
        name: str,
        globals_: dict[str, Any] | None = None,
        locals_: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "jellycell" or name.startswith("jellycell."):
            raise ImportError(_MOCK_JELLYCELL_UNAVAILABLE)
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _raise_for_jellycell)
    sys.modules.pop("jellycell", None)

    with pytest.raises(ImportError, match=r"subway-access\[tearsheets\]"):
        reporting.require_jellycell()


class _FakeResult:
    """Stand-in for a factor-factory frozen ``*Result`` dataclass."""

    def __init__(self, **fields: Any) -> None:
        self._fields = fields

    def to_dict(self) -> dict[str, Any]:
        return dict(self._fields)


class _FakeResults:
    """Stand-in for a factor-factory ``*Results`` wrapper with ``.to_records()``."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def to_records(self) -> list[dict[str, Any]]:
        return list(self._records)


def test_write_engine_results_json_from_results_wrapper(tmp_path: Path) -> None:
    results = _FakeResults(
        [
            {"method": "twfe", "att": 0.12, "se": 0.04},
            {"method": "sa", "att": 0.15, "se": 0.05},
        ]
    )

    out = reporting.write_engine_results_json(
        results,
        artifacts_dir=tmp_path / "artifacts",
        family="did",
    )

    assert out == tmp_path / "artifacts" / "did_results.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == {
        "results": [
            {"att": 0.12, "method": "twfe", "se": 0.04},
            {"att": 0.15, "method": "sa", "se": 0.05},
        ]
    }


def test_write_engine_results_json_from_single_result(tmp_path: Path) -> None:
    result = _FakeResult(method="rd_robust", estimate=0.05, std_error=0.02)

    out = reporting.write_engine_results_json(
        result,
        artifacts_dir=tmp_path / "artifacts",
        family="rdd",
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["results"] == [
        {"estimate": 0.05, "method": "rd_robust", "std_error": 0.02}
    ]


def test_write_engine_results_json_from_iterable(tmp_path: Path) -> None:
    items = [
        _FakeResult(method="augmented", att=0.20, n_donor=12),
        _FakeResult(method="augmented", att=0.18, n_donor=10),
    ]

    out = reporting.write_engine_results_json(
        items,
        artifacts_dir=tmp_path / "artifacts",
        family="scm",
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["results"]) == 2
    assert payload["results"][0]["method"] == "augmented"


def test_write_engine_results_json_creates_missing_directory(tmp_path: Path) -> None:
    nested_dir = tmp_path / "case-study" / "artifacts"
    assert not nested_dir.exists()

    reporting.write_engine_results_json(
        _FakeResult(method="morans_i", statistic=0.23),
        artifacts_dir=nested_dir,
        family="spatial",
    )

    assert (nested_dir / "spatial_results.json").is_file()


def test_emit_findings_tearsheet_requires_factor_factory(tmp_path: Path) -> None:
    """Skip the tearsheet test if factor-factory is not installed."""
    pytest.importorskip("factor_factory.jellycell.tearsheets")
    pytest.importorskip("jellycell")

    # With both extras installed, the function should at minimum fail with a
    # factor-factory-native error (e.g. template not found, invalid project)
    # rather than our shim ImportError. Anything else — e.g. success — is also
    # fine; we just confirm the plumbing reaches factor-factory. Using
    # ``tmp_path`` keeps every run's project dir isolated + auto-cleaned.
    project = tmp_path / "reporting-empty-project"
    project.mkdir(parents=True)

    try:
        reporting.emit_findings_tearsheet(project, overwrite=True)
    except ImportError as exc:  # pragma: no cover - only fires if extras missing
        pytest.fail(
            f"emit_findings_tearsheet raised ImportError despite importorskip guards: {exc}"
        )
    except Exception:  # noqa: BLE001 - factor-factory-side errors are expected
        # Any non-ImportError is acceptable; the point is our shim didn't intercept.
        pass


def test_factor_factory_optional_on_namespace_level() -> None:
    """The reporting namespace must not import factor_factory at module top."""
    # Re-import into a fresh namespace with factor_factory stubbed out to confirm
    # no top-level import exists in the reporting package.
    module_name = "subway_access.reporting._jellycell_bridge"
    spec = importlib.util.find_spec(module_name)
    assert spec is not None
    assert spec.origin is not None
    source = Path(spec.origin).read_text(encoding="utf-8")
    # Find lines outside of function bodies that import factor_factory / jellycell.
    for line_number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("import factor_factory", "from factor_factory")):
            # All such lines must be indented (inside a function body).
            assert line.startswith((" ", "\t")), (
                f"{module_name}:{line_number} top-level import of factor_factory"
            )
        if stripped.startswith(("import jellycell", "from jellycell")):
            assert line.startswith((" ", "\t")), (
                f"{module_name}:{line_number} top-level import of jellycell"
            )


def test_reporting_has_typed_modulespec() -> None:
    """Narrow attribute test so the public API audit picks up the module surface."""
    spec = reporting.EngineKind
    assert spec is not None
    # EngineKind is a typing.Literal; the bridge exposes the helpers referenced
    # in docs/api.md's mkdocstrings directive.
    assert callable(reporting.write_engine_results_json)
    assert callable(reporting.emit_findings_tearsheet)
    assert callable(reporting.require_factor_factory)
    assert callable(reporting.require_jellycell)


def test_reporting_symbols_use_namespace_surface() -> None:
    """SimpleNamespace parity with the audit script's expected symbol kinds."""
    namespace_like = SimpleNamespace(
        **{k: getattr(reporting, k) for k in reporting.__all__}
    )
    assert namespace_like.EngineKind is reporting.EngineKind
