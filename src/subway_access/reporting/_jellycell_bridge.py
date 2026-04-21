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
    from collections.abc import Iterable, Mapping
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
_JELLYCELL_14_HINT = (
    "jellycell>=1.4 is required for render_findings_from_dict — the "
    "'jellycell.tearsheets' module was introduced in v1.4.0. "
    "Install via 'pip install \"jellycell>=1.4\"' (or "
    "'pip install --upgrade jellycell' if [tearsheets] is already installed)."
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
    # Trailing newline keeps `end-of-file-fixer` (pre-commit) happy when the
    # JSON is committed alongside a jellycell-backed example.
    output_path.write_text(
        json.dumps({"results": records}, indent=2, default=str, sort_keys=True) + "\n",
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


def render_findings_from_dict(
    results: Mapping[str, Mapping[str, Any]],
    *,
    out_path: Path,
    project: str,
    template_overrides: Mapping[str, Any] | None = None,
) -> Path:
    """Render a ``FINDINGS.md`` tearsheet directly from in-memory results.

    Thin wrapper over
    [``jellycell.tearsheets.findings``](https://github.com/random-walks/jellycell/releases/tag/v1.4.0)
    (new in jellycell v1.4.0). Complementary to
    :func:`emit_findings_tearsheet`: that helper scans a factor-factory project
    directory for ``artifacts/<family>_results.json`` files and renders
    ``manuscripts/FINDINGS.md`` with freeze-marker splicing. This one takes a
    plain Python dict and writes to any path — useful when you already have
    engine fits in memory (notebook, CI smoke, blog-post assembly) and don't
    want the project-directory dance.

    Parameters
    ----------
    results
        Mapping of ``method_name -> {field: value}``. One ``## <method_name>``
        heading + two-column metric table is emitted per top-level key. Nested
        dicts flatten with dotted keys (``{"cs": {"att": 0.2}}`` →  ``cs.att``
        row). The canonical way to produce this shape from factor-factory
        results is::

            results_dict = {r.method: r.to_dict() for r in did_results}

    out_path
        Target markdown path. Parent directories are created if needed.
    project
        Project name rendered in the manuscript header (e.g.
        ``"subway-access / accessibility-change"``). Does not have to be a
        filesystem path — this is just a label.
    template_overrides
        Optional header-field overrides forwarded to
        ``jellycell.tearsheets.findings``. Supported keys include ``author``,
        ``author_url``, ``month_year``, ``version``, ``project``.

    Returns
    -------
    Path
        The resolved path of the rendered tearsheet.

    Raises
    ------
    ImportError
        If ``jellycell`` is not installed (points at ``[tearsheets]``) or if
        the installed ``jellycell`` is older than v1.4.0.
    """
    require_jellycell()
    try:
        from jellycell.tearsheets import (  # pylint: disable=import-error
            findings as _jc_findings,
        )
    except ImportError as exc:  # pragma: no cover - exercised in lazy-import tests
        raise ImportError(_JELLYCELL_14_HINT) from exc

    rendered = _jc_findings(
        results=dict(results),
        out_path=str(out_path),
        project=project,
        template_overrides=dict(template_overrides) if template_overrides else None,
    )
    return Path(rendered)
