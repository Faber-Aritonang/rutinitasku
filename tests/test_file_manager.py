"""
Tests for File Manager Tool
"""

import pytest
import os
import tempfile
from pathlib import Path

from tools.file_manager import _validate_path, file_list, file_read, file_write, file_info


@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path / "workspace"


def test_validate_path_within_sandbox(workspace_dir):
    """Test path validation allows paths within sandbox."""
    workspace_dir.mkdir(parents=True)
    test_file = workspace_dir / "test.txt"
    test_file.write_text("test")

    result = _validate_path("test.txt", workspace_dir)
    assert result == test_file.resolve()


def test_validate_path_rejects_traversal(workspace_dir):
    """Test path validation rejects directory traversal."""
    workspace_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="Akses ditolak"):
        _validate_path("../../etc/passwd", workspace_dir)


def test_validate_path_absolute_within_sandbox(workspace_dir):
    """Test absolute path within sandbox is allowed."""
    workspace_dir.mkdir(parents=True)
    test_file = workspace_dir / "test.txt"
    test_file.write_text("test")

    result = _validate_path(str(test_file), workspace_dir)
    assert result == test_file.resolve()


@pytest.mark.asyncio
async def test_file_write_and_read(workspace_dir, monkeypatch):
    """Test writing and reading a file."""
    workspace_dir.mkdir(parents=True)
    monkeypatch.setattr("tools.file_manager.WORKSPACE_DIR", workspace_dir)

    # Write file
    result = await file_write("test.txt", "Hello World")
    assert "berhasil" in result.lower() or "Berhasil" in result

    # Read file
    result = await file_read("test.txt")
    assert "Hello World" in result


@pytest.mark.asyncio
async def test_file_list(workspace_dir, monkeypatch):
    """Test listing directory contents."""
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "file1.txt").write_text("content1")
    (workspace_dir / "file2.txt").write_text("content2")

    monkeypatch.setattr("tools.file_manager.WORKSPACE_DIR", workspace_dir)

    result = await file_list(".")
    assert "file1.txt" in result
    assert "file2.txt" in result


@pytest.mark.asyncio
async def test_file_info(workspace_dir, monkeypatch):
    """Test getting file information."""
    workspace_dir.mkdir(parents=True)
    test_file = workspace_dir / "test.txt"
    test_file.write_text("Hello World")

    monkeypatch.setattr("tools.file_manager.WORKSPACE_DIR", workspace_dir)

    result = await file_info("test.txt")
    assert "test.txt" in result
    assert "11" in result or "bytes" in result  # 11 bytes for "Hello World"


@pytest.mark.asyncio
async def test_file_read_nonexistent(workspace_dir, monkeypatch):
    """Test reading non-existent file."""
    workspace_dir.mkdir(parents=True)
    monkeypatch.setattr("tools.file_manager.WORKSPACE_DIR", workspace_dir)

    result = await file_read("nonexistent.txt")
    assert "tidak ditemukan" in result.lower() or "not found" in result.lower()


@pytest.mark.asyncio
async def test_file_write_creates_dirs(workspace_dir, monkeypatch):
    """Test writing creates parent directories."""
    workspace_dir.mkdir(parents=True)
    monkeypatch.setattr("tools.file_manager.WORKSPACE_DIR", workspace_dir)

    result = await file_write("subdir/nested/file.txt", "content")
    assert "berhasil" in result.lower() or "Berhasil" in result
    assert (workspace_dir / "subdir" / "nested" / "file.txt").exists()