"""Reusable helpers extracted from example scaffolding."""

from __future__ import annotations

from ._export import dataclass_fieldnames, export_records_csv
from ._iteration import (
    ALL_BOROUGHS,
    borough_cache_dir,
    fetch_borough_snapshots,
    iter_borough_snapshots,
    load_borough_snapshots,
)
from ._metadata import write_markdown_report, write_metadata_json

__all__ = [
    "ALL_BOROUGHS",
    "borough_cache_dir",
    "dataclass_fieldnames",
    "export_records_csv",
    "fetch_borough_snapshots",
    "iter_borough_snapshots",
    "load_borough_snapshots",
    "write_markdown_report",
    "write_metadata_json",
]
