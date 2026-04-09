"""Tests for the helpers subpackage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from subway_access.helpers import (
    ALL_BOROUGHS,
    borough_cache_dir,
    dataclass_fieldnames,
    export_records_csv,
    write_markdown_report,
    write_metadata_json,
)


class TestBoroughCacheDir:
    def test_basic(self) -> None:
        result = borough_cache_dir("/tmp/cache", "Manhattan")
        assert result.name == "manhattan"

    def test_space_in_name(self) -> None:
        result = borough_cache_dir("/tmp/cache", "Staten Island")
        assert result.name == "staten-island"

    def test_all_boroughs_constant(self) -> None:
        assert len(ALL_BOROUGHS) == 5
        assert "Manhattan" in ALL_BOROUGHS


@dataclass(frozen=True, slots=True)
class _SampleRecord:
    name: str
    value: float
    count: int


class TestDataclassFieldnames:
    def test_basic(self) -> None:
        names = dataclass_fieldnames(_SampleRecord)
        assert names == ("name", "value", "count")


class TestExportRecordsCsv:
    def test_basic_export(self, tmp_path: Path) -> None:
        records = (
            _SampleRecord(name="a", value=1.5, count=10),
            _SampleRecord(name="b", value=2.7, count=20),
        )
        output = export_records_csv(records, tmp_path / "out.csv")
        assert output.exists()
        lines = output.read_text(encoding="utf-8").strip().splitlines()
        assert lines[0] == "name,value,count"
        assert len(lines) == 3

    def test_with_formatters(self, tmp_path: Path) -> None:
        records = (_SampleRecord(name="a", value=1.23456, count=10),)
        output = export_records_csv(
            records,
            tmp_path / "fmt.csv",
            formatters={"value": ".2f"},
        )
        content = output.read_text(encoding="utf-8")
        assert "1.23" in content
        assert "1.23456" not in content

    def test_empty_records(self, tmp_path: Path) -> None:
        output = export_records_csv((), tmp_path / "empty.csv")
        assert output.exists()

    def test_custom_fieldnames(self, tmp_path: Path) -> None:
        records = (_SampleRecord(name="a", value=1.5, count=10),)
        output = export_records_csv(
            records,
            tmp_path / "subset.csv",
            fieldnames=("name", "count"),
        )
        header = output.read_text(encoding="utf-8").splitlines()[0]
        assert header == "name,count"


class TestWriteMetadataJson:
    def test_basic(self, tmp_path: Path) -> None:
        output = write_metadata_json(
            tmp_path / "meta.json",
            title="Test",
            extra={"count": 42},
        )
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["title"] == "Test"
        assert data["count"] == 42
        assert "generated_at" in data


class TestWriteMarkdownReport:
    def test_basic(self, tmp_path: Path) -> None:
        output = write_markdown_report(tmp_path / "report.md", "# Hello\n")
        assert output.exists()
        assert output.read_text(encoding="utf-8") == "# Hello\n"
