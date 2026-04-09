"""Metadata and report writing helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def write_metadata_json(
    path: Path,
    *,
    title: str,
    generated_at: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write a timestamped metadata JSON file.

    Args:
        path: Output file path.
        title: Human-readable title for the metadata record.
        generated_at: Timestamp. Defaults to now (UTC).
        extra: Additional key-value pairs to include.

    Returns:
        The resolved output path.

    Example:
        >>> write_metadata_json(
        ...     Path("metadata.json"),
        ...     title="Manhattan gap analysis",
        ...     extra={"tract_count": 200},
        ... )
    """

    payload: dict[str, Any] = {
        "title": title,
        "generated_at": (generated_at or datetime.now(tz=timezone.utc)).isoformat(),
    }
    if extra:
        payload.update(extra)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return path


def write_markdown_report(
    path: Path,
    content: str,
) -> Path:
    """Write a markdown report file.

    Args:
        path: Output file path.
        content: Markdown content to write.

    Returns:
        The resolved output path.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
