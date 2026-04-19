"""Implementation for :mod:`subway_access.reporting`.

Every function defers imports of ``factor_factory`` and ``jellycell`` so this
module stays importable without the optional extras. Errors point at the
right extras group so users can recover in one step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:  # pragma: no cover - import-time only for type checkers.
    from collections.abc import Iterable
    from types import ModuleType

EngineKind = Literal["did", "rdd", "scm", "spatial", "event_study", "mediation"]
"""Factor-factory engine-family identifiers supported by the bridge.

The family name is used as the artifact filename stem: an ``EngineKind`` of
``"did"`` writes to ``<artifacts_dir>/did_results.json``, matching the key
the shipped jellycell ``findings`` template reads from.
"""

_FACTOR_FACTORY_HINT = (
    "factor-factory is required for engine-based reporting. "
    "Install via 'pip install \"subway-access[factor-factory]\"'."
)
_JELLYCELL_HINT = (
    "jellycell is required for tearsheet rendering. "
    "Install via 'pip install \"subway-access[tearsheets]\"'."
)


def require_factor_factory() -> ModuleType:
    """Return the ``factor_factory`` top-level module or raise a crisp error.

    Returns
    -------
    ModuleType
        The imported ``factor_factory`` module.

    Raises
    ------
    ImportError
        If ``factor-factory`` is not installed. The message includes the
        exact ``pip install`` command to recover.
    """
    try:
        import factor_factory
    except ImportError as exc:  # pragma: no cover - exercised in lazy-import tests
        raise ImportError(_FACTOR_FACTORY_HINT) from exc
    # The paired ignore codes are intentional: ``no-any-return`` fires when
    # factor-factory is NOT installed (the mypy override treats the import
    # as ``Any``), and ``unused-ignore`` silences mypy when it IS installed
    # (the real module resolves cleanly). Keeping both keeps CI green under
    # either environment.
    return factor_factory  # type: ignore[no-any-return, unused-ignore]


def require_jellycell() -> ModuleType:
    """Return the ``jellycell`` top-level module or raise a crisp error.

    Returns
    -------
    ModuleType
        The imported ``jellycell`` module.

    Raises
    ------
    ImportError
        If ``jellycell`` is not installed. The message includes the exact
        ``pip install`` command to recover.
    """
    try:
        import jellycell
    except ImportError as exc:  # pragma: no cover - exercised in lazy-import tests
        raise ImportError(_JELLYCELL_HINT) from exc
    return jellycell  # type: ignore[no-any-return, unused-ignore]


def write_engine_results_json(
    results: Iterable[Any] | Any,
    *,
    artifacts_dir: Path,
    family: EngineKind | str,
) -> Path:
    """Serialize one or more factor-factory engine results to ``<family>_results.json``.

    The shipped jellycell ``findings.md.j2`` template reads from a structured
    JSON file at ``<project_dir>/artifacts/<family>_results.json`` with the
    shape ``{"results": [<to_dict>...]}``. This helper accepts either a
    single result dataclass (with a ``.to_dict()`` method), an iterable of
    them, or a pre-built ``Results`` wrapper (with a ``.to_records()``
    method, as returned by ``factor_factory.engines.<family>.estimate(...)``).

    Parameters
    ----------
    results
        One of:

        - A ``*Results`` wrapper exposing ``.to_records()`` (e.g.
          ``DidResults``, ``RddResults``, ``ScmResults``, ``SpatialResults``).
        - A single ``*Result`` frozen dataclass exposing ``.to_dict()``.
        - An iterable of such dataclasses.

    artifacts_dir
        Directory where the JSON file is written. Created if it does not
        already exist.
    family
        Engine-family name used as the filename stem. Supported values are
        listed in :data:`EngineKind`; any string is accepted to support
        downstream engines not yet enumerated here.

    Returns
    -------
    Path
        The absolute path of the written JSON file.
    """
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]]
    if hasattr(results, "to_records") and not isinstance(results, (list, tuple)):
        records = list(results.to_records())
    elif hasattr(results, "to_dict") and not isinstance(results, (list, tuple)):
        records = [results.to_dict()]
    else:
        records = [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in results
        ]

    output_path = artifacts_dir / f"{family}_results.json"
    output_path.write_text(
        json.dumps({"results": records}, indent=2, default=str, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def emit_findings_tearsheet(
    project_dir: Path,
    *,
    overwrite: bool = True,
    template_overrides: dict[str, Any] | None = None,
) -> Path:
    """Render the ``FINDINGS.md`` tearsheet for a project directory.

    Thin wrapper around ``factor_factory.jellycell.tearsheets.findings(...)``.
    The target project directory is expected to follow the factor-factory
    convention:

    - ``<project_dir>/artifacts/<family>_results.json`` (one per engine family
      fit, written via :func:`write_engine_results_json`)
    - ``<project_dir>/artifacts/figures/`` (optional, picked up by the
      template if present)
    - ``<project_dir>/manuscripts/FINDINGS.md`` (the rendered output)

    The freeze-marker splicing behavior of factor-factory is preserved: when
    ``overwrite=True``, any text in an existing ``FINDINGS.md`` that sits
    *below* a ``<!-- tearsheet:freeze -->`` line is kept verbatim; text above
    the marker is regenerated from the template.

    Parameters
    ----------
    project_dir
        Absolute or relative path to the project directory.
    overwrite
        When ``True`` (the default), regenerate the tearsheet using
        freeze-marker splicing. When ``False``, raise ``FileExistsError`` if
        the target already exists.
    template_overrides
        Optional mapping overlaid on top of the default template context.
        Keys depend on the shipped ``findings.md.j2`` template — consult
        factor-factory documentation for the supported fields.

    Returns
    -------
    Path
        The absolute path of the rendered tearsheet.

    Raises
    ------
    ImportError
        If ``factor-factory`` (which bundles jellycell bindings) is not
        installed.
    """
    factor_factory = require_factor_factory()
    # jellycell is a direct runtime dep of factor-factory's tearsheet renderer;
    # surface the friendlier subway-access-specific hint up front so install
    # guidance is consistent.
    require_jellycell()

    from factor_factory.jellycell.tearsheets import (  # pylint: disable=import-error
        findings as _render_findings,
    )

    _ = factor_factory  # kept for the import-validation side-effect above

    rendered = _render_findings(
        project=str(Path(project_dir).resolve()),
        overwrite=overwrite,
        template_overrides=template_overrides,
    )
    return Path(rendered)
