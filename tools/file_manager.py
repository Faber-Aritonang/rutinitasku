"""
RutinitasKu - File Manager Tool
Sandboxed file operations within workspace.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

from config import WORKSPACE_DIR, UPLOADS_DIR
from .registry import registry


def _validate_path(file_path: str, base_dir: Path) -> Path:
    """
    Validate and resolve file path within sandbox.

    Args:
        file_path: Relative or absolute file path
        base_dir: Base directory for sandboxing

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is outside sandbox
    """
    path = Path(file_path)

    # If relative, resolve against base directory
    if not path.is_absolute():
        path = base_dir / path

    # Resolve to absolute path
    path = path.resolve()

    # Check if path is within sandbox
    if not str(path).startswith(str(base_dir.resolve())):
        raise ValueError(f"Akses ditolak: {file_path} berada di luar workspace")

    return path


@registry.tool(
    name="file_list",
    description="List file dan folder dalam direktori workspace.",
    input_schema={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Path direktori (default: root workspace)",
                "default": "."
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Tampilkan file hidden (default: false)",
                "default": False
            }
        },
        "required": []
    }
)
async def file_list(directory: str = ".", show_hidden: bool = False) -> str:
    """
    List files in workspace directory.

    Args:
        directory: Directory path relative to workspace
        show_hidden: Whether to show hidden files

    Returns:
        Formatted file listing
    """
    try:
        dir_path = _validate_path(directory, WORKSPACE_DIR)

        if not dir_path.exists():
            return f"Direktori tidak ditemukan: {directory}"

        if not dir_path.is_dir():
            return f"{directory} bukan direktori"

        items = []
        for item in sorted(dir_path.iterdir()):
            # Skip hidden files if not requested
            if not show_hidden and item.name.startswith("."):
                continue

            stat = item.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            if item.is_dir():
                items.append(f"📁 {item.name}/  ({modified})")
            else:
                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                items.append(f"📄 {item.name}  ({size_str}, {modified})")

        if not items:
            return f"Direktori kosong: {directory}"

        return f"Isi direktori '{directory}':\n\n" + "\n".join(items)

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat list file: {str(e)}"


@registry.tool(
    name="file_read",
    description="Baca isi file teks (TXT, MD, JSON, CSV, PY, dll).",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file yang akan dibaca"
            },
            "max_chars": {
                "type": "integer",
                "description": "Maksimal karakter yang dibaca (default: 10000)",
                "default": 10000
            }
        },
        "required": ["file_path"]
    }
)
async def file_read(file_path: str, max_chars: int = 10000) -> str:
    """
    Read text file content.

    Args:
        file_path: Path to file
        max_chars: Maximum characters to read

    Returns:
        File content
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        if not path.is_file():
            return f"{file_path} bukan file"

        # Check file size
        size = path.stat().st_size
        if size > 10 * 1024 * 1024:  # 10MB limit
            return f"File terlalu besar ({size / (1024*1024):.1f} MB). Maksimal 10 MB."

        # Read file
        content = path.read_text(encoding="utf-8")

        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[... file dipotong, total {len(content)} karakter]"

        return f"Isi file '{file_path}':\n\n{content}"

    except UnicodeDecodeError:
        return f"Error: '{file_path}' bukan file teks atau encoding tidak didukung"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat baca file: {str(e)}"


@registry.tool(
    name="file_write",
    description="Tulis konten ke file. Buat file baru atau overwrite yang sudah ada.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file yang akan ditulis"
            },
            "content": {
                "type": "string",
                "description": "Konten yang akan ditulis ke file"
            },
            "append": {
                "type": "boolean",
                "description": "Append ke file yang sudah ada (default: false = overwrite)",
                "default": False
            }
        },
        "required": ["file_path", "content"]
    }
)
async def file_write(file_path: str, content: str, append: bool = False) -> str:
    """
    Write content to file.

    Args:
        file_path: Path to file
        content: Content to write
        append: Whether to append or overwrite

    Returns:
        Success message
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

        action = "ditambahkan ke" if append else "ditulis ke"
        return f"Berhasil {action} file '{file_path}' ({len(content)} karakter)"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat tulis file: {str(e)}"


@registry.tool(
    name="file_delete",
    description="Hapus file. Aksi ini memerlukan konfirmasi.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file yang akan dihapus"
            }
        },
        "required": ["file_path"]
    }
)
async def file_delete(file_path: str) -> str:
    """
    Delete a file.

    Args:
        file_path: Path to file

    Returns:
        Deletion result
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        if path.is_file():
            path.unlink()
            return f"File '{file_path}' berhasil dihapus"
        elif path.is_dir():
            shutil.rmtree(path)
            return f"Direktori '{file_path}' berhasil dihapus"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat hapus file: {str(e)}"


@registry.tool(
    name="file_move",
    description="Pindahkan atau rename file.",
    input_schema={
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Path file sumber"
            },
            "destination": {
                "type": "string",
                "description": "Path tujuan"
            }
        },
        "required": ["source", "destination"]
    }
)
async def file_move(source: str, destination: str) -> str:
    """
    Move or rename a file.

    Args:
        source: Source path
        destination: Destination path

    Returns:
        Move result
    """
    try:
        src_path = _validate_path(source, WORKSPACE_DIR)
        dst_path = _validate_path(destination, WORKSPACE_DIR)

        if not src_path.exists():
            return f"File sumber tidak ditemukan: {source}"

        # Create destination directory if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))

        return f"Berhasil memindahkan '{source}' ke '{destination}'"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat pindah file: {str(e)}"


@registry.tool(
    name="file_info",
    description="Dapatkan informasi detail tentang file.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file"
            }
        },
        "required": ["file_path"]
    }
)
async def file_info(file_path: str) -> str:
    """
    Get file information.

    Args:
        file_path: Path to file

    Returns:
        File information
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        stat = path.stat()

        # Format size
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"

        info = f"""Informasi file '{file_path}':

📁 Nama: {path.name}
📍 Lokasi: {path.parent}
📊 Ukuran: {size_str}
📅 Dibuat: {datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")}
📝 Dimodifikasi: {datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")}
🔒 Tipe: {'Direktori' if path.is_dir() else 'File'}
"""
        return info

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat ambil info file: {str(e)}"