"""Generic export utilities for frozen dataclass records."""

from __future__ import annotations

import csv
from dataclasses import asdict, fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def dataclass_fieldnames(cls: type) -> tuple[str, ...]:
    """Return field names for a frozen dataclass type.

    Args:
        cls: A dataclass type.

    Returns:
        Tuple of field name strings in declaration order.

    Example:
        >>> from subway_access.models import GapRecord
        >>> dataclass_fieldnames(GapRecord)
        ('tract_id', 'tract_name', 'borough', ...)
    """

    return tuple(f.name for f in fields(cls))


def export_records_csv(
    records: tuple[Any, ...],
    path: Path,
    *,
    fieldnames: tuple[str, ...] | None = None,
    formatters: dict[str, str] | None = None,
) -> Path:
    """Export a tuple of frozen dataclass records to CSV.

    Automatically extracts field names from the dataclass type if
    ``fieldnames`` is not provided.

    Args:
        records: Tuple of frozen dataclass instances.
        path: Output file path.
        fieldnames: Column names to include. Defaults to all fields.
        formatters: Optional mapping of field name to format string
            (e.g. ``{"disability_rate": ".4f"}``).

    Returns:
        The resolved output path.

    Example:
        >>> export_records_csv(gap_analysis.records, Path("gaps.csv"))
        PosixPath('gaps.csv')
    """

    if not records:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return path

    names = fieldnames or dataclass_fieldnames(type(records[0]))
    fmt = formatters or {}

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(names))
        writer.writeheader()
        for record in records:
            row_data = asdict(record)
            row: dict[str, Any] = {}
            for name in names:
                value = row_data.get(name)
                if value is None:
                    row[name] = ""
                elif name in fmt:
                    row[name] = format(value, fmt[name])
                else:
                    row[name] = value
            writer.writerow(row)

    return path
