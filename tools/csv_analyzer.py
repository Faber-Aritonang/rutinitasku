"""
RutinitasKu - CSV/Excel Analyzer Tool
Data analysis for tabular files.
"""

import pandas as pd
from pathlib import Path

from config import WORKSPACE_DIR
from .registry import registry
from .file_manager import _validate_path


@registry.tool(
    name="csv_analyze",
    description="Analisis file CSV/Excel. Tampilkan statistik deskriptif, sample data, dan informasi kolom.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file CSV atau Excel"
            },
            "sheet_name": {
                "type": "string",
                "description": "Nama sheet untuk Excel (default: sheet pertama)"
            }
        },
        "required": ["file_path"]
    }
)
async def csv_analyze(file_path: str, sheet_name: str = None) -> str:
    """
    Analyze CSV/Excel file and provide statistics.

    Args:
        file_path: Path to CSV/Excel file
        sheet_name: Sheet name for Excel files

    Returns:
        Analysis results
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        # Read file based on extension
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(path, sheet_name=sheet_name)
        else:
            return f"Format file tidak didukung: {ext}. Gunakan CSV atau Excel."

        # Basic info
        rows, cols = df.shape

        result = f"📊 Analisis file '{file_path}'\n"
        result += f"{'=' * 50}\n\n"
        result += f"📋 Informasi Dasar:\n"
        result += f"   - Jumlah baris: {rows:,}\n"
        result += f"   - Jumlah kolom: {cols}\n"
        result += f"   - Tipe file: {ext.upper()}\n\n"

        # Column info
        result += f"📝 Informasi Kolom:\n"
        for col in df.columns:
            dtype = df[col].dtype
            non_null = df[col].count()
            null_count = df[col].isnull().sum()
            result += f"   - {col}: {dtype} ({non_null:,} non-null, {null_count:,} null)\n"
        result += "\n"

        # Sample data
        result += f"📄 Sample Data (5 baris pertama):\n"
        result += df.head().to_string() + "\n\n"

        # Descriptive statistics for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            result += f"📈 Statistik Deskriptif (Kolom Numerik):\n"
            stats = df[numeric_cols].describe()
            result += stats.to_string() + "\n\n"

        # Value counts for categorical columns (top 5)
        cat_cols = df.select_dtypes(include=["object"]).columns
        if len(cat_cols) > 0:
            result += f"🏷️ Distribusi Kolom Kategorikal (Top 5):\n"
            for col in cat_cols[:5]:  # Limit to 5 categorical columns
                value_counts = df[col].value_counts().head()
                result += f"\n   {col}:\n"
                for value, count in value_counts.items():
                    result += f"      {value}: {count:,}\n"

        return result

    except Exception as e:
        return f"Error saat analisis CSV: {str(e)}"


@registry.tool(
    name="csv_query",
    description="Query data CSV/Excel dengan filter, grouping, dan aggregasi.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path file CSV atau Excel"
            },
            "query": {
                "type": "string",
                "description": "Query pandas (contoh: 'kolom_a > 100')"
            },
            "group_by": {
                "type": "string",
                "description": "Kolom untuk grouping"
            },
            "aggregate": {
                "type": "string",
                "description": "Fungsi aggregasi (sum, mean, count, min, max)"
            },
            "sort_by": {
                "type": "string",
                "description": "Kolom untuk sorting"
            },
            "ascending": {
                "type": "boolean",
                "description": "Sorting ascending (default: false)",
                "default": False
            },
            "limit": {
                "type": "integer",
                "description": "Batas hasil (default: 20)",
                "default": 20
            }
        },
        "required": ["file_path"]
    }
)
async def csv_query(
    file_path: str,
    query: str = None,
    group_by: str = None,
    aggregate: str = None,
    sort_by: str = None,
    ascending: bool = False,
    limit: int = 20
) -> str:
    """
    Query CSV/Excel data with filters and aggregations.

    Args:
        file_path: Path to file
        query: Filter query
        group_by: Column to group by
        aggregate: Aggregation function
        sort_by: Column to sort by
        ascending: Sort order
        limit: Result limit

    Returns:
        Query results
    """
    try:
        path = _validate_path(file_path, WORKSPACE_DIR)

        if not path.exists():
            return f"File tidak ditemukan: {file_path}"

        # Read file
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        else:
            return f"Format file tidak didukung: {ext}"

        # Apply filter
        if query:
            try:
                df = df.query(query)
            except Exception as e:
                return f"Error dalam query: {str(e)}"

        # Apply grouping and aggregation
        if group_by:
            if group_by not in df.columns:
                return f"Kolom '{group_by}' tidak ditemukan"

            if aggregate:
                agg_func = aggregate.lower()
                if agg_func in ["sum", "mean", "count", "min", "max", "median", "std"]:
                    df = df.groupby(group_by).agg(agg_func).reset_index()
                else:
                    return f"Fungsi aggregasi tidak valid: {aggregate}"
            else:
                df = df.groupby(group_by).size().reset_index(name="count")

        # Apply sorting
        if sort_by:
            if sort_by not in df.columns:
                return f"Kolom '{sort_by}' tidak ditemukan"
            df = df.sort_values(sort_by, ascending=ascending)

        # Apply limit
        df = df.head(limit)

        # Format result
        result = f"🔍 Hasil Query:\n"
        result += f"   - Filter: {query or 'Tidak ada'}\n"
        result += f"   - Group by: {group_by or 'Tidak ada'}\n"
        result += f"   - Aggregasi: {aggregate or 'Tidak ada'}\n"
        result += f"   - Jumlah hasil: {len(df)}\n\n"
        result += df.to_string()

        return result

    except Exception as e:
        return f"Error saat query: {str(e)}"


@registry.tool(
    name="csv_export",
    description="Export hasil query/analisis ke file CSV baru.",
    input_schema={
        "type": "object",
        "properties": {
            "source_file": {
                "type": "string",
                "description": "Path file sumber"
            },
            "output_file": {
                "type": "string",
                "description": "Path file output"
            },
            "query": {
                "type": "string",
                "description": "Filter query (opsional)"
            },
            "columns": {
                "type": "string",
                "description": "Kolom yang dipisahkan koma (opsional)"
            }
        },
        "required": ["source_file", "output_file"]
    }
)
async def csv_export(
    source_file: str,
    output_file: str,
    query: str = None,
    columns: str = None
) -> str:
    """
    Export filtered data to new CSV file.

    Args:
        source_file: Source file path
        output_file: Output file path
        query: Filter query
        columns: Comma-separated column names

    Returns:
        Export result
    """
    try:
        src_path = _validate_path(source_file, WORKSPACE_DIR)
        out_path = _validate_path(output_file, WORKSPACE_DIR)

        if not src_path.exists():
            return f"File sumber tidak ditemukan: {source_file}"

        # Read source file
        ext = src_path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(src_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(src_path)
        else:
            return f"Format file tidak didukung: {ext}"

        # Apply filter
        if query:
            df = df.query(query)

        # Select columns
        if columns:
            col_list = [c.strip() for c in columns.split(",")]
            missing = [c for c in col_list if c not in df.columns]
            if missing:
                return f"Kolom tidak ditemukan: {', '.join(missing)}"
            df = df[col_list]

        # Create output directory if needed
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export to CSV
        df.to_csv(out_path, index=False)

        return f"Berhasil export {len(df)} baris ke '{output_file}'"

    except Exception as e:
        return f"Error saat export: {str(e)}"