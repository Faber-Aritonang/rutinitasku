"""
RutinitasKu - PDF Reader Tool
Read and extract text content from PDF files.
"""

import asyncio
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from config import WORKSPACE_DIR
from .registry import registry
from .file_manager import _validate_path


@registry.tool(
    name="pdf_read",
    description="Baca dan ekstrak teks dari file PDF. Bisa membaca halaman tertentu atau seluruh dokumen.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file PDF yang akan dibaca"
            },
            "pages": {
                "type": "string",
                "description": "Halaman yang akan dibaca (contoh: '1-5', '3', '1,3,5'). Kosong = semua halaman."
            },
            "max_chars": {
                "type": "integer",
                "description": "Maksimal karakter yang dikembalikan (default: 10000)",
                "default": 10000
            }
        },
        "required": ["file_path"]
    }
)
async def pdf_read(
    file_path: str,
    pages: str = None,
    max_chars: int = 10000
) -> str:
    """
    Read text content from a PDF file.

    Args:
        file_path: Path to PDF file
        pages: Page range (e.g., '1-5', '3', '1,3,5')
        max_chars: Maximum characters to return

    Returns:
        Extracted text content
    """
    if PdfReader is None:
        return "Error: PyPDF2 tidak terinstall. Jalankan: pip install PyPDF2"

    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        if not path.suffix.lower() == ".pdf":
            return f"File bukan PDF: {file_path}"

        # Read PDF in thread to avoid blocking
        def _read_pdf():
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)

            # Parse page numbers
            page_numbers = []
            if pages:
                for part in pages.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-", 1)
                        start = max(1, int(start))
                        end = min(total_pages, int(end))
                        page_numbers.extend(range(start - 1, end))
                    else:
                        page_num = int(part) - 1
                        if 0 <= page_num < total_pages:
                            page_numbers.append(page_num)
            else:
                page_numbers = list(range(total_pages))

            # Extract text from selected pages
            text_parts = []
            for page_num in page_numbers:
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- Halaman {page_num + 1} ---\n{page_text}")

            return "\n".join(text_parts), total_pages

        text, total_pages = await asyncio.to_thread(_read_pdf)

        if not text.strip():
            return f"PDF '{file_path}' tidak mengandung teks yang bisa diekstrak ({total_pages} halaman)."

        # Format result
        result = f"📄 PDF: {file_path}\n"
        result += f"📊 Total halaman: {total_pages}\n"
        if pages:
            result += f"📑 Halaman dibaca: {pages}\n"
        result += f"{'=' * 50}\n"
        result += text

        # Truncate if too long
        if len(result) > max_chars:
            result = result[:max_chars] + f"\n\n[... konten dipotong, total {len(result)} karakter]"

        return result

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat baca PDF: {str(e)}"


@registry.tool(
    name="pdf_info",
    description="Dapatkan informasi tentang file PDF (jumlah halaman, metadata).",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file PDF"
            }
        },
        "required": ["file_path"]
    }
)
async def pdf_info(file_path: str) -> str:
    """
    Get PDF file information.

    Args:
        file_path: Path to PDF file

    Returns:
        PDF metadata and info
    """
    if PdfReader is None:
        return "Error: PyPDF2 tidak terinstall. Jalankan: pip install PyPDF2"

    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        if not path.suffix.lower() == ".pdf":
            return f"File bukan PDF: {file_path}"

        def _get_info():
            reader = PdfReader(str(path))
            info = reader.metadata
            total_pages = len(reader.pages)

            result = f"Informasi PDF '{file_path}':\n\n"
            result += f"📄 Jumlah halaman: {total_pages}\n"

            if info:
                if info.title:
                    result += f"📋 Judul: {info.title}\n"
                if info.author:
                    result += f"👤 Penulis: {info.author}\n"
                if info.subject:
                    result += f"📝 Subjek: {info.subject}\n"
                if info.creator:
                    result += f"🔧 Creator: {info.creator}\n"

            # Size
            size = path.stat().st_size
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            result += f"📊 Ukuran: {size_str}\n"

            return result

        return await asyncio.to_thread(_get_info)

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat ambil info PDF: {str(e)}"