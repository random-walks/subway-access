"""Cache helpers for ``subway-access`` real-data snapshots."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for cache metadata."""

    return datetime.now(tz=timezone.utc).isoformat()


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> Path:
    """Write a tabular CSV snapshot."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_json(path: Path, payload: object) -> Path:
    """Write JSON with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return path
