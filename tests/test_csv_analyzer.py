"""
Tests for CSV Analyzer Tool
"""

import pytest
import pandas as pd
from pathlib import Path

from tools.csv_analyzer import csv_analyze, csv_query, csv_export
from tools.registry import registry


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    data = {
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "age": [25, 30, 35, 28, 32],
        "city": ["Jakarta", "Bandung", "Jakarta", "Surabaya", "Bandung"],
        "salary": [5000000, 7000000, 8000000, 6000000, 7500000]
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "sample.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def test_csv_tools_registered():
    """Test CSV tools are registered."""
    assert registry.has_tool("csv_analyze")
    assert registry.has_tool("csv_query")
    assert registry.has_tool("csv_export")


@pytest.mark.asyncio
async def test_csv_analyze(sample_csv, monkeypatch):
    """Test CSV analysis."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    result = await csv_analyze(sample_csv.name)

    assert "sample.csv" in result
    assert "5" in result or "baris" in result  # 5 rows
    assert "name" in result
    assert "age" in result


@pytest.mark.asyncio
async def test_csv_query(sample_csv, monkeypatch):
    """Test CSV querying."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    result = await csv_query(
        sample_csv.name,
        query="age > 30"
    )

    assert "Charlie" in result
    assert "Eve" in result


@pytest.mark.asyncio
async def test_csv_query_group_by(sample_csv, monkeypatch):
    """Test CSV grouping."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    result = await csv_query(
        sample_csv.name,
        group_by="city",
        aggregate="count"
    )

    assert "Jakarta" in result
    assert "Bandung" in result


@pytest.mark.asyncio
async def test_csv_query_sort(sample_csv, monkeypatch):
    """Test CSV sorting."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    result = await csv_query(
        sample_csv.name,
        sort_by="age",
        ascending=True,
        limit=3
    )

    assert "Alice" in result  # age 25


@pytest.mark.asyncio
async def test_csv_export(sample_csv, tmp_path, monkeypatch):
    """Test CSV export."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    output_file = "exported.csv"
    result = await csv_export(
        sample_csv.name,
        output_file,
        query="city == 'Jakarta'"
    )

    assert "berhasil" in result.lower() or "2 baris" in result

    # Verify exported file
    exported_path = sample_csv.parent / output_file
    assert exported_path.exists()


@pytest.mark.asyncio
async def test_csv_export_select_columns(sample_csv, monkeypatch):
    """Test CSV export with column selection."""
    monkeypatch.setattr("tools.csv_analyzer.WORKSPACE_DIR", sample_csv.parent)

    result = await csv_export(
        sample_csv.name,
        "subset.csv",
        columns="name,salary"
    )

    assert "berhasil" in result.lower() or "5 baris" in result