"""Optional reporting helpers: jellycell tearsheets from factor-factory engine results.

This module is an **optional** surface. All dependencies on ``factor_factory``
and ``jellycell`` are deferred to call time, so importing
``subway_access.reporting`` succeeds even when those extras are not installed.
Invoking any of the helpers below without the relevant extras raises a
:class:`ImportError` that points at the right ``pip install`` command.

Install via::

    pip install "subway-access[factor-factory,tearsheets]"
"""

from __future__ import annotations

from ._jellycell_bridge import (
    EngineKind,
    emit_findings_tearsheet,
    render_findings_from_dict,
    require_factor_factory,
    require_jellycell,
    write_engine_results_json,
)

__all__ = [
    "EngineKind",
    "emit_findings_tearsheet",
    "render_findings_from_dict",
    "require_factor_factory",
    "require_jellycell",
    "write_engine_results_json",
]
