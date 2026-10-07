"""
NaraTask AI - Web Search Tool
DuckDuckGo-based web search integration.
"""

from duckduckgo_search import DDGS
from .registry import registry


@registry.tool(
    name="web_search",
    description="Cari informasi di internet menggunakan DuckDuckGo. Mengembalikan top results dengan title, URL, dan snippet.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Kata kunci pencarian"
            },
            "max_results": {
                "type": "integer",
                "description": "Jumlah hasil maksimal (default: 5)",
                "default": 5
            },
            "region": {
                "type": "string",
                "description": "Region pencarian (wt-w untuk global, id-id untuk Indonesia)",
                "default": "wt-w"
            }
        },
        "required": ["query"]
    }
)
async def web_search(query: str, max_results: int = 5, region: str = "wt-w") -> str:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum number of results
        region: Search region

    Returns:
        Formatted search results
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                region=region,
                max_results=max_results
            ))

        if not results:
            return f"Tidak ditemukan hasil untuk: '{query}'"

        # Format results
        formatted = f"Hasil pencarian untuk: '{query}'\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"**{i}. {result['title']}**\n"
            formatted += f"   URL: {result['href']}\n"
            formatted += f"   {result['body']}\n\n"

        return formatted

    except Exception as e:
        return f"Error saat pencarian: {str(e)}"


@registry.tool(
    name="web_news",
    description="Cari berita terbaru di internet.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topik berita yang dicari"
            },
            "max_results": {
                "type": "integer",
                "description": "Jumlah hasil maksimal (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
)
async def web_news(query: str, max_results: int = 5) -> str:
    """
    Search for recent news.

    Args:
        query: News topic
        max_results: Maximum results

    Returns:
        Formatted news results
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(
                query,
                region="wt-w",
                max_results=max_results
            ))

        if not results:
            return f"Tidak ditemukan berita untuk: '{query}'"

        formatted = f"Berita terbaru untuk: '{query}'\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"**{i}. {result['title']}**\n"
            formatted += f"   Sumber: {result['source']} | Tanggal: {result['date']}\n"
            formatted += f"   URL: {result['url']}\n"
            formatted += f"   {result['body']}\n\n"

        return formatted

    except Exception as e:
        return f"Error saat pencarian berita: {str(e)}"