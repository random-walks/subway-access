"""CLI scaffold for the future ``subway-access`` command."""

from __future__ import annotations

from collections.abc import Sequence

from ._not_implemented import planned_surface


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the future command-line interface."""
    del argv
    planned_surface("subway-access CLI")
